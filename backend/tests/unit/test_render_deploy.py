"""Unit tests for the Render deployment configuration.

These run without a Render account: they validate ``render.yaml`` and exercise
``scripts/render.py``. A live smoke test is ``make render-verify``.
"""

from __future__ import annotations

import copy
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Any

import yaml
from pytest import CaptureFixture, raises

ROOT = Path(__file__).resolve().parents[3]
BLUEPRINT = ROOT / "render.yaml"
SCRIPT = ROOT / "scripts" / "render.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("render_script", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


render = _load_script()


def load_blueprint() -> dict[str, Any]:
    data = yaml.safe_load(BLUEPRINT.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_blueprint_passes_local_validation() -> None:
    assert render.validate_blueprint(load_blueprint()) == []


def test_blueprint_defines_a_free_docker_service_and_database() -> None:
    data = load_blueprint()
    [web] = data["services"]
    [database] = data["databases"]

    assert web["type"] == "web"
    assert web["name"] == "openseat"
    assert web["runtime"] == "docker"
    assert web["plan"] == "free"
    assert web["region"] == "frankfurt"
    assert web["healthCheckPath"] == "/healthz"
    assert web["dockerfilePath"] == "./Dockerfile"
    assert web["autoDeployTrigger"] == "checksPass"

    assert database["name"] == "openseat-db"
    assert database["plan"] == "free"
    assert database["region"] == "frankfurt"
    assert database["databaseName"] == "openseat"
    assert database["user"] == "openseat"
    assert database["ipAllowList"] == []


def test_secrets_are_generated_or_referenced_not_committed() -> None:
    data = load_blueprint()
    [web] = data["services"]
    env = {item["key"]: item for item in web["envVars"]}

    assert env["SESSION_SECRET"] == {"key": "SESSION_SECRET", "generateValue": True}
    assert env["DATABASE_URL"]["fromDatabase"] == {
        "name": "openseat-db",
        "property": "connectionString",
    }
    assert "APP_VERSION" not in env
    text = BLUEPRINT.read_text(encoding="utf-8").lower()
    assert "postgres://" not in text
    assert "password" not in text


def test_validation_rejects_a_missing_database() -> None:
    data = copy.deepcopy(load_blueprint())
    data["databases"] = []

    errors = render.validate_blueprint(data)
    assert any("database" in error for error in errors)


def test_validation_rejects_a_committed_secret() -> None:
    data = copy.deepcopy(load_blueprint())
    [web] = data["services"]
    for item in web["envVars"]:
        if item["key"] == "SESSION_SECRET":
            item["value"] = "not-a-generated-secret"

    errors = render.validate_blueprint(data)
    assert any("SESSION_SECRET" in error for error in errors)


def test_health_error_requires_ok_and_available() -> None:
    healthy = {"status": "ok", "database": "available", "version": "abc123"}
    assert render.health_error(healthy) is None
    assert render.health_error(healthy, expected_version="abc123") is None

    assert "unhealthy" in (render.health_error({"status": "degraded"}) or "")
    assert "expected" in (render.health_error(healthy, expected_version="def456") or "")


def test_validate_command_prints_a_success_message(capsys: CaptureFixture[str]) -> None:
    assert render.main(["validate"]) == 0
    assert "render.yaml is valid" in capsys.readouterr().out


def test_validate_fails_without_a_blueprint(tmp_path: Path) -> None:
    missing = tmp_path / "missing.yaml"
    with raises(FileNotFoundError):
        render.load_blueprint(missing)


def test_makefile_exposes_the_render_targets_and_no_fly_targets() -> None:
    makefile = (ROOT / "Makefile").read_text(encoding="utf-8")
    assert "render-validate:" in makefile
    assert "render-verify:" in makefile
    assert "fly-" not in makefile
