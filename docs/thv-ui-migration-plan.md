# THV UI Migration Plan

## Objective

Unify the existing product under a responsive THV design system without changing business behavior or service contracts.

## Delivery sequence

1. Foundation: semantic tokens, typography, spacing, status colors, focus and reduced-motion rules.
2. Shells: public shell, authenticated desktop shell, compact mobile header, mobile bottom navigation.
3. Public experience: home, program information, process, policy, catalog, search, work detail, verification.
4. Authentication: login, registration, password recovery, verification, invitation activation.
5. Participant experience: overview, account, saved items, notifications, voting history, submission availability.
6. Operations: reviewer, council, and administration screens using task-oriented navigation.
7. Quality: responsive checks, keyboard access, contrast, loading/error/empty states, browser and E2E regression.

## Current implementation slice

- Make public routes keep the public shell after authentication.
- Replace the mobile dashboard disclosure menu with persistent bottom navigation.
- Introduce the THV green semantic token set and dark-mode equivalent.
- Normalize user-facing shell labels and remove role-centric wording.

## Remediation sequence — 2026-08-29

### P0 — Theme and navigation integrity

- Replace legacy olive/green workspace tokens with one THV red-gold semantic
  palette for both themes; keep green only for explicit success status.
- Make dark-mode surface/text/border variables authoritative so utility classes
  do not require page-specific color patches.
- Keep a visible one-tap “Về bảng điều khiển” action on public pages for signed-in
  mobile users.
- Generate reviewer navigation only from reachable capabilities; never show the
  Super Admin council route to a Moderator.
- Add browser regression coverage for light/dark and public/workspace return paths.

### P1 — Reviewer workflow

- Reframe the queue around actionable stages, SLA/due-time priority, progress and
  the next required decision.
- Keep conflict declaration, evidence review, 5T scoring, draft save and final
  submission in a clear ordered workflow with persistent return navigation.
- Verify all reviewer routes and mobile actions against backend authorization.

### P1 — Admin users and dashboard analytics

- Extend the admin user read model with server-side Firebase identity state
  (UID, providers, disabled state, last sign-in and sync status) through a backend
  Firebase Admin gateway. Never call Firebase Admin from the browser.
- Treat internal DB as the authorization/business source of truth and Firebase as
  the authentication source; expose mismatches explicitly instead of silently
  overwriting either system.
- Add real aggregate dashboard endpoints and responsive charts only after metric
  definitions and database queries are verified. No production fixture metrics.

## Acceptance criteria

- Public navigation does not change unexpectedly after login.
- A mobile user can reach the primary destinations in one tap.
- No horizontal overflow at 360, 768, 1024, 1440, or 1920 px.
- Light and dark themes meet readable contrast for text and controls.
- Existing authorization and feature gates remain effective.
- Lint, typecheck, unit tests, build, and relevant E2E tests pass.

## Risks and controls

- Broad CSS regressions: migrate through semantic tokens and focused component tests.
- Role navigation regressions: retain existing visibility predicates and change presentation only.
- Release-gate leakage: reuse existing preview helpers; do not reproduce availability logic in CSS.
- Auth regressions: preserve request and session code; modify only shell and presentation layers.

## Delivery update - 2026-08-29

- Firebase-backed suspend/restore is enforced server-side before the internal
  status transition; session revocation and audit logging remain transactional.
- The operations dashboard renders a responsive, accessible dossier-stage chart
  from the existing aggregate API and uses semantic theme surfaces.
- Firebase read-side reconciliation metadata remains a follow-up. Implement it
  with batched server-side lookup or a background snapshot, never per-row browser
  calls.
