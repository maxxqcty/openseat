"""Validate, deploy, promote, roll back, and verify the Render deployment.

Render builds the root Dockerfile through ``render.yaml``. The GitHub workflow
triggers a deploy only after the E2E gate. The free plan deploys from Git; the
paid image-backed path promotes the same GHCR digest without rebuilding.

Usage::

    python scripts/render.py validate
    python scripts/render.py verify
    RENDER_DEPLOY_HOOK_URL=... python scripts/render.py deploy-hook
    RENDER_API_KEY=... python scripts/render.py promote --service-id srv-... \
        --image ghcr.io/owner/openseat:tag --confirm promote
    RENDER_API_KEY=... python scripts/render.py rollback --service-id srv-... \
        --deploy-id dep-...
    RENDER_URL=https://your-service.onrender.com python scripts/render.py verify
"""

from __future__ import annotations

import argparse
import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
BLUEPRINT = ROOT / "render.yaml"
DEFAULT_URL = "https://openseat-9b15.onrender.com"
HEALTH_TIMEOUT_SECONDS = 180


def load_blueprint(path: Path = BLUEPRINT) -> dict[str, Any]:
    """Load render.yaml and require a mapping at the root."""
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SystemExit(f"{path} must contain a YAML mapping")
    return data


def _service(data: dict[str, Any], service_type: str) -> dict[str, Any] | None:
    services = data.get("services")
    if not isinstance(services, list):
        return None
    for service in services:
        if isinstance(service, dict) and service.get("type") == service_type:
            return service
    return None


def _database(data: dict[str, Any], name: str) -> dict[str, Any] | None:
    databases = data.get("databases")
    if not isinstance(databases, list):
        return None
    for database in databases:
        if isinstance(database, dict) and database.get("name") == name:
            return database
    return None


def _env_var(service: dict[str, Any], key: str) -> dict[str, Any] | None:
    env_vars = service.get("envVars")
    if not isinstance(env_vars, list):
        return None
    for item in env_vars:
        if isinstance(item, dict) and item.get("key") == key:
            return item
    return None


def validate_blueprint(data: dict[str, Any]) -> list[str]:
    """Return the list of problems in a parsed Blueprint."""
    errors: list[str] = []
    web = _service(data, "web")
    if web is None:
        return ["render.yaml must define a web service"]

    expected = {
        "runtime": "docker",
        "plan": "free",
        "region": "frankfurt",
        "healthCheckPath": "/healthz",
        "dockerfilePath": "./Dockerfile",
    }
    for key, value in expected.items():
        if web.get(key) != value:
            errors.append(f"web service {key!r} must be {value!r}")

    app_env = _env_var(web, "APP_ENV")
    if not app_env or app_env.get("value") != "production":
        errors.append("web service APP_ENV must be 'production'")

    session_secret = _env_var(web, "SESSION_SECRET")
    if not session_secret or session_secret.get("generateValue") is not True:
        errors.append("SESSION_SECRET must use generateValue: true")
    if session_secret and "value" in session_secret:
        errors.append("SESSION_SECRET must not have a committed value")

    database_url = _env_var(web, "DATABASE_URL")
    database_ref = (database_url or {}).get("fromDatabase")
    if not isinstance(database_ref, dict):
        errors.append("DATABASE_URL must reference the Render database")
        database_name = None
    else:
        database_name = database_ref.get("name")
        if database_ref.get("property") != "connectionString":
            errors.append("DATABASE_URL must use the connectionString property")
        if "value" in (database_url or {}):
            errors.append("DATABASE_URL must not have a committed value")

    database = _database(data, database_name) if database_name else None
    if database is None:
        errors.append("render.yaml must define the referenced Render database")
    else:
        for key, value in {
            "plan": "free",
            "region": "frankfurt",
            "databaseName": "openseat",
            "user": "openseat",
        }.items():
            if database.get(key) != value:
                errors.append(f"database {key!r} must be {value!r}")
        if database.get("ipAllowList") != []:
            errors.append("database ipAllowList must be [] (private network only)")

    return errors


def validate(path: Path = BLUEPRINT) -> int:
    """Validate the Blueprint structure without contacting Render."""
    errors = validate_blueprint(load_blueprint(path))
    if errors:
        for error in errors:
            print(f"render.yaml: {error}")
        return 1
    print("render.yaml is valid")
    return 0


def health_error(body: object, expected_version: str | None = None) -> str | None:
    """Return why a /healthz body fails the contract, or None when healthy."""
    if not isinstance(body, dict):
        return f"unexpected health response: {body!r}"
    if body.get("status") != "ok" or body.get("database") != "available":
        return f"unhealthy: {body}"
    version = body.get("version")
    if expected_version and version != expected_version:
        return (
            f"reports version {version!r} but expected {expected_version!r}; "
            "the deploy may not have finished"
        )
    return None


def fetch_health(url: str) -> tuple[int, object]:
    """Fetch /healthz and decode its JSON body."""
    health_url = f"{url.rstrip('/')}/healthz"
    request = urllib.request.Request(
        health_url,
        headers={"User-Agent": "openseat-render-verify"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def verify(url: str, expected_version: str | None = None) -> int:
    """Wait for a Render deploy to become healthy."""
    deadline = time.monotonic() + HEALTH_TIMEOUT_SECONDS
    last_error = "no response yet"
    body: object | None = None

    while time.monotonic() < deadline:
        try:
            status, body = fetch_health(url)
            if status == 200:
                break
            last_error = f"status {status}"
        except (urllib.error.URLError, OSError, json.JSONDecodeError) as exc:
            last_error = str(exc)
        body = None
        time.sleep(5)

    if body is None:
        print(f"{url}/healthz did not become healthy: {last_error}")
        return 1

    problem = health_error(body, expected_version)
    if problem:
        print(f"{url}/healthz {problem}")
        return 1
    print(f"{url}/healthz is healthy: {body}")
    return 0


def _api_request(
    method: str,
    path: str,
    token: str,
    payload: dict[str, Any] | None = None,
) -> tuple[int, str]:
    """Call the Render API and return ``(status, body)``."""
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    request = urllib.request.Request(
        f"https://api.render.com/v1{path}",
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "openseat-render-cli",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8")


def trigger_deploy_hook(hook_url: str | None, *, dry_run: bool = False) -> int:
    """Call a Render deploy hook after CI and E2E have passed."""
    if not hook_url:
        print("RENDER_DEPLOY_HOOK_URL is not configured")
        return 1
    if dry_run:
        print("POST <RENDER_DEPLOY_HOOK_URL> (dry run; the hook is a secret)")
        return 0
    request = urllib.request.Request(
        hook_url,
        data=b"",
        method="POST",
        headers={"User-Agent": "openseat-render-deploy"},
    )
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            print(f"deploy hook accepted with status {response.status}")
            return 0
    except urllib.error.URLError as exc:
        print(f"deploy hook failed: {exc}")
        return 1


def promote(
    *,
    service_id: str,
    image: str,
    confirm: str,
    token: str | None,
    dry_run: bool = False,
) -> int:
    """Promote the exact GHCR digest to the paid image-backed service."""
    if confirm != "promote":
        print("refusing to promote: pass --confirm promote")
        return 1
    payload = {"imageUrl": image}
    if dry_run:
        print(f"POST /v1/services/{service_id}/deploys {json.dumps(payload)} (dry run)")
        return 0
    if not token:
        print("RENDER_API_KEY is not configured")
        return 1
    status, body = _api_request("POST", f"/services/{service_id}/deploys", token, payload)
    print(f"promote status={status} body={body}")
    return 0 if 200 <= status < 300 else 1


def rollback(
    *,
    service_id: str,
    deploy_id: str,
    token: str | None,
    dry_run: bool = False,
) -> int:
    """Roll back to a previous Render deploy without rebuilding."""
    payload = {"deployId": deploy_id}
    if dry_run:
        print(f"POST /v1/services/{service_id}/rollback {json.dumps(payload)} (dry run)")
        return 0
    if not token:
        print("RENDER_API_KEY is not configured")
        return 1
    status, body = _api_request("POST", f"/services/{service_id}/rollback", token, payload)
    print(f"rollback status={status} body={body}")
    return 0 if 200 <= status < 300 else 1


def main(argv: list[str] | None = None) -> int:
    """Parse arguments and run the requested command."""
    parser = argparse.ArgumentParser(description="Validate and operate the Render deployment.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("validate", help="check render.yaml without contacting Render")

    verify_parser = subparsers.add_parser("verify", help="poll the public /healthz endpoint")
    verify_parser.add_argument(
        "url",
        nargs="?",
        default=os.environ.get("RENDER_URL", DEFAULT_URL),
        help="service URL (default: RENDER_URL or %(default)s)",
    )

    hook_parser = subparsers.add_parser("deploy-hook", help="trigger the guarded deploy hook")
    hook_parser.add_argument("--dry-run", action="store_true")

    promote_parser = subparsers.add_parser("promote", help="deploy an image to a paid service")
    promote_parser.add_argument("--service-id", required=True)
    promote_parser.add_argument("--image", required=True)
    promote_parser.add_argument("--confirm", required=True)
    promote_parser.add_argument("--dry-run", action="store_true")

    rollback_parser = subparsers.add_parser("rollback", help="redeploy a previous Render deploy")
    rollback_parser.add_argument("--service-id", required=True)
    rollback_parser.add_argument("--deploy-id", required=True)
    rollback_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args(argv)

    if args.command == "validate":
        return validate()
    if args.command == "deploy-hook":
        return trigger_deploy_hook(
            os.environ.get("RENDER_DEPLOY_HOOK_URL"),
            dry_run=args.dry_run,
        )
    if args.command == "promote":
        return promote(
            service_id=args.service_id,
            image=args.image,
            confirm=args.confirm,
            token=os.environ.get("RENDER_API_KEY"),
            dry_run=args.dry_run,
        )
    if args.command == "rollback":
        return rollback(
            service_id=args.service_id,
            deploy_id=args.deploy_id,
            token=os.environ.get("RENDER_API_KEY"),
            dry_run=args.dry_run,
        )
    return verify(args.url, os.environ.get("EXPECTED_VERSION"))


if __name__ == "__main__":
    raise SystemExit(main())
