# Tinh Hoa Việt UX/UI transformation 2026

## Scope and baseline — 2026-10-27

Implement the supplied master brief incrementally in the existing Next.js 16,
React 19, Tailwind 4 and FastAPI application. Preserve routes, authorization,
business states, pricing configuration, private evidence and payment contracts.
Existing redesign evidence is in `thv-system-ux-redesign-2026-10.md` and
`UI_UX_AUDIT.md`; it does not establish current staging acceptance.

## Current audit

| Priority     | Route / role                        | Evidence                                                                                                           | Change / acceptance                                                                                                        |
| ------------ | ----------------------------------- | ------------------------------------------------------------------------------------------------------------------ | -------------------------------------------------------------------------------------------------------------------------- |
| P1           | `/dashboard`, applicant, all widths | Source selects its priority from five recent dossiers only; an older supplementation request can disappear         | Fetch actionable statuses through existing server filters; show up to three prioritized tasks, including older requests    |
| P1           | `/dashboard`, applicant, mobile     | Large decorative hero precedes work; fake “Cập nhật gần nhất” lists product promises rather than activity          | Compact task surface; real next actions and timestamps; remove simulated activity                                          |
| P1           | `/dashboard`, applicant             | Row shows only title/code/badge; pending fee copy assumes issuance                                                 | Show next action and date per row; use neutral fee copy pending verified obligation                                        |
| P2           | `/`, guest                          | Live browser: hero primarily offers registration/login; process and discovery appear much lower                    | Task-first nomination/discovery links; preserve legal content                                                              |
| P1           | `/community/new`, author            | Full suite exposed nested `<form>` from image dialog inside editor                                                 | Replaced dialog form with an explicit non-submit close button; regression proves no parent submission                      |
| P0 gap       | Submission/payment workflow         | `DossierService._submit` transitions to `SUBMITTED`; `FeeObligationService` only accepts approved dossiers         | Resolved in source after user chose replacement charging; see SUBMISSION_FEE_MIGRATION.md. Production migration is pending |
| P1 resolved locally | `/dossiers/new`, applicant    | Pre-creation state previously existed only in React memory | Revision-based account recovery, session backup and explicit device conflict choices implemented; migration 0144 pending deployment |
| Validation   | Authenticated routes                | No staging credentials supplied                                                                                    | Local fixture browser checks are explicitly distinct from staging verification                                             |

Live home inspected using Chrome DevTools; no console errors were reported.
DevTools window resizing did not produce the requested 390px layout viewport
(reported 501px); use Playwright viewport emulation for exact-width acceptance.
DevTools screenshot file output is unavailable under its configured workspace
roots; use local Playwright for repository screenshots.

## Information architecture

- Guest: discover → understand process/cost → nominate; verify independently.
- Applicant: tasks → dossiers → notifications/account; wallet, membership,
  advertising and community remain explicit destinations.
- Reviewer: assignments → evidence → assessment; keep commercial information
  outside the assessment surface.
- Admin: intake/assignment → decisions → operations; preserve permission gates.

## Ordered implementation tasks

1. Applicant task overview (existing dossier API only). Acceptance: older
   actionable dossiers appear; supplement/payment precede drafts; at most three
   tasks; no action panel when none; retry on failure; loading never implies no
   tasks. Recent rows show date and next action.
2. Public task entry and navigation audit. Acceptance: nomination, discovery,
   process and verification reachable; exact-width checks at
   360/375/390/430/768/1024/1440.
3. Revalidate auth/session and wizard regression tests before changing their
   already implemented synchronization/autosave behavior.
4. Audit remaining review, finance, membership, community, advertising and admin
   journeys against backend behavior. Record unverified integration and
   physical-device behavior; do not mark the entire brief complete early.

## Implementation and verification conventions

Use existing semantic CSS tokens and accessible native links/buttons. Reuse
`dossierKeys.list` and `dossierApi.list`; do not fetch every dossier or infer
global totals from a page. New tests live beside the changed component.

From `frontend/`:
`npm test -- src/components/dashboard/dashboard-overview.test.tsx`,
`npm run lint`, `npm run typecheck`, `npm run build`. Browser checks use local
mock-backed sessions and screenshots, plus live read-only public inspection. No
production deployment, real payment, database reset, new dependency or migration
was performed in this pass.

## Delivery evidence

Implemented the applicant task overview, compact recent list and service links,
task-first public hero, desktop CTA visibility, mobile CTA ordering, and image
dialog hydration fix. Kept existing theme tokens, legal content and role gates.
Removed the large applicant hero, sample-based status metrics and simulated
activity. Recent rows use server timestamps and status-specific next actions.

The task lookup uses three bounded existing `GET /api/v1/dossiers` queries
(`NEEDS_SUPPLEMENT`, `PAYMENT_PENDING`, `DRAFT`, each `pageSize=3`) alongside
the recent page. Existing TanStack Query keys provide caching and invalidation.
Supplementation and payments precede drafts; at most three actions appear.
Failures offer retry without pretending there are no tasks. No backend contract,
price, wallet debit, publication transition or database table changed.

Validation:

- 919 frontend tests passed across 225 files, with `--maxWorkers=2`. An earlier
  concurrent run timed out in an advertising test; its isolated run and the
  complete bounded-worker rerun passed. Existing jsdom image/layout and payment
  mock warnings remain; no clean-console claim is made for the entire unit
  suite.
- Six desktop and six mobile Chrome Playwright cases passed: task priority,
  light/dark layouts, public CTA/return destination, guest actions at every
  viewport, session reload/logout, refresh-cookie recovery and cross-tab logout.
  The final mobile hero/screenshot follow-up passed both affected cases again.
- Exact widths: 360, 375, 390, 430, 768, 1024, 1440. Dashboard browser case
  checks both resolved themes, keyboard focus, no horizontal overflow and page
  errors.
- Live public audit: eight routes × seven widths, no horizontal overflow or
  `pageerror` events. This is not exhaustive console/network/accessibility
  testing.
- ESLint: zero errors, five existing unused-variable warnings in
  `community-vip-rooms.tsx` and `membership-chat-access-admin.tsx`.
- Typecheck, production build and `git diff --check` passed.

Evidence: [public audit JSON](ux-evidence-2026-10-27/public-audit.json),
[home before / mobile](ux-evidence-2026-10-27/home-before-390.png),
[home after / mobile](ux-evidence-2026-10-27/home-390.png),
[home after / desktop](ux-evidence-2026-10-27/home-1440.png),
[dashboard / mobile light](ux-evidence-2026-10-27/tasks-light-390.png),
[dashboard / mobile dark](ux-evidence-2026-10-27/tasks-dark-390.png),
[dashboard / desktop](ux-evidence-2026-10-27/tasks-light-1440.png). Before
screenshots are production guest pages; after screenshots use the local app.
Dashboard screenshots use explicitly synthetic fixture data. No authenticated
production before screenshot was available.

## Existing modules and remaining acceptance

| Area             | Current source foundation                                                                 | Outstanding acceptance                                                                                         |
| ---------------- | ----------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- |
| Auth/navigation  | `user-context.tsx`, `session-sync.ts`, `shells.tsx`, `dashboard-navigation.tsx`           | Local session regression passed; real staging MFA and role accounts still needed                               |
| Dossiers         | `dossier-create-form.tsx`, `dossier-workspace.tsx`, `dossier-workflow-timeline.tsx`       | Real device upload; deploy and stage-test prepared fee/recovery migrations |
| Reviewer         | `review-workspace.tsx`, `use-review-autosave.ts`, existing permission and conflict checks | Authenticated staging evidence/review/supplementation journey                                                  |
| Wallet           | `wallet-workspace.tsx`, backend wallet/payment services                                   | Provider sandbox top-up, timeout/reconciliation/idempotent debit integration                                   |
| Membership       | Catalog-backed pricing and `membership-workspace.tsx`                                     | Staging expiry/upgrade/benefit fulfillment and actual asset placement                                          |
| Advertising      | Existing moderation, reservation, wallet checkout and campaign workspaces                 | PostgreSQL last-slot concurrency and real sandbox booking; independent publication acceptance                  |
| Public discovery | `/works`, `/verify`, `/process`, `/community` inspected live                              | Real detail/withdrawn-proof fixtures; exhaustive accessibility and performance measurement                     |
| Admin            | Existing intake, assignment, finance, HR, CMS and audit workspaces                        | Route-by-route staging/mobile operations review                                                                |

No measured Core Web Vitals, real-user conversion improvement, physical Safari
testing, complete WCAG conformance or sitewide completion is claimed.

## Submission-fee follow-up

The user confirmed replacement charging at submission. New-policy dossiers now
pay before review and reuse that payment at approval. Existing dossiers retain
the legacy policy. See [migration and validation](SUBMISSION_FEE_MIGRATION.md).
This supersedes the earlier audit gap and business clarification; no production
migration or real payment was performed.

The fee follow-up passed backend regression/payment suites, schema
compatibility, mypy across 454 source files, Ruff, frontend lint/typecheck/build
and desktop/mobile checkout recovery. The full frontend run passed 922 tests;
the added pricing-error recovery case and updated guidance passed focused tests
afterwards. Invoice screenshots use local fixtures.

## Preparation recovery follow-up

Pre-creation recovery is implemented across refresh and browser contexts, with
explicit conflict resolution, account isolation and atomic draft creation.
See [contract, migration and verification](DOSSIER_PREPARATION_RECOVERY.md).
This closes the local refresh-recovery gap. Migration 0144 remains unapplied
to production; real sessions and PostgreSQL concurrency need staging acceptance.

## Role route audit and mobile corrections

Audited 16 local fixture-backed routes: applicant dashboard, dossiers, creation,
wallet, membership, advertising, notifications and account; reviewer assignments;
admin overview, intake, users, payments, content, memberships and advertising.
Each passed horizontal-overflow checks at seven widths (360–1440 px), in both
themes. Desktop axe checks using WCAG 2 A/AA and 2.1 AA tags found no violations
on these initial route states. This does not establish full accessibility
conformance or exercise every editor, dialog and operational action.

The audit found and fixed nested main landmarks in admin payment requests and
applicant checkout. The public-work editor's automatic grid tracks allowed its
long public URL to force mobile overflow; explicit shrinkable single-column
tracks and a shrinkable URL cell now preserve the viewport width.

Evidence: `ux-evidence-2026-10-27/role-audit-*.json`,
`content-overflow-before.png`, `content-light-390.png`, `content-dark-390.png`,
and desktop equivalents. Screenshots use synthetic local data. The browser
audit remains a repeatable test in `e2e/role-route-audit.spec.ts`.

Final code checks: 932 frontend tests across 226 files, 21 focused backend
tests, TypeScript, production build, Ruff and diff whitespace checks passed.
Full ESLint has zero errors and the same five pre-existing warnings; final
edited components/browser tests also passed focused lint. Existing jsdom image
and payment mock warnings remain. Browser fixtures now reset preparation state
before independent wizard cases so server persistence cannot contaminate them.
The final desktop/mobile wizard, recovery, reviewer and fee rerun passed 11
cases; one mobile-only layout case was intentionally skipped on desktop.

## Full-brief reconciliation follow-up

The section-by-section inventory is now
[MASTER_PROMPT_ACCEPTANCE_2026.md](MASTER_PROMPT_ACCEPTANCE_2026.md), including
an explicit external-acceptance matrix, minimum lawful measurement proposal and
five usability scripts. The master brief is not fully accepted merely because
the locally implemented routes pass tests.

Closed two further source gaps: live applicant wallet/unread context with
independent error recovery; and owner-only optional promotion links in the
approved/published dossier view. Ordinary publication tracking stays available
without advertising. Promotion passes the original dossier ID to existing
booking UI, including older dossiers outside the first 100 results. It does not
change publication permissions/state or charge another submission fee.

Broader local verification passed 24 desktop/mobile E2E cases for applicant
tasks/account context, membership cards/room access, reviewer document/criteria
submission, and certificate verification. Another two desktop/mobile cases
verified ordinary-publication tracking and promotion of the same older dossier.
Backend wallet/API, membership, publication, advertising inventory and delivery
regressions passed 37 tests. Provider integration and PostgreSQL contention
remain unverified. Verification pages emitted existing image-loading/LCP
recommendations; no field performance improvement is claimed.

Visual review also exposed a published dossier still marked as receiving its
certificate. Timeline now has an explicit publication stage and treats published
as completed; certificate issuance and future publication remain distinct.
Focused timeline/workspace tests and desktop/mobile promotion reruns passed.

Final stable-source regression run: **942 frontend tests across 228 files
passed**. The earlier in-flight full run loaded the pre-fix timeline module;
the focused rerun and this complete stable-source run supersede that result.
Final lint/typecheck/build and whitespace checks passed (five existing lint
warnings remain). Account-summary screenshots now persist in the evidence
directory; mobile and desktop screenshots were visually inspected.

## Certificate sharing and expanded mobile accessibility

Native share cancellation and denied clipboard writes previously produced
uncaught promise rejections. Sharing now handles cancellation without an error,
announces confirmed copying, prevents repeated in-flight actions and provides a
selectable canonical verification link when automatic sharing is unavailable.
Feedback is scoped to the certificate number. No new API or migration.

The 390px axe check exposed low-contrast certificate gold labels, legacy muted
text on dossier/reviewer pages (4.11:1 on cream), and a dark notification eyebrow
(2.07:1). Fixed these specific surfaces using darker certificate text and the
existing semantic muted/accent tokens. No global palette replacement.

Role-route axe checks now cover 390 and 1440 px in both themes, with motion
reduced to inspect resolved states. They still do not establish full WCAG
conformance. Browser reports include detailed failure summaries and widths.
Certificate sharing screenshots are `share-recovery-*.png` in the evidence
directory. Existing image-loading/LCP suggestions remain unaddressed here.

Docker daemon is unavailable and no disposable PostgreSQL test URL is set;
concurrency acceptance remains unexecuted. No production operations occurred.

Follow-up validation passed: 10 focused unit cases; 11 browser cases (eight
certificate cases plus three role audits); three intentionally skipped duplicate
role audits in the mobile project. The role audits include 64 axe scans across
16 routes, two widths and two themes with zero final violations, plus the seven
width overflow checks. This is Chrome emulation and resolved initial-state
coverage, not physical-device or complete WCAG acceptance. Focused lint,
typecheck, production build and whitespace checks passed. The earlier full
942-test result remains baseline evidence; this small follow-up used focused
regressions. Updated JSON reports and share-recovery screenshots are preserved.
