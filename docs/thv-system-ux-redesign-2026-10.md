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
