#!/usr/bin/env python
"""Create the OpenSeat GitHub issues from the files in _docs/issues.

Usage:
    python scripts/create_issues.py --dry-run
    python scripts/create_issues.py
    python scripts/create_issues.py --repo owner/name

Requires the GitHub CLI (`gh`) to be installed and authenticated. The script is
idempotent in the sense that it can be re-run, but it does not detect issues it
already created; running it twice creates duplicates.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ISSUE_DIR = ROOT / "_docs" / "issues"
MAP_FILE = ROOT / ".issue-map.json"

LABELS: dict[str, tuple[str, str]] = {
    "setup": ("6b7280", "Repository bootstrap and tooling"),
    "backend": ("2563eb", "Backend application code"),
    "frontend": ("db2777", "Frontend application code"),
    "ci": ("0ea5e9", "Continuous integration and delivery"),
    "auth": ("7c3aed", "Authentication and authorization"),
    "database": ("059669", "Schema, migrations, and data"),
    "sessions": ("f59e0b", "Workshop sessions"),
    "booking": ("ef4444", "Bookings, capacity, and waitlist"),
    "api": ("6366f1", "HTTP API and contract"),
    "test": ("10b981", "Automated tests"),
    "e2e": ("14b8a6", "Browser end-to-end tests"),
    "infra": ("475569", "Containers, deployment, and platform"),
    "docker": ("0ea5e9", "Images and local Compose stack"),
    "deploy": ("8b5cf6", "Release and environment operations"),
    "observability": ("f97316", "Metrics, traces, logs, and alerts"),
    "agent": ("a855f7", "AI on-call workflow"),
    "docs": ("64748b", "Documentation and evidence"),
    "release": ("e11d48", "Final release and submission"),
    "integration": ("ec4899", "Frontend-to-backend integration"),
    "needs-grooming": ("eab308", "Not yet groomed by the PM"),
    "groomed": ("22c55e", "Groomed and ready for implementation"),
    "in-progress": ("3b82f6", "Implementation in progress"),
    "in-review": ("a855f7", "Waiting for QA verification"),
    "blocked": ("dc2626", "Blocked on a decision or dependency"),
}


def parse_issue(path: Path) -> tuple[str, list[str], list[str], str]:
    text = path.read_text(encoding="utf-8")
    if not text.startswith("---"):
        raise ValueError(f"{path.name}: missing frontmatter")
    parts = text.split("---", 2)
    if len(parts) != 3:
        raise ValueError(f"{path.name}: malformed frontmatter")
    front, body = parts[1], parts[2].lstrip("\n")

    title = ""
    labels: list[str] = []
    depends: list[str] = []
    for line in front.splitlines():
        key, _, raw = line.partition(":")
        raw = raw.strip()
        if not raw:
            continue
        if key.strip() == "title":
            title = json.loads(raw)
        elif key.strip() == "labels":
            labels = json.loads(raw)
        elif key.strip() == "depends_on":
            depends = json.loads(raw)
    if not title:
        raise ValueError(f"{path.name}: missing title")
    return title, labels, depends, body


def run(cmd: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
    )
    if check and result.returncode != 0:
        print(result.stdout, end="")
        print(result.stderr, end="", file=sys.stderr)
        raise SystemExit(f"command failed ({result.returncode}): {' '.join(cmd)}")
    return result


def repo_args(repo: str | None) -> list[str]:
    return ["--repo", repo] if repo else []


def check_gh(repo: str | None) -> None:
    if shutil.which("gh") is None:
        raise SystemExit(
            "GitHub CLI not found. Install it from https://cli.github.com/ and "
            "run `gh auth login`."
        )
    auth = run(["gh", "auth", "status"], check=False)
    if auth.returncode != 0:
        raise SystemExit(
            "GitHub CLI is not authenticated. Run `gh auth login` first.\n"
            + auth.stderr
        )
    view = run(["gh", "repo", "view", *repo_args(repo), "--json", "nameWithOwner"], check=False)
    if view.returncode != 0:
        raise SystemExit(
            "Cannot resolve the GitHub repository. Push the repo and add an "
            "origin remote, or pass --repo owner/name.\n" + view.stderr
        )
    print(f"Repository: {json.loads(view.stdout)['nameWithOwner']}")


def create_labels(repo: str | None) -> None:
    for name, (color, description) in LABELS.items():
        run(
            [
                "gh",
                "label",
                "create",
                name,
                "--color",
                color,
                "--description",
                description,
                "--force",
                *repo_args(repo),
            ]
        )
    print(f"Labels ready: {len(LABELS)}")


def create_issue(
    title: str,
    labels: list[str],
    body: str,
    repo: str | None,
) -> tuple[int, str]:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", suffix=".md", delete=False
    ) as handle:
        handle.write(body)
        body_path = Path(handle.name)
    try:
        cmd = [
            "gh",
            "issue",
            "create",
            "--title",
            title,
            "--body-file",
            str(body_path),
            *repo_args(repo),
        ]
        for label in labels:
            cmd.extend(["--label", label])
        result = run(cmd)
    finally:
        body_path.unlink(missing_ok=True)

    url = result.stdout.strip().splitlines()[-1]
    number = int(url.rstrip("/").rsplit("/", 1)[-1])
    return number, url


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print without creating")
    parser.add_argument("--repo", help="owner/name, when the cwd has no remote")
    args = parser.parse_args()

    files = sorted(ISSUE_DIR.glob("*.md"))
    if not files:
        raise SystemExit(f"No issue files in {ISSUE_DIR}")

    issues = []
    for path in files:
        title, labels, depends, body = parse_issue(path)
        local_id = path.stem.split("-", 1)[0]
        issues.append((local_id, title, labels, depends, body, path))

    print(f"Found {len(issues)} issues in {ISSUE_DIR}")
    if args.dry_run:
        for local_id, title, labels, depends, _, _ in issues:
            deps = ", ".join(depends) or "none"
            print(f"  {local_id}  {title}")
            print(f"      labels: {', '.join(labels)}; depends on: {deps}")
        return

    check_gh(args.repo)
    create_labels(args.repo)

    mapping: dict[str, dict[str, object]] = {}
    failed: list[str] = []
    for local_id, title, labels, depends, body, path in issues:
        all_labels = list(dict.fromkeys([*labels, "needs-grooming"]))
        print(f"Creating {local_id}: {title}")
        try:
            number, url = create_issue(title, all_labels, body, args.repo)
        except SystemExit as exc:
            print(f"  failed: {exc}", file=sys.stderr)
            failed.append(local_id)
            continue
        mapping[local_id] = {
            "number": number,
            "url": url,
            "title": title,
            "depends_on": depends,
        }
        print(f"  #{number} {url}")

    MAP_FILE.write_text(json.dumps(mapping, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {MAP_FILE}")

    for local_id, entry in mapping.items():
        deps = entry.get("depends_on", [])
        resolved = [
            f"#{mapping[dep]['number']}" for dep in deps if dep in mapping
        ]
        if resolved:
            number = entry["number"]
            run(
                [
                    "gh",
                    "issue",
                    "comment",
                    str(number),
                    "--body",
                    "Depends on " + ", ".join(resolved),
                    *repo_args(args.repo),
                ]
            )
            print(f"  dependency comment on #{number}: {', '.join(resolved)}")

    if failed:
        raise SystemExit(f"Failed to create: {', '.join(failed)}")
    print(f"Created {len(mapping)} issues.")


if __name__ == "__main__":
    main()
