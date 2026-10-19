# Role Based Help Center: Spec and Plan

Date: 2026-10-18

## Objective

Replace the separate, hard-coded public, account, and administrator guide surfaces with a searchable Help Center whose articles match implemented routes and access rules. Visitors can read public guides; signed-in users can read guides for their current roles and linked employee access; authorized administrators can draft, edit, publish, archive, and remove guide articles without changing source code.

## Audit findings

- The frontend is Next.js 16 / React 19 with an App Router, TypeScript, Tailwind CSS, and existing semantic theme tokens.
- Current guide surfaces are `/guide`, role-aware `/help`, and Super Admin only `/admin/guide`. Their content is hard-coded in the route files.
- There is no guide article model or guide API. The existing CMS already has drafts, publication status, version snapshots, audit records, HTML sanitization, categories, and Super Admin authorization.
- Product roles are `VIEWER`, `USER`, `MODERATOR`, and `SUPER_ADMIN`. `isEmployee` is a linked employee profile attribute and must not be presented as a product role.
- The preview release hides or redirects some dossier, review, certificate, notification, and payment paths. `/payments` has no list page; payment routes are per order. Guide links must use implemented paths and account for preview availability.
- Existing user edits include the CMS workspace and other unrelated files. This implementation will avoid overwriting those files.

## Contract and boundaries

- Public article APIs return only published articles explicitly tagged `PUBLIC`; public detail requests return 404 for every other article.
- Signed-in article APIs return published public articles plus articles whose role or employee audience matches the server-side principal. Drafts and archived articles remain private.
- Guide management is authorized server-side for the existing `SUPER_ADMIN` capability. A page-level role gate is only a UX guard.
- Article HTML uses the existing CMS sanitizer. Input schemas reject unknown fields, invalid slugs, unsupported audience values, and oversized content.
- Guide changes extend the existing CMS module and reuse its content status, category, audit, version, and sanitizer conventions. Existing news, pages, and banner APIs retain their current behavior.
- No new roles, permissions, authentication flows, external services, or dependencies.
- Feedback stores an anonymous per-browser token hash, vote, optional short comment, and timestamp only. It stores no account, IP address, or user agent and accepts one vote per article/token.

## UX and data requirements

- `/guide` is the public Help Center home with categorized guides, accent-insensitive title/body search, responsive navigation, and a keyboard-accessible search dialog (`Ctrl/Cmd+K`, arrows, Enter, Escape).
- `/guide/{slug}` serves public articles with breadcrumb, title, summary, applicable audience, reading estimate, modified date, sanitized content, generated heading links, related articles, and previous/next navigation.
- `/help` personalizes the article list using server-authorized role/employee visibility. `/help/{slug}` displays authorized internal articles.
- `/admin/guide/articles` provides search and filters for category, audience, and status; create/edit form; safe preview; draft, publish, archive, and delete actions; and updated/author metadata.
- Search supports case-insensitive Vietnamese with or without diacritics, relevance ordering, pagination, loading and empty states, and visible match highlights.
- Mobile navigation uses a drawer and collapsible contents list; layouts support keyboard use, focus states, reduced motion, and narrow screens without page-level horizontal overflow.
- Seeded guidance is limited to verified catalog, account, dossier, reviewer, employee, verification, and administration workflows. Employee is an audience attribute, not a role.
- Public guide metadata, canonical links, Open Graph data, and sitemap entries include only public published articles.

## Tech stack and structure

- Backend: FastAPI, SQLAlchemy async, Pydantic v2, Alembic. Extend `backend/app/modules/cms` with guide article and feedback persistence, service/repository methods, API contracts, authorization, and migration.
- Frontend: Next.js App Router and existing `frontend/src/lib/api/client.ts`; add reusable guide search, reader, and admin workspace components. Keep established routes and navigation compatible.
- Tests: pytest for service/API authorization, sanitization, search, lifecycle and feedback; Vitest for search, role filtering, navigation, article metadata and CMS actions; Playwright/browser inspection for responsive layout and keyboard interaction.

## Commands

- Backend focused: `python -m pytest backend/app/tests/test_cms_guide_articles.py backend/app/tests/test_cms_guide_api.py backend/app/tests/test_cms_guide_migration.py -q --tb=short`
- Frontend focused: `node ./node_modules/vitest/vitest.mjs run --configLoader runner src/components/guide/guide-search.test.ts src/components/guide/guide-content.test.ts src/components/guide/guide-center.test.tsx src/components/guide/guide-article-reader.test.tsx src/components/admin/guide-article-workspace.test.tsx src/app/user-guide-page.test.tsx src/app/account-guide-page.test.tsx src/app/admin-guide-page.test.tsx src/app/sitemap.xml/route.test.ts 'src/app/sitemaps/guides/[page]/route.test.ts'` (run from `frontend/`)
- Frontend typecheck: `node ./node_modules/typescript/bin/tsc --noEmit --incremental false --pretty false` (run from `frontend/`)
- Frontend lint: run ESLint on the changed guide routes, components, API modules, and tests.
- Browser: inspect public search and article navigation at desktop and 390 px mobile widths, light/dark modes, and keyboard search. A local API stub is used when no backend is running.

## Implementation plan

1. **CMS data and contracts** — add guide article/feedback models, validation, migration and reversible migration test. Seed verified guide articles with public, role and employee scopes. Acceptance: migration round-trips; existing CMS models and endpoints remain unchanged.
2. **CMS service and API** — implement public, authenticated, and administrator article queries; CRUD/status lifecycle; audience enforcement; accent-insensitive ranked search; safe anonymous feedback; audit/version records. Acceptance: unauthorized roles cannot list or fetch internal/draft content, and sanitization is applied on writes.
3. **Frontend API and search core** — add guide DTOs/client functions, accent normalization, result highlighting, keyboard dialog and focused tests. Acceptance: Vietnamese accent variants match; keyboard navigation and empty/loading states work.
4. **Public and role reader** — replace the hard-coded `/guide` and `/help` bodies with searchable categorized lists and article reader routes; add responsive sidebar, generated TOC, feedback, related and previous/next links, metadata and sitemap behavior. Acceptance: route links resolve and restricted content never enters public responses.
5. **Administration** — add a Super Admin guide workspace without changing the existing admin operations guide or the user-edited CMS workspace. Acceptance: draft, edit, preview, publish, archive, delete, audience and category workflows persist through the API.
6. **Verification and handoff** — run focused backend/frontend tests, typecheck/lint as the current worktree permits, inspect browser at mobile/tablet/desktop and light/dark themes, audit routes and access boundaries, then record remaining gaps in `docs/handoffs/role-based-help-center.md`.

## Success criteria

- The guide center uses implemented roles and routes only; no invented role or unavailable feature is described as active.
- Anonymous visitors receive public published content only; authenticated users receive only their role/employee-scoped content; admin writes are server-authorized.
- Search, article navigation, feedback, and CMS lifecycle operate against the backend.
- Public and internal article URLs, responsive navigation, TOC, keyboard access, metadata, and sitemap rules work as described.
- Existing public catalog, account, dossier, review, admin, CMS, and authentication flows remain compatible.
- Tests and browser checks cover the critical boundaries; unverified items are named in the handoff.

## Explicit non-goals

- Creating new product roles or granting permissions.
- Replacing the existing CMS, auth/session system, or public shell.
- Adding external search, rich text editor, analytics, or view counters.
- Claiming production readiness without successful migration, permission, and browser verification.
