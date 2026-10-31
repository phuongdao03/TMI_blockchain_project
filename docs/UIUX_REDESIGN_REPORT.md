# UI/UX redesign report — 2026-10-30

## Delivered in this pass

Direct changes to the existing application; no standalone demo, backend change,
new dependency, migration, production transaction, push, merge or deployment.

- Review verdict form: criterion index plus one active editor, responsive two
  columns, previous/next controls, completion labels. Controlled verdicts,
  rationale and evidence references survive switching. Invalid submission opens
  its first invalid criterion before focusing the field. Existing evidence
  validation, autosave, final confirmation and submission payload remain intact.
- Reviewer navigation: separate assessment and HR; restore notifications,
  account and activity destinations. Applicant navigation prioritizes overview
  and dossiers, with separate services and account groups. Existing route and
  permission filtering remains in force.
- Desktop shell: expandable sidebar and compact icon rail, official logo,
  accessible link names and native tooltips. Existing mobile drawer/focus trap
  and bottom navigation remain.
- Private evidence: use the existing semantic muted token for secondary text
  after an axe scan identified insufficient contrast in light mobile mode.
- Wallet: retain the page title/description while loading or failing; offer
  retry without inventing a balance or permitting unsupported transactions.
- Review action bar: remove negative horizontal margins that extended 0.8125px
  beyond each edge of the 768px viewport.

## Audit and architecture

[Audit and all 97 page entry points](UIUX_AUDIT.md).
[Before/after information architecture and implementation criteria](UIUX_INFORMATION_ARCHITECTURE.md).
[Current design contract](../DESIGN.md).

Existing dossier creation, recovery, evidence upload, submission review,
dashboard task priority, membership, community, advertising and admin flows were
retained. Earlier implementations and external acceptance are tracked in
[the acceptance inventory](MASTER_PROMPT_ACCEPTANCE_2026.md) and
[the prior handoff](handoffs/ux-task-first-2026-10-27.md). Retention is not a
claim that every existing screen was redesigned again in this pass.

## Changed source and shared components

| Area                          | Source                                                                |
| ----------------------------- | --------------------------------------------------------------------- |
| Role navigation               | `frontend/src/components/layout/dashboard-navigation.tsx`             |
| Shared workspace shell        | `frontend/src/components/layout/shells.tsx`                           |
| Responsive compact rail       | `frontend/src/app/globals.css`                                        |
| Criterion workspace           | `frontend/src/components/reviews/verdict-review-form.tsx`             |
| Private evidence verification | `frontend/src/components/documents/private-document-verification.tsx` |
| Wallet loading/error recovery | `frontend/src/components/wallet/wallet-workspace.tsx`                 |

Extended existing components rather than adding parallel versions. Colocated
tests cover navigation ordering/permissions, sidebar interaction, criterion
switching and invalid-field focus, and wallet failure recovery. Reviewer E2E
covers keyboard selection, retained rationale/evidence, submission, admin report
visibility, themes and viewport reflow.

## Verification

- Full frontend unit suite: **1,023 tests / 239 files passed**. An earlier run
  exposed synchronous focus expectations; the implementation now focuses
  immediately for a visible invalid field and after render for a hidden one.
- ESLint: zero errors; four existing warnings in
  `membership-chat-access-admin.tsx` (unused imports/variables).
- Typecheck and final production build passed after the layout correction; all
  60 directly affected component tests passed again.
- Chrome E2E: 20 passed (10 desktop, 10 mobile); two intentional viewport skips.
  Includes the eight-width/two-theme review reflow regression, retained
  rationale/evidence, final submission and admin report checks. An earlier
  audit/test run shared mutable mock state and failed the admin report check;
  sequential execution passed. Keep these harness runs isolated.
- Changed-file formatting, ESLint and `git diff --check` passed.
- Unit environment still prints its known jsdom navigation warning. No claim of
  a completely warning-free unit environment is made.

## Browser coverage and evidence

Local Chrome with the repository mock API and test-only role fixtures. Widths:
320, 360, 390, 428, 768, 1024, 1280 and 1440; light and dark; reduced motion
enabled. This validates local rendering, not production data.

Final isolated audit: **18 routes, 288 route/theme/width measurements, zero page
overflows or page errors**. **21 axe scans** across applicant overview, wallet
error state, review queue/detail, admin overview and collapsed sidebar: zero
violations for the selected WCAG A/AA rule tags. Other routes received layout
checks, not an axe acceptance claim. One initial membership resize measurement
was transient; stable repeated measurements fit at 320px.

| Role      | Routes inspected                                                                     |
| --------- | ------------------------------------------------------------------------------------ |
| Guest     | `/`, `/works`, `/process`, `/verify`, `/cong-dong/hoi-vien`, `/community`, `/login`  |
| Applicant | `/workspace`, `/dossiers`, `/dossiers/new`, `/wallet`, `/membership`, `/advertising` |
| Reviewer  | `/reviews`, `/reviews/4155dbf5-bb3e-449d-8bf0-9572cc642cac`                          |
| Admin     | `/admin`, `/admin/reviews`, `/admin/payments`                                        |

The mock API does not implement the wallet summary endpoint in this harness; its
audit exercises the real error/retry state. Wallet success/QR behavior is
covered by existing component tests; provider acceptance remains external.

Local artifacts (not committed binary assets):

- [Before, desktop](../tmp/uiux-20261030/before-review-1440.png)
- [Before, mobile](../tmp/uiux-20261030/before-review-390.png)
- [After, light desktop](../tmp/uiux-20261030/after-review-light-1440.png)
- [After, dark mobile](../tmp/uiux-20261030/after-review-dark-390.png)
- [Compact sidebar](../tmp/uiux-20261030/after-sidebar-collapsed.png)
- [Machine-readable audit](../tmp/uiux-20261030/audit.json)

[Versioned per-route measurement summary](UIUX_BROWSER_EVIDENCE.json).

## Limits and remaining acceptance

### Screenshot feedback: mobile-first form and sidebar

- The desktop collapse action is now a 44×44px icon beside the brand, with no
  large bordered row. Accessible name, tooltip, expanded state and icon rail
  remain. The sidebar and collapse button are hidden on phone/tablet; drawer
  open/close and focus recovery were verified at 390px.
- `registrationNumber` is optional in the organization schema from seed 0055 and
  the mock catalog. The UI now explicitly labels optional fields and explains
  that this number comes from the organization's registration papers, is
  distinct from the system dossier ID, and may be left blank. API keys, schema
  required flags and backend validation remain unchanged. Custom server help
  text takes precedence; a required custom field is never described as optional
  by the fallback help.
- Mobile creation inputs use 16px text; primary actions fill the available width
  with a 48px minimum height. The secondary back action is separate.
- Validation: 36 affected component tests and four desktop/mobile E2E passed;
  the latter cover all eight widths, both themes, omission of registration,
  drawer focus and draft creation. Eight scoped form axe scans had zero
  violations. Typecheck, production build and changed-source ESLint passed.
- Initial E2E used `.check()` on the visually hidden type radio; the runner
  correctly rejected clicking through its label. Changed the test to click the
  visible type choice, matching the user interaction; no UI guard bypass.

The following external acceptance limits still apply.

- No staging credentials or physical devices supplied. Real authentication,
  payment/webhook, private-file provider, publication, council decision and
  blockchain signing need authorized staging acceptance.
- Automated axe checks cover selected initial states; screen-reader testing,
  200% zoom task completion, every dialog/error/upload state and all 97 routes
  remain outside this pass's measured coverage.
- No production Core Web Vitals claim: dev-server timings and a local build do
  not establish p75 LCP/INP/CLS.
- No new affiliate or council role/module invented where absent from the current
  route/permission model. Broader 1–5 task-based UX scoring remains pending
  observed user journeys.
- This pass closes the listed source-confirmed issues. It does not establish
  completion of every item in the comprehensive master brief.
