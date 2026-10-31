# UI/UX follow-up — 2026-10-30

- Requirements/audit: `../UIUX_AUDIT.md`, `../UIUX_INFORMATION_ARCHITECTURE.md`.
- Results and limits: `../UIUX_REDESIGN_REPORT.md`.
- Review form now selects one criterion; keep draft state outside hidden
  fieldsets. Invalid submit reveals its criterion before focus. Evidence policy,
  autosave, API payload and confirmation are unchanged.
- Sidebar collapse is desktop-only; link accessible names/title remain. Role
  navigation separates HR, account and services without widening permissions.
- Private evidence text uses theme-muted. Wallet retains identity in failure
  and loading states. Review sticky bar no longer uses negative margins.
- Full unit suite: 1,023 tests / 239 files. No migration/deployment performed.
- Final: production build/typecheck passed; lint zero errors/four pre-existing
  warnings; 20 E2E passed/two viewport skips; 18 routes × eight widths × two
  themes fit (288 measurements); 21 scoped axe scans had zero violations.
- Run mock-backed audits and reviewer submission tests sequentially; both use
  mutable reset/review fixture state. Raw local evidence remains in
  `tmp/uiux-20261030/`.
- Browser fixtures are not staging acceptance. Keep external requirements in
  `../MASTER_PROMPT_ACCEPTANCE_2026.md` open until evidenced.
- Homepage redesign completed locally 2026-10-31: see `../HOME_REDESIGN_2026.md`.
  Hero → original founding decision → real gallery precede mission. Shared
  media dialog; on-demand two-page PDF renderer/proposal; six representative
  thumbnails and keyboard/touch/zoom lightbox. Auth/API/legal assets unchanged.
  1,027-test checkpoint, final 72 public tests, 27 E2E/7 viewport skips, 12 scoped
  axe scans, typecheck/build passed. No physical-device/Lighthouse/RUM claim.
  Gallery no longer depends on JS opacity to reveal its image. Full no-JS
  browsing remains blocked by the pre-existing streamed public auth layout
  (`S:1` hidden Suspense content), explicitly recorded as unpassed.
- Screenshot follow-up: compact 44px sidebar control beside the brand; 16px
  mobile form inputs and full-width primary action. Optional organization
  registration has source/skip guidance, distinct from generated dossier IDs.
  Required flags/API unchanged. 36 focused unit + four E2E passed; eight scoped
  form axe scans passed, plus typecheck/build/changed-source lint.
