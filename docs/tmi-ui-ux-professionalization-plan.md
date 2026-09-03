# Implementation plan: TMI UI/UX professionalization

## Phase 1 — Foundation and navigation

- [ ] Repair shell/navigation UTF-8 copy and consolidate semantic interaction
      tokens.
- [ ] Make mobile navigation deterministic: four role tasks plus “Thêm”.
- [ ] Verify focus trap/restoration, safe areas, 320px and landscape behavior.

### Checkpoint

- Shell component tests and navigation E2E pass at all target widths.

## Phase 2 — Blockchain comprehension and signing

- [ ] Add reusable human-readable blockchain verification card.
- [ ] Redesign `/blockchain` around one primary action and four-step status.
- [ ] Add wallet/network/gas/file-version/fingerprint facts, MetaMask failures,
      polling progress, copy hash and PolygonScan action.
- [ ] Keep advanced identifiers and `ProofRecorded` under disclosure.

### Checkpoint

- Signing component and E2E state matrix pass; confirmed remains backend-only.

## Phase 3 — Task dashboards, forms and notifications

- [ ] Standardize skeleton/empty/error/next-action primitives.
- [ ] Migrate highest-frequency selects/date inputs to accessible responsive
      fields.
- [ ] Complete role-specific notification grouping, badge and read actions.

### Checkpoint

- Keyboard, modal focus and notification tests pass.

## Phase 4 — Public experience and theme polish

- [ ] Tighten mobile hero and public journey cards.
- [ ] Apply plain-language blockchain content and optimized media behavior.
- [ ] Audit light/dark contrast, hover/focus/disabled/loading/error states and
      motion.

## Phase 5 — Qualification

- [ ] Run format, lint, typecheck, unit/integration and E2E commands.
- [ ] Inspect browser console, accessibility and horizontal overflow at 320,
      375, 390, 768, 1024 and 1440.
- [ ] Production build and review with no Mainnet mutation, commit or deploy.

## Risks

- Large legacy CSS surface: migrate through scoped semantic classes, not
  rewrite.
- Mojibake breadth: repair touched user-facing surfaces first and gate remaining
  source with an encoding test.
- Existing dirty worktree: preserve all migration work and unrelated media
  files.
