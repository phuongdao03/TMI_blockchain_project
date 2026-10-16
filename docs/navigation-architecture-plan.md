# Navigation architecture implementation plan

1. [x] **Authentication destinations** — preserve safe local paths and queries through password, Google, registration, and protected-route login; default to `/workspace`.
2. [x] **Workspace and menus** — add `/workspace`, retain `/dashboard`, add the public account menu and permission-aware admin entry, and return logout to the public site.
3. [x] **Navigation areas** — separate personal and admin navigation while keeping links to Website, Community, and role-permitted operations.
4. [x] **Mobile navigation** — add the five public destinations and keep admin routes on the separate drawer; include safe-area spacing and overlay ordering.
5. [x] **Verification and handoff** — focused tests, TypeScript, lint, local HTTP redirect checks, and handoff documentation completed. CUA had no available browser for screenshot review.
