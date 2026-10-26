"""Manage the two Fly.io environments defined in ``deploy/fly/``.

Issue #15 deploys the image from issue #13 to two apps — ``openseat-dev`` and
``openseat-prod`` — each with its own Fly Managed Postgres cluster and its own
secrets. This script is the manual promotion path (CI/CD arrives in #16):

    python scripts/fly.py create     # create the Fly apps (idempotent)
    python scripts/fly.py db         # create + attach a Postgres cluster each
    python scripts/fly.py secrets    # apply deploy/fly/<env>.secrets
    python scripts/fly.py deploy     # build the Dockerfile and release it
    python scripts/fly.py verify     # check /healthz on both public URLs
    python scripts/fly.py releases   # list releases with their image tags
    python scripts/fly.py rollback   # redeploy the previous release's image
    python scripts/fly.py validate   # `fly config validate` both fly.toml files

Every subcommand takes ``dev``, ``prod`` or ``all`` (default ``all`` for the
setup commands, ``dev`` for ``deploy``/``rollback``). Set ``FLY_DRY_RUN=1`` to
print the commands without executing them, and ``IMAGE=registry/…:tag`` to
deploy or roll back to a specific prebuilt image.

Requires ``flyctl`` (or ``fly``) on PATH and ``flyctl auth login``. Secrets are
read from ``deploy/fly/<env>.secrets`` (git-ignored; see ``secrets.example``),
passed to flyctl on stdin rather than argv, and redacted from output — they
never appear in this file, in git, in the image, or in a log line.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FLY_DIR = ROOT / "deploy" / "fly"

# Region for both databases. Machines are placed by `primary_region` in each
# fly.toml — change both together before the first deploy, because a Fly region
# cannot be changed afterwards without recreating the app. `fly platform
# regions` lists the available codes.
REGION = "fra"

HEALTH_TIMEOUT_SECONDS = 120
DRY_RUN = os.environ.get("FLY_DRY_RUN") == "1"


def find_fly() -> str | None:
    """Locate flyctl, preferring the `flyctl` binary over the `fly` alias."""
    return shutil.which("flyctl") or shutil.which("fly")


# Resolved in main(); the placeholder keeps the module importable in tests.
FLY = find_fly() or "flyctl"


@dataclass(frozen=True)
class Target:
    """One Fly app and everything named after it."""

    env: str
    app: str
    cluster: str
    config: Path

    @property
    def secrets_file(self) -> Path:
        return FLY_DIR / f"{self.env}.secrets"

    @property
    def url(self) -> str:
        return f"https://{self.app}.fly.dev"


TARGETS: dict[str, Target] = {
    "dev": Target("dev", "openseat-dev", "openseat-dev-db", FLY_DIR / "dev.fly.toml"),
    "prod": Target("prod", "openseat-prod", "openseat-prod-db", FLY_DIR / "prod.fly.toml"),
}


def log(message: str) -> None:
    """Print a step so a long deploy shows progress."""
    print(f"==> {message}", flush=True)


def repo_path(path: Path) -> str:
    """Repo-relative path with forward slashes, for commands and output."""
    try:
        return path.relative_to(ROOT).as_posix()
    except ValueError:
        return path.as_posix()


def run(
    command: list[str],
    *,
    cwd: Path = ROOT,
    echo: str | None = None,
    input_text: str | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Run a command, echoing it first.

    `echo` replaces the command line in the output and `input_text` feeds
    stdin, so secret values are never printed or passed as arguments.
    """
    print(f"$ {echo or ' '.join(command)}", flush=True)
    if DRY_RUN:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
    return subprocess.run(command, cwd=cwd, check=check, text=True, input=input_text)


def capture(command: list[str], *, cwd: Path = ROOT) -> str:
    """Run a command quietly and return its stdout."""
    if DRY_RUN:
        print(f"$ {' '.join(command)}", flush=True)
        return ""
    result = subprocess.run(
        command, cwd=cwd, check=True, text=True, capture_output=True, input=""
    )
    return result.stdout


def require_fly() -> str:
    """Return the flyctl path, or explain how to install it."""
    path = find_fly()
    if path:
        return path
    if DRY_RUN:
        return "flyctl"
    raise SystemExit(
        "flyctl is required but was not found on PATH. Install it from "
        "https://fly.io/docs/flyctl/install/ (winget install Fly.io.flyctl, "
        "brew install flyctl, or curl -L https://fly.io/install.sh | sh) and "
        "run `flyctl auth login`."
    )


def targets_for(name: str) -> list[Target]:
    """Resolve a CLI environment argument to its targets."""
    if name == "all":
        return [TARGETS["dev"], TARGETS["prod"]]
    if name not in TARGETS:
        raise SystemExit(f"unknown environment {name!r}; expected dev, prod, or all")
    return [TARGETS[name]]


def app_exists(app: str) -> bool:
    """True when the Fly app already exists on the account."""
    if DRY_RUN:
        return False
    return app in capture([FLY, "apps", "list", "--quiet"]).split()


def read_secrets(target: Target) -> dict[str, str]:
    """Parse a KEY=VALUE secrets file, ignoring comments and blanks."""
    if not target.secrets_file.exists():
        raise SystemExit(
            f"{repo_path(target.secrets_file)} does not exist. Copy "
            f"deploy/fly/secrets.example to it and fill in real values first."
        )
    secrets: dict[str, str] = {}
    for raw_line in target.secrets_file.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        secrets[key.strip()] = value.strip()
    return secrets


def health(url: str, timeout: float = 10) -> dict[str, object] | None:
    """Fetch /healthz and return its JSON body, or None when unreachable."""
    try:
        with urllib.request.urlopen(f"{url.rstrip('/')}/healthz", timeout=timeout) as response:
            if response.status != 200:
                return None
            body = json.loads(response.read().decode("utf-8"))
    except (urllib.error.URLError, OSError, ValueError):
        return None
    return body if isinstance(body, dict) else None


def _image_from(entry: object) -> str | None:
    """Pull the image reference out of one release record."""
    if not isinstance(entry, dict):
        return None
    for key in ("image", "Image", "imageName", "full_image"):
        value = entry.get(key)
        if isinstance(value, str) and value:
            return value
    return None


def release_images(payload: str) -> list[str]:
    """Extract release image references from `fly releases --json --image`.

    Falls back to the text table (whose only column containing both a `/` and
    a `:` is the image reference) when the JSON shape is unrecognized.
    """
    images: list[str] = []
    try:
        document = json.loads(payload)
    except json.JSONDecodeError:
        document = None

    entries: list[object] = []
    if isinstance(document, list):
        entries = document
    elif isinstance(document, dict):
        for key in ("releases", "Releases", "data", "items"):
            value = document.get(key)
            if isinstance(value, list):
                entries = value
                break

    for entry in entries:
        image = _image_from(entry)
        if image:
            images.append(image)
    if images:
        return images

    for line in payload.splitlines():
        for token in line.split():
            if "/" in token and ":" in token and not token.startswith("http"):
                images.append(token)
                break
    return images


def create(target: Target) -> None:
    """Create the Fly app when it does not exist yet (idempotent)."""
    log(f"[{target.env}] ensuring Fly app {target.app} exists")
    if app_exists(target.app):
        log(f"[{target.env}] {target.app} already exists")
        return
    run([FLY, "apps", "create", target.app, "--yes"])


def database(target: Target) -> None:
    """Create a Managed Postgres cluster and attach it (sets DATABASE_URL)."""
    log(f"[{target.env}] ensuring Postgres cluster {target.cluster} exists ({REGION})")

    def find_cluster(listing: str) -> str | None:
        try:
            document = json.loads(listing)
        except json.JSONDecodeError:
            return None
        entries = document if isinstance(document, list) else document.get("clusters", [])
        if not isinstance(entries, list):
            return None
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            names = (entry.get("name"), entry.get("Name"), entry.get("id"), entry.get("ID"))
            if target.cluster in names:
                return str(entry.get("id") or entry.get("ID") or entry.get("name"))
        return None

    listing = "" if DRY_RUN else capture([FLY, "mpg", "list", "--json"])
    cluster = find_cluster(listing) if listing else None

    if cluster is None and not DRY_RUN:
        run([FLY, "mpg", "create", "--name", target.cluster, "--region", REGION])
        cluster = find_cluster(capture([FLY, "mpg", "list", "--json"]))
    cluster = cluster or target.cluster

    log(f"[{target.env}] attaching {cluster} to {target.app} as DATABASE_URL")
    run([FLY, "mpg", "attach", cluster, "--app", target.app])


def secrets(target: Target) -> None:
    """Apply the git-ignored secrets file to the app over stdin, redacted."""
    values = read_secrets(target)
    pairs = [f"{key}={value}" for key, value in values.items() if value]
    if not pairs:
        raise SystemExit(f"{target.secrets_file} has no KEY=VALUE lines to apply")
    redacted = " ".join(f"{key}=***" for key, value in values.items() if value)
    log(f"[{target.env}] applying secrets to {target.app}")
    run(
        [FLY, "secrets", "import", "--app", target.app],
        echo=f"fly secrets import --app {target.app}  # stdin: {redacted}",
        input_text="\n".join(pairs) + "\n",
    )


def deploy(target: Target, image: str | None) -> None:
    """Build the issue #13 image and release it, or promote a given image."""
    command = [FLY, "deploy", "--config", repo_path(target.config)]
    if image:
        log(f"[{target.env}] promoting prebuilt image {image} to {target.app}")
        command += ["--image", image]
    else:
        log(f"[{target.env}] building the Dockerfile and deploying to {target.app}")
    run(command)

    if not DRY_RUN:
        images = release_images(capture([FLY, "releases", "--app", target.app, "--json", "--image"]))
        if images:
            log(f"[{target.env}] released image: {images[0]}")
            log(
                f"[{target.env}] keep it for rollback: "
                f"IMAGE={images[0]} python scripts/fly.py rollback {target.env}"
            )


def health_error(body: dict[str, object], expected_version: str | None = None) -> str | None:
    """Return why a /healthz body fails the contract, or None when healthy.

    The contract value for a reachable database is ``available``
    (openapi.yaml / app.schemas.health); ``status`` must be ``ok``.
    """
    if body.get("status") != "ok" or body.get("database") != "available":
        return f"unhealthy: {body}"
    version = body.get("version")
    if expected_version and expected_version != version:
        return (
            f"reports version {version!r} but the secrets file sets "
            f"APP_VERSION={expected_version!r} — the deployed image is stale"
        )
    return None


def verify(target: Target) -> None:
    """Wait for /healthz on the public URL and assert the contract values."""
    log(f"[{target.env}] checking {target.url}/healthz")
    if DRY_RUN:
        print(f"$ GET {target.url}/healthz", flush=True)
        return

    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    body: dict[str, object] | None = None
    while time.monotonic() < deadline:
        body = health(target.url)
        if body is not None:
            break
        time.sleep(3)
    if body is None:
        raise SystemExit(f"{target.url}/healthz did not answer within {HEALTH_TIMEOUT_SECONDS}s")

    expected = read_secrets(target).get("APP_VERSION") if target.secrets_file.exists() else None
    problem = health_error(body, expected)
    if problem:
        raise SystemExit(f"{target.url}/healthz {problem}")
    log(f"[{target.env}] healthy: status=ok database=available version={body.get('version')}")


def releases(target: Target) -> None:
    """List the app's releases with their image references."""
    run([FLY, "releases", "--app", target.app, "--image"])


def rollback(target: Target, image: str | None) -> None:
    """Redeploy the previous release's image (or an explicit IMAGE)."""
    if image is None:
        log(f"[{target.env}] looking up the previous release of {target.app}")
        if DRY_RUN:
            images: list[str] = []
        else:
            images = release_images(
                capture([FLY, "releases", "--app", target.app, "--json", "--image"])
            )
        if len(images) < 2:
            raise SystemExit(
                f"could not find two release images for {target.app} "
                f"({len(images)} found); pass one explicitly with IMAGE=…"
            )
        image = images[1]
    log(f"[{target.env}] rolling back to {image}")
    run([FLY, "deploy", "--config", repo_path(target.config), "--image", image])


def validate(target: Target) -> None:
    """Validate a fly.toml against the Fly platform (needs `flyctl auth login`)."""
    log(f"[{target.env}] validating {repo_path(target.config)}")
    run([FLY, "config", "validate", "--strict", "--config", repo_path(target.config)])


SETUP_COMMANDS = {"create": create, "db": database, "secrets": secrets, "releases": releases, "validate": validate}


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested command."""
    parser = argparse.ArgumentParser(
        prog="scripts/fly.py",
        description="Deploy and operate the openseat-dev and openseat-prod Fly apps.",
    )
    parser.add_argument(
        "command",
        choices=["create", "db", "secrets", "deploy", "verify", "releases", "rollback", "validate"],
    )
    parser.add_argument(
        "env",
        nargs="?",
        default=None,
        help="dev, prod, or all (default: all for setup commands, dev for deploy/rollback)",
    )
    parser.add_argument(
        "--image",
        default=os.environ.get("IMAGE"),
        help="prebuilt image tag to deploy or roll back to",
    )
    args = parser.parse_args(argv)

    global FLY
    FLY = require_fly()

    default_env = "all" if args.command in SETUP_COMMANDS else "dev"
    targets = targets_for(args.env or default_env)

    if args.command in SETUP_COMMANDS:
        for target in targets:
            SETUP_COMMANDS[args.command](target)
        return 0
    if args.command == "deploy":
        deploy(targets[0], args.image)
        return 0
    if args.command == "rollback":
        rollback(targets[0], args.image)
        return 0
    if args.command == "verify":
        for target in targets:
            verify(target)
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
