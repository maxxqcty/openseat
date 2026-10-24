# Reviewing Agent Work

Purpose: decide whether generated work is actually done. Use at every gate,
before merging, and before any deploy.

## Evidence hierarchy

Trust in this order:

1. **The running system, observed by you.** Click the flow, hit the endpoint,
   open the dashboard.
2. **Executable checks with output.** Test commands, CI runs, health checks,
   query results.
3. **The diff and the code.** Read what changed.
4. **The agent's summary.** Useful as an index, never as proof.

If a claim is only supported by level 4, it is unverified.

## Intent review

Compare the result with the specification and acceptance criteria — not with
the agent's description of what it built.

Ask:

- Which requested behaviour is missing?
- What was added that nobody asked for?
- Were acceptance criteria edited, weakened, or silently reinterpreted?
- Were tests deleted, skipped, or marked expected-failure?
- Is a mock or fixture still standing in for the real thing?
- Does the UI solve the user's problem, or merely render the data?

The most expensive failure is a coherent, tested implementation of the wrong
product. Catch it at the spec, not at the diff.

## Diff review

Start with the file list. Unexpected files are a signal: new scripts,
migrations, config, or dependencies deserve explanation.

Look for:

- swallowed exceptions and catch-all handlers;
- authorization checks that exist on the route but not on the object
  (can user A read user B's record by changing an ID?);
- permissive defaults (`allow all`, `verify=False`, debug mode, CORS `*`);
- TODOs, commented-out code, temporary endpoints, and backdoors;
- dependency additions and lockfile churn that nobody requested;
- secrets, tokens, connection strings, or personal data in code, fixtures, or
  logs;
- error paths that return 200 with an error body, or leak stack traces;
- boundary handling: null, empty, duplicate, oversized, unicode, timezone,
  concurrent writes.

Review tests before implementation when possible. Tests state intended
behaviour more clearly than the code does.

## Test review

- Does every acceptance criterion map to at least one test?
- Do the assertions check values and state, not just status codes?
- Would the test fail if the feature were removed? (Delete or break the
  behaviour locally and confirm a red test.)
- Are error and permission paths covered, or only the happy path?
- Are tests deterministic: no real clock, network, random ordering, or shared
  state?
- Do integration tests hit a real database, or a fake that hides the bug?
- Does the E2E test use the shipping topology and two real sessions when the
  product is multi-user?

An independent verifier — a fresh session or a different person — should judge
the criteria against the running code. The implementer's own test run is
necessary but not sufficient.

## Security review

- Authentication on every non-public endpoint.
- Object-level authorization, not just role checks.
- Input validation and parameterised queries.
- No secrets in the repository, image layers, logs, or error messages.
- Least privilege for CI, runtime, and any agent.
- Databases, dashboards, and admin surfaces on private networks with
  authentication.
- Dependency audit and a plan for updates.
- Rate limiting or abuse controls on public write endpoints.
- Personal data minimised, retained deliberately, and absent from telemetry.

Security is not a final checklist item. If the design makes it impossible to
secure, fix the design.

## Operability review

- Health endpoint reflects real dependencies, not just process liveness.
- Startup behaviour when the database is unavailable is defined.
- Migrations run as a controlled step, with a rollback or forward-fix plan.
- Logs are structured and correlated; traces cross service boundaries.
- Metrics carry service, environment, and version.
- Alerts have an owner, duration, dashboard, and runbook.
- Rollback to the previous artifact is possible and tested.
- Backups exist and a restore has been performed.

## Deployment review

- One immutable image, non-root, with a health check.
- Configuration injected by environment, not baked in.
- The promoted artifact is the tested artifact.
- Deploy verification hits the health endpoint and, where possible, the
  acceptance scenario.
- Temporary resources, DNS records, and credentials are cleaned up.

## Questions to ask the agent

Use these to convert a confident summary into evidence:

```text
Show me the exact commands you ran and their output.

Which acceptance criteria are not covered by a test? Why?

List every assumption you made that is not in the specification.

What did you deliberately not implement?

What would make this fail under real traffic or a real user?

Which test would fail if this feature were removed?

What did you change outside the files the task allowed?
```

The last question catches scope creep that a summary will not mention.

## Verdict

Report as:

```text
Verdict: PASS | FAIL

- [x] Criterion one — PASS (evidence)
- [ ] Criterion two — FAIL (what I did, what happened)

Checks: <commands and results>
Changed: <files>
Gaps: <untested cases, known risks>
```

A single failed criterion is a FAIL. Do not average. Do not pass on the
condition that someone fixes it later without recording the gap.

## Red flags

- A large diff with no failing-before test.
- "All tests pass" with no command or count.
- New dependency with no explanation.
- Tests that assert only `status == 200`.
- An auth check on the route but not on the object.
- A mock still in the default path.
- A dashboard or database reachable from the internet.
- `latest` promoted across environments.
- An agent with production write access.
- A summary that describes intent instead of results.
- A fix that changes the test instead of the behaviour.
- A skipped step justified by time pressure, with no recorded gap.
