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
