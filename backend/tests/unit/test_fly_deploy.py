"""Unit tests for the Fly.io deployment configuration (issue #15).

These run without credentials: they parse both ``fly.toml`` files, check the
acceptance criteria that can be checked statically (port, HTTPS, one warm
machine, release command, no secrets in git), and exercise ``scripts/fly.py``
in dry-run mode.
"""

from __future__ import annotations

import importlib.util
import shutil
import subprocess
import sys
import tomllib
from pathlib import Path
from types import ModuleType

from pytest import CaptureFixture, MonkeyPatch, raises

ROOT = Path(__file__).resolve().parents[3]
FLY_DIR = ROOT / "deploy" / "fly"
SCRIPT = ROOT / "scripts" / "fly.py"

CONFIGS = {
    "dev": FLY_DIR / "dev.fly.toml",
    "prod": FLY_DIR / "prod.fly.toml",
}
APPS = {"dev": "openseat-dev", "prod": "openseat-prod"}


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("fly_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    # Register before executing: dataclass decorators resolve annotations
    # through sys.modules and fail on a partially initialized module.
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


fly = _load_script()


def test_both_apps_are_configured_for_https_on_8080_with_one_warm_machine() -> None:
    for env, path in CONFIGS.items():
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        assert config["app"] == APPS[env]
        assert config["primary_region"] == "fra"

        service = config["http_service"]
        assert service["internal_port"] == 8080
        assert service["force_https"] is True
        assert service["auto_stop_machines"] == "stop"
        assert service["auto_start_machines"] is True
        assert service["min_machines_running"] == 1

        checks = service["checks"]
        assert checks[0]["path"] == "/healthz"

        # [[vm]] is an array of tables in TOML.
        assert config["vm"][0]["cpu_kind"] == "shared"
        assert config["vm"][0]["memory"] == "512mb"


def test_release_command_runs_migrations() -> None:
    for path in CONFIGS.values():
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        release_command = config["deploy"]["release_command"]
        assert "alembic upgrade head" in release_command


def test_no_secret_values_live_in_the_committed_configuration() -> None:
    forbidden = ("SESSION_SECRET", "DATABASE_URL", "APP_ENV", "APP_VERSION")
    for path in CONFIGS.values():
        config = tomllib.loads(path.read_text(encoding="utf-8"))
        environment = config.get("env", {})
        # Secrets belong in `fly secrets`, never in the committed [env] block.
        assert not any(key in environment for key in forbidden)
        text = path.read_text(encoding="utf-8").lower()
        assert "postgres://" not in text and "password" not in text


def test_entrypoint_runs_release_commands_and_exits_with_their_status() -> None:
    # Fly replaces CMD but not ENTRYPOINT, so the entrypoint must dispatch on
    # its arguments: a release machine runs `alembic upgrade head` and exits
    # instead of starting uvicorn.
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert 'exec sh -c "$1"' in dockerfile
    assert 'exec "$@"' in dockerfile
    assert "alembic upgrade head" in dockerfile
    assert "uvicorn app.main:app" in dockerfile


def test_secrets_example_documents_the_required_variables() -> None:
    example = (FLY_DIR / "secrets.example").read_text(encoding="utf-8")
    for key in ("SESSION_SECRET", "APP_ENV", "APP_VERSION"):
        assert f"{key}=" in example
    # DATABASE_URL is written by `fly mpg attach`, never by hand.
    assert "DATABASE_URL=" not in example


def test_secret_files_are_git_ignored_but_the_example_is_not() -> None:
    if shutil.which("git") is None:
        return

    def ignored(path: str) -> bool:
        result = subprocess.run(
            ["git", "check-ignore", "-q", path],
            cwd=ROOT,
            capture_output=True,
            check=False,
        )
        return result.returncode == 0

    assert ignored("deploy/fly/dev.secrets")
    assert ignored("deploy/fly/prod.secrets")
    assert not ignored("deploy/fly/secrets.example")


def test_read_secrets_parses_lines_and_refuses_a_missing_file(
    monkeypatch: MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(fly, "FLY_DIR", tmp_path)
    target = fly.Target("dev", "openseat-dev", "openseat-dev-db", CONFIGS["dev"])

    with raises(SystemExit, match="does not exist"):
        fly.read_secrets(target)

    secrets_file = tmp_path / "dev.secrets"
    secrets_file.write_text(
        "# comment\n"
        "\n"
        "SESSION_SECRET=" + "x" * 40 + "\n"
        "APP_ENV=development\n"
        "APP_VERSION=20261027-000000-abc1234\n",
        encoding="utf-8",
    )
    values = fly.read_secrets(target)
    assert values["APP_ENV"] == "development"
    assert values["SESSION_SECRET"] == "x" * 40
    assert "APP_VERSION" in values


def test_release_images_reads_json_and_falls_back_to_the_table() -> None:
    json_list = (
        '[{"Version": 3, "image": "registry.fly.io/app/image:deployment-b"}, '
        '{"Version": 2, "image": "registry.fly.io/app/image:deployment-a"}]'
    )
    assert fly.release_images(json_list) == [
        "registry.fly.io/app/image:deployment-b",
        "registry.fly.io/app/image:deployment-a",
    ]

    wrapped = '{"releases": [{"Image": "registry.fly.io/app/image:deployment-c"}]}'
    assert fly.release_images(wrapped) == ["registry.fly.io/app/image:deployment-c"]

    table = (
        "ID  TYPE Status  Version Image\n"
        "v3  solicited success 3     registry.fly.io/app/image:deployment-b\n"
        "3 days ago\n"
    )
    assert fly.release_images(table) == ["registry.fly.io/app/image:deployment-b"]

    assert fly.release_images("not json at all") == []


def test_health_error_matches_the_contract() -> None:
    healthy = {"status": "ok", "database": "available", "version": "v1"}
    assert fly.health_error(healthy) is None
    assert fly.health_error(healthy, expected_version="v1") is None

    unhealthy = {"status": "degraded", "database": "unavailable", "version": "v1"}
    assert "unhealthy" in (fly.health_error(unhealthy) or "")
    assert "stale" in (fly.health_error(healthy, expected_version="v2") or "")


def test_dry_run_deploy_and_rollback_print_the_expected_commands(
    monkeypatch: MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    monkeypatch.setattr(fly, "DRY_RUN", True)

    assert fly.main(["deploy", "dev"]) == 0
    output = capsys.readouterr().out
    assert "deploy --config deploy/fly/dev.fly.toml" in output

    assert fly.main(["deploy", "prod", "--image", "registry.example/app:tag1"]) == 0
    output = capsys.readouterr().out
    assert "--image registry.example/app:tag1" in output

    assert fly.main(["rollback", "prod", "--image", "registry.example/app:tag0"]) == 0
    output = capsys.readouterr().out
    assert "deploy --config deploy/fly/prod.fly.toml --image registry.example/app:tag0" in output


def test_rollback_without_an_image_fails_with_a_clear_message(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr(fly, "DRY_RUN", True)
    monkeypatch.setattr(fly, "release_images", lambda payload: ["only-one"])

    with raises(SystemExit, match="could not find two release images"):
        fly.main(["rollback", "dev"])


def test_makefile_exposes_the_fly_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    for target in (
        "fly-create:",
        "fly-db:",
        "fly-secrets:",
        "fly-deploy:",
        "fly-verify:",
        "fly-rollback:",
        "fly-validate:",
    ):
        assert target in makefile
