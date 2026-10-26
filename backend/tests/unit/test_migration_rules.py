"""Tests keeping migrations the only way the schema changes."""

from __future__ import annotations

from pathlib import Path

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_application_and_migrations_never_call_create_all() -> None:
    offenders: list[str] = []
    for directory in ("app", "migrations"):
        for path in sorted((BACKEND_ROOT / directory).rglob("*.py")):
            if "create_all" in path.read_text(encoding="utf-8"):
                offenders.append(f"{directory}/{path.name}")

    assert offenders == []
