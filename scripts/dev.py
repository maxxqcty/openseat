"""Run the API and the Vite dev server together.

The two processes share a terminal and shut down together when either one
exits or the user presses Ctrl+C.
"""

from __future__ import annotations

import contextlib
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"

Process = subprocess.Popen[bytes]


def enable_console_interrupts() -> None:
    """Make Ctrl+C reach this process when started in a new process group."""
    if os.name == "nt":
        import ctypes

        kernel32 = ctypes.windll.kernel32  # type: ignore[attr-defined]
        kernel32.SetConsoleCtrlHandler(None, False)


def require(command: str) -> str:
    """Return the absolute path of a required executable."""
    path = shutil.which(command)
    if path is None:
        raise SystemExit(f"Missing required command: {command}")
    return path


def start(command: list[str], cwd: Path, name: str) -> Process:
    """Start a child process and report it."""
    print(f"[dev] starting {name}: {' '.join(command)}", flush=True)
    options: dict[str, object] = {"cwd": cwd}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        options["start_new_session"] = True
    return subprocess.Popen(command, **options)  # type: ignore[arg-type]


def stop(process: Process, name: str) -> None:
    """Stop a child and every process it spawned."""
    if process.poll() is not None:
        return

    print(f"[dev] stopping {name}", flush=True)
    if os.name == "nt":
        subprocess.run(
            ["taskkill", "/PID", str(process.pid), "/T", "/F"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=False,
        )
    else:
        with contextlib.suppress(ProcessLookupError):
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)

    try:
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    enable_console_interrupts()
    uv = require("uv")
    npm = require("npm")

    children: list[tuple[str, Process]] = []
    try:
        children.append(
            (
                "api",
                start(
                    [uv, "run", "uvicorn", "app.main:app", "--reload", "--port", "8091"],
                    BACKEND,
                    "api on http://localhost:8091",
                ),
            )
        )
        children.append(
            (
                "web",
                start([npm, "run", "dev"], FRONTEND, "web on http://localhost:5173"),
            )
        )

        print("[dev] ready; press Ctrl+C to stop", flush=True)
        while True:
            for name, process in children:
                code = process.poll()
                if code is not None:
                    print(f"[dev] {name} exited with code {code}", flush=True)
                    return code or 1
            time.sleep(0.5)
    except KeyboardInterrupt:
        print("\n[dev] interrupted", flush=True)
        return 0
    finally:
        for name, process in reversed(children):
            stop(process, name)


if __name__ == "__main__":
    sys.exit(main())
