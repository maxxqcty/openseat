# Working Process

How OpenSeat is specified, implemented, and verified.

## Roles

| Role | Owns | Definition |
| --- | --- | --- |
| Product Manager (PM) | Grooming | `_docs/team/pm.md` |
| Software Engineer (SWE) | Implementation | `_docs/team/swe.md` |
| QA Engineer (QA) | Verification | `_docs/team/qa.md` |
| Orchestrator | Sequencing | This document |

The orchestrator is the main session. It does not groom, implement, or test
itself. It launches the roles as subagents or as fresh sessions.

## Lifecycle

1. Pick the next open issue from the GitHub backlog, lowest number first unless
   a dependency says otherwise.
2. **PM** grooms it: rewrites the issue using `_docs/task-template.md`, makes
   acceptance criteria checkable, moves anything out of scope to a follow-up
   issue.
3. **SWE** implements it against the groomed criteria, writes tests, commits,
   and comments on the issue. SWE does not close it.
4. **QA** verifies in a fresh context: checks each criterion against the running
   code, runs the tests, and posts a `PASS` or `FAIL` verdict.
5. On `FAIL`, return to step 3 with the QA comment as input. Repeat until PASS.
6. On `PASS`, the orchestrator closes the issue and moves to the next one.
7. Stop when the backlog is empty or the current milestone gate is met.

Do not skip grooming. A misunderstanding caught in a paragraph costs a
sentence; the same misunderstanding caught after implementation costs a rewrite.

## Task states

| State | Meaning | Who moves it |
| --- | --- | --- |
| `open` | Not groomed | Anyone |
| `groomed` | Has goal, criteria, out of scope, constraints | PM |
| `in progress` | SWE is working | SWE |
| `in review` | SWE finished; QA is verifying | SWE |
| `done` | QA passed; issue closed | Orchestrator |

Use labels rather than inventing new states: `needs-grooming`, `groomed`,
`in-progress`, `in-review`, `blocked`, plus the area labels.

## Session protocol

Start a **new session** for each role and each issue. Pass the issue number and
the documents, not the previous conversation.

```text
Groom issue #12 following _docs/team/pm.md.
Implement issue #12 following _docs/team/swe.md.
Test issue #12 following _docs/team/qa.md.
```

Why: the implementer's history biases review. QA in a fresh context is the
cheapest independent check available.

## Commit conventions

- Commit after every meaningful decision, not at the end of the day.
- Reference the issue: `feat(booking): add atomic seat allocation (#6)`.
- Types: `feat`, `fix`, `test`, `docs`, `refactor`, `chore`, `perf`, `ci`.
- The body explains why, not what. The diff already shows what.
- Never commit `.env`, secrets, database dumps, or generated artifacts.

## Branching and parallel work

- Default: one branch per issue, `issue-<number>-<slug>`.
- Merge one issue at a time into `main`; rerun tests after each merge.
- Parallel work is allowed only for issues that do not touch the same files.
  Do not run two agents on migrations, lockfiles, or the API contract.
- Use git worktrees for parallel agents. Cap concurrency at three until review
  throughput is proven.
- Delete the worktree after merge.

## Blocked work

If a criterion is wrong, impossible, or contradicts another:

1. Stop implementation.
2. Comment on the issue with the exact conflict.
3. Label it `blocked` and mention the orchestrator.
4. Do not silently reinterpret the requirement.

## Definition of done (all roles)

- Every acceptance criterion has a verdict.
- Tests pass, including at least one failure path.
- `make lint` passes.
- The change is committed and pushed.
- The issue has a comment describing what changed and how it was verified.
- Documentation is updated when behaviour or commands change.

## Documents

| Document | Purpose |
| --- | --- |
| `_docs/spec.md` | Product scope and domain rules |
| `_docs/process.md` | This file |
| `_docs/task-template.md` | Issue structure |
| `_docs/team/pm.md` | Grooming role |
| `_docs/team/swe.md` | Implementation role |
| `_docs/team/qa.md` | Verification role |
| `_docs/architecture.md` | Components and contract policy |
| `_docs/testing.md` | Test strategy |
| `_docs/runbook.md` | Alerts and response |

## Improvement loop

When the same correction happens twice, do not repeat it a third time. Ask the
agent to update the relevant document — `AGENTS.md`, this process, a role, or a
skill — and commit the documentation change separately. The next session should
start with the correction already in place.
