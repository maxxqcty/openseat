"""Unit tests for the OpenAPI drift check."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from pytest import CaptureFixture, MonkeyPatch

ROOT = Path(__file__).resolve().parents[3]
SCRIPT = ROOT / "scripts" / "check_contract.py"


def _load_script() -> ModuleType:
    spec = importlib.util.spec_from_file_location("check_contract", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


check_contract = _load_script()


def test_checked_in_contract_matches_the_app() -> None:
    assert check_contract.main() == 0


def test_compare_names_the_missing_operations() -> None:
    contract = {("/a", "get"): {}, ("/b", "post"): {}}
    generated = {("/a", "get"): {}, ("/c", "delete"): {}}

    missing_in_contract, missing_in_app, warnings = check_contract.compare_operations(
        contract,
        generated,
    )

    assert missing_in_contract == [("/c", "delete")]
    assert missing_in_app == [("/b", "post")]
    assert warnings == []


def test_mismatch_exits_nonzero_and_names_the_operation(
    monkeypatch: MonkeyPatch,
    capsys: CaptureFixture[str],
) -> None:
    monkeypatch.setattr(
        check_contract,
        "load_contract",
        lambda: {"paths": {"/a": {"get": {}}}},
    )
    monkeypatch.setattr(
        check_contract,
        "load_generated",
        lambda: {"paths": {"/a": {"get": {}}, "/b": {"post": {}}}},
    )

    assert check_contract.main() == 1
    assert "MISSING in openapi.yaml: POST /b" in capsys.readouterr().err
