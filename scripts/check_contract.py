#!/usr/bin/env python
"""Check the checked-in OpenAPI contract against the FastAPI schema.

The check runs offline: it imports the app, reads the generated schema, and
never opens a database connection or starts a server. Settings that would
normally come from `.env` are supplied with test values first.

Usage (from the repository root):

    cd backend && uv run python ../scripts/check_contract.py

A missing path or method in either direction exits non-zero and names the
operation. Schema-level differences are reported as warnings only.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
CONTRACT_PATH = ROOT / "openapi.yaml"
BACKEND_ROOT = ROOT / "backend"

# Supplied before importing the app; keeps the check independent of a real .env
# or a running database.
os.environ["APP_ENV"] = "test"
os.environ["DATABASE_URL"] = ""
os.environ.setdefault(
    "SESSION_SECRET",
    "contract-check-secret-0123456789abcdef0123456789",
)

HTTP_METHODS = frozenset(
    {"get", "put", "post", "delete", "options", "head", "patch", "trace"},
)

OperationKey = tuple[str, str]
Operation = dict[str, Any]


def load_contract() -> dict[str, Any]:
    """Read openapi.yaml."""
    import yaml

    with CONTRACT_PATH.open(encoding="utf-8") as handle:
        loaded = yaml.safe_load(handle)
    if not isinstance(loaded, dict):
        raise SystemExit(f"{CONTRACT_PATH} is not a YAML object")
    return loaded


def load_generated() -> dict[str, Any]:
    """Return the schema generated from the FastAPI app."""
    if str(BACKEND_ROOT) not in sys.path:
        sys.path.insert(0, str(BACKEND_ROOT))
    from app.main import app

    return app.openapi()


def operations(schema: dict[str, Any]) -> dict[OperationKey, Operation]:
    """Index the path and method operations of an OpenAPI document."""
    indexed: dict[OperationKey, Operation] = {}
    for path, item in (schema.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, operation in item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                indexed[(path, method.lower())] = operation
    return indexed


def _success_codes(operation: Operation) -> set[str]:
    responses = operation.get("responses") or {}
    return {str(code) for code in responses if str(code).startswith("2")}


def compare_operations(
    contract: dict[OperationKey, Operation],
    generated: dict[OperationKey, Operation],
) -> tuple[list[OperationKey], list[OperationKey], list[str]]:
    """Return operations missing from each side plus schema-level warnings.

    Only 2xx responses are compared because error responses are raised
dynamically by the domain layer and are not declared in the FastAPI schema.
    """
    missing_in_contract = sorted(set(generated) - set(contract))
    missing_in_app = sorted(set(contract) - set(generated))

    warnings: list[str] = []
    for path, method in sorted(set(contract) & set(generated)):
        declared = _success_codes(contract[(path, method)])
        produced = _success_codes(generated[(path, method)])
        for status in sorted(declared ^ produced):
            warnings.append(
                f"{method.upper()} {path}: success response {status} declared on only one side",
            )
        contract_body = "requestBody" in contract[(path, method)]
        generated_body = "requestBody" in generated[(path, method)]
        if contract_body != generated_body:
            warnings.append(
                f"{method.upper()} {path}: request body declared on only one side",
            )

    return missing_in_contract, missing_in_app, warnings


def main() -> int:
    """Run the comparison and return a process exit code."""
    contract_operations = operations(load_contract())
    generated_operations = operations(load_generated())
    missing_in_contract, missing_in_app, warnings = compare_operations(
        contract_operations,
        generated_operations,
    )

    for path, method in missing_in_contract:
        print(
            f"MISSING in openapi.yaml: {method.upper()} {path}",
            file=sys.stderr,
        )
    for path, method in missing_in_app:
        print(
            f"MISSING in FastAPI app: {method.upper()} {path}",
            file=sys.stderr,
        )
    for warning in warnings:
        print(f"warning: {warning}")

    if missing_in_contract or missing_in_app:
        return 1

    print(
        f"Contract check passed: {len(contract_operations)} operations match.",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
