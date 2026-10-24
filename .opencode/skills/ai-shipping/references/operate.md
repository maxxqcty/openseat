# Stage 3: Operate

Goal: know when the product is failing, understand why, and respond without
guessing. Keep a human in control of production.

Exit gate: an injected failure is detected, routed, diagnosed, and turned into
a reviewed fix; rollback and restore have been exercised.

## 1. Separate development from production

Every push deploys to dev. Production receives only a manually promoted
release.

```text
Create a second, independent copy of our infrastructure.
Use the new copy as production and the existing one as development.
```

If the infrastructure is code, this is mostly parameterisation and sizing. If
it is not, treat that as the reason to introduce it now.

Promotion workflow:

```text
Create a manual <CI> workflow that promotes the current dev version to
production. Require explicit confirmation and show the version being promoted.
```

Rules:

- dev and prod have separate data stores, credentials, and telemetry resource
  attributes;
- production promotion is a decision, not a schedule;
- the person promoting can see the version, the test results, and the change
  summary.

## 2. Build once, promote the artefact

Building during deploy is two operations pretending to be one, and promotion
that rebuilds can produce a different image from the one tested.

Split it:

```text
Currently we build the image during the deploy stage.

Split it into two stages:

- Build: build the image, tag it, and push it to <registry>
- Deploy: pull the image from the registry and serve it

The production promotion workflow pulls the currently deployed dev image.
Tag each image as YYYYMMDD-HHMMSS-shortsha.
```

Everything downstream depends on the tag being stable: dashboards filter by
version, alerts name the version, rollback selects a previous tag.

## 3. Instrument with OpenTelemetry

Telemetry is three signals with different jobs:

| Signal | Answers | Cost characteristic |
| --- | --- | --- |
| Metrics | Is the system healthy? How fast, how many, how often? | Cheap to store, expensive to over-cardinalise |
| Logs | What exactly happened in this event? | Volume grows with traffic |
| Traces | Where did this request spend time or fail? | Sampling required at scale |

```text
Instrument the backend with OpenTelemetry.

Include in the resource attributes:
- service name
- environment
- deployed version
```

Apply:

- auto-instrumentation for the framework and database client where available;
- manual spans around the domain operations that matter;
- trace context propagation through HTTP and background jobs;
- sampling that keeps errors and slow requests;
- no secrets, tokens, passwords, or personal data in span attributes or logs.

Instrument the frontend too if the product is interactive: JS errors, page
load, and the client side of the critical flow. A backend-only view misses the
half of the failure users actually see.

## 4. Put a collector between the app and storage

The app exports OTLP; the collector decides where it goes. Keep the
observability stack as a separate Compose project (or separate deployment) from
the application stack, and connect both dev and prod to it.

```text
Add an OpenTelemetry Collector.

Create observability/ with Docker Compose for:
- collector
- metrics store
- log store
- trace store
- dashboards

Keep it separate from the application Compose project.
```

Choose self-hosted versus managed explicitly. Self-hosting is cheaper on paper
and more expensive in attention; a managed OTel-compatible service removes an
entire operational surface. Either is valid, but say which you chose and why.

**Never expose the observability stack publicly.** Put it on a private network,
require authentication, and restrict access. "We will secure it later" is how
dashboards with customer data end up indexed.

## 5. Track product metrics, not just infrastructure

CPU and memory tell you something is wrong. They do not tell you whether users
can do the thing the product exists for.

Pick 3–6 metrics that describe the product. Examples:

- rooms/groups/projects created;
- active participants;
- core action completed (element created, message sent, order placed);
- core action failed;
- propagation delay for real-time features;
- signup or invitation conversion.

Tag every metric with environment and deployed version. Otherwise a dashboard
cannot answer "did the last release cause this?"

Beware cardinality: user IDs, session IDs, and raw URLs as labels will melt the
metrics store. Aggregate.

## 6. Build dashboards that answer questions

A useful dashboard has:

- a time range and environment/version filters at the top;
- golden signals: traffic, errors, latency, saturation;
- the product metrics from the previous step;
- one panel per user-visible promise, not one per internal function;
- links from alerts straight to the relevant panel.

Verify the dashboard by generating traffic and watching the numbers move. A
metric you have never seen change is a metric you do not know works.

## 7. Alert on symptoms, with enough context to act

```text
Add an actionable alert for <user-visible failure>.

Use a threshold and duration that represent real user impact.
Include the service, environment, deployed version, owner, dashboard URL,
and runbook link in the alert.
```

Alert design:

- prefer symptoms (failed core action, error rate, latency) over causes (CPU);
- require a duration so a single blip does not page anyone;
- set the threshold from observed normal behaviour, not a round number;
- one alert per actionable condition; deduplicate related ones;
- every alert has an owner and a first diagnostic step;
- if you have an SLO, alert on the burn rate, not on every raw error.

Review alerts after incidents: which fired too late, which fired for nothing,
which never fired when they should have.

## 8. Add an AI responder under guardrails

Architecture:

```text
alert → event/queue → isolated job → headless coding agent → evidence + branch
```

Minimum viable loop:

```text
Add an on-call-engineer/ directory with a script that polls the alert API.

When an alert fires, pass a bounded evidence packet to a headless coding agent:
alert details, service, environment, version, relevant logs, metric window,
and links to the dashboard and runbook.
```

Agent system prompt:

```text
You are the on-call engineer for this repository. An alert just fired.

Investigate the root cause. Read the code and reproduce the failure.
If you find a real bug, make the smallest correction, run the tests,
and commit the fix to an isolated branch with a clear message.
If the alert is a false positive, explain why and do not change the code.
Do not deploy. Do not modify production data. Do not change alert thresholds.
```

Guardrails that must exist outside the prompt:

- read-only access to logs, metrics, and traces;
- repository write access limited to a branch, never the protected main branch;
- no production credentials, no database write access, no deploy permission;
- a bounded time and token budget per incident;
- all actions logged; the session transcript retained;
- escalation to a human when severity, uncertainty, or blast radius is high;
- a human reviews and merges the fix through the normal pipeline.

A responder that can silently change production is not an on-call engineer; it
is an unmonitored deploy system.

## 9. Test the loop by breaking something

```text
Introduce a realistic bug in <core action>.

For some requests it should fail even though the existing tests pass.
Keep the failure reproducible so we can verify that it produces an alert
and an on-call response.
```

Verify the whole chain: metric moves → alert fires within the intended window →
evidence packet is sufficient → agent reproduces → fix is correct and scoped →
CI catches regressions. Then remove the injected bug.

If the agent cannot reproduce the failure, the evidence packet is inadequate.
Fix the observability, not the agent's confidence.

## 10. Production readiness checklist

- [ ] Dev and prod are separate, with separate data and credentials.
- [ ] Images are immutable, tagged, and promoted without rebuilding.
- [ ] Telemetry carries service, environment, and version.
- [ ] Dashboards filter by environment and version.
- [ ] Alerts have an owner, duration, dashboard, and runbook.
- [ ] The AI responder has read-only evidence and branch-only write access.
- [ ] At least one injected failure was detected and resolved end to end.
- [ ] Rollback to the previous image has been tested.
- [ ] Backups run on a schedule and a restore has been performed into a fresh
      environment.
- [ ] Databases and observability are on private networks with authentication.
- [ ] Secrets are managed, rotated, and absent from the repository.
- [ ] Resource usage and monthly cost are known.
- [ ] Temporary resources are scheduled for teardown.

## 11. What still is not production

Be explicit when any of these remain true:

- app and database share one host;
- deploys are shell scripts on a pet instance;
- there is no container orchestrator or restart policy;
- migrations are forward-only with no tested rollback;
- there is one database with no replica and no restore drill;
- alerting is a polling script with no deduplication or escalation;
- there is no load test, so capacity is unknown;
- security auditing is a one-time request, not a recurring practice.

These are acceptable for a proof of concept. They are not acceptable claims
about a production system.
