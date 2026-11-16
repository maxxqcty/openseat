"""Unit tests for the on-call worker, packet redaction, and chaos helper."""

from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
WORKER_PATH = ROOT / "on-call" / "worker.py"
CHAOS_PATH = ROOT / "on-call" / "chaos.py"


def _load(path: Path, name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


worker = _load(WORKER_PATH, "oncall_worker")
chaos = _load(CHAOS_PATH, "oncall_chaos")


class FakeAlerts:
    def __init__(self, alerts: list[dict[str, Any]]) -> None:
        self.alerts = alerts

    def fetch(self) -> list[dict[str, Any]]:
        return self.alerts


class FakeMetrics:
    def values(self, environment: str) -> dict[str, float | None]:
        return {
            "open_seat_with_waitlist": 1.0,
            "overbooked_sessions": 0.0,
            "http_5xx_ratio": 0.0,
            "booking_error_rate": 0.0,
        }


def make_alert(
    *,
    state: str = "active",
    fingerprint: str = "fingerprint-abc12345",
    labels: dict[str, str] | None = None,
    annotations: dict[str, str] | None = None,
) -> dict[str, Any]:
    merged_labels = {
        "alertname": "OpenSeatWaitlistStalled",
        "severity": "page",
        "environment": "production",
        "owner": "backend",
        "version": "v1.2.3",
    }
    merged_labels.update(labels or {})
    merged_annotations = {
        "summary": "A free seat exists while someone is waiting",
        "description": "The open-seat-with-waitlist gauge stayed above zero.",
        "dashboard_url": "https://example.grafana.net/d/openseat-main",
        "runbook_url": "https://github.com/maxxqcty/openseat/blob/main/_docs/runbook.md",
    }
    merged_annotations.update(annotations or {})
    return {
        "fingerprint": fingerprint,
        "status": {"state": state},
        "labels": merged_labels,
        "annotations": merged_annotations,
        "startsAt": "2026-11-01T10:00:00Z",
        "endsAt": "2026-11-01T11:00:00Z",
    }


def make_runner(
    calls: list[dict[str, Any]],
    *,
    code: int = 0,
    transcript: str = "",
    touch_workflow: bool = False,
) -> Any:
    def runner(
        command: Any,
        *,
        cwd: Path,
        env: dict[str, str],
        timeout_seconds: int,
        transcript_path: Path,
    ) -> Any:
        calls.append(
            {
                "command": list(command),
                "cwd": cwd,
                "env": dict(env),
                "timeout_seconds": timeout_seconds,
            },
        )
        if touch_workflow:
            path = Path(cwd) / ".github" / "workflows" / "ci.yml"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("name: injected\n", encoding="utf-8")
        transcript_path.parent.mkdir(parents=True, exist_ok=True)
        transcript_path.write_text(transcript, encoding="utf-8")
        return worker.AgentOutcome(
            returncode=code,
            timed_out=False,
            transcript_path=transcript_path,
        )

    return runner


def make_config(
    repo: Path,
    tmp_path: Path,
    **overrides: Any,
) -> Any:
    values: dict[str, Any] = {
        "grafana_url": "",
        "grafana_token": "",
        "environment": "production",
        "state_dir": tmp_path / "state",
        "repo_root": repo,
        "agent_cmd": worker.DEFAULT_AGENT_CMD,
        "timeout_seconds": 5,
        "poll_seconds": 60,
        "dry_run": False,
        "once": True,
    }
    values.update(overrides)
    return worker.WorkerConfig(**values)


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    path = tmp_path / "repo"
    path.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.name", "Test"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    (path / "README.md").write_text("initial\n", encoding="utf-8")
    subprocess.run(["git", "add", "README.md"], cwd=path, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "initial"],
        cwd=path,
        check=True,
        capture_output=True,
    )
    return path


def test_deduplicates_active_alerts_by_fingerprint(
    repo: Path,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path)
    source = FakeAlerts([make_alert()])
    runner = make_runner(
        calls,
        transcript="opened https://github.com/maxxqcty/openseat/pull/42\n",
    )

    first = worker.Worker(
        config,
        alert_source=source,
        metric_source=FakeMetrics(),
        runner=runner,
    ).poll_once()

    assert len(calls) == 1
    assert first[0].status == "succeeded"
    assert first[0].pr_url == "https://github.com/maxxqcty/openseat/pull/42"
    assert first[0].branch.startswith("on-call/openseatwaitliststalled-")
    assert Path(first[0].packet).is_file()
    assert Path(first[0].transcript).is_file()
    assert not str(config.state_dir).startswith(str(repo))

    # A new worker process loads the same state and skips the fingerprint.
    second = worker.Worker(
        config,
        alert_source=source,
        metric_source=FakeMetrics(),
        runner=runner,
    ).poll_once()

    assert second == []
    assert len(calls) == 1


def test_resolved_alert_is_ignored_and_can_fire_again(
    repo: Path,
    tmp_path: Path,
) -> None:
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path)
    runner = make_runner(calls)
    instance = worker.Worker(
        config,
        alert_source=FakeAlerts([make_alert()]),
        metric_source=FakeMetrics(),
        runner=runner,
    )

    assert instance.poll_once()[0].status == "succeeded"
    instance.alert_source = FakeAlerts([make_alert(state="resolved")])
    assert instance.poll_once() == []
    assert instance.state.seen["fingerprint-abc12345"]["status"] == "resolved"
    assert len(calls) == 1

    instance.alert_source = FakeAlerts([make_alert()])
    assert instance.poll_once()[0].status == "succeeded"
    assert len(calls) == 2


def test_packet_redacts_pii_and_secrets(repo: Path, tmp_path: Path) -> None:
    log_file = tmp_path / "render.log"
    log_file.write_text(
        "2026-11-01T10:00:00Z display_name=Alice email=alice@example.com "
        "Cookie: openseat_session=super-secret token=verysecretvalue\n",
        encoding="utf-8",
    )
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path, log_file=log_file)
    alert = make_alert(
        labels={"email": "alice@example.com", "display_name": "Alice"},
        annotations={
            "summary": "failure for alice@example.com display_name=Alice",
            "description": "Cookie: openseat_session=super-secret token=verysecretvalue",
        },
    )

    record = worker.Worker(
        config,
        alert_source=FakeAlerts([alert]),
        metric_source=FakeMetrics(),
        runner=make_runner(calls),
    ).poll_once()[0]

    packet_text = Path(record.packet).read_text(encoding="utf-8")
    for secret in (
        "alice@example.com",
        "display_name=Alice",
        "super-secret",
        "verysecretvalue",
        "Alice",
    ):
        assert secret not in packet_text, secret
    assert "[redacted-email]" in packet_text
    assert "[redacted-pii]" in packet_text
    assert json.loads(packet_text)["metrics"]["open_seat_with_waitlist"] == 1.0


def test_agent_timeout_is_enforced(tmp_path: Path) -> None:
    outcome = worker.run_agent(
        [sys.executable, "-c", "import time; time.sleep(30)"],
        cwd=tmp_path,
        env=worker.build_agent_env(),
        timeout_seconds=1,
        transcript_path=tmp_path / "transcript.txt",
    )

    assert outcome.timed_out is True
    assert outcome.returncode is None
    transcript = (tmp_path / "transcript.txt").read_text(encoding="utf-8")
    assert "timed out after 1 seconds" in transcript


def test_failed_agent_run_is_recorded(repo: Path, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path)
    record = worker.Worker(
        config,
        alert_source=FakeAlerts([make_alert()]),
        metric_source=FakeMetrics(),
        runner=make_runner(calls, code=1, transcript="agent failed\n"),
    ).poll_once()[0]

    assert record.status == "failed"
    assert "code 1" in record.reason
    assert record.pr_url == ""
    state = json.loads((config.state_dir / "state.json").read_text(encoding="utf-8"))
    assert state["seen"]["fingerprint-abc12345"]["run_status"] == "failed"


def test_workflow_change_is_rejected(repo: Path, tmp_path: Path) -> None:
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path)
    record = worker.Worker(
        config,
        alert_source=FakeAlerts([make_alert()]),
        metric_source=FakeMetrics(),
        runner=make_runner(calls, touch_workflow=True),
    ).poll_once()[0]

    assert record.status == "rejected"
    assert "protected paths" in record.reason
    assert ".github/workflows/ci.yml" in record.reason


def test_dry_run_prints_the_packet_and_command_without_running(
    repo: Path,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    calls: list[dict[str, Any]] = []
    config = make_config(repo, tmp_path, dry_run=True)
    records = worker.Worker(
        config,
        alert_source=FakeAlerts([make_alert()]),
        metric_source=FakeMetrics(),
        runner=make_runner(calls),
    ).poll_once()

    assert calls == []
    assert records[0].status == "dry_run"
    output = capsys.readouterr().out
    assert '"open_seat_with_waitlist": 1.0' in output
    assert "agent command: opencode run" in output
    assert "worktree:" in output
    assert not (config.state_dir / "worktrees").exists()


def test_agent_environment_is_allowlisted() -> None:
    env = worker.build_agent_env(
        {
            "PATH": "/usr/bin",
            "DATABASE_URL": "postgresql://user:secret@db/openseat",
            "RENDER_API_KEY": "rnd_secret",
            "GRAFANA_TOKEN": "grafana_secret",
            "SESSION_SECRET": "session_secret",
            "OTEL_EXPORTER_OTLP_HEADERS": "Authorization=Basic secret",
            "ON_CALL_GITHUB_TOKEN": "github_pat_fine_grained",
            "ON_CALL_AGENT_ENV": "ANTHROPIC_API_KEY",
            "ANTHROPIC_API_KEY": "model-key",
        },
    )

    assert env["PATH"] == "/usr/bin"
    for key in (
        "DATABASE_URL",
        "RENDER_API_KEY",
        "GRAFANA_TOKEN",
        "SESSION_SECRET",
        "OTEL_EXPORTER_OTLP_HEADERS",
    ):
        assert key not in env
    assert env["GH_TOKEN"] == "github_pat_fine_grained"
    assert env["GITHUB_TOKEN"] == "github_pat_fine_grained"
    assert env["ANTHROPIC_API_KEY"] == "model-key"
    assert env["GIT_TERMINAL_PROMPT"] == "0"


def test_state_must_live_outside_the_repository(
    repo: Path,
    tmp_path: Path,
) -> None:
    config = make_config(repo, tmp_path, state_dir=repo / "on-call-state")
    with pytest.raises(ValueError, match="outside the repository"):
        config.validate()


def test_metric_queries_use_the_environment_label() -> None:
    for template in worker.METRIC_QUERIES.values():
        expression = template % (("production",) * template.count("%s"))
        assert 'environment="production"' in expression


def test_chaos_helper_injects_and_reverts(tmp_path: Path) -> None:
    worktree = tmp_path / "worktree"
    target = worktree / chaos.TARGET
    target.parent.mkdir(parents=True)
    target.write_text(f"def status():\n    {chaos.ORIGINAL}\n", encoding="utf-8")

    chaos.apply(worktree)
    assert chaos.BROKEN in target.read_text(encoding="utf-8")

    chaos.revert(worktree)
    assert chaos.ORIGINAL in target.read_text(encoding="utf-8")
    assert chaos.BROKEN not in target.read_text(encoding="utf-8")
