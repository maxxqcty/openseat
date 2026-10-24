# Stage 0–1: Frame and Build

Goal: turn an idea into a specification, then into a running local application
whose only mocked parts are the ones you have not built yet.

Exit gate: the written acceptance scenario passes locally, twice, from a clean
start.

## 1. Write the specification

Use a chat tool, not the coding agent. Dictate, and force a dialogue:

```text
I want to build <one-line idea>.

Help me set the scope precisely. Brainstorm with me and give me options.
Ask one question at a time and keep your output short.
```

Then make the implicit decisions explicit. A useful spec answers:

- Who are the users, and what problem do they have?
- What are the core flows, step by step?
- What data exists, who owns it, and who can see it?
- What are the auth and sharing rules?
- What is explicitly out of scope for the first version?
- What does "working" look like in a demo?

Ask for the result as Markdown, save it to `_docs/spec.md`, and commit it
before any code exists.

## 2. Write the acceptance scenario

A numbered sequence a person can perform without reading the code. Example:

```text
1. Open the home page and sign up.
2. Create a group.
3. Create an event in the group.
4. Copy the share link.
5. Open the link in a second browser session and join.
6. Verify the first session sees the join.
```

This scenario becomes the E2E test in Stage 2. Write it now, while the product
is still cheap to change.

## 3. Choose the build order

| Order | Best when | Cost |
| --- | --- | --- |
| Frontend first, mocked | Solo, uncertain idea, UI-heavy product | Backend is designed later from real calls |
| Contract first | Multiple clients or teams, stable domain | Requires discipline before anything is visible |
| Data model first | The domain is the hard part (billing, permissions, scheduling) | Slower feedback on the product experience |

For a solo MVP, default to frontend first. The point is to test the idea before
paying for a server.

## 4. Build the frontend against a mock

Use a UI generator (Lovable, v0, Bolt) or the coding agent. The load-bearing
instruction is the services layer:

```text
Create <application description>.

<paste specification>

Centralize every backend call in one services layer, and create a mock
implementation of it so the whole app runs without a real backend.

Add tests.
```

Review for:

- one service module (or a small set per domain), not `fetch` scattered through
  components;
- a mock implementation selected by configuration, not commented-out code;
- tests that exercise the mock at the service boundary;
- a build that runs with no backend process at all.

Move the result into a stable layout and commit the move separately:

```text
/backend
/docs
/frontend
AGENTS.md
openapi.yaml
```

Run it, click through the scenario, and fix what is wrong before defining the
API. Do not describe endpoints the UI does not actually need.

## 5. Create the project context

Minimal `AGENTS.md`:

```markdown
Commands

- install: <command>
- test: <command>
- run: <command>

Rules

- Commit regularly, with messages that explain decisions.
- Do not add dependencies without asking.
```

If the team uses Claude Code, add `CLAUDE.md` containing `@AGENTS.md` so both
read the same source. Add topic documents only when they earn their keep:
`_docs/process.md`, `_docs/testing-guidelines.md`, `_docs/design-system.md`.
Link them from `AGENTS.md` so they load on demand.

## 6. Derive the API contract

```text
Read the frontend's API client in frontend/.

Create openapi.yaml at the repository root.

Specify the backend this frontend expects: every endpoint, method, path,
request body, response body, error shape, and which endpoints need
authentication.
```

Review the contract against the service layer. Check:

- every call the frontend makes appears exactly once;
- auth requirements are stated per endpoint, not globally;
- error responses are specified (400/401/403/404/409/422);
- list endpoints state pagination/filtering if the UI needs them;
- IDs, timestamps, and enums have types and formats.

Decide the drift policy now. Either keep `openapi.yaml` as the source of truth
and diff it in CI, or delete it after the backend generates its own schema and
accept that the contract is descriptive. Do not pretend it is enforced if it
is not.

## 7. Choose the stack deliberately

```text
Read _docs/spec.md and openapi.yaml.

Propose 2-3 backend stack options. For each: pros, cons, operational cost,
and fit with the existing frontend. Recommend one and wait for approval
before writing code.
```

Pick something you can review, or explicitly delegate the choice. Record the
decision and the reasons in `_docs/stack.md`. "The agent chose it" is not a
reason; write down the criteria.

## 8. Implement the backend against the contract

```text
Build <stack> backend in backend/ that implements openapi.yaml.

Use an in-memory store seeded with realistic data so the frontend has
something to show.

Add authentication with hashed passwords and bearer tokens for the endpoints
that need it.

Split the code into modules: routers, models, store, auth.
Write tests.
```

Requirements for this slice:

- the in-memory store is behind an interface, so replacing it is one file;
- auth is real (hashing, token validation), not a header the code trusts;
- seed data covers the acceptance scenario;
- tests cover success and at least one failure per endpoint;
- a `Makefile` (or task runner) exposes `run`, `test`, and later `e2e`.

Add the Makefile in the same session if the agent has not already:

```text
Create a Makefile so I can run the application with one command.
```

## 9. Connect the halves

```text
Switch the frontend to use the real backend client.
```

Expect CORS errors and mismatched payloads. That is the point of this slice:
the only new variable is the connection. Debug by comparing the actual request
with `openapi.yaml`, not by rewriting both sides.

Run the acceptance scenario with two browser sessions if the product is
multi-user. Fix one failure at a time. Commit when the scenario passes.

## 10. Add persistence

```text
Replace the in-memory store with a database. Use <SQLite/Postgres> and an ORM.
Configure the connection with an environment variable.
Keep it database-agnostic: no vendor-specific features in the first version.
Add migrations for the schema.
```

Do not skip migrations "because it is early". The first schema change after
other people have data is where the cost appears. SQLite is fine for local
development; use a server database when concurrency, durability, or multiple
processes matter.

Use a stable interface:

```text
DATABASE_URL=...
```

The store implementation changes; the rest of the app does not.

## Gate checklist

- [ ] Spec is committed and matches what was built.
- [ ] Acceptance scenario is written and passes from a clean start.
- [ ] Frontend runs with the mock and with the real backend.
- [ ] All backend calls go through one service layer.
- [ ] `openapi.yaml` matches the calls the frontend makes.
- [ ] Real auth, not a placeholder.
- [ ] In-memory store replaced by a database with migrations.
- [ ] Tests cover success and at least one failure path per endpoint.
- [ ] `make run` and `make test` work from a fresh clone.
- [ ] `AGENTS.md` has accurate commands.

## Common failure modes

- **Green but wrong.** The agent built a coherent product that does not match
  the spec. Fix the spec and the acceptance criteria, not just the code.
- **Mock in production.** The mock remains the default because configuration
  was never flipped. Make the real client the default and the mock explicit.
- **Contract drift.** `openapi.yaml` is generated once and never checked. Either
  enforce it or stop calling it a contract.
- **Scattered fetching.** The service layer was skipped, so integration becomes
  a refactor. Enforce it in the first prompt.
- **Premature database.** Persistence was added before the connection worked,
  so every bug has two possible causes.
- **Untested error paths.** The happy path passes; duplicate signups, expired
  links, and permission failures are unknown.
