# Security audit

Date: 2026-11-01. Scope: the public repository, the backend runtime and
development dependencies, the frontend production dependencies, and the full
git history.

## Results

| Check | Command | Result |
| --- | --- | --- |
| Python dependencies | `cd backend && uv run pip-audit` | No known vulnerabilities |
| Frontend production dependencies | `cd frontend && npm audit --omit=dev` | 0 vulnerabilities |
| Secret scan (git history) | `gitleaks detect --source . --redact` | 29 commits, ~896 KB, no leaks |

No high or critical findings required a fix. The audit tools are not committed:
`pip-audit` is a backend dev dependency, and the gitleaks binary was downloaded
to the git-ignored `tmp/` directory for the scan.

## Reproduce

```bash
cd backend
uv run pip-audit

cd ../frontend
npm audit --omit=dev

# Install gitleaks from https://github.com/gitleaks/gitleaks/releases, then:
gitleaks detect --source . --redact --verbose
```

## Controls

### Secrets

- `.env` is git-ignored. `.env.example` contains names and empty values only.
- Render generates `SESSION_SECRET` and injects `DATABASE_URL`. Neither is
  committed or baked into the image.
- Grafana OTLP endpoint headers and the Render API key are GitHub or Render
  secrets, never repository files.
- The deploy hook URL is a GitHub repository secret. The workflow skips the
  hook and warns when it is absent.
- The on-call worker passes an allowlisted environment to the agent. It never
  forwards `RENDER_API_KEY`, `DATABASE_URL`, `SESSION_SECRET`, the Grafana
  token, or OTLP headers.

### Authentication and authorization

- Argon2id password hashes; passwords are never logged or returned.
- JWT session in an `HttpOnly`, `SameSite=Lax`, `Secure` (prod) cookie.
- Mutations require `X-Requested-With: openseat` (CSRF defense).
- Host and guest ownership checks are covered by integration tests.
- Login and registration are rate limited.

### Telemetry and evidence redaction

- The logging filter removes emails, display names, cookies, authorization
  headers, bearer tokens, passwords, tokens, and API keys.
- Request bodies and payloads are replaced with `[redacted-body]`.
- The on-call packet applies the same redaction to labels, annotations, logs,
  and commit text before writing `packet.json`.
- Unit tests prove the redaction, including a packet with an email, display
  name, cookie, and token.

### Agent blast radius

- The worker creates an isolated worktree outside the repository.
- The agent receives a fine-grained GitHub token with contents and pull-request
  access only. Workflow, deployment, and environment permissions are excluded.
- The worker rejects changes to `.github/`, `render.yaml`, `deploy/`, `on-call/`,
  and `observability/` even if the token would allow them.
- A 20-minute timeout bounds the run. The worker never merges, approves, or
  deploys.
- A human reviews every draft pull request.

### Data

- Integration tests use a disposable PostgreSQL database and unique emails.
- Seed data uses example.com addresses and refuses to run when
  `APP_ENV=production`.
- No production data is copied into tests, packets, logs, or screenshots.

## Residual risks

- `npm audit --omit=dev` does not audit development-only packages. CI installs
  them from the lockfile; a separate dev audit can be added if needed.
- The free Render Postgres database expires 30 days after creation. It must be
  recreated or upgraded before it expires; the app has no automatic backup.
- The live Grafana stack, contact point, and alert notification require
  operator action. The repository contains the configuration and local tests,
  not a live account.
- A compromised model provider or agent could still attempt a harmful change.
  The worktree, token scope, protected-path guard, timeout, and human review
  reduce but do not eliminate that risk.
- The public demo uses a free service that sleeps after inactivity. Availability
  during the first request after idle is lower than a paid plan.

## External evidence still required

- Live Grafana dashboard and alert screenshots.
- A real notification delivered to a contact point.
- The on-call chaos deploy, transcript, branch, and draft PR.
- The demo video and three peer reviews.

These are tracked in `_docs/evidence/README.md`. They are not simulated or
claimed as complete.
