# Tinh Hoa Viet: UX audit and redesign plan

Date: 2026-10-07. Scope: authenticated dossier, reviewer, and admin journeys in the Next.js frontend. This is a source audit; usability claims still need observation with real users.

## Objective and constraints

Make each role see its current task, status, and next action without changing authorization, API contracts, dossier state transitions, database schema, or blockchain operations. The backend's versioned dossier type and document rules remain the source of truth. A draft must exist before a file can be attached.

## Current system

- Next.js 16 App Router, React 19, TypeScript, Tailwind 4, semantic theme tokens. TanStack Query loads API data; React Hook Form and Zod validate the creation and review forms.
- Dashboard routes live in `frontend/src/app/(dashboard)`; authentication is checked in its layout and role gates protect dossier, review, and admin routes. `role-workspaces.ts` resolves the entry workspace. Permissions in the navigation are presentation only; server authorization remains authoritative.
- `dossierApi` exposes type discovery, draft creation, detail, evidence attachment, submit/resubmit, versions, and timeline. `reviewApi` exposes assignment list/detail, draft save, and submit. `adminReviewApi` exposes admin queues and decisions. Dossier status is a 16-value backend contract, not a UI-defined workflow.
- Shared surfaces already exist: `dossier-status`, `dossier-workflow-timeline`, `review-workspace`, `five-t-scorecard`, confirmation dialog, buttons, form controls, shell and navigation. Existing behavior includes autosave, preflight document rules, reviewer completion checks, and admin assignment. Preserve these.

## Screen audit

| Role | Screen / route | Purpose | Observed UX issue | Priority | Improvement |
| --- | --- | --- | --- | --- | --- |
| User | Dashboard `/dashboard` | Resume work | Three counts are calculated from the first five dossiers, yet read as totals. Hero can displace the create action when an older dossier needs attention. | P0 | Label sample counts honestly until an aggregate endpoint exists; keep a visible `Nộp hồ sơ mới` action. |
| User | New dossier `/dossiers/new` | Select type and prepare draft | Type, document preflight, title, summary, visibility and every schema field render on one screen. Upload occurs only after draft creation, so the visible three-step journey spans two routes. | P0 | Progressive type → core fields → required schema fields → draft confirmation; then upload → final review → receipt in the existing detail route. Preserve entered data on back/validation errors. |
| User | Dossier detail `/dossiers/[id]` | Upload, submit, track | Preparation steps are present, but status guidance is generic for `NEEDS_SUPPLEMENT`; submit success has no dedicated receipt with code and next step. | P0 | Surface an available request reason from the timeline, add a completion receipt after successful submit, and retain the existing version/history panels under details. |
| User | Dossier list `/dossiers` | Track dossiers | Each row gives status and a next-action sentence; filters and empty state exist. Status-specific action is still a generic detail link for many states. | P1 | Group `Cần bạn xử lý`, `Đang xử lý`, `Hoàn tất`; use action labels matching the status and preserve current pagination. |
| Reviewer | Dashboard `/dashboard` | Find assigned work | Role overview links to `/reviews`, but primary workspace routing points to `/work-allocations`; the two queues compete for attention. | P1 | Make `/reviews` the explicit review entry for staff who can review; keep work allocations for broader tasks. |
| Reviewer | Queue `/reviews` | Pick next assignment | Deadline and action are visible, but no clear today/late priority order is surfaced. List summary API has no applicant name or submitted date. | P1 | Separate overdue/active/completed work using existing status and due date; request extra fields only if product evidence justifies an API addition. |
| Reviewer | Workspace `/reviews/[assignmentId]` | Inspect evidence and submit assessment | Locked evidence, deadline, scorecard and next action exist. The 5T scorecard renders all criteria expanded, followed by findings/checklist, making the form long. | P0 | One criterion at a time or accessible disclosure groups, persistent progress, explicit blockers and final review; retain autosave and submit confirmation. |
| Admin | Portal `/admin` and operations `/admin/dashboard` | Decide today's work | Operations charts and many module cards appear before a direct intake/assignment path. There are two competing overview destinations. | P0 | Lead with dossier stages and actionable queues, then diagnostics. Treat `/admin` as the task hub and `/admin/dashboard` as operational analytics. |
| Admin | Review queue `/admin/reviews` and detail | Assign reviewer, inspect outcome, decide | Queue and decision routes exist but are absent from sidebar navigation; empty/error states do not offer retry or the next useful action. | P0 | Add permission-gated `Tiếp nhận & phân công` navigation, stage tabs, and contextual empty/error actions. |
| Admin | Work allocations, users, HR, certificates, finance, content, audit | Manage supporting operations | Sidebar has a long, mostly flat `Điều hành` group mixing dossier work with HR and settings. | P1/P2 | Group by task: dossier workflow, people, finance, system. Preserve permission filtering and existing routes. |
| All | Shell, statuses, form controls, loading/error states | Orient and recover | Design tokens and many states already exist, but some pages use one-off surfaces and generic recovery copy. | P1 | Share status guidance and state patterns; test keyboard, narrow viewport and contrast on each critical journey. |

## Information architecture

Navigation must expose existing routes according to actual permission, rather than implying a new role or granting access from the client.

```text
User: Tổng quan /dashboard
  → Hồ sơ của tôi /dossiers → Nộp hồ sơ mới /dossiers/new
  → Hồ sơ chi tiết /dossiers/[id] → Bằng xác lập /certificates
  → Thông báo /notifications → Tài khoản /account → Trợ giúp /help

Reviewer: Việc thẩm định /reviews → Phiếu thẩm định /reviews/[assignmentId]
  → Công việc khác /work-allocations → Thông báo /notifications
  → Nhân sự cá nhân (if applicable) → Trợ giúp /help

Admin: Công việc hôm nay /admin
  → Tiếp nhận & phân công /admin/reviews → Hồ sơ /admin/reviews/[dossierId]
  → Theo dõi vận hành /admin/dashboard
  → Công việc /admin/work-allocations → Người dùng & nhân sự
  → Tài chính & phát hành → Nội dung → Báo cáo & lịch sử
```

## Journeys and state contract

### User

1. Select a live dossier type returned by `/dossiers/types`; explain its required fields and files in plain language.
2. Enter core information, then type-specific required information. Keep optional metadata in a secondary section and preserve values between steps.
3. Review the draft information and create the draft with the current `POST /dossiers` contract. Explain that this is not yet submission.
4. Upload files into each server-defined document rule on `/dossiers/[id]`; show accepted MIME types, limit, count, upload state and retry. Keep evidence access rules unchanged.
5. Review title, type, files, visibility and missing requirements. Submit with the current idempotent endpoint. Show a receipt with code, submitted time, resulting status, next step and a link to detail/list. For supplementation use the existing resubmit endpoint.
6. Track a single current stage, meaningful status explanation, requested correction when available, and historical versions under details. Never invent an SLA.

### Reviewer

1. Open assigned or in-progress work from `/reviews`; show due date and the direct `Thẩm định` action.
2. In the workspace, identify dossier and locked version, inspect evidence, complete any required evidence assessments, rubric gates and 5T criteria.
3. Show criterion progress and first blocking item. Keep applicant feedback separate from private notes. Save the validated draft, confirm irreversible submission, then show submitted state.

### Admin

1. Open `/admin` and see actionable counts or queues first: newly submitted/precheck, assignment needed, reviews in progress, decision needed, payment/issuance exceptions.
2. Open `/admin/reviews` to route a dossier to a reviewer using current permissions and transitions. Admin does not write the reviewer's assessment.
3. Read submitted reviewer reports and make the existing final decision. Payment, signing, certificate and publication remain separate existing steps; the UI presents them in order and links to the responsible workspace.

## State and component rules

- Preserve all 16 dossier statuses and five reviewer assignment statuses. Centralize label, semantic tone, description and next action in one presenter reused by dashboard, list and detail. A badge alone never explains `NEEDS_SUPPLEMENT`.
- Keep `DossierStatusBadge`, `DossierWorkflowTimeline`, button/form/dialog primitives, query keys and current validation. Add a shared stepper/receipt only when the first vertical slice needs it.
- Use one primary action per step. Loading reserves space; empty states give the next useful route; errors include retry when a query can be retried. Confirmation names the action and effect.
- The admin workflow diagram is explanatory. It must follow actual transition rules; do not expose disabled actions merely to make the diagram look complete.

## Implementation slices

1. **P0 user creation**: progressive preparation within the current form, current API, focused component tests; verify type switching and validation preserve inputs.
2. **P0 upload and receipt**: retain media upload and submit/resubmit, add a reliable success receipt and contextual supplement request; verify duplicate submit prevention and version history.
3. **P0 reviewer**: accessible criterion disclosure and completion path; verify autosave, evidence requirements, submit confirmation and read-only state.
4. **P0 admin**: workflow-first portal and permission-gated review queue navigation; verify assignment, submitted report and final decision links.
5. **P1 dashboards and IA**: remove misleading counts, make role navigation coherent, improve list status actions and recovery states.
6. **P2 supporting screens**: user management, analytics, HR, finance, publication and blockchain copy/visual polish after critical journeys work.

## Verification and boundaries

- Commands from `frontend/`: `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd test -- --run`, `npm.cmd run build`; run focused Playwright journeys in `frontend/e2e` for each role after each slice.
- Check 360, 768 and 1440 px, keyboard-only navigation, visible focus, screen reader names, no horizontal overflow, and light/dark state. Test loading, empty, error, validation, success, and permission denial.
- No new dependency, database migration, role change, or blockchain transaction is part of this plan. No production submission or approval is used for verification without a dedicated test environment.
- Backend limitations: dossier list is paginated, so the dashboard cannot claim global status totals from its first page; reviewer summary lacks applicant and submitted date; a precise supplement instruction depends on a reason being available in existing history. Record these honestly until a backward-compatible API enhancement is explicitly scoped.

## Acceptance checks

- New users can find `Nộp hồ sơ mới`, complete the guided path and distinguish draft creation from final submission.
- A dossier needing changes states what to do, or says clearly when the available API does not provide the requested detail.
- A reviewer can identify the next unfinished criterion and submit without hunting across the page.
- An admin can reach intake, assignment and decisions directly from the task hub and navigation.
- Existing role gates, API payloads, dossier transitions, file access and blockchain behavior remain intact.

## Delivery status for this pass

- Implemented: role navigation for review intake; honest scope for user dashboard counters; staged type/core/type-specific/review creation with a full input summary; document-rule selection and upload after draft creation; submission receipt and supplement reason from dossier history; editing resumes when a submitted dossier later needs a supplement; autosave blocks step changes while data is unsaved and preserves edits made during an in-flight request; collapsed 5T criterion groups; ordered admin workflow entry; paginated admin intake with retry and stage-aware action; real admin stage counts linked to filtered queues; grouped dossier status filtering with all 16 statuses; reviewer queue priority for overdue work within the current page.
- Verified: 633 frontend tests, 33 focused backend Cloudinary/blockchain tests, full ESLint, TypeScript, production build and `git diff --check` passed. After the final copy change, focused form tests, lint and production build passed. Chrome opened four role previews at 390 px: all had matching document widths with no horizontal overflow or console errors. A screenshot request stalled and was stopped; visual inspection from that request is not claimed. Authenticated browser E2E was attempted but the local Playwright/dev-server harness stalled, so end-to-end behavior is not claimed as verified.
- Remaining: authenticated role journeys on staging or a local backend with test accounts; mobile device validation of upload, install and animations; audit secondary HR/finance/content/settings screens beyond the critical dossier path. Queue priority is limited to the current server page. The existing PATCH dossier contract cannot change type-specific `formData` after draft creation; the confirmation step now states this limitation. Cloudinary delivery and blockchain signing still require staging credentials and live integration validation. No backend contract was changed for the UX workflow.

## Public UI follow-up — 2026-10-09

- Audited the live public home, library, process, login and registration routes. Authenticated routes redirected to login without a session; no production data was changed.
- Kept the existing pending editorial typography, mobile menu, reviewer anchors and admin queue work. Added a two-row public header at 1280–1664 px so all six destinations remain visible without clipping. Fixed sticky-header offsets for public in-page anchors and removed the duplicate accessible close control from the menu backdrop.
- Browser checks: loaded local public routes at 320, 360, 375, 390, 430, 768 and 1280 px showed no horizontal overflow or page errors. Live home at 320, 390, 430, 768 and 1280 px also showed no horizontal overflow. Local menu navigation and document anchors were exercised directly.
- Verification: full frontend tests, lint, typecheck, production build and `git diff --check` passed; focused tests also passed after the final contact correction. A focused admin Playwright run against the repository's mock server stalled during startup and was stopped, so authenticated E2E is not claimed. Authenticated staging journeys still require role-specific test accounts. The pending footer contact change was reverted to the production/proposal contact details.

## Protected mobile follow-up — 2026-10-09

- Applicant creation now filters the actual dossier types by Vietnamese text with or without accents. The list uses page scrolling on mobile, so all choices and the next action remain reachable. Type selection and progression to the information step were exercised against the local mock API.
- Reviewer queue filters are collapsed until requested, bringing the current assignment action into the first 390 px viewport. The URL-driven filter and its existing query behavior remain intact.
- Admin home presents workflow steps and live stage counts as compact mobile rows. Diagnostic charts and job operations remain on the existing `/admin/dashboard` route; the home emphasizes links to work queues. No API or permission logic changed.
- Chrome with the repository mock API loaded these three protected routes at 320, 360, 375, 390, 430, 768 and 1280 px with no horizontal overflow. This is a local mock-backed browser check, not a production or staging role test.
- Verification for this follow-up: the full 647-test frontend suite passed; the dossier form tests passed again after the final selection hint. ESLint, TypeScript typecheck, production build and `git diff --check` passed after the final code edit. The existing Next image warnings in the test environment did not fail the suite.

## Homepage visual pass — 2026-10-09

- Kept the established section order: introduction, program mission, institution documents and gallery, journey, fields, published nominations, account action. The published nominations section remains near the end as requested.
- Unified homepage display headings on Newsreader with a responsive size scale and room for Vietnamese diacritics. Tightened section spacing without shortening or moving brand and institutional content.
- Shortened the mobile hero by omitting its duplicate large emblem below the header; the official brand mark remains in the sticky header. At 769–1023 px, a smaller emblem balances the intro while the primary actions stay visible beside it.
- Restricted entrance motion to the hero and reduced hover travel on journey links. Pressed buttons respond immediately; reduced-motion preference disables decorative motion.
- Tightened the three existing field descriptions on mobile with consistent separators and spacing; their content and place in the page did not change.
- Verified the revised homepage in Chrome at 320, 360, 390, 430, 768, 769, 820, 900, 1023, 1024, 1280 and 1440 px: no horizontal overflow; section order and main actions remain intact. At 820 px, both CTAs stay within the first viewport. The establishment-document anchor resolves, the search form still submits to `/works`, and reduced-motion disables hero animation.
- Focused homepage/media tests (8), ESLint, TypeScript typecheck, production build and `git diff --check` passed after this visual pass. No production content or data was changed.

## Mobile hero and header refinement — 2026-10-10

- Changed the public header wordmark to the existing Newsreader display serif, with a title-case name and a compact institutional line. The official logo asset remains in place.
- Removed the oversized hero seal above the mobile headline. A small seal now accompanies the establishment note after the main actions; desktop keeps its right-side seal. Homepage sections retain their existing order.
- Reduced the mobile primary action width and hero height. Kept the establishment-document link and search route unchanged.
- Verified the production build in Chrome at 320, 360, 375, 390, 430 and 768 px: the wordmark uses Newsreader, the primary action and establishment note are visible, and there is no horizontal overflow. Focused homepage/brand tests, targeted ESLint, TypeScript production compilation and `git diff --check` passed. Physical-device testing and deployment remain outstanding.

## Opening section reflow — 2026-10-10

- Reworked the phone and tablet hero as a single editorial reading path on a warm paper surface: introduction, actions, then establishment note. The header carries the only visible seal on these widths; the desktop illustration remains in place.
- Kept the primary discovery action full width on phones and paired it with the document link on tablet. The mobile header is shorter while its official logo and serif name stay legible. The search and published nominations stay in their existing later positions.
- Set the desktop hero illustration to native lazy loading, as it is hidden on mobile. Chrome checks against the new production build at 320, 360, 375, 390, 430, 768 and 1280 px showed no horizontal overflow. Focused homepage and brand tests passed (9/9); targeted ESLint and the production build passed. Physical-device testing and deployment remain outstanding.

## Mobile hero theme correction — 2026-10-10

- Fixed the dark-mode contrast regression caused by older `!important` text colors combined with the new light hero background. The mobile hero now has separate light and dark surface, text, action and divider colors.
- Checked both themes against the production build in Chrome at 390 px, including switching to dark mode through the mobile menu. Titles, supporting copy, actions and establishment text are readable in each mode, with no horizontal overflow. The production build, 9 focused homepage/theme tests and `git diff --check` passed. Physical-device testing and deployment remain outstanding.

## Mobile identity and account entry — 2026-10-10

- Added a compact official seal beside the hero's organization label on phone and tablet, with a circular crop that works on both light and dark surfaces. The larger desktop seal remains in its existing position.
- Replaced the hero's discovery CTA with direct `/register` and `/login` actions. The establishment-document anchor remains below them. The public works route remains available through navigation and the later discovery sections.
- Shortened the hero's supporting sentence and hid the repeated establishment paragraph on mobile; the full Decision 55 facts and document remain in the institution section below. Homepage section order is unchanged.
- Focused homepage tests passed (5/5). The production build and Chrome checks at 320, 360, 375, 390, 430, 768 and 1280 px passed with no horizontal overflow. Both mobile themes and the menu theme switch were checked. Physical-device validation and deployment remain outstanding.

## Mobile seal placement follow-up — 2026-10-10

- Moved the extra mobile seal out of the hero to the program introduction, immediately after its lead paragraph and before “Lời mời đồng hành”. The official header logo and desktop hero illustration remain in place.
- Centered the circular seal at 112 px on phone and tablet; restored the small hero kicker dot. The homepage section order is unchanged.
- The focused homepage tests, targeted ESLint and production build passed. Chrome checks at 320, 360, 390, 430, 768 and 1280 px found no horizontal overflow or page errors. Physical-device validation and deployment remain outstanding.

## Desktop account action deduplication — 2026-10-10

- At 1280 px and wider, the header already exposes `/register` and `/login`, so the duplicated hero pair is hidden. Below 1280 px the header pair is hidden and the hero pair remains visible.
- Chrome checks at 390, 768, 1216, 1279, 1280, 1440 and 1920 px confirmed one visible account pair per viewport, the establishment-document link remained visible, and no horizontal overflow occurred. The production build passed.

## Full desktop introduction restored — 2026-10-10

- Restored the complete public introduction on screens from 1280 px, including the original description, nomination discovery action and hero search. The establishment facts now sit between the story and actions; the right-side official seal is larger on wide screens.
- Kept the short account-oriented copy and account actions below 1280 px. Search remains in the later discovery section on mobile, not in its hero. Desktop account actions stay in the header, avoiding duplicate sign-in and registration buttons.
- Focused homepage tests (5/5), targeted ESLint and the production build passed. Chrome verified dark mode at 390, 768, 1024, 1279, 1280, 1440 and 1920 px plus light mode at 1920 px, with no page errors or horizontal overflow. Physical-device testing and deployment remain outstanding.
