---
title: "Seed data, test database isolation, and migration checks"
labels: ["database", "backend", "test"]
depends_on: ["04", "09"]
---

## Goal

A developer can populate a realistic demo dataset with one command, and tests
run against a clean, migrated PostgreSQL database without sharing state.

## Acceptance criteria

- [ ] `backend/app/seed.py` creates, idempotently, one host, two guests, one
      open session, one full session with a waitlist, and one cancelled session.
- [ ] Seeded users have stable IDs and emails: `host@example.com`,
      `guest-a@example.com`, `guest-b@example.com`; the dev-only password is
      documented.
- [ ] `uv run python -m app.seed` and `make seed` populate the database;
      `--reset` removes only seeded rows and recreates them.
- [ ] Seeded sessions start in the future relative to the run, so the demo does
      not go stale.
- [ ] Seeding is never automatic in production; the README says so.
- [ ] Integration tests apply `alembic upgrade head` to an empty database and
      never call `create_all`.
- [ ] Each test is isolated: either a transaction rollback or a fresh schema;
      tests can run in any order.
- [ ] CI starts a PostgreSQL 16 service, runs migrations, and then the
      integration suite.
- [ ] `alembic check` reports no pending model changes.
- [ ] A test upgrades from an empty database to head, and the latest revision
      downgrades one step and upgrades again.
- [ ] No real personal data and no production credentials appear in the seed.

## Out of scope

- Production data migration or backfills.
- Analytics or reporting seed data.
- Loading fixtures automatically at app startup.

## Constraints

- Seed code in `backend/app/seed.py`; expose it as a module entry point.
- Use deterministic UUIDs for seeded users and sessions.
- Test fixtures in `backend/tests/conftest.py`.
- The seed must be safe to run twice without duplicating rows.
- Do not weaken constraints to make seeding easier.
