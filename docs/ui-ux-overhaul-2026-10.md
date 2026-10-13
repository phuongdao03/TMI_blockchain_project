# UI/UX overhaul: Tinh Hoa Viet workspaces

## Objective

Make the existing web application easier to scan and operate at desktop, tablet,
and mobile widths while preserving its brand, data contracts, routes, permissions,
and business transitions. Prefer typographic hierarchy and separated rows over
stacks of bordered cards. A surface is reserved for a distinct task, warning, or
editable form, not every piece of supporting information.

## Inventory and boundaries

- 71 page routes: 28 admin, 21 other authenticated workspace, 11 public, 8 auth,
  and 3 local/utility routes. Shared public, auth, and dashboard shells cover them.
- Workspace personas: `VIEWER`, `USER`, `MODERATOR`, `SUPER_ADMIN`. Specific
  employee, reviewer, signer, finance, HR, and operations access is determined
  by existing permissions; UI changes must retain these gates.
- No API, schema, route, role, or workflow changes. Form fields and document
  requirements continue to come from the existing dossier type schema.
- Existing brand colors, wordmark, and logo remain in place.

## Root causes

1. Shared cards default to a border, radius, background, and generous padding.
   Page components then repeat the same treatment for nested sections and rows.
2. Different feature areas define their own border, spacing, table, and empty
   state styles. Breakpoints differ and some tables rely only on horizontal scroll.
3. Per-section entrance animation and large surface shadows cause avoidable paint
   and style work, especially during workspace navigation.
4. The applicant dashboard shows status counts based on a small recent page even
   when there are no dossiers; the first action is diluted by empty metrics.

## Implementation order and acceptance

1. **Foundation:** Apply shared workspace spacing, flat section hierarchy,
   controls, table readability, reduced paint, and three-width behavior. Verify
   keyboard focus, dark theme, and no horizontal viewport overflow.
2. **Applicant:** Show a useful first-dossier path before any metrics; make type
   selection, required fields, document preflight, validation, and next action
   readable as one sequence. Preserve the existing draft and upload workflow.
3. **Reviewer and staff:** Make assignment, deadline, comments, attendance,
   leave, and overtime sections scan as lists and forms with visible actions.
4. **Admin:** Make dashboard, review intake, work allocation, payments,
   publication, certificates, people, departments, users, and other permissioned
   management pages share dense tables, grouped filters, and distinct alerts.
5. **Verify:** Focused behavior tests, all frontend tests, lint, typecheck, build;
   browser checks at 390, 768, and 1440 CSS px on available public and preview
   routes. Authenticated operations need suitable test accounts and backend data.

## Commands

From `frontend/`: `npm.cmd run lint`, `npm.cmd run typecheck`,
`npm.cmd run build`, `npm.cmd run test -- --maxWorkers=2 --configLoader runner`.

## Code and test locations

- Routes: `frontend/src/app/`; feature views: `frontend/src/components/`.
- Shared styling: `frontend/src/app/globals.css`; UI primitives:
  `frontend/src/components/ui/`; tests colocated as `*.test.tsx`.
- Use semantic classes and theme variables; preserve existing query, mutation,
  and role gates. Test changed behavior rather than incidental CSS class strings.

## Verification limits

The deployed URL may differ from the checked-out revision. Browser previews
without production credentials cannot certify protected mutations or every data
state. Report each unavailable check explicitly.

## Result in this revision

- Shared dashboard layout and nested surfaces now use flatter section hierarchy,
  rows, lighter separators, and fewer entrance effects. Embedded public library
  views inherit the same flat workspace surface. Brand tokens and assets remain.
- Admin portal, operations priorities, Reviewer assignments, staff shortcuts,
  HR summaries, and work allocation views use rows in place of repeated cards.
  The fee-decision page groups its form and next-status context with separators
  while retaining the existing payment and waiver actions.
- Applicant first use now explains the existing three-step dossier flow rather
  than displaying zero-valued status metrics. Required title is marked visibly
  and accessibly without changing schema-driven fields or upload behavior.
- Attendance, leave, overtime, employee, payroll detail, member, staff account,
  search analytics, and operations tables use labeled stacked records below
  56rem; headers remain available to assistive technology. Existing user, audit,
  and payroll period views keep their separate mobile lists. Tablet filters use
  two columns at 768px; desktop retains the multi-column tables.
- Focused and full Vitest suites, lint, typecheck, and build passed. Browser
  checks used the repository auth mock at 390/768/1440 CSS px. Production
  credentials and real backend mutation checks were not available.

## Follow-up visual corrections and backend check

- The dossier preparation section now appears before the long type list. On
  mobile, selecting a type farther down the list scrolls its preparation
  details into view. The message for types with no separate required document
  group now describes that state without a misleading zero count.
- Restored rounded corners on shared workspace sections, the Admin module
  list, form surfaces, the leave hero, and applicant choices. Admin module
  icons keep their own compact grid row instead of stretching across the
  entire link. Hover uses an existing theme color variable.
- `frontend/e2e/ui-corrections.spec.ts` checks the three reported views on
  desktop and mobile plus a 768px tablet viewport. The same mock preview is
  available at `http://127.0.0.1:3003/preview-tabs`.
- A local FastAPI process starts and `/health` returns 200. `/ready` returns
  503 because Redis and Anvil are unavailable here. Dossier requests require
  `DATABASE_URL`, which is not configured in this workspace, and therefore
  return 500. These are runtime environment gaps; they do not verify live
  database-backed operations.
- Final checks: frontend full Vitest 665/665, focused dossier tests 7/7 after
  the mobile scroll change, Playwright UI corrections 7 passed/1 intentionally
  skipped across desktop/mobile/tablet, ESLint, typecheck, and production build.
  Backend pytest 1,022 passed/2 skipped, Ruff passed, mypy passed for 405
  source files. The legacy browser suite's default `load` wait stalled on the
  dev preview; the focused browser suite waits for `domcontentloaded` and then
  asserts rendered content and geometry.

## Follow-up: applicant submission and reviewer decision flow

- Applicant creation now keeps category guidance and the preparation checklist
  in one section. Document requirements are rows, and the empty requirement
  message stays visible without another card.
- The dossier workspace presents status as a flat band, keeps the three steps
  together, shows the final information and evidence checks as two rows, and
  places the submit action directly after those checks. Optional document
  naming and empty evidence use light separators. Version and timeline entries
  remain available below the submit action.
- The reviewer workspace puts locked evidence and the assessment form before
  optional coordination. The assistance form is closed by default and uses
  theme colors in dark mode. The dossier heading, next action, deadlines,
  progress, score bands, and final conclusion use typography and separators
  instead of repeated panels. The same permission and mutation gates remain.
- `frontend/e2e/submission-review-flow.spec.ts` covers applicant and reviewer
  flows at desktop/mobile widths, including dark-mode assistance, plus a
  768px tablet overflow check. Unit tests cover assistance disclosure,
  reviewer order, and flattened applicant sections.
- Final verification for this follow-up: frontend Vitest 160 files and 665
  tests passed; Playwright 5 passed with one intentional duplicate tablet skip;
  lint, typecheck and production build passed, with 69 static pages generated.

## Follow-up: evidence names and document choices

- The local reviewer preview uses "Bằng chứng về quyền sử dụng nhãn hiệu"
  and a rule label that also covers representation, rather than claiming every
  file is an ownership certificate. Real uploaded titles remain as supplied.
- Reviewer criterion evidence choices now show full, wrapping file titles and
  formats as compact rows. Evidence outside configured document rules gets a
  neutral group label. The no-rule applicant upload choices describe rights,
  source material, and other documents without implying a mandatory certificate.
- The browser test creates its own applicant draft, so it no longer depends on
  state left by an earlier test or preview session.
- Verified with 50/50 focused review/dossier unit tests, 11/11 running browser
  checks across desktop/mobile (one duplicate tablet check skipped), lint,
  typecheck, and a production build of 69 static pages. The browser suite's
  reviewer navigation now waits for DOM content, avoiding a dev-server `load`
  stall while still asserting rendered workflow and submission.

## Follow-up: reviewer detail layout

- The reviewer detail now shows locked evidence before a full-width assessment
  form. This removes the long empty column beside the form on desktop.
- Evidence rows use the available width; criterion fields use two columns on
  tablet/desktop and one column on mobile. Nested form backgrounds and duplicate
  section navigation were removed. Evidence viewing, verification, decisions,
  notes, autosave, submission, and assistance retain their existing behavior.
- Browser checks passed for reviewer behavior at desktop/mobile and for tablet
  overflow (5 passed, one duplicate tablet check skipped). Screenshots were
  inspected at 1280, 768 and 390 px; document widths matched the viewports.
  Focused reviewer component tests passed 18/18; lint, typecheck and production
  build passed (69 static pages).

## Follow-up: Admin reads Reviewer findings

- The Admin review dossier API already returned the submitted criterion
  conclusions, rationale and evidence IDs. The Admin page had displayed only
  overall applicant feedback and private notes. The report now renders each
  submitted verdict with its rubric label, conclusion, rationale and cited
  file title. It also supports scored specialist answers, rubric gates and
  legacy 5T comments without changing the API or database.
- The report body is a divided list inside the existing report section, with
  one column on mobile. The Reviewer-to-Admin browser flow uses one submitted
  mock report and confirms the Admin sees the same findings.
- Verification: 18/18 focused Admin component tests, Reviewer-to-Admin
  Playwright flow on desktop and mobile, 4/4 related backend API tests, ESLint,
  typecheck and production build (69 static pages). Desktop/mobile report
  screenshots were inspected. Live database-backed behavior remains
  unverified in this workspace because the database and dependent services are
  not configured.

## Follow-up: reviewer form dividers

- Removed repeated horizontal rules from evidence choices, file assessments,
  reception conditions, and criteria. Spacing and numbered criterion headings
  now separate related inputs; one rule marks the transition to the final result.
- The evidence viewer no longer stacks borders around its header, groups, and
  individual files. Evidence links, verification, autosave, and submission
  behavior are unchanged.
- Inspected light and dark screenshots at desktop, tablet (820 px), and mobile.
  Reviewer Playwright checks passed 7/7, focused component tests 12/12, lint,
  typecheck, and production build passed (69 static pages). No backend code or
  contract changed in this follow-up.
