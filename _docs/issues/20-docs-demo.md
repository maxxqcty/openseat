---
title: "Documentation, demo video, and rubric audit"
labels: ["docs", "release"]
depends_on: ["01", "02", "03", "04", "05", "06", "07", "08", "09", "10", "11", "12", "13", "14", "15", "16", "17", "18", "19"]
---

## Goal

A reviewer can understand the problem, run the project, verify every rubric
criterion, and watch the demo without asking a question.

## Acceptance criteria

- [ ] README opens with the problem, the users, and the core flow, then lists
      features, architecture, local run, tests, deploy, observability, and
      evidence links.
- [ ] README lists the public dev and prod URLs, the demo video, and the
      on-call evidence.
- [ ] `_docs/RUBRIC.md` copies the 12 criteria and 24 points, marks each with
      points claimed and a public evidence link.
- [ ] The architecture document matches the code; every deviation is recorded
      in its decisions table.
- [ ] A 5–8 minute demo video shows: browse, sign up, host creates a session,
      guest books, second guest joins the waitlist, cancellation promotes the
      waiter, host checks in, Grafana trace/log correlation, the alert, the
      agent branch/PR, and the fix verification.
- [ ] The video and screenshots contain no secrets, tokens, emails, or real
      personal data.
- [ ] A fresh clone passes `docker compose up --build`, `make test`, and
      `make e2e`; the commands and results are recorded.
- [ ] `uv run pip-audit`, `npm audit --omit=dev`, and a secret scan
      (`gitleaks` or `trufflehog`) have been run; high and critical findings are
      fixed or documented.
- [ ] The repository is public, has a tag `v1.0.0`, and the README links the
      project description and the three peer reviews.
- [ ] The submission checklist in `_docs/RUBRIC.md` is complete for the target
      deadline.

## Out of scope

- New product features after the audit.
- Writing the three peer reviews; they are tracked in the submission checklist.
- A marketing site.

## Constraints

- Evidence links must be publicly reachable without an account.
- Do not paste secrets or customer data into screenshots or logs.
- Keep the README readable in under ten minutes.
- English only.
- If a criterion is not fully met, say so and record the reason instead of
  overstating it.
