---
name: AI Shipping
description: Plan, build, deploy, and operate software with AI coding agents using spec-driven slices, explicit contracts, independent verification, and production guardrails. Use when starting or rescuing an agent-built app, setting up a spec/backlog/agent-team workflow, taking a prototype to production, or designing an AI on-call loop.
---

# AI Shipping

A working method for taking software from a vague idea to an operated service
with coding agents. The method is stack-agnostic; substitute your own
language, framework, database, cloud, and observability tools.

The central claim: an agent given a vague task does not fail loudly. It builds
something coherent, tested, and wrong. Reliability comes from **small slices,
explicit contracts, and independent verification**, not from better prompting
alone.

## Use this skill when

- Starting a new application or feature with a coding agent.
- Rescuing a prototype that "works locally" but has no contract, tests, or
  deployment path.
- Setting up a repeatable workflow: specification, backlog, roles, gates.
- Taking an app to production: container, database, CI/CD, environments,
  telemetry, alerting.
- Designing an autonomous or semi-autonomous response loop (AI on-call).
- Reviewing agent-generated work and deciding whether it is actually done.

## Do not use when

- The task is a one-line fix, a throwaway script, or pure analysis. Just do it.
- The user explicitly wants a disposable demo. Use Stage 0 + the frontend slice
  only, and state what was deliberately skipped.
- The ceremony would cost more than the change. Match process to stakes (see
  "Choose the path").

## Core principles

1. **Intent before code.** Tests prove internal consistency, not that you built
   the right product. Write the specification and a manual acceptance scenario
   first. A green suite can certify the wrong app.
2. **One new risk per slice.** Every step should introduce exactly one new
   unknown (UI, integration, persistence, container, cloud). When something
   breaks, you then know which seam to inspect.
3. **Mock the boundary you have not built.** Frontend against a mock service
   layer; backend against an in-memory store. Replace one mock at a time.
4. **Derive the contract from the client.** Generate the API contract from the
   frontend's actual service layer, then implement the backend against it. Keep
   the contract and check for drift, or accept that it is documentation.
5. **Fresh context per role.** Never let the implementer be the only verifier.
   Verification in a separate session is not bureaucracy; it removes the
   implementation history that biases review.
6. **Definitions of done must be checkable.** "All acceptance criteria pass",
   "health endpoint returns 200", "all issues groomed". Not "make it better".
7. **Build once, promote the artefact.** Build an immutable, tagged image,
   test it in dev, promote that exact image. Never rebuild for production.
8. **Every signal carries service, environment, and version.** Without all
   three, dashboards cannot attribute a regression and alerts cannot route.
9. **Alerts need an owner, a dashboard, and a runbook.** A threshold without a
   recipient and a next action is noise.
10. **Humans own production.** An agent may investigate, reproduce, and commit
    to an isolated branch. It does not get direct production deploy rights or
    standing admin credentials.
11. **Complexity is a cost.** Skills, subagents, loops, and parallel worktrees
    are optional. Start with one agent and add structure when review quality,
    not enthusiasm, demands it.
12. **Tear down what you create.** Cloud resources, test environments, and
    temporary credentials are part of the change, not an afterthought.

## The pipeline

| Stage | Outcome | Gate (evidence, not a checkbox) | Reference |
| --- | --- | --- | --- |
| 0. Frame | Specification, acceptance scenario, stack shortlist | A human can read the spec and say "yes, that is the product"; the scenario is written down | `references/build.md` |
| 1. Build | Clickable frontend on mocks → contract → backend on in-memory store → real database | The written scenario passes locally, twice, from a clean start | `references/build.md` |
| 2. Ship | One image, production database, Compose, integration + E2E tests, public deploy, CI/CD | The public URL passes the scenario; the pipeline is green from a clean clone | `references/ship.md` |
| 3. Operate | Dev/prod split, build-once promotion, telemetry, dashboards, alerts, AI responder | An injected failure is detected, routed, and diagnosed; rollback and restore are tested | `references/operate.md` |
| 4. Systematize | `AGENTS.md`, backlog, PM/SWE/QA roles, skills, subagents, worktrees | A fresh agent can execute a task from the repo alone, without verbal context | `references/agent-workflow.md` |

Do not advance a stage because the code compiles. Advance when the gate's
evidence exists. If a gate cannot be met, record it as a known gap and say so.

## Choose the path

Not every project needs every stage. Pick the smallest row that fits, and be
explicit about what was skipped.

| Stakes | Apply | Minimum evidence |
| --- | --- | --- |
| Throwaway demo | Frame + mocked frontend | The demo flow works once |
| Solo MVP | Frame → Build → Ship on a managed platform | Acceptance scenario + one E2E test + public URL |
| Real users | All stages | Health checks, rollback, backups with a restore drill, private data services, owned alerts |
| Team / high change rate | All stages + Stage 4 | Fresh-context roles, groomed backlog, parallel worktrees with a merge policy |

Frontend-first is the default for solo work because it is the cheapest way to
test whether the idea is worth building. Choose data-first or contract-first
instead when the domain model is the hard part or multiple teams build against
the same API.

## How to run a step

- **Start a new session per step.** Pass artefact paths (`_docs/spec.md`,
  `openapi.yaml`, the issue number), not the whole history.
- **Ask for options before irreversible decisions.** Stack, cloud, database,
  observability backend: request 2–3 options with trade-offs and a
  recommendation, then decide.
- **Write acceptance criteria before implementation.** The implementer writes
  tests; an independent verifier checks the criteria against running code.
- **Review at every gate.** Read the diff; check the running system, the tests,
  and the security boundaries against `references/review.md`. Small, regular
  commits with explanatory messages are review artefacts, not just
  checkpoints. The agent's summary is an index, not evidence.
- **When corrected twice on the same thing, fix the system.** Update
  `AGENTS.md`, the process document, or the skill instead of re-prompting.
- **Make stop conditions machine-checkable.** "All tests pass", "all issues
  groomed", "no file over 200 lines". Never "make it better".
- **Prefer reversible moves.** New branch, new worktree, mock, feature flag,
  second environment. Keep the last known-good state easy to return to.

## Guardrails (non-negotiable)

- Never let the implementer be the only verifier of its own work.
- Never give an autonomous agent production deploy rights, admin cloud
  credentials, or unrestricted network access.
- Never expose databases, observability dashboards, or internal services to the
  public internet. Private network, restricted access, authentication.
- Never commit secrets. Use a secret manager or injected environment variables.
- Never promote by rebuilding. Promote the tested image digest.
- Never run the app and its primary database on one host for real users
  without automated backups and a tested restore.
- Never accept generated tests that only assert a 200. Require error paths,
  auth failures, and the awkward cases named in the acceptance criteria.
- Never change a schema without migrations and a rollback plan.
- Never leave paid resources running after an exercise.

## Required report at each gate

End every stage with this structure, in the chat and in the repo where useful:

```text
Stage: <0-4>
Artefacts: <paths created/changed>
Changed: <one or two lines>
Evidence: <commands + results, scenario steps, URL/health, screenshots>
Contract/telemetry impact: <endpoints, schema, metrics, alerts>
Risks / skipped: <known gaps, why>
Next gate: <what must be true before continuing>
```

If evidence is missing, the stage is not done. Say "not verified" rather than
implying success.

## Red flags

- A large diff with no acceptance criteria and no failing-before test.
- A mock still wired in production, or a "temporary" in-memory store that
  persists.
- `openapi.yaml` that nobody regenerates or checks.
- An image tag like `latest` promoted across environments.
- A dashboard that cannot filter by environment and version.
- An alert with no owner, no dashboard link, and no runbook.
- An agent with write access to production and no audit trail.
- Green tests that never exercise a failure path.
- "It works on my machine" offered as deployment evidence.

## Reference map

| Read | When |
| --- | --- |
| `references/build.md` | Stage 0–1: spec, frontend slice, contract, backend, database |
| `references/ship.md` | Stage 2: container, Postgres, Compose, tests, cloud, CI/CD |
| `references/operate.md` | Stage 3: environments, build-once, OTel, alerts, AI on-call |
| `references/agent-workflow.md` | Stage 4: context files, backlog, roles, loops, subagents, worktrees |
| `references/review.md` | At every gate: evidence, diff, tests, security, verdict |

Read only the reference for the stage you are in. The full method is
deliberately heavier than most tasks require.
