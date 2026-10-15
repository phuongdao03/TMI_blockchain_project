# Spec: Tinh Hoa Việt Community Module

Date: 2026-10-15

Status: implemented and locally verified; deployment remains separate

## Objective

Add a small, integrated discussion forum to the existing `decu.tinhhoaviet.org.vn` application. Signed-in users can publish stories and discuss public nominations; visitors can read published content. Community content must remain clearly user-authored and separate from verified nomination records.

## Audited stack and existing boundaries

- Frontend: Next.js App Router 16, React 19, TypeScript; public routes live in `frontend/src/app/(public)`.
- Backend: FastAPI modular monolith, async SQLAlchemy, PostgreSQL, Alembic; business modules own models, schemas, repositories, services, routers, and tests.
- Authentication: existing cookie-backed application session. Use `CurrentPrincipalDependency` for reads that need identity and `CsrfProtectedPrincipalDependency` for mutations.
- Existing integrations: `public` owns published nomination visibility, `media` owns signed uploads and inspection, `notifications` owns in-app notifications, and `content_reports` provides a moderation workflow for published works.
- UI: public shell and theme tokens already exist. Use `PublicShell`, the shared API client, and semantic `--theme-*` tokens.

## Scope

- Public community feed, category pages, search, filters, paginated results, post detail, and member profile pages.
- Authenticated post and comment creation/edit/delete; drafts; tags; public image attachments; likes, bookmarks, follows, and reports.
- Community-specific profile handle and biography, without exposing private account fields.
- Community category management, post/comment/report moderation, configurable post approval, and moderation history.
- Public nomination links that resolve only to currently published works.
- In-app notifications for community activity, using the existing notification model/service.
- Mention notifications for active community members, deduplicated per post/comment and emitted only when a post becomes public.
- Controlled server-side draft autosave after a complete post pauses for 1.2 seconds.
- Responsive Vietnamese UI with existing light/dark themes and accessible controls.

The broader UI/UX refresh named in the supplied prompt is included in the phased plan. Its shared shell and existing-page changes follow the community foundations and must preserve current routes, permissions, and API contracts.

## Routes and contracts

Canonical frontend paths use English: `/community`, `/community/posts/[slug]`, `/community/new`, `/community/members/[username]`, `/community/saved`, and `/admin/community`. `/cong-dong` redirects to `/community` as a Vietnamese entry alias. API paths use `/api/v1/community/...`; UI copy remains Vietnamese.

List APIs are server-paginated and return the repository's standard success envelope. Mutations require the existing CSRF-protected session dependency. Public responses expose only community username, display name, and avatar; never email, phone, employment, or identity-verification fields.

## Data and behavior rules

- Community entities are separate from CMS posts and official `public_works`.
- Seed the six requested categories; administrators may add, edit, hide, and reorder categories.
- Posts have explicit `DRAFT`, `PENDING`, `PUBLISHED`, `REJECTED`, `HIDDEN`, and `DELETED` states. Default approval mode is pre-moderation until an administrator changes it.
- Comments retain arbitrary parent-child depth. API responses flatten replies beneath each paginated root while preserving each `parentId`; the UI labels reply targets without deeply nesting the page. Owners may edit/delete their own content; moderation is enforced in backend services.
- Database constraints prevent duplicate likes, bookmarks, and follows. Counters derive from committed relation rows or atomic updates.
- Draft, pending, hidden, deleted, and private content never appears in public APIs, search, metadata, or sitemap.
- Markdown input is stored as text and rendered with safe escaping; arbitrary HTML is rejected. Image uploads use the existing media inspection/quarantine pipeline with a community-specific purpose and association policy.
- Anonymous visitors have read-only community access: they may browse published posts, profiles, categories, and search, while every community write or interaction requires a signed-in session and CSRF protection. The UI links guests to sign-in when they try to participate.
- Members may set a community avatar by uploading a JPEG, PNG, or WebP image (up to the configured AVATAR limit) from their device. The existing private media upload and inspection pipeline is reused; only an inspected image owned by the member can be attached, and public delivery is scoped to an active community profile.
- Public nomination links resolve only through the existing published-work read model; community copy is labeled as user discussion.
- Mention syntax is `@username`, case-insensitive, limited to 20 distinct active profiles per post/comment. Mentions notify only after post publication; self-mentions are excluded.
- Autosave starts only after title, content, and category are valid. It persists a real draft through the community API and coalesces in-flight writes.
- Backend settings `COMMUNITY_POST_IMAGE_MAX_COUNT` and `COMMUNITY_POST_IMAGE_MAX_BYTES` configure limits (defaults: 5 images, 5 MiB; bounds: 1–10 images and 1–20 MiB). Build-time `NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_COUNT` and `NEXT_PUBLIC_COMMUNITY_POST_IMAGE_MAX_BYTES` provide matching frontend validation; backend limits remain authoritative.

## Success criteria

- A signed-in member can create a draft, submit it, and see its actual moderation state; authorized moderators can publish or reject it.
- Visitors can list and open published posts; private states remain inaccessible by ID and slug.
- Comments, likes, bookmarks, follows, reports, and admin moderation persist in PostgreSQL and respect ownership/permissions.
- Image attachments are inspected before publication and cannot be delivered outside an authorized published post.
- Public author cards reveal no private account fields.
- Anonymous visitors can read published community content but cannot mutate or participate; an authenticated member can upload, preview, save, and remove their own community avatar.
- Navigation, mobile layout, light/dark themes, accessibility states, and nomination links work without regressing existing journeys.
- Backend and frontend focused tests, typecheck/lint, and production builds pass; migration upgrade/downgrade is documented.
- Deep comment replies render in a flat conversation view, mentions create safe in-app notifications, and valid drafts autosave after the debounce.

## Commands

- Backend focused tests: `python -m pytest app/tests/test_community_*.py` (from `backend/`).
- Frontend focused tests: `npm.cmd test -- --run src/components/community` (from `frontend/`).
- Frontend checks: `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build` (from `frontend/`).
- Backend checks: `python -m ruff check app/modules/community app/api/v1/community.py app/tests/test_community_*.py` and `python -m mypy app` (from `backend/`, subject to configured environment).

## Boundaries

- Always reuse the current auth/session, database, API envelope, theme, and media infrastructure.
- Any new permission, media purpose, notification type, or schema change must have a migration and a focused regression test.
- Do not change nomination lifecycle, publish private nomination data, or add a second auth system.
- No production deployment or production data mutation is part of this implementation task.
- A transferred upload removed from the upload queue is deleted through the authenticated media endpoint; removing an image already attached to a saved draft only detaches it, so provider cleanup for that case remains manual.
