# Mobile discovery navigation and speed

## Objective

Signed-in mobile visitors can move from their workspace to search and the
nomination library without losing quick navigation. The return path must be easy
to recognize. Opening discovery pages should avoid redundant API requests and
unnecessary paint work.

## Acceptance criteria

- Search and library pages show a signed-in quick navigation with workspace,
  search, and library destinations; the current destination is marked.
- Guests keep the public navigation without workspace controls.
- The mobile return strip does not duplicate the quick navigation.
- Server-provided catalog data is reused briefly on hydration, and search facets
  load when needed.
- Mobile navigation does not require a blurred backdrop while scrolling.

## Implementation and verification

- Next.js 16 App Router, React 19, Vitest and Playwright in `frontend/`.
- Edit the existing public shell, catalog and search components and their
  focused tests.
- Run focused Vitest tests, typecheck, and mobile browser verification.
