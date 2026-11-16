# Demo video script

Target length: 5-8 minutes. Use the seeded example.com accounts. Do not show
tokens, cookies, database URLs, or real personal data.

## 0:00-0:30 - Problem and users

- Show the README problem statement.
- Name the two users: host and guest.
- State the invariant: never overbook, and never leave a free seat while
  someone waits.

## 0:30-1:00 - Browse and sign up

- Open the public demo.
- Browse the upcoming sessions.
- Register a new guest with an example.com address.

## 1:00-2:00 - Host creates a session

- Sign in as the seeded host.
- Create a capacity-1 session with a title, time, duration, and location.
- Open the session detail page.

## 2:00-3:00 - First guest books

- Sign in as guest A.
- Book the session; show the confirmed state.
- Point out that the seat count is now full.

## 3:00-3:45 - Second guest joins the waitlist

- Sign in as guest B.
- Book the same session; show the waitlisted state and position 1.

## 3:45-4:45 - Cancellation promotes the waiter

- Sign in as guest A and cancel.
- Refresh or wait for the poll; show guest B promoted to confirmed.
- Mention that promotion happens in the same transaction as the cancellation.

## 4:45-5:30 - Host checks in

- Sign in as the host.
- Open the roster; show confirmed, waitlisted, and checked-in groups.
- Check guest B in.
- Show that the checked-in booking still occupies the seat.

## 5:30-6:30 - Grafana trace and log correlation

- Open the dashboard.
- Set the environment and version filters.
- Show traffic, 5xx rate, p95 latency, bookings by result, and promotions.
- Open one trace from the booking journey and follow it to the matching JSON
  log line with the same `trace_id`.

## 6:30-7:15 - Alert and runbook

- Show the firing `OpenSeatWaitlistStalledDev` alert (or the production rule).
- Open the dashboard link and the runbook link from the alert.
- Explain the 2-minute dev window and the 10-minute production window.

## 7:15-8:00 - Agent branch, PR, and fix verification

- Show the on-call worker transcript, branch, and draft PR.
- Open the PR: the failing regression test, the fix, and the passing suite.
- State that a human reviews and merges; the worker never deploys.
- End on the post-fix verification command and the green result.

## Recording checklist

- [ ] 1280x720 or larger, readable text.
- [ ] No secrets, tokens, cookies, emails, or real personal data.
- [ ] The alert and runbook links resolve.
- [ ] The PR is a draft and the reviewer is visible.
- [ ] The final verification command passes.
- [ ] The public link is added to `_docs/evidence/README.md`.
