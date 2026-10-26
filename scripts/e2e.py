"""Run the Playwright end-to-end suite with one command.

`make e2e` runs this so the Compose stack, a fresh database, and the browser
suite are a single step: the database volume is dropped, the image is rebuilt,
`/healthz` is polled until it is ready, the tests run, and the stack is torn
down again — even when the tests fail.

Set ``E2E_BASE_URL`` to run the same suite against an environment that is
already running. Nothing is built, started, or removed in that case.

Playwright's exit code is the exit code of this script, so CI and `make` fail
with it.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
E2E_DIR = ROOT / "e2e"
BASE_URL = os.environ.get("E2E_BASE_URL")
LOCAL_URL = "http://localhost:8080"
HEALTH_TIMEOUT_SECONDS = 240


def log(message: str) -> None:
    """Print a step so a long build shows progress."""
    print(f"==> {message}", flush=True)


def run(command: list[str], *, cwd: Path = ROOT, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a command, echoing it first."""
    print(f"$ {' '.join(command)}", flush=True)
    return subprocess.run(command, cwd=cwd, check=check, text=True)


def require(binary: str) -> str:
    """Return the absolute path of a required executable."""
    path = shutil.which(binary)
    if path is None:
        raise SystemExit(f"`{binary}` is required but was not found on PATH")
    return path


def compose(*args: str, check: bool = True) -> subprocess.CompletedProcess[str]:
    """Run a docker compose subcommand from the repository root."""
    return run([require("docker"), "compose", *args], check=check)


def wait_for_health(url: str) -> None:
    """Poll `/healthz` until it answers 200, or fail after the timeout."""
    health_url = f"{url.rstrip('/')}/healthz"
    log(f"waiting for {health_url}")
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    last_error = "no response yet"

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(health_url, timeout=5) as response:
                if response.status == 200:
                    log(f"healthy: {health_url}")
                    return
                last_error = f"status {response.status}"
        except (urllib.error.URLError, OSError) as exc:
            last_error = str(exc)
        time.sleep(2)

    raise SystemExit(
        f"{health_url} did not become healthy within {HEALTH_TIMEOUT_SECONDS}s ({last_error})"
    )


def install_dependencies() -> None:
    """Install the suite's packages and the Chromium build when missing."""
    npm = require("npm")
    if not (E2E_DIR / "node_modules").exists():
        log("installing e2e dependencies")
        run([npm, "ci"], cwd=E2E_DIR)
    log("ensuring the Chromium build is installed")
    run([npm, "exec", "--", "playwright", "install", "chromium"], cwd=E2E_DIR)


def main() -> int:
    """Start the stack when needed, run the suite, and always clean up."""
    install_dependencies()
    target = BASE_URL or LOCAL_URL

    if BASE_URL:
        log(f"running against the environment at {BASE_URL}")
        result = run([require("npm"), "exec", "--", "playwright", "test"], cwd=E2E_DIR, check=False)
        return result.returncode

    if shutil.which("docker") is None:
        print(
            "docker is required to start the stack. Start it yourself and rerun with "
            "E2E_BASE_URL=http://localhost:8080 make e2e",
            file=sys.stderr,
        )
        return 1

    try:
        log("dropping the previous database so the run starts from an empty schema")
        compose("down", "--volumes", "--remove-orphans", check=False)
        log("building and starting the stack")
        compose("up", "--detach", "--build")
        wait_for_health(target)
        result = run([require("npm"), "exec", "--", "playwright", "test"], cwd=E2E_DIR, check=False)
        return result.returncode
    finally:
        log("tearing the stack down")
        compose("down", "--volumes", "--remove-orphans", check=False)


if __name__ == "__main__":
    raise SystemExit(main())
