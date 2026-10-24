---
title: "OpenAPI contract and drift check"
labels: ["docs", "backend", "frontend", "ci"]
depends_on: ["05", "09"]
---

## Goal

The frontend and backend agree on every endpoint, and CI catches the case where
one side changes without the other.

## Acceptance criteria

- [ ] `openapi.yaml` at the repository root documents every endpoint in
      `_docs/spec.md`, the error shape, auth cookie, CSRF header, and status
      codes.
- [ ] The document includes request and response schemas for auth, sessions,
      bookings, roster, and health.
- [ ] `scripts/check_contract.py` imports the FastAPI app, reads the generated
      schema, and asserts that every path and method appears in both
      `openapi.yaml` and the generated schema.
- [ ] The check exits non-zero and names the missing path and method on a
      mismatch.
- [ ] Schema-level differences are reported as warnings, not failures, and the
      policy is documented in `_docs/architecture.md`.
- [ ] CI has a `contract` job that runs the check after installing backend
      dependencies.
- [ ] The frontend service types match the documented request and response
      shapes; a mismatch is fixed in the same pull request.
- [ ] README explains which document is canonical and how to run the check.

## Out of scope

- Generating a TypeScript client.
- Full JSON Schema diffing or a breaking-change gate.
- Publishing the spec to an external developer portal.

## Constraints

- The check must run without a database connection and without starting a
  server.
- Set test defaults for required settings inside the script; do not read a real
  `.env`.
- Add `pyyaml` to the backend dev dependencies.
- Update the contract in the same pull request as any endpoint change.
- Do not hand-edit the FastAPI-generated schema.
