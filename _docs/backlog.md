# Backlog

Twenty issue sources in `_docs/issues/`, published to the GitHub tracker. Local
numbers match the GitHub issue numbers in this repository.

| # | Issue | Area | Depends on | Est. |
| --- | --- | --- | --- | --- |
| 01 | Bootstrap repository, tooling, CI skeleton, and health endpoint | setup, backend, ci | — | 1.5h |
| 02 | Frontend shell, routes, navigation, and design tokens | frontend | 01 | 1h |
| 03 | Frontend service layer with an in-memory mock | frontend | 02 | 1.5h |
| 04 | Database foundation and authentication | backend, auth, database | 01 | 2h |
| 05 | Session creation, listing, detail, and host cancellation | backend, sessions | 04 | 1.5h |
| 06 | Race-safe booking with capacity enforcement | backend, booking, database | 05 | 2h |
| 07 | Waitlist position in session detail and my bookings | backend, api | 06 | 0.5h |
| 08 | Cancellation and automatic promotion of the oldest waiter | backend, booking, database | 06, 07 | 1.5h |
| 09 | Host roster and check-in API | backend, api | 05, 08 | 1h |
| 10 | OpenAPI contract and drift check | docs, backend, frontend, ci | 05, 09 | 1h |
| 11 | Seed data, test database isolation, and migration checks | database, backend, test | 04, 09 | 1h |
| 12 | Frontend integration with the real API and complete UI states | frontend, integration | 03, 09, 10 | 2h |
| 13 | Production Dockerfile and one-command Compose stack | infra, docker | 11, 12 | 1.5h |
| 14 | Playwright end-to-end tests for booking, waitlist, promotion, and check-in | test, e2e | 13 | 1.5h |
| 15 | Deploy dev and prod to Fly.io with PostgreSQL | infra, deploy | 13 | 1h |
| 16 | CI/CD: build once, deploy dev, promote to prod, and roll back | ci, infra, deploy | 14, 15 | 1.5h |
| 17 | OpenTelemetry traces, metrics, and structured logs | observability, backend | 15 | 2h |
| 18 | Grafana dashboard, alert rules, and runbook verification | observability, docs | 17 | 1h |
| 19 | On-call worker, evidence packet, and chaos fix | agent, observability | 18 | 2.5h |
| 20 | Documentation, demo video, and rubric audit | docs, release | all | 2h |

**Total:** about 29.5 hours plus a 0.5-hour buffer.

## Milestones

| Milestone | Issues | Outcome |
| --- | --- | --- |
| M0 Skeleton | 01 | App runs, tests run, CI is green |
| M1 UI | 02–03 | All routes and a realistic mock |
| M2 Core | 04–09 | Auth, sessions, booking, waitlist, promotion, check-in |
| M3 Contract and data | 10–11 | Contract check, seed, clean migrations |
| M4 Integration | 12–14 | Real UI, one container, browser tests |
| M5 Delivery | 15–16 | Public dev/prod, promotion, rollback |
| M6 Operations | 17–19 | Telemetry, dashboard, alerts, agent fix |
| M7 Release | 20 | Evidence, video, audit |

## Status

| State | Meaning |
| --- | --- |
| staged | Written locally, not yet on GitHub |
| open | Created on GitHub, waiting for grooming |
| groomed | Acceptance criteria are checkable |
| in progress | SWE is implementing |
| in review | QA is verifying |
| done | QA passed and the issue is closed |

Issue 01 is **done**. Issues 02–20 are **open** in the GitHub tracker;
grooming and implementation continue in dependency order.

## Creating the issues

Install and authenticate the GitHub CLI, connect the repository to a GitHub
remote, then:

```bash
python scripts/create_issues.py --dry-run
python scripts/create_issues.py
```

The script creates the labels, creates the issues in order, and adds dependency
comments. It writes the local-to-GitHub number map to `.issue-map.json`, which
is git-ignored. Use `--repo owner/name` to target a repository that is not the
current git remote.

## Grooming order

Groom and implement in dependency order. Issues 02 and 03 can run in parallel
with 04 after 01. Issues 12 and 17 can overlap only after their dependencies
are merged. Do not parallelise migrations, the API contract, or the lockfile.

## Definition of ready

An issue is ready for implementation when:

- all four sections of `_docs/task-template.md` are complete;
- every acceptance criterion is observable;
- dependencies are closed or explicitly waived;
- the files it may touch are named;
- the follow-ups are linked.
