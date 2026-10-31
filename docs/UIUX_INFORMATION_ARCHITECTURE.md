# UI/UX information architecture — 2026-10-30

## Scope and specification

Apply the supplied comprehensive redesign brief to the existing application.
Preserve backend authorization, review policy, payment and dossier contracts.
Existing implementation and acceptance history: `UX_UI_REDESIGN_2026.md`,
`MASTER_PROMPT_ACCEPTANCE_2026.md`, `handoffs/ux-task-first-2026-10-27.md`. This
pass prioritizes remaining source-confirmed review/navigation issues.

## Before → after

- Reviewer: assessment + attendance in one group, discovery, truncated personal
  links → assessment, separate HR, discovery, account/notifications/activity.
- Applicant: discovery before dossiers → overview and dossiers first, services
  and account separated, discovery retained.
- Verdict form: all criterion editors stacked → criterion index and one active
  editor; previous/next, completion labels, unchanged controlled draft state.
- Invalid submission: focus may target another criterion → reveal its editor
  before focusing the invalid field. Submission rules remain unchanged.

## Ordered implementation / acceptance

### Screenshot feedback follow-up

- Replace the full-width sidebar collapse row with a 44px icon control beside
  the brand; preserve its accessible name, expanded state and tooltip. Hide
  desktop controls on phone/tablet; retain the existing drawer.
- Organization `registrationNumber` is optional in seed migration 0055 and the
  test catalog. Explain the source document, distinguish it from the dossier
  identifier, and allow proceeding without it. Do not change backend validation.
- Mobile dossier entry: 16px input text, no horizontal overflow, full-width
  primary action and legible optional-field guidance. Verify 320–428px, tablet,
  desktop and both themes; check drawer open/close and focus recovery.
- Regression tests: optional registration can be omitted through draft review;
  required representative stays required; sidebar button remains operable.

1. Focused review editor: only one visible criterion; switching preserves input,
   radio and evidence selections; all criteria remain in saved payloads;
   incomplete submission reveals its first invalid criterion. Files: verdict
   form, colocated tests, reviewer E2E.
2. Task navigation: keep every currently authorized destination; separate HR,
   finance/services and account; restore reviewer account/notification links.
   Files: dashboard navigation and colocated tests.
3. Browser audit: baseline/after screenshots, both themes and exact target
   widths 320/360/390/428/768/1024/1280/1440. Mock fixtures are local QA only.
4. Review, lint, typecheck, build, relevant regression suite; document limits.

## Conventions and verification

Next.js App Router / React / Tailwind, existing semantic `--theme-*` tokens.
Interactive state stays in the existing client component. Example:
`<button type="button" aria-pressed={active} onClick={...}>…</button>`. Tests
beside source use Vitest/Testing Library; E2E uses existing Playwright mock API,
never a production transaction. From repository root:

```sh
npm --prefix frontend test -- --maxWorkers=2
npm --prefix frontend run lint
npm --prefix frontend run typecheck
npm --prefix frontend run build
```

No dependency, migration, schema, permission or API changes; no push/deploy.
Public, finance, community and secondary admin screens retain their implemented
flows; runtime audit results are recorded separately from redesign completion.
