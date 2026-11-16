# Render deployment notes

The root `render.yaml` is the source of truth. Render creates one free web
service (`openseat`) and one free Postgres database (`openseat-db`) in
Frankfurt from the root `Dockerfile`.

## Free-tier limits (October 2026)

- A free web service spins down after 15 minutes without traffic and takes
  roughly a minute to wake up. The workspace gets 750 free instance hours per
  calendar month.
- Only one free Postgres database can be active per workspace. It has 1 GB of
  storage and **expires 30 days after creation**, with a 14-day grace period
  before deletion. Do not use this for data you need to keep.
- Free web services have no shell or one-off jobs, and pre-deploy commands are
  paid-only. The Docker entrypoint runs `alembic upgrade head` before starting
  uvicorn, so migrations still run (and a failure stops the service).
- Free services can send private-network traffic to the database, but cannot
  receive private-network traffic. The database therefore uses
  `ipAllowList: []` (private network only).
- The free plan deploys from Git. It cannot promote a prebuilt image, so the
  GHCR image is the record of what E2E tested, not the deploy artifact on this
  plan.

Because of the single-database limit, this Blueprint deploys one
production/demo environment. Development stays local:

```bash
docker compose up --build
make seed            # uses the published localhost:5432 database
```

## First deploy

1. Push the repository to GitHub.
2. In the Render Dashboard, choose **New > Blueprint**, connect the repository,
   and apply `render.yaml`.
3. Render generates `SESSION_SECRET`, wires `DATABASE_URL` from
   `openseat-db`, and builds the image.
4. Open the service URL and check
   `https://openseat-9b15.onrender.com/healthz`.
   `version` is the deployed Git commit because the app falls back to Render's
   `RENDER_GIT_COMMIT`.
5. Add the optional telemetry variables from `.env.example`
   (`OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_EXPORTER_OTLP_HEADERS`, and the
   sampling settings) in the Render dashboard. Export is disabled while the
   endpoint is empty.

No Fly/GHCR setup is required for the free demo.

## Deploys

`render.yaml` sets `autoDeployTrigger: checksPass`, so a merge to `main`
deploys only after Render sees the repository's GitHub checks pass.

The CI workflow adds a second, stricter gate:

1. The build job builds the root Dockerfile once and saves that image.
2. The E2E job loads the saved image and runs Playwright against it.
3. The deploy job runs only on `main`, only after E2E, and calls the Render
   deploy hook when `RENDER_DEPLOY_HOOK_URL` is set.
4. The workflow polls `/healthz` with `EXPECTED_VERSION` set to the commit SHA.

Add the hook as a GitHub repository secret:

1. In Render, open the service, then **Settings > Deploy Hook**, and copy the
   URL.
2. In GitHub, open **Settings > Secrets and variables > Actions** and add
   `RENDER_DEPLOY_HOOK_URL`.
3. Re-run the workflow. Without the secret the job prints a warning and skips
   the hook; `checksPass` remains the fallback.

The hook URL is a secret. Never commit it, print it, or paste it into an issue.

## Rollback

On the free plan:

1. Open the service's **Deploys** page.
2. Pick a previous successful deploy and choose **Rollback**. Free services can
   roll back to the two most recent previous deploys.
3. Confirm `/healthz` and run the booking smoke test.

On the paid image-backed path, use the workflow, which redeploys a previous
Render deploy and requires a typed confirmation:

```bash
gh workflow run rollback.yml \
  -f deploy_id=dep-xxxxxxxxxxxx \
  -f confirm=rollback
```

Migrations must stay backward compatible for one release (expand, then
contract), because a rollback runs the previous image against the current
schema.

## Verify a deploy

```bash
make render-validate
make render-verify URL=https://openseat-9b15.onrender.com
EXPECTED_VERSION=<commit> make render-verify URL=https://openseat-9b15.onrender.com
```

`validate` checks the Blueprint offline. `verify` polls the public URL for up
to three minutes to cover a cold start. Set `EXPECTED_VERSION` to assert the
deployed commit.

## Paid image promotion

The free plan cannot deploy a prebuilt image. With a paid workspace, switch the
service to an image-backed deploy and use
`.github/workflows/promote.yml`. It:

- promotes the exact GHCR digest that passed E2E, without rebuilding;
- requires the `production` GitHub Environment and its required reviewer;
- requires the operator to type `promote`.

```bash
gh workflow run promote.yml \
  -f image_tag=YYYYMMDD-HHMMSS-<shortsha> \
  -f confirm=promote
```

`scripts/render.py promote` performs the API call. The free demo keeps the Git
path; the promotion workflow is documented and tested but not active.

## Adding a second environment (paid)

The free tier cannot host two Postgres databases. With a paid database plan,
add a second web service and database to `render.yaml`:

```yaml
services:
  - type: web
    name: openseat-dev
    runtime: docker
    plan: free
    region: frankfurt
    dockerfilePath: ./Dockerfile
    healthCheckPath: /healthz
    envVars:
      - key: APP_ENV
        value: development
      - key: SESSION_SECRET
        generateValue: true
      - key: DATABASE_URL
        fromDatabase:
          name: openseat-dev-db
          property: connectionString

databases:
  - name: openseat-dev-db
    plan: 0.1c-256mb
    region: frankfurt
    databaseName: openseat
    user: openseat
```

Keep `openseat-db` for production and never copy production data into dev.
