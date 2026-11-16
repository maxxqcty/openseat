"""Inject and revert the off-by-one chaos bug for the on-call demo.

The bug makes the last free seat look occupied, so a guest is waitlisted even
though a seat is free. The open-seat-with-waitlist gauge then stays above zero
and the alert fires.

Run this only against a disposable worktree, never the main checkout:

    git worktree add --detach /tmp/openseat-chaos origin/main
    python on-call/chaos.py --worktree /tmp/openseat-chaos --apply

Deploy that worktree to the development service, create a capacity-1 session,
book it, and join the waitlist. Revert before submitting:

    python on-call/chaos.py --worktree /tmp/openseat-chaos --revert
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

TARGET = Path("backend/app/services/bookings.py")
ORIGINAL = (
    "return STATUS_WAITLISTED if occupied >= capacity else STATUS_CONFIRMED"
)
BROKEN = (
    "return STATUS_WAITLISTED if occupied >= capacity - 1 else STATUS_CONFIRMED"
)


def _target(worktree: Path) -> Path:
    path = worktree / TARGET
    if not path.is_file():
        raise FileNotFoundError(path)
    return path


def apply(worktree: Path) -> None:
    path = _target(worktree)
    text = path.read_text(encoding="utf-8")
    if BROKEN in text:
        print("chaos bug is already present")
        return
    if ORIGINAL not in text:
        raise RuntimeError(f"cannot find the original line in {path}")
    path.write_text(text.replace(ORIGINAL, BROKEN, 1), encoding="utf-8")
    print(f"injected the off-by-one bug in {path}")
    print("deploy this worktree to the development service, then create a waitlist")


def revert(worktree: Path) -> None:
    path = _target(worktree)
    text = path.read_text(encoding="utf-8")
    if BROKEN not in text:
        print("chaos bug is not present")
        return
    path.write_text(text.replace(BROKEN, ORIGINAL, 1), encoding="utf-8")
    print(f"reverted the off-by-one bug in {path}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inject or revert the chaos bug.")
    parser.add_argument("--worktree", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--apply", action="store_true")
    action.add_argument("--revert", action="store_true")
    args = parser.parse_args(argv)

    worktree = args.worktree.resolve()
    repo_root = Path(__file__).resolve().parents[1].resolve()
    if worktree == repo_root:
        print("refusing to modify the main checkout; use a disposable worktree")
        return 2
    try:
        if args.apply:
            apply(worktree)
        else:
            revert(worktree)
    except (OSError, RuntimeError) as exc:
        print(f"chaos error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
