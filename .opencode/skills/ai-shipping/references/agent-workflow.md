# Stage 4: Systematize the Agent Workflow

Goal: make the working method repeatable, so a fresh agent can execute a task
from the repository alone and a verifier can judge the result independently.

Exit gate: a task goes from backlog to verified completion without verbal
context, and a correction to the process is written back into the repo.

## 1. Decide whether you need this

Use Stage 4 when at least one of these is true:

- more than one task per week is implemented by an agent;
- the same correction keeps recurring;
- review quality, not speed, is the bottleneck;
- several people or agents work in parallel.

Do not use it for a one-off script. The full PM/SWE/QA graph costs
significantly more time and tokens than a single engineer session. Start with
one agent and a good spec; add roles when you can name what the missing role
would catch.

## 2. Put durable context in the repository

`AGENTS.md` is loaded at session start. Keep it short and operational:

```markdown
# Commands

- install: <command>
- test: <command>
- test one file: <command>
- run: <command>

# Rules

- Commit regularly with messages that explain decisions.
- Do not add dependencies without asking.
- Read `_docs/process.md` before starting work.
- Read `_docs/testing-guidelines.md` before writing tests.
- Read `_docs/design-system.md` before changing UI.
```

Apply progressive disclosure: `AGENTS.md` is the index; topic documents hold
the detail and load only when relevant. For Claude Code, add `CLAUDE.md`
containing `@AGENTS.md` so both conventions share one source.

Documents worth keeping, once they have content:

| File | Holds |
| --- | --- |
| `_docs/process.md` | How work is organised, roles, lifecycle, merge rules |
| `_docs/testing-guidelines.md` | What to test, fixtures, naming, commands |
| `_docs/design-system.md` | Tokens, components, layout rules |
| `_docs/api.md` | API conventions the contract does not capture |
| `_docs/stack.md` | Technology decisions and why |

Documents are living. When you correct an agent twice on the same point, ask it
to update the relevant document, then commit the document change separately
from the code change.

## 3. Turn the specification into a backlog

Ask for tasks that fit one session and stand alone:

```text
Create a backlog in _docs/tasks.md.

Each task must be finishable in one session and understandable without
reading the others.

Template:
## <number>. <title>
Goal: <one line>
Description: <two or three sentences>

The first task is an empty project with a passing test.
Do not write code yet.
```

Review the list: merge tasks that are too small, split tasks that are not one
session, remove anything outside the MVP. Then move the backlog to the issue
tracker (GitHub Issues or equivalent) and make it the only active source of
truth. Delete or archive the intermediate file.

## 4. Groom before implementing

A raw task is a paragraph. A groomed task is implementable without questions.
Use this template:

```markdown
## Goal

One or two sentences on what should be true when this is done.

## Acceptance criteria

- [ ] A statement you can check by looking at the result
- [ ] One line per case, including the awkward ones

## Out of scope

- Something that does not belong here, moved to #<follow-up>

## Constraints

- Files this should stay inside
- Libraries to use or avoid
- Guidelines to follow
```

The PM role:

```text
You are a Product Manager.

You groom a task before anyone implements it.

- Read the issue as written.
- Rewrite it using _docs/task-template.md.
- Make acceptance criteria checkable: someone can point at the screen and
  say yes or no.
- Think about edge cases the reporter did not consider.
- Do not write code.

Definition of done:
- All four sections are filled in.
- Every criterion can be checked against the result.
- Anything moved out of scope links to a follow-up issue.
- An engineer who has never spoken to you could implement it from the issue
  and the linked documents.
```

The cheapest place to catch a misunderstanding is here: correcting a paragraph
costs a sentence; correcting an implementation costs a rewrite.

## 5. Implement with a narrow engineer role

```text
You are a Software Engineer.

You implement one groomed task at a time.

- Read the issue and implement what it describes.
- Implement against the acceptance criteria; do not change them.
- Stay inside the files and constraints the issue names.
- Write tests for the new behaviour.
- Do not close the issue.
- Commit regularly.

Definition of done:
- Every acceptance criterion is implemented.
- Tests cover the new behaviour and the whole suite passes.
- The work is committed.
- The issue remains open with a comment describing what you did.

If a criterion is wrong, impossible, or contradicts another, comment on the
issue instead of silently reinterpreting it.
```

Two rules matter more than they look:

- **the implementer does not close the issue** — closure belongs to the
  verifier or orchestrator;
- **the implementer does not rewrite acceptance criteria** — if they are wrong,
  that is a conversation, not a unilateral edit.

## 6. Verify in a fresh context

```text
You are a QA Engineer.

You check finished work against the issue that specified it.

- Read the acceptance criteria.
- Check each one against what the code actually does.
- Run the tests and say which command you ran.
- Look for cases the criteria describe but the tests do not cover.
- Do not fix anything you find. Report it in a comment.

Your output is a verdict: PASS or FAIL. FAIL if a single criterion fails.

## QA: FAIL

- [x] Criterion one - PASS
- [ ] Criterion two - FAIL
      Submitted a duplicate and received an unhandled error

Tests: `<command>`, 18 passed, 0 failed.

Definition of done:
- The comment starts with PASS or FAIL.
- Every criterion has a verdict.
- Every FAIL states what you did and what happened.
- The test command and result are included.
- No code was changed.

Ignore what the implementation says it does. Only the acceptance criteria and
the running code count.
```

Why a separate session: when the implementer judges its own work, it grades its
own homework and the implementation history biases what it checks. QA is still
an LLM, not an oracle — that is why executable tests and the running app remain
the primary evidence.

## 7. Use loops only with checkable stop conditions

Loop engineering delegates "keep going" to the harness:

```text
/goal groom all issues
```

The harness checks the condition after each run and resumes if it is false. For
this to work, the condition must be machine-evaluable:

- good: "all tests pass", "all issues are groomed", "no file is over 200 lines";
- bad: "make the code better", "finish the feature".

If the harness has no goal command, implement the loop with stop hooks. Always
set a budget (turns, time, or tokens) as a backstop.

## 8. Define roles as subagents, not long prompts

Subagent definition at `.opencode/agents/<name>.md`, `.agents/agents/<name>.md`,
or the equivalent for your harness:

```markdown
---
name: software-engineer
description: Use this agent to execute a well-scoped coding assignment.
---

Read your role definition from _docs/team/software-engineer.md
```

Rules:

- one role per subagent, one task per run;
- the subagent gets `AGENTS.md` plus its task, not the parent's transcript;
- a new agent definition may require a session restart before it is discovered;
- keep the role definition in one place and point to it, rather than copying it
  into every prompt.

## 9. Orchestrate as a graph, and close only on PASS

Put the lifecycle in `_docs/process.md`:

```markdown
# Orchestrator

The main session is the orchestrator. It launches the PM, the engineer, and QA
as subagents. It does not groom, implement, or test itself.

## Lifecycle

1. Pick the next open issue from the backlog.
2. PM grooms it.
3. Engineer implements it.
4. QA verifies it.
5. On FAIL, return to step 3 with the QA comment as input.
6. On PASS, close the issue.
7. Repeat until the backlog is empty.

## Rules

- Do not skip grooming.
- The engineer does not close the issue.
- QA does not fix code; it only outputs PASS or FAIL.
- The orchestrator closes an issue only after QA outputs PASS.
```

Then a single prompt can drive the whole graph:

```text
Implement #101.
```

Know the limit: `process.md` is prose, not an enforced state machine. A tired
orchestrator can skip a step. For higher assurance, enforce transitions with CI
checks or a small state machine rather than trusting the prompt.

## 10. Parallelise with worktrees, and control the merge

Independent tasks can run concurrently; dependent ones cannot. Use git
worktrees for filesystem and branch isolation:

```text
Work in isolated git worktrees and run up to five agents in parallel.

You are the orchestrator:

- Split the backlog into independent issue tracks.
- Give each agent a separate worktree and clear file ownership.
- Keep the agent slots full while eligible work remains.
- Send completed work to a fresh reviewer.
- Return review findings to the correct implementer.
- Merge approved work into main one issue at a time.
- Coordinate the work. Never implement the issues yourself.
```

Additional rules that prevent pain:

- cap concurrency at a number you can actually review;
- assign file ownership; do not run two agents on the same migration,
  lockfile, or generated client;
- merge one branch at a time and rerun tests after each merge;
- delete the worktree after merge;
- have a conflict policy before you need it (rebase, or a dedicated resolver,
  or drop and retry);
- treat parallel agents as a throughput multiplier for reviewable work, not as
  a way to avoid review.

## 11. Package repeated procedures as skills

A skill is a discoverable procedure: Markdown with frontmatter, placed at
`.opencode/skills/<id>/SKILL.md` (or the harness equivalent).

```markdown
---
name: release
description: Release a new version of the current project
---

1. Inspect the project and determine its package registry.
2. Run the tests and required checks.
3. Bump the version in the source of truth.
4. Commit and push a version tag.
5. Verify the CI publishing job succeeds.
```

Create skills from real runs, not from imagination:

```text
Save this as a skill. Cover the workflow we followed and keep all the
corrections I made in mind, so the next agent can do the task correctly
from the start.

This skill is specific to this project, so do not create a global skill.
```

Keep project-specific skills in the repo. Keep cross-project procedures global
(`~/.config/opencode/skills` or the harness equivalent). When a skill run needs
correction, fold the correction back into the skill at the end of the session.

## Anti-patterns

- **Role theatre.** Three agents with the same context and the same prompt,
  producing three versions of the same bias.
- **Grooming skipped under time pressure.** The most expensive place to save
  five minutes.
- **Implementer closes its own issue.** Verification becomes a formality.
- **QA fixes the bug.** The verifier stops being independent.
- **Unbounded loops.** No stop condition, no budget, no review of the diff.
- **Parallelism without ownership.** Two agents edit the same files; the
  orchestrator spends its time resolving conflicts.
- **Skills as documentation.** A skill written before the task was ever done
  encodes guesses; do the task first.
- **Process drift.** The documented process and the actual process diverge
  because corrections are never written back.

## Gate checklist

- [ ] `AGENTS.md` has accurate commands and links to topic documents.
- [ ] The backlog is in the issue tracker, one source of truth.
- [ ] Every task has goal, checkable criteria, out-of-scope, constraints.
- [ ] Implementer and verifier run in separate contexts.
- [ ] Only the orchestrator or verifier closes an issue, and only on PASS.
- [ ] Loops have a machine-checkable stop condition and a budget.
- [ ] Repeated procedures exist as skills, created from real runs.
- [ ] Parallel work uses worktrees, ownership, a concurrency cap, and serial
      merges.
- [ ] A fresh agent can execute a task from the repository alone.
