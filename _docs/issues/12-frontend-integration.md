---
title: "Frontend integration with the real API and complete UI states"
labels: ["frontend", "integration"]
depends_on: ["03", "09", "10"]
---

## Goal

The product works end to end in the browser against FastAPI: browse, sign up,
book, waitlist, cancel, host, and check in, with useful loading and error states.

## Acceptance criteria

- [ ] `frontend/src/services/http.ts` implements the `Api` interface with
      `credentials: "include"`, `X-Requested-With: openseat` on mutations, JSON
      error mapping, and a typed error class.
- [ ] Browse, session detail, sign-in, sign-up, my bookings, host dashboard,
      create session, and roster pages use real data.
- [ ] The session detail shows seats left, the caller's booking status, and the
      waitlist position when applicable.
- [ ] The booking button is disabled while a request is pending and shows a
      clear success or error message.
- [ ] A 401 redirects to sign-in with a `returnTo` path that only accepts local
      paths; a 403 and a 409 show actionable messages.
- [ ] The session detail refreshes every 10 seconds while the tab is visible and
      on window focus, then stops when the page unmounts.
- [ ] A guest promoted after a cancellation sees `Confirmed` within one polling
      interval without a second manual refresh.
- [ ] The host can create a session, open its roster, and check in a confirmed
      guest; the roster updates without a full page reload.
- [ ] Loading, empty, and error states exist for every data page.
- [ ] Testing Library tests cover 401, 409, waitlist rendering, polling with fake
      timers, and a successful booking.
- [ ] `npm run build` passes and the app still runs with
      `VITE_API_MODE=mock`.
- [ ] No `fetch` appears outside `frontend/src/services/`.

## Out of scope

- WebSockets or server-sent events.
- Email or push notifications.
- Optimistic updates and offline mode.
- Server-side rendering.

## Constraints

- HTTP code only in `frontend/src/services/http.ts`; hooks in
  `frontend/src/hooks/`.
- No Redux, Zustand, or React Query. Use local state and small hooks.
- Keep the mock implementation working for frontend-only development.
- Preserve the shared components and tokens from issue #02.
- Handle the error shape from `_docs/spec.md`, not raw response text.
