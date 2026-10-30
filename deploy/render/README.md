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
4. Open the service URL and check `https://<service>.onrender.com/healthz`.
   `version` is the deployed Git commit because the app falls back to Render's
   `RENDER_GIT_COMMIT`.

No Fly/GHCR setup is required.

## Deploys and rollback

Merging to `main` triggers a deploy only after the repository's GitHub checks
pass (`autoDeployTrigger: checksPass`). If Render does not detect the checks,
change the setting to `commit` in the dashboard.

- **Rollback:** open the service's **Deploys** page, pick a previous successful
  deploy, and choose **Rollback**. Free services can roll back to the two most
  recent previous deploys.
- **Deploy a specific commit:** use **Manual Deploy > Deploy a specific commit**
  in the dashboard.
- **Verify:** `make render-verify URL=https://<service>.onrender.com`. Set
  `EXPECTED_VERSION=<commit>` to assert the deployed version.

There is no image-promotion pipeline: Render builds the root Dockerfile from
the selected commit. If you later need dev/prod image promotion, use a paid
workspace and an image registry; see the out-of-scope notes in issue #16.

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
