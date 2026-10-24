---
title: "Frontend shell, routes, navigation, and design tokens"
labels: ["frontend"]
depends_on: ["01"]
---

## Goal

Every page in the product has a real route, a consistent layout, and accessible
navigation, using placeholder content until the data layer lands.

## Acceptance criteria

- [ ] Routes exist and render a page heading:
      `/`, `/login`, `/signup`, `/sessions/:id`, `/me`, `/host`,
      `/host/sessions/new`, `/host/sessions/:id`.
- [ ] An unknown path renders a 404 page with a link home.
- [ ] The header links to Browse, My bookings, and Host; the active link is
      distinguishable; the layout works at 360 px and 1280 px.
- [ ] A signed-out state shows Sign in and Create account; a signed-in state
      shows the display name and Sign out (wired in issue #12).
- [ ] A skip link targets the main content; every interactive element has a
      visible focus ring; the mobile menu button has an accessible name.
- [ ] Design tokens for primary, surface, text, muted, danger, success, radius,
      and focus ring are defined once and used by the shared components.
- [ ] Shared `Button`, `Input`, `StatusBadge`, `EmptyState`, and `ErrorState`
      components exist with accessible defaults.
- [ ] Component tests cover the header navigation and the 404 page.
- [ ] `npm run build` passes and every route loads without console errors.

## Out of scope

- Real data fetching, forms that submit, authentication. Issues #03 and #12.
- A dark theme.
- A component library or icon package beyond inline SVG.

## Constraints

- React Router for routing; Tailwind for styling.
- Pages in `frontend/src/pages/`, reusable components in
  `frontend/src/components/`, tokens in `frontend/src/styles/`.
- No `fetch` in this issue.
- Do not invent product copy that contradicts `_docs/spec.md`.
