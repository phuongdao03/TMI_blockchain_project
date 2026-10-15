# Community test plan

Date: 2026-10-15. Focused verification will be added with each implementation slice.

## Backend behavior seams

- HTTP API with a real test database and authenticated test principal: public visibility, pagination/filtering, owner authorization, CSRF-protected mutation, moderation transitions, reports, media association access, notification deduplication.
- Recursive comment query and UI behavior: arbitrary-depth `parentId` values are preserved, replies are displayed as a flat list, and comment counts include descendants.
- Mention notification behavior: active-profile matching is case-insensitive and deduplicated, self-mentions are excluded, and post mentions fire only after publication.
- Migration seam: Alembic upgrade from current revision and downgrade of only community-owned objects.
- Settings boundary: community image count/size can be changed within the safe bounds and invalid values are rejected.
- Service behavior seam where transaction/race rules cannot be observed reliably through a single HTTP request: duplicate like/bookmark/follow constraints and status transition validation.

## Frontend behavior seams

- User-facing components/pages with Vitest and Testing Library: loading/empty/error states, category/filter state, editor validation, auth prompts, ownership menu, interaction feedback, moderation labels, and private/public author rendering.
- Editor autosave: a complete draft saves after the 1.2-second quiet period, repeated edits coalesce, queued uploads pause saves, and a failure can be retried.
- Playwright critical paths: public feed → post detail; login → draft/submit; moderator → review/report resolution; responsive navigation and discussion link from a public work.

## Security and regression matrix

- Anonymous vs. member vs. content owner vs. community moderator vs. superadmin.
- Draft/pending/rejected/hidden/deleted access by ID, slug, search, metadata, sitemap, and attachment URL.
- XSS payloads, invalid links, malformed tags, upload MIME/size mismatch, uninspected/rejected files, CSRF, rate limits, IDOR, and concurrent duplicate reactions.
- Existing nomination listing/detail, auth, upload, admin report, and mobile navigation journeys.

## Visual/accessibility checks

At 360, 768, and 1440 CSS px, in light and dark themes: keyboard-only operation, visible focus, screen-reader labels, dialog focus, reduced motion, text contrast, long content, image ratios, and no horizontal overflow.

## Commands

Use focused backend tests during each backend slice. Current commands from `backend/` and `frontend/` are:

- Backend community suite: `python -m pytest app/tests -q --tb=short -k community`
- Frontend full suite: `npm.cmd exec -- vitest run --maxWorkers=2 --configLoader runner`
- Frontend checks: `npm.cmd run lint -- --no-cache` and `npm.cmd exec -- tsc --noEmit --incremental false`
- Production build: `npm.cmd run build`

Run relevant Playwright specs before release. Do not claim browser or production evidence until the respective run is recorded.
