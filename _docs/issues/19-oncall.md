---
title: "On-call worker, evidence packet, and chaos fix"
labels: ["agent", "observability"]
depends_on: ["18"]
---

## Goal

When the open-seat-with-waitlist alert fires, an automated worker wakes a
coding agent with enough evidence to reproduce the bug, fix it on a branch, and
hand a reviewed change back to a human.

## Acceptance criteria

- [ ] `on-call/worker.py` polls Grafana Alerting every 60 seconds for active
      page-severity alerts in the configured environment.
- [ ] It deduplicates by alert fingerprint, ignores resolved alerts, and stores
      its state outside the repository.
- [ ] It builds an evidence packet with the alert, labels, annotations,
      environment, deployed version, dashboard and runbook URLs, current metric
      values, recent commits, and sanitised log excerpts.
- [ ] The packet contains no secrets, cookies, emails, display names, or
      request bodies; a redaction test proves it.
- [ ] It creates an isolated git worktree and starts a headless coding agent
      with a prompt that requires reproduction, a failing test, a fix, and a
      passing suite.
- [ ] The agent has repository read/write and pull-request access only; it
      cannot merge, deploy, change workflows, or read production secrets.
- [ ] The worker enforces a 20-minute timeout, captures the transcript, and
      records the branch name and draft PR URL.
- [ ] `--dry-run` prints the packet and the exact agent command without running
      it.
- [ ] Unit tests cover deduplication, timeout, redaction, and a failed agent
      run.
- [ ] A chaos demo injects an off-by-one so the last seat is never confirmed,
      deploys it to dev, creates a waitlist, and lets the alert fire.
- [ ] The agent reproduces the bug, commits a real fix with a regression test
      to a branch, and opens a draft PR; a human reviews it.
- [ ] The transcript, branch, PR, and post-fix verification are linked from
      the README.
- [ ] The worker is started with `make on-call`; it may run locally for the
      demo.

## Out of scope

- Auto-merge, auto-deploy, or production database writes.
- Multi-alert correlation and a full incident commander.
- Running the agent in production.

## Constraints

- Worker code in `on-call/`; keep the agent command configurable.
- Use a fine-grained GitHub token scoped to this repository and branch/PR
  operations; never a production deploy token.
- Do not put the packet, transcript, or model key in git until it has passed
  the secret and PII scan.
- The injected bug must be on a dev-only deploy and must be reverted or fixed
  before submission.
- Document the model, token cost, and the fact that a human approves every
  change.
