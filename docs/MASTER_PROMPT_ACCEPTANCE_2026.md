# Master prompt acceptance — 2026-10-27

This is an evidence inventory, not a declaration of full acceptance. The source
brief is the supplied “TINH HOA VIỆT UX/UI TRANSFORMATION 2026” attachment.
Preserve the existing app and the confirmed replacement submission-fee policy.

## Remaining implementation and verification plan

1. Add applicant account context: acknowledged wallet balance and unread count,
   with independent loading/error/retry and account-scoped financial caching.
   Reuse existing APIs; never replace missing data with zero. Verify failures,
   zero balance, cache updates and account switching, then browser layouts.
2. Exercise existing wallet/membership, reviewer and public verification E2E
   journeys, rather than treating route layout checks as operational acceptance.
3. Record all brief sections against code/tests. Add the minimum lawful analytics
   event proposal and usability scripts where there is no deployed measurement
   pipeline. Mark every baseline unmeasured.
4. Run affected checks and update the handoff. Production migration/deployment,
   real provider integration and physical-device acceptance remain outside the
   available local environment and must not be claimed as completed.

## Acceptance boundaries

The earlier 932 unit tests and 16-route responsive audit are baseline evidence.
They do not prove every role, state, dialog, payment integration or device.
Production deployment, real payments and database resets are prohibited by the
brief. Additive migrations 0143/0144 remain unapplied to production.

## Implementation completed in this follow-up

- `ApplicantAccountSummary` uses `/wallet` and `/notifications/unread-count`;
  independent errors/retry, genuine zero balances, no invented fallback counts.
  Wallet data shares the existing user-scoped cache with checkout/wallet flows.
  Formatting/query keys moved to `lib/wallet/summary.ts`; the previous exports
  remain available so existing consumers retain compatibility.
- Owner-only dossier promotion entry for approved through published states;
  ordinary publication tracking remains separate from optional advertising.
  The action opens the existing advertising setup with the same dossier ID.
  It does not publish, waive fees or manufacture a publication transition.
- Advertising setup fetches an explicitly requested older dossier if absent
  from the first page. It no longer silently replaces an ineligible selection
  with another dossier. Backend ownership/eligibility checks remain authoritative.
- Measurement proposal and five usability scripts below satisfy planning work;
  collection, participant observation and measured outcomes remain outstanding.
- Timeline now separates certificate issuance from publication. Published
  dossiers complete every stage, instead of displaying certificate receipt as
  still in progress. Unit cases and refreshed promotion screenshots cover this.

## External acceptance still required

Final local snapshot: 942 frontend tests / 228 files passed, 37 additional
backend regressions passed, 24 broader Chrome E2E cases and two promotion cases
passed. The affected dashboard and promotion cases were rerun after the final
visual corrections. ESLint: zero errors/five existing warnings; typecheck,
production build and whitespace checks passed. Screenshots include
`account-summary-{light,dark}-{390,1440}.png` and `promotion-*.png` in the evidence
directory. Existing jsdom image/payment-mock warnings are not suppressed.

| Requirement | Missing environment/evidence | Acceptance action |
| --- | --- | --- |
| Migration 0143/0144 and real auth | Staging deployment/session accounts | Apply reviewed migrations in staging; test restore, submission/payment and multi-role MFA |
| Provider payments | Sandbox provider configuration/callbacks | Exercise success, failure, timeout, retry and reconciliation without real money |
| Final advertising slot concurrency | Disposable PostgreSQL test URL | Run `test_advertising_postgres_concurrency.py` against an isolated test database |
| Devices/accessibility | Physical Safari/Android and broader assistive-technology testing | Camera upload, keyboard/dialog checks, full status/state matrix |
| Performance and usability | Production-like baseline, consented observation | Measure CWV and run scripts; no improvement claim until measured |

These are not hidden behind the passing local tests. The complete master prompt
remains **not fully accepted** until this evidence exists. No additional user
confirmation is required for ordinary local implementation/checks; deployment
and live financial operations remain constrained by the original brief.

## Brief coverage

“Local” means code/test evidence; it never means production acceptance.

| Brief section | Evidence / current acceptance | Remaining verification |
| --- | --- | --- |
| I philosophy | Task-first applicant dashboard; removed sample metrics/fake activity | Observed usability sessions |
| II audit | `UX_UI_REDESIGN_2026.md`, public/role JSON and before/after screenshots | Authenticated staging audit |
| III role architecture | `role-workspaces.ts`, dashboard navigation, role gates, backend permissions | Real multi-role/MFA accounts |
| IV design system | `globals.css` theme tokens; shared UI controls and theme/keyboard tests | Every component/state, physical devices |
| V homepage | Nomination/discovery/process actions; exact-width browser tests | Field performance and conversion |
| VI mobile navigation | Public/workspace shells; session and layout E2E | Physical Safari/Android |
| VII applicant dashboard | Prioritized tasks, server totals/dates; live account summary added in this follow-up | Real account freshness |
| VIII wizard/upload | Versioned type forms, recovery API, autosave, upload queue and preparation/creation tests | Real camera/files and deployed migration 0144 |
| IX fee/publication | Submission fee migration 0143; prepaid review/approval; optional dossier promotion entry added | Staging migration/provider/publication acceptance |
| X reviewer | Evidence review, criteria, draft, completion, tablet/dark E2E | Real assignments/conflicts/council accounts |
| XI auth | SSR/session synchronization, reload/logout/refresh/multi-tab E2E | Real provider expiry/MFA |
| XII wallet | Existing ledger/top-up/payment/retry UI; wallet service/API tests | Provider sandbox timeout/reconciliation |
| XIII membership/community | Tier cards, room access, catalog benefits, membership tests | Real expiry/upgrade fulfillment |
| XIV advertising | Reservation/peak capacity, wallet checkout, moderation, delivery tests | PostgreSQL final-slot integration; real sandbox bookings |
| XV discovery/verification | Public catalog/detail/security and certificate verification E2E | Real withdrawn/revoked fixtures |
| XVI statuses/notifications | Shared dossier badges/timeline; notification center/bell/count | Full delivery channels with real accounts |
| XVII writing/onboarding | Contextual dossier steps, first-dossier guidance, plain status copy | Older/new users' comprehension |
| XVIII performance/accessibility | Responsive/theme/keyboard/axe route checks; optimized media components | CWV baseline; all dialogs/states; full WCAG audit |
| XIX automated tests | Unit/backend/Chrome E2E evidence in summary report | External integration/device matrix |
| XX measurement/usability | Event proposal and five scripts below | Approved collector and observed baseline |
| XXI–XXV execution/handoff | Incremental source changes, migrations, tests, screenshots and handoff | Release acceptance; no production deployment authorized |

## Certificate sharing and mobile accessibility follow-up

Scope: handle native share cancellation, clipboard denial/unavailability and
acknowledged copying without uncaught promises or false success. Keep a
selectable canonical public verification URL as a recovery path. Feedback is
scoped to its certificate number and the share control is disabled while active.
Unit acceptance covers success, permission denial and cancellation/retry.

Browser checks reproduced three low-contrast gold labels on the certificate;
their text now uses the existing darker certificate tone. Decorative borders
and backgrounds remain unchanged. The fallback is tested at 390 px with axe and
page-error collection. Role-route axe checks are extended from desktop only to
390 and 1440 px, both themes; results remain initial-state local evidence.

Environment check: Docker CLI exists but its daemon pipe is unavailable;
`ADVERTISING_TEST_DATABASE_URL` is unset. No database service was launched and no
database was reset. PostgreSQL final-slot integration remains unexecuted.

The expanded stable-frame mobile audit reproduced additional text contrast
failures: dossier/review secondary text measured 4.11:1 on the mobile cream
background; the notification eyebrow measured 2.07:1 in dark mode. Replaced
those legacy text colors with semantic muted/accent tokens. Certificate gold
labels use the existing darker certificate tone. Audits disable motion to
measure resolved UI states and preserve detailed axe failure summaries.

Final follow-up: 10 focused unit tests and 11 E2E cases passed. All 64 initial
role-state axe scans (16 routes × two widths × two themes) report zero violations;
seven-width overflow checks passed. Lint/typecheck/build/whitespace checks passed.
Three duplicate role audits are intentionally skipped in the mobile project.
This supplements the previous 942-test baseline; no new full-suite count claimed.

## Minimum measurement proposal

The existing `lib/analytics/public-catalog.ts` and `public-work-actions.ts`
dispatch local browser events. They are not evidence of an approved collector
for applicant/reviewer/payment funnels. Do not silently add external tracking.
The following is the requested minimum proposal, pending collection approval.
Every baseline and improvement percentage is **unmeasured**.

| Metric | Proposed event / authoritative source |
| --- | --- |
| Registration completion | `registration_started`, `registration_completed` after server success |
| Dossier start/completion | `preparation_started`, `dossier_submitted` after acknowledged transitions |
| Step abandonment | `preparation_step_viewed`, next acknowledged step; session end is not proof of abandonment |
| Upload failures | `upload_finished` with outcome and bounded error category |
| Creation time | First preparation to confirmed draft creation, with resumed sessions distinguished |
| Payment success | Server-confirmed order transition, unique order deduplication; never redirect flags |
| Session loss | `session_expired` distinguished from explicit logout |
| Return visits | Consent-compatible aggregate retention; no fingerprinting |
| Review processing time | Assignment to submitted verdict from existing server timestamps |
| Navigation effort | `workspace_destination_opened` with allowlisted destination/entry surface |
| Advertising purchase/renewal | Server-confirmed paid order and purchase context |
| Membership use | Confirmed purchase/upgrade and fulfilled benefit events |

Only allowlisted event names, schema version, coarse duration, step number,
entry surface and outcome category should enter browser telemetry. Never include
names, email, tokens, dossier text/title, evidence URLs/files, free-form errors,
payment credentials or bank details. Financial event deduplication belongs on
the server; exported reports should be aggregate. Define retention, access and
consent before connecting a collector. Local custom events alone are not metrics.

## Usability scripts ready for observation

Use synthetic accounts/files and sandbox money. Start without coaching; record
completion, elapsed time, wrong actions, status comprehension and help requests.
No real participant session has been run or results invented.

| Participant | Task and pass condition |
| --- | --- |
| New visitor | Find an eligible nomination, explain the process/cost, open registration and return to the intended task |
| Older user | At 390 px, locate notifications, read an update and return to the correct dossier without assistance |
| Applicant | Choose a type, enter incomplete fields, reload, resume on a second device, resolve a conflict, attach synthetic evidence, submit and explain the pending fee/review state |
| Reviewer | Open an assignment, inspect PDF/image evidence, save an assessment, resume it and submit only after required criteria are complete |
| Admin | Filter intake, assign an eligible reviewer, inspect a fee record, review publication conditions and identify that advertising is optional |

For all five: include a connection failure and recovery; ask “What happens
next?” before showing instructions. Capture friction without collecting private
evidence. Acceptance requires observed results, not merely this script.
