# On-call worker

The worker turns a firing Grafana alert into a reviewed draft pull request. It
is deliberately narrow: it polls, builds evidence, creates an isolated
worktree, and starts a headless coding agent. It never merges, deploys, or
writes to production.

```text
Grafana Alerting
      |
      v
worker.py -- poll every 60s, page severity, configured environment
      |
      +-- deduplicate by alert fingerprint (state outside the repository)
      |
      +-- packet.json: alert, labels, annotations, version, metrics,
      |                recent commits, sanitised log excerpts
      |
      +-- git worktree on branch on-call/<alert>-<run-id>
      |
      +-- headless agent: reproduce -> failing test -> fix -> full suite
      |
      +-- transcript.txt, branch name, draft PR URL, protected-path check
      |
      v
human review and merge
```

## Prerequisites

- Grafana Cloud stack with the dashboard and alert rules from
  [`../observability/`](../observability/README.md).
- A Grafana service account token with alert-read access.
- The Prometheus query URL for the stack (usually the same host as the OTLP
  gateway). If it is unset, the packet records `null` metrics instead of
  guessing.
- A **fine-grained GitHub token** scoped to this repository with:

  | Permission | Access |
  | --- | --- |
  | Contents | Read and write |
  | Pull requests | Read and write |
  | Metadata | Read |
  | Workflows | **No access** |
  | Deployments / Environments | **No access** |

  Do not use a classic PAT, a Render API key, or a token with workflow or
  deployment permissions.
- The model provider key used by the agent, for example `ANTHROPIC_API_KEY`.
- The `opencode` CLI (or any other headless agent) on `PATH`.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| `GRAFANA_URL` | required | Grafana base URL, for example `https://example.grafana.net` |
| `GRAFANA_TOKEN` | required | Service account token for Alerting and Prometheus |
| `GRAFANA_PROMETHEUS_URL` | empty | Prometheus query base URL; empty records `null` metrics |
| `ON_CALL_ENVIRONMENT` | `production` | Only alerts with this `environment` label run the agent |
| `ON_CALL_STATE_DIR` | `~/.openseat/on-call` | State, worktrees, packets, transcripts; must be outside the repository |
| `ON_CALL_AGENT_CMD` | `opencode run --agent build --file {prompt_file} ...` | Agent command template; must contain `{prompt_file}` |
| `ON_CALL_AGENT_ENV` | empty | Comma-separated model keys to pass through, for example `ANTHROPIC_API_KEY` |
| `ON_CALL_GITHUB_TOKEN` | empty | Fine-grained token passed to the agent as `GH_TOKEN` |
| `ON_CALL_TIMEOUT_SECONDS` | `1200` | Hard agent timeout (20 minutes) |
| `ON_CALL_POLL_SECONDS` | `60` | Poll interval |
| `ON_CALL_LOG_FILE` | empty | Optional downloaded log file; the last 100 lines are redacted and added to the packet |

The worker never forwards the operator's `RENDER_API_KEY`, `DATABASE_URL`,
`SESSION_SECRET`, `GRAFANA_TOKEN`, or `OTEL_EXPORTER_OTLP_HEADERS` to the
agent. `build_agent_env` is an allowlist and is covered by
`backend/tests/unit/test_oncall_worker.py`.

## Run it

```bash
# Poll once with a real Grafana account.
make on-call ARGS="--once"

# Loop every 60 seconds.
make on-call

# Show the packet and the exact agent command without creating a worktree.
make on-call ARGS="--dry-run --alert-file /tmp/alert.json"
```

`make on-call` runs the worker inside the backend environment because it reuses
the backend redaction filter. A dry run needs no Grafana account when
`--alert-file` points at a saved alert payload.

State lives in `~/.openseat/on-call` by default:

```text
state.json                 fingerprints, run status, branch, PR URL
runs/<run-id>/packet.json  redacted evidence packet
runs/<run-id>/prompt.md    exact agent brief
runs/<run-id>/transcript.txt
worktrees/<run-id>/        isolated checkout
```

Nothing in that directory is committed. The worker refuses to start when
`ON_CALL_STATE_DIR` is inside the repository.

## What the agent is asked to do

1. Reproduce the alert condition in a test.
2. Add a failing regression test.
3. Fix the root cause without weakening the capacity invariants.
4. Run `uv run pytest`, `uv run ruff check .`, and `uv run mypy app`.
5. Commit to the generated branch and open a draft pull request.
6. Stop and explain if the bug cannot be reproduced.

The worker rejects a run when the agent changes `.github/`, `render.yaml`,
`deploy/`, `on-call/`, or `observability/`. The fine-grained token has no
workflow permission, so the guard is defense in depth rather than the only
control.

## Model and cost

The default agent is OpenCode's `build` agent. The model is whatever the
OpenCode configuration selects; set `ON_CALL_AGENT_CMD` to add
`--model provider/model` and `--format json` when you need structured usage
events in the transcript. A typical run reads a small packet and a few source
files, runs the test suite, and writes one test plus one fix. Cost depends on
the model and the repository size; record the token usage from the transcript
or the OpenCode session for each demo run. The worker itself makes no model
calls.

A human reviews every draft pull request. The worker never approves, merges, or
deploys it.

## Chaos demo

The demo injects an off-by-one so the last free seat looks occupied. Use a
disposable worktree, never the main checkout:

```bash
git worktree add --detach /tmp/openseat-chaos origin/main
python on-call/chaos.py --worktree /tmp/openseat-chaos --apply
```

Deploy that worktree to the **development** Render service, create a
capacity-1 session, book it, and join the waitlist. The
`openseat_open_seat_with_waitlist` gauge becomes `1`; the dev alert
(`OpenSeatWaitlistStalledDev`) fires after two minutes and the production rule
after ten. Let the worker produce a branch and draft PR, then review it.

Revert the injected bug before submitting:

```bash
python on-call/chaos.py --worktree /tmp/openseat-chaos --revert
```

The live chaos deploy, alert notification, transcript, branch, and draft PR
require a Grafana account, a Render development service, and a model key. They
are tracked as external evidence in
[`../_docs/evidence/README.md`](../_docs/evidence/README.md) and are not
fabricated in the repository.

## Tests

```bash
cd backend
uv run pytest tests/unit/test_oncall_worker.py
```

The tests cover fingerprint deduplication, resolved alerts, redaction of
emails, display names, cookies, and tokens, the 20-minute timeout mechanism,
a failed agent run, protected-path rejection, the dry-run output, the agent
environment allowlist, state placement, and the chaos helper.
