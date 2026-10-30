---
title: "CI/CD: test every change, deploy to Render, and roll back"
labels: ["ci", "infra", "deploy"]
depends_on: ["14", "15"]
---

## Goal

Every pull request and merge to `main` is tested. A merge to `main` deploys to
Render only after CI passes, and a previous deploy can be rolled back without
rebuilding.

## Acceptance criteria

- [ ] `ci.yml` runs backend lint and tests, frontend lint and tests, the
      contract check, and integration tests against PostgreSQL on every pull
      request and push to `main`.
- [ ] On `main`, a build job builds the root Dockerfile once, pushes it to
      GHCR tagged `YYYYMMDD-HHMMSS-<shortsha>`, and exposes the tag as a job
      output.
- [ ] The E2E job runs against the built image and blocks the deploy.
- [ ] The deploy waits for CI (`autoDeployTrigger: checksPass`) and then runs
      `make render-verify URL=https://<service>.onrender.com` against the
      public URL.
- [ ] If Render cannot detect the repository's GitHub checks, the documented
      fallback is a Render deploy hook called from the workflow after E2E,
      never an unguarded push-to-`main` deploy.
- [ ] A paid two-environment promotion uses the same image digest, never
      rebuilds, requires a typed confirmation, and uses a GitHub Environment
      named `production` with a required reviewer.
- [ ] A rollback is documented and tested once. It redeploys a previous Render
      deploy (dashboard, or API by deploy ID) and smoke-tests `/healthz`.
- [ ] Render API keys live in GitHub secrets or environment secrets; dev and
      prod keys are separate and scoped to their service.
- [ ] Workflows use least-privilege `permissions`, concurrency groups, and do
      not echo secrets.
- [ ] A failed smoke test fails the workflow and leaves the previous deploy
      running.
- [ ] README shows the pipeline diagram and links to one successful deploy,
      one approved promotion (when paid), and one rollback run.

## Out of scope

- Canary, blue/green, or automatic rollback.
- Multi-region deployment.
- Deploying pull-request previews.

## Constraints

- Build the image once in the build job; pass the tag, not the source, to any
  promotion job.
- The free Render plan deploys from Git, so image promotion requires a paid
  image-backed service. Document that limitation instead of simulating it.
- Do not run migrations during the image build; the container entrypoint owns
  migrations.
- Pin third-party actions to a major version and keep `GITHUB_TOKEN` permissions
  minimal.
- Do not put a Render API key or GHCR token in repository files.
- The manual prod approval is configured in GitHub, not simulated by a delay.
