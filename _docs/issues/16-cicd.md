---
title: "CI/CD: build once, deploy dev, promote to prod, and roll back"
labels: ["ci", "infra", "deploy"]
depends_on: ["14", "15"]
---

## Goal

Every merge to `main` produces one tested image, deploys it to dev
automatically, and promotes that exact image to production only after a human
approves.

## Acceptance criteria

- [ ] `ci.yml` runs backend lint and tests, frontend lint and tests, the
      contract check, and integration tests against PostgreSQL on every pull
      request and push to `main`.
- [ ] On `main`, a build job pushes one image to GHCR tagged
      `YYYYMMDD-HHMMSS-<shortsha>` and exposes the tag as a job output.
- [ ] The E2E job runs against the built image and blocks the dev deploy.
- [ ] The dev deploy uses the exact image tag from the build job, runs after
      E2E, and smoke-tests `/healthz` on the public dev URL.
- [ ] `promote-prod.yml` is manual (`workflow_dispatch`), requires the tag and a
      typed confirmation, and uses a GitHub Environment named `production`
      with a required reviewer.
- [ ] The prod deploy uses the same image digest, never rebuilds, and
      smoke-tests `/healthz` and the public UI.
- [ ] `rollback.yml` is manual, takes a previous tag, deploys it without
      rebuilding, and smoke-tests the result.
- [ ] Fly API tokens live in GitHub secrets or environment secrets; prod and dev
      tokens are separate and scoped to their app.
- [ ] Workflows use least-privilege `permissions`, concurrency groups, and do
      not echo secrets.
- [ ] A failed smoke test fails the workflow and leaves the previous release
      running.
- [ ] README shows the pipeline diagram and links to one successful dev deploy,
      one approved prod deploy, and one rollback run.

## Out of scope

- Canary, blue/green, or automatic rollback.
- Multi-region deployment.
- Deploying pull-request previews.

## Constraints

- Build the image once in the build job; pass the tag, not the source, to deploy
  jobs.
- Do not run migrations during the image build; the Fly release command owns
  migrations.
- Pin third-party actions to a major version and keep `GITHUB_TOKEN` permissions
  minimal.
- Do not put a Fly token or GHCR token in repository files.
- The manual prod approval is configured in GitHub, not simulated by a delay.
