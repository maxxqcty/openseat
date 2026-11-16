"""On-call worker for OpenSeat.

The worker polls Grafana Alerting for active page-severity alerts, turns the
first unseen alert into an evidence packet, creates an isolated git worktree,
and runs a headless coding agent against it. The agent may open a draft pull
request; a human always reviews and merges it.

State, worktrees, packets, and transcripts live outside the repository by
default (``~/.openseat/on-call``). Run it with ``make on-call``.

The agent environment is an allowlist. It never receives the Render API key,
the Grafana token, the database URL, the session secret, or OTLP headers. Only
``ON_CALL_GITHUB_TOKEN`` (a fine-grained token for this repository) and the
model keys named in ``ON_CALL_AGENT_ENV`` are passed through.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import json
import logging
import os
import re
import shlex
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from app.telemetry import redact_text, redact_value

LOGGER = logging.getLogger("openseat.on-call")

DEFAULT_STATE_DIR = Path.home() / ".openseat" / "on-call"
DEFAULT_AGENT_CMD = (
    "opencode run --agent build --file {prompt_file} "
    '"Follow the attached on-call brief. Work only in this worktree. '
    "Do not merge, deploy, change .github/workflows, or read production secrets.\""
)
PROTECTED_PREFIXES = (
    ".github/",
    "deploy/",
    "on-call/",
    "observability/",
    "render.yaml",
)
PR_URL_RE = re.compile(r"https://github\.com/[^\s/]+/[^\s/]+/pull/\d+")
EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
METRIC_QUERIES = {
    "open_seat_with_waitlist": (
        'max(openseat_open_seat_with_waitlist{environment="%s"})'
    ),
    "overbooked_sessions": 'max(openseat_overbooked_sessions{environment="%s"})',
    "http_5xx_ratio": (
        "sum(rate(openseat_http_requests_total"
        '{environment="%s",status=~"5.."}[5m])) / clamp_min('
        "sum(rate(openseat_http_requests_total"
        '{environment="%s"}[5m])), 0.000001)'
    ),
    "booking_error_rate": (
        "sum(rate(openseat_bookings_total"
        '{environment="%s",result="error"}[5m]))'
    ),
}
SAFE_ENV_KEYS = (
    "PATH",
    "HOME",
    "USERPROFILE",
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "TMPDIR",
    "LANG",
    "LC_ALL",
    "SHELL",
    "APPDATA",
    "LOCALAPPDATA",
    "PROGRAMDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
)


class AlertSource(Protocol):
    """Fetch raw alerts from Grafana or a test double."""

    def fetch(self) -> list[dict[str, Any]]: ...


class MetricSource(Protocol):
    """Read current metric values for the evidence packet."""

    def values(self, environment: str) -> dict[str, float | None]: ...


class AgentRunner(Protocol):
    """Run the configured coding agent and capture its transcript."""

    def __call__(
        self,
        command: Sequence[str],
        *,
        cwd: Path,
        env: Mapping[str, str],
        timeout_seconds: int,
        transcript_path: Path,
    ) -> AgentOutcome: ...


@dataclass(frozen=True)
class Alert:
    """A normalised Grafana alert."""

    fingerprint: str
    name: str
    state: str
    labels: dict[str, str]
    annotations: dict[str, str]
    starts_at: str
    ends_at: str
    raw: dict[str, Any]

    @property
    def is_active(self) -> bool:
        return self.state.lower() == "active"

    def is_page_for(self, environment: str) -> bool:
        return (
            self.labels.get("severity") == "page"
            and self.labels.get("environment") == environment
        )


@dataclass
class AgentOutcome:
    """The result of one agent process."""

    returncode: int | None
    timed_out: bool
    transcript_path: Path


@dataclass
class RunRecord:
    """One worker attempt, stored in the state file and printed in dry-run."""

    run_id: str
    fingerprint: str
    alert: str
    status: str
    started_at: str
    finished_at: str = ""
    branch: str = ""
    pr_url: str = ""
    packet: str = ""
    prompt: str = ""
    transcript: str = ""
    reason: str = ""

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "fingerprint": self.fingerprint,
            "alert": self.alert,
            "status": self.status,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "branch": self.branch,
            "pr_url": self.pr_url,
            "packet": self.packet,
            "prompt": self.prompt,
            "transcript": self.transcript,
            "reason": self.reason,
        }


@dataclass
class WorkerState:
    """Deduplication state and run history, persisted as JSON."""

    seen: dict[str, dict[str, Any]] = field(default_factory=dict)
    runs: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class WorkerConfig:
    """Configuration read from the environment or the command line."""

    grafana_url: str
    grafana_token: str
    environment: str
    state_dir: Path
    repo_root: Path
    agent_cmd: str = DEFAULT_AGENT_CMD
    timeout_seconds: int = 1200
    poll_seconds: int = 60
    dry_run: bool = False
    once: bool = False
    log_file: Path | None = None
    prometheus_url: str = ""

    def validate(self) -> None:
        if self.timeout_seconds <= 0:
            raise ValueError("ON_CALL_TIMEOUT_SECONDS must be positive")
        if self.poll_seconds < 1:
            raise ValueError("ON_CALL_POLL_SECONDS must be at least 1")
        state = self.state_dir.resolve()
        repo = self.repo_root.resolve()
        if state == repo or repo in state.parents:
            raise ValueError(
                "ON_CALL_STATE_DIR must be outside the repository; "
                "the packet and transcript are not committed",
            )
        if "{prompt_file}" not in self.agent_cmd:
            raise ValueError("ON_CALL_AGENT_CMD must contain {prompt_file}")


def utc_now() -> datetime:
    return datetime.now(tz=UTC)


def iso_now() -> str:
    return utc_now().isoformat()


def parse_alert(raw: Mapping[str, Any]) -> Alert | None:
    """Normalise one Grafana alert, or return ``None`` when it is malformed."""
    labels = {str(key): str(value) for key, value in (raw.get("labels") or {}).items()}
    annotations = {
        str(key): str(value)
        for key, value in (raw.get("annotations") or {}).items()
    }
    status = raw.get("status") or {}
    state = ""
    if isinstance(status, Mapping):
        state = str(status.get("state") or "")
    state = state or str(raw.get("state") or "")
    fingerprint = str(raw.get("fingerprint") or "")
    if not fingerprint:
        digest = hashlib.sha256(
            json.dumps(
                {"labels": labels, "annotations": annotations},
                sort_keys=True,
            ).encode("utf-8"),
        ).hexdigest()
        fingerprint = digest[:16]
    name = labels.get("alertname") or str(raw.get("name") or "OpenSeatAlert")
    return Alert(
        fingerprint=fingerprint,
        name=name,
        state=state,
        labels=labels,
        annotations=annotations,
        starts_at=str(raw.get("startsAt") or ""),
        ends_at=str(raw.get("endsAt") or ""),
        raw=dict(raw),
    )


def load_state(state_dir: Path) -> WorkerState:
    path = state_dir / "state.json"
    if not path.exists():
        return WorkerState()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        LOGGER.warning("state_unreadable", extra={"path": str(path)})
        return WorkerState()
    return WorkerState(
        seen=dict(data.get("seen") or {}),
        runs=list(data.get("runs") or []),
    )


def save_state(state_dir: Path, state: WorkerState) -> None:
    state_dir.mkdir(parents=True, exist_ok=True)
    path = state_dir / "state.json"
    temporary = path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(
            {"seen": state.seen, "runs": state.runs},
            indent=2,
            sort_keys=True,
        ),
        encoding="utf-8",
    )
    temporary.replace(path)


def run_git(repo: Path, arguments: Sequence[str], *, check: bool = True) -> str:
    completed = subprocess.run(
        ["git", *arguments],
        cwd=repo,
        check=check,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    return completed.stdout.strip()


def resolve_base(repo_root: Path) -> str:
    for candidate in ("origin/main", "main", "HEAD"):
        if run_git(repo_root, ["rev-parse", "--verify", candidate], check=False):
            return candidate
    raise RuntimeError("the repository has no main branch or commits")


def collect_recent_commits(repo_root: Path, limit: int = 10) -> list[str]:
    output = run_git(
        repo_root,
        ["log", f"-{limit}", "--oneline", "--no-decorate"],
        check=False,
    )
    return [line for line in output.splitlines() if line.strip()]


def read_logs(log_file: Path | None, limit: int = 100) -> dict[str, Any]:
    if log_file is None:
        return {
            "source": "",
            "lines": [],
            "note": "ON_CALL_LOG_FILE is not configured",
        }
    try:
        lines = log_file.read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError as exc:
        return {"source": str(log_file), "lines": [], "note": str(exc)}
    return {"source": str(log_file), "lines": lines[-limit:]}


def build_evidence_packet(
    *,
    alert: Alert,
    config: WorkerConfig,
    metrics: Mapping[str, float | None],
    commits: Sequence[str],
    logs: Mapping[str, Any],
    run_id: str,
    base: str,
) -> dict[str, Any]:
    """Build a redacted packet with everything the agent needs to reproduce."""
    version = (
        alert.labels.get("version")
        or alert.annotations.get("version")
        or run_git(config.repo_root, ["rev-parse", "--short", "HEAD"], check=False)
    )
    packet: dict[str, Any] = {
        "run_id": run_id,
        "created_at": iso_now(),
        "alert": {
            "alertname": alert.name,
            "fingerprint": alert.fingerprint,
            "state": alert.state,
            "starts_at": alert.starts_at,
            "ends_at": alert.ends_at,
        },
        "labels": alert.labels,
        "annotations": alert.annotations,
        "environment": config.environment,
        "version": version,
        "dashboard_url": alert.annotations.get("dashboard_url", ""),
        "runbook_url": alert.annotations.get("runbook_url", ""),
        "metrics": dict(metrics),
        "recent_commits": list(commits),
        "logs": dict(logs),
        "repository": {
            "root": str(config.repo_root),
            "base": base,
        },
    }
    redacted = redact_value(packet)
    assert isinstance(redacted, dict)
    return redacted


def build_prompt(
    *,
    packet_path: Path,
    branch: str,
    alert: Alert,
    environment: str,
) -> str:
    """Prompt the agent with a fixed reproduction and verification workflow."""
    return f"""You are the OpenSeat on-call coding agent.

An alert is firing in the {environment} environment:

- Alert: {alert.name}
- Fingerprint: {alert.fingerprint}

The full evidence packet is at:

    {packet_path}

Read it first. It contains the alert labels and annotations, the deployed
version, current metric values, recent commits, and sanitised log excerpts.

Required workflow:

1. Reproduce the failure described by the alert in an automated test. Do not
   guess: use the packet, the repository, and the failing signal.
2. Add a regression test that fails for the current code.
3. Fix the root cause with the smallest change that keeps the existing
   invariants (never overbook; never leave a free seat while someone waits).
4. Run `cd backend && uv run pytest` and any focused tests. Every test must
   pass. Keep `uv run ruff check .` and `uv run mypy app` clean.
5. Commit the test and the fix on the current branch: {branch}
6. Push the branch and open a draft pull request with `gh pr create --draft`.
   Include the alert name, the reproduction, the fix, and the verification
   commands in the pull request body.

Hard constraints:

- Do not merge, deploy, or change production data.
- Do not edit `.github/`, `render.yaml`, `deploy/`, `on-call/`, or
  `observability/`. The worker rejects such changes.
- Do not read or print production secrets. The environment is allowlisted.
- Do not weaken or delete existing tests to make the suite pass.
- If the bug cannot be reproduced, stop and explain why in the transcript
  instead of committing a speculative fix.
"""


def slug(value: str) -> str:
    cleaned = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return cleaned or "alert"


def build_command(template: str, *, prompt_file: Path, worktree: Path) -> list[str]:
    parts = shlex.split(template)
    return [
        part.replace("{prompt_file}", str(prompt_file)).replace(
            "{worktree}",
            str(worktree),
        )
        for part in parts
    ]


def build_agent_env(source: Mapping[str, str] | None = None) -> dict[str, str]:
    """Return an allowlisted environment for the agent process.

    The operator's shell may contain Render, Grafana, and database secrets.
    None of them are passed through. A fine-grained GitHub token must be
    supplied separately as ``ON_CALL_GITHUB_TOKEN``.
    """
    environment = source or os.environ
    agent_env = {
        key: environment[key]
        for key in SAFE_ENV_KEYS
        if key in environment
    }
    token = environment.get("ON_CALL_GITHUB_TOKEN", "")
    if token:
        agent_env["GH_TOKEN"] = token
        agent_env["GITHUB_TOKEN"] = token
    extra = environment.get("ON_CALL_AGENT_ENV", "")
    for key in (part.strip() for part in extra.split(",")):
        if key and key in environment:
            agent_env[key] = environment[key]
    agent_env.update(
        {
            "GIT_TERMINAL_PROMPT": "0",
            "GH_PROMPT_DISABLED": "1",
            "CI": "1",
        },
    )
    return agent_env


def create_worktree(
    repo_root: Path,
    worktree_path: Path,
    branch: str,
) -> str:
    """Create an isolated worktree on a new branch and return the base ref."""
    base = resolve_base(repo_root)
    if worktree_path.exists():
        raise FileExistsError(worktree_path)
    worktree_path.parent.mkdir(parents=True, exist_ok=True)
    run_git(repo_root, ["worktree", "add", "--detach", str(worktree_path), base])
    run_git(worktree_path, ["switch", "-c", branch])
    return base


def read_branch(worktree: Path) -> str:
    return run_git(worktree, ["rev-parse", "--abbrev-ref", "HEAD"], check=False)


def find_pr_url(transcript_path: Path) -> str:
    try:
        text = transcript_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return ""
    matches = PR_URL_RE.findall(text)
    return matches[-1] if matches else ""


def protected_changes(worktree: Path, base: str) -> list[str]:
    """Return changed paths that the agent is not allowed to touch.

    ``git diff`` sees committed and unstaged edits; ``git status`` adds
    untracked files, so a new workflow file is rejected before any push.
    """
    changed: list[str] = []
    diff = run_git(worktree, ["diff", "--name-only", base], check=False)
    changed.extend(line.strip() for line in diff.splitlines() if line.strip())
    status = run_git(worktree, ["status", "--porcelain", "-uall"], check=False)
    for line in status.splitlines():
        path = line[3:].strip()
        if " -> " in path:
            path = path.split(" -> ", 1)[1]
        if path:
            changed.append(path)
    return [
        path
        for path in changed
        if any(path == prefix or path.startswith(prefix) for prefix in PROTECTED_PREFIXES)
    ]


def _terminate_tree(process: subprocess.Popen[str]) -> None:
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/F", "/T", "/PID", str(process.pid)],
            capture_output=True,
            check=False,
        )
        return
    try:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait(timeout=5)
    except (ProcessLookupError, subprocess.TimeoutExpired):
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGKILL)


def run_agent(
    command: Sequence[str],
    *,
    cwd: Path,
    env: Mapping[str, str],
    timeout_seconds: int,
    transcript_path: Path,
) -> AgentOutcome:
    """Run the agent, capture stdout/stderr, and enforce the timeout."""
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    popen_kwargs: dict[str, Any] = {}
    if os.name == "nt":
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        popen_kwargs["start_new_session"] = True

    with transcript_path.open("w", encoding="utf-8", errors="replace") as transcript:
        transcript.write(f"$ {redact_text(shlex.join(command))}\n\n")
        transcript.flush()
        process = subprocess.Popen(
            list(command),
            cwd=cwd,
            env=dict(env),
            stdin=subprocess.DEVNULL,
            stdout=transcript,
            stderr=subprocess.STDOUT,
            text=True,
            **popen_kwargs,
        )
        try:
            returncode = process.wait(timeout=timeout_seconds)
            timed_out = False
        except subprocess.TimeoutExpired:
            _terminate_tree(process)
            returncode = None
            timed_out = True
            transcript.write(
                f"\n[worker] agent timed out after {timeout_seconds} seconds\n",
            )
    return AgentOutcome(
        returncode=returncode,
        timed_out=timed_out,
        transcript_path=transcript_path,
    )


class GrafanaAlertSource:
    """Fetch active alerts from Grafana's Alertmanager-compatible API."""

    def __init__(self, base_url: str, token: str, *, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def fetch(self) -> list[dict[str, Any]]:
        query = urllib.parse.urlencode(
            {
                "active": "true",
                "silenced": "false",
                "inhibited": "false",
                "unprocessed": "false",
                "filter": "severity=page",
            },
        )
        request = urllib.request.Request(
            f"{self.base_url}/api/alertmanager/grafana/api/v2/alerts?{query}",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/json",
                "User-Agent": "openseat-on-call",
            },
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            alerts = payload.get("alerts") or payload.get("data") or []
            if isinstance(alerts, dict):
                alerts = alerts.get("alerts") or []
            return [item for item in alerts if isinstance(item, dict)]
        return []


class PrometheusMetricSource:
    """Read current metric values from the Prometheus HTTP API."""

    def __init__(self, base_url: str, token: str = "", *, timeout: int = 20) -> None:
        self.base_url = base_url.rstrip("/")
        self.token = token
        self.timeout = timeout

    def query(self, expression: str) -> float | None:
        query = urllib.parse.urlencode({"query": expression})
        headers = {
            "Accept": "application/json",
            "User-Agent": "openseat-on-call",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        request = urllib.request.Request(
            f"{self.base_url}/api/v1/query?{query}",
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
        results = payload.get("data", {}).get("result", [])
        if not results:
            return None
        try:
            return float(results[0]["value"][1])
        except (KeyError, IndexError, TypeError, ValueError):
            return None

    def values(self, environment: str) -> dict[str, float | None]:
        values: dict[str, float | None] = {}
        for name, template in METRIC_QUERIES.items():
            expression = template % ((environment,) * template.count("%s"))
            try:
                values[name] = self.query(expression)
            except (urllib.error.URLError, TimeoutError, json.JSONDecodeError):
                values[name] = None
        return values


class NullMetricSource:
    """Return no metrics when Prometheus is not configured."""

    def values(self, environment: str) -> dict[str, float | None]:
        return {name: None for name in METRIC_QUERIES}


class StaticAlertSource:
    """Read alerts from a JSON file for ``--dry-run`` demos and tests."""

    def __init__(self, path: Path) -> None:
        self.path = path

    def fetch(self) -> list[dict[str, Any]]:
        payload = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(payload, list):
            return [item for item in payload if isinstance(item, dict)]
        if isinstance(payload, dict):
            return [payload]
        return []


class Worker:
    """Poll alerts, deduplicate them, and run the agent once per fingerprint."""

    def __init__(
        self,
        config: WorkerConfig,
        *,
        alert_source: AlertSource,
        metric_source: MetricSource | None = None,
        runner: AgentRunner = run_agent,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        config.validate()
        self.config = config
        self.alert_source = alert_source
        self.metric_source = metric_source or NullMetricSource()
        self.runner = runner
        self.sleep = sleep
        self.state = load_state(config.state_dir)

    def poll_once(self) -> list[RunRecord]:
        alerts = self.alert_source.fetch()
        results: list[RunRecord] = []
        for raw in alerts:
            alert = parse_alert(raw)
            if alert is None:
                continue
            if not alert.is_active:
                self._mark_resolved(alert)
                continue
            if not alert.is_page_for(self.config.environment):
                continue
            if self._already_active(alert.fingerprint):
                LOGGER.info(
                    "alert_deduplicated",
                    extra={"fingerprint": alert.fingerprint, "alert": alert.name},
                )
                continue
            results.append(self.handle_alert(alert))
        save_state(self.config.state_dir, self.state)
        return results

    def run_forever(self) -> None:
        while True:
            try:
                self.poll_once()
            except Exception:  # pragma: no cover - keep the worker alive
                LOGGER.exception("poll_failed")
            if self.config.once:
                return
            self.sleep(self.config.poll_seconds)

    def _already_active(self, fingerprint: str) -> bool:
        entry = self.state.seen.get(fingerprint)
        return bool(entry and entry.get("status") == "active")

    def _mark_resolved(self, alert: Alert) -> None:
        entry = self.state.seen.get(alert.fingerprint)
        if entry and entry.get("status") != "resolved":
            entry["status"] = "resolved"
            entry["resolved_at"] = iso_now()
            LOGGER.info(
                "alert_resolved",
                extra={"fingerprint": alert.fingerprint, "alert": alert.name},
            )

    def handle_alert(self, alert: Alert) -> RunRecord:
        run_id = (
            f"{utc_now().strftime('%Y%m%d-%H%M%S')}-"
            f"{alert.fingerprint[:8]}-{uuid.uuid4().hex[:6]}"
        )
        branch = f"on-call/{slug(alert.name)}-{run_id}"
        run_dir = self.config.state_dir / "runs" / run_id
        worktree = self.config.state_dir / "worktrees" / run_id
        packet_path = run_dir / "packet.json"
        prompt_path = run_dir / "prompt.md"
        transcript_path = run_dir / "transcript.txt"

        base = resolve_base(self.config.repo_root)
        packet = build_evidence_packet(
            alert=alert,
            config=self.config,
            metrics=self.metric_source.values(self.config.environment),
            commits=collect_recent_commits(self.config.repo_root),
            logs=read_logs(self.config.log_file),
            run_id=run_id,
            base=base,
        )
        prompt = build_prompt(
            packet_path=packet_path,
            branch=branch,
            alert=alert,
            environment=self.config.environment,
        )
        command = build_command(
            self.config.agent_cmd,
            prompt_file=prompt_path,
            worktree=worktree,
        )
        record = RunRecord(
            run_id=run_id,
            fingerprint=alert.fingerprint,
            alert=alert.name,
            status="running",
            started_at=iso_now(),
            branch=branch,
            packet=str(packet_path),
            prompt=str(prompt_path),
            transcript=str(transcript_path),
        )

        if self.config.dry_run:
            print(json.dumps(packet, indent=2, sort_keys=True))
            print(f"worktree: {worktree}")
            print(f"branch: {branch}")
            print(f"agent command: {shlex.join(command)}")
            print(f"transcript: {transcript_path}")
            record.status = "dry_run"
            record.finished_at = iso_now()
            return record

        run_dir.mkdir(parents=True, exist_ok=True)
        packet_path.write_text(
            json.dumps(packet, indent=2, sort_keys=True),
            encoding="utf-8",
        )
        prompt_path.write_text(prompt, encoding="utf-8")

        try:
            create_worktree(self.config.repo_root, worktree, branch)
        except (OSError, RuntimeError, subprocess.CalledProcessError) as exc:
            record.status = "failed"
            record.reason = f"worktree creation failed: {exc}"
            record.finished_at = iso_now()
            self._remember(record)
            return record

        outcome = self.runner(
            command,
            cwd=worktree,
            env=build_agent_env(),
            timeout_seconds=self.config.timeout_seconds,
            transcript_path=transcript_path,
        )
        record.finished_at = iso_now()
        record.pr_url = find_pr_url(transcript_path)
        actual_branch = read_branch(worktree)
        if actual_branch and actual_branch != "HEAD":
            record.branch = actual_branch
        violations = protected_changes(worktree, base)
        if violations:
            record.status = "rejected"
            record.reason = "agent changed protected paths: " + ", ".join(violations)
        elif outcome.timed_out:
            record.status = "timed_out"
            record.reason = (
                f"agent exceeded the {self.config.timeout_seconds}-second timeout"
            )
        elif outcome.returncode != 0:
            record.status = "failed"
            record.reason = f"agent exited with code {outcome.returncode}"
        else:
            record.status = "succeeded"
        self._remember(record)
        return record

    def _remember(self, record: RunRecord) -> None:
        self.state.seen[record.fingerprint] = {
            "status": "active",
            "run_id": record.run_id,
            "run_status": record.status,
            "branch": record.branch,
            "pr_url": record.pr_url,
            "updated_at": record.finished_at,
        }
        self.state.runs.append(record.as_dict())
        save_state(self.config.state_dir, self.state)


def config_from_env(
    *,
    state_dir: Path | None = None,
    repo_root: Path | None = None,
    dry_run: bool = False,
    once: bool = False,
    log_file: Path | None = None,
) -> WorkerConfig:
    return WorkerConfig(
        grafana_url=os.environ.get("GRAFANA_URL", ""),
        grafana_token=os.environ.get("GRAFANA_TOKEN", ""),
        environment=os.environ.get("ON_CALL_ENVIRONMENT", "production"),
        state_dir=state_dir
        or Path(os.environ.get("ON_CALL_STATE_DIR", DEFAULT_STATE_DIR)),
        repo_root=repo_root or Path(__file__).resolve().parents[1],
        agent_cmd=os.environ.get("ON_CALL_AGENT_CMD", DEFAULT_AGENT_CMD),
        timeout_seconds=int(os.environ.get("ON_CALL_TIMEOUT_SECONDS", "1200")),
        poll_seconds=int(os.environ.get("ON_CALL_POLL_SECONDS", "60")),
        dry_run=dry_run,
        once=once,
        log_file=log_file
        or (
            Path(os.environ["ON_CALL_LOG_FILE"])
            if os.environ.get("ON_CALL_LOG_FILE")
            else None
        ),
        prometheus_url=os.environ.get("GRAFANA_PROMETHEUS_URL", ""),
    )


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Poll Grafana alerts and run a coding agent on a fix.",
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="poll once and exit instead of looping every 60 seconds",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the packet and agent command without creating a worktree",
    )
    parser.add_argument(
        "--alert-file",
        type=Path,
        help="read alerts from JSON instead of Grafana (useful with --dry-run)",
    )
    parser.add_argument("--state-dir", type=Path, help="override ON_CALL_STATE_DIR")
    parser.add_argument("--repo-root", type=Path, help="override the repository root")
    parser.add_argument("--log-file", type=Path, help="tail this file for log excerpts")
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )
    args = parse_args(argv)
    config = config_from_env(
        state_dir=args.state_dir,
        repo_root=args.repo_root,
        dry_run=args.dry_run,
        once=args.once or args.dry_run,
        log_file=args.log_file,
    )
    try:
        config.validate()
    except ValueError as exc:
        print(f"configuration error: {exc}", file=sys.stderr)
        return 2

    if args.alert_file:
        alert_source: AlertSource = StaticAlertSource(args.alert_file)
    elif config.grafana_url and config.grafana_token:
        alert_source = GrafanaAlertSource(config.grafana_url, config.grafana_token)
    else:
        print(
            "GRAFANA_URL and GRAFANA_TOKEN are required (or pass --alert-file).",
            file=sys.stderr,
        )
        return 2

    metric_source: MetricSource
    if config.prometheus_url:
        metric_source = PrometheusMetricSource(
            config.prometheus_url,
            config.grafana_token,
        )
    else:
        metric_source = NullMetricSource()

    worker = Worker(
        config,
        alert_source=alert_source,
        metric_source=metric_source,
    )
    try:
        worker.run_forever()
    except KeyboardInterrupt:
        print("on-call worker stopped", file=sys.stderr)
        return 130
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
