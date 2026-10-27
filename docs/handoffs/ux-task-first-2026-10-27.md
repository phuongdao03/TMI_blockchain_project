# Task-first UX follow-up — 2026-10-27

- Spec/audit/evidence: `docs/UX_UI_REDESIGN_2026.md` and
  `docs/ux-evidence-2026-10-27/`.
- Applicant dashboard: replace decorative hero, sample metrics and fake activity
  with up to three globally filtered actionable dossiers, recent next actions,
  dates, server total and service links. `applicant-tasks.tsx` reuses existing
  dossier list filters/query keys. No backend API changes.
- Public home: nomination primary, discovery secondary, process/cost link;
  preserve preview account entry and authenticated workspace access. Mobile
  actions precede the heritage image. Desktop no longer hides the CTA group.
- Community image preview: remove nested dialog form; explicit close button does
  not submit the editor. Regression covers open/close within a parent form.
- Checks: 919 frontend tests; six desktop and six mobile E2E cases, with final
  affected mobile cases rerun; ESLint zero errors/five unrelated warnings;
  typecheck, build and diff whitespace checks passed. No deployment/migration.
- Business clarification resolved: replace the post-approval charge for new
  dossiers with a submission fee; preserve existing dossiers and financial
  history. Implemented source/migration and verification are recorded in
  `docs/SUBMISSION_FEE_MIGRATION.md`. Production migration remains unapplied.
- Pre-creation recovery implemented: owner-scoped revision API, migration 0144,
  session-only backup, explicit conflict choice, atomic creation/replay. Details
  and verification: `docs/DOSSIER_PREPARATION_RECOVERY.md`. Migration unapplied.
- Remaining: staging role, payment-provider,
  publication/advertising concurrency and device accessibility acceptance. Do
  not report the master transformation as fully complete.
- Local role audit: 16 routes, seven widths, both themes; no page overflow after
  fixing public-work editor grid/URL sizing. Desktop axe initial-state checks
  passed. Removed nested main landmarks in admin/applicant payment workspaces.
  Reports/screenshots are in the evidence directory; no exhaustive accessibility
  or operational staging acceptance is implied.
- Latest checks: 932 frontend tests/226 files, 21 focused backend tests,
  typecheck/build/Ruff passed; lint zero errors/five existing warnings.
- Full brief inventory: `docs/MASTER_PROMPT_ACCEPTANCE_2026.md`, with analytics
  proposal, usability scripts and exact external acceptance requirements.
- Added applicant live balance/unread summary; owner-only approved/published
  promotion entry; older advertising dossier selection now fetches by ID rather
  than silently choosing another dossier. Shared wallet helpers preserve exports.
- Broader follow-up: 24 role/membership/verification E2E plus two promotion E2E
  passed; 37 wallet/membership/publication/advertising backend regressions passed.
- Final source snapshot: 942 frontend tests/228 files passed, lint zero errors
  (five existing warnings), typecheck/build and whitespace checks passed.
  Timeline now separates publication and completes published dossiers correctly.
- Continued: certificate sharing catches native cancellation and clipboard
  denial, announces success, and offers a selectable canonical URL fallback.
  Three new unit cases reproduced the old missing feedback/unhandled rejections.
- Expanded axe to mobile 390 plus desktop 1440, both themes, reduced motion.
  Fixed specific low-contrast certificate labels, dossier/reviewer muted text
  and dark notification eyebrow using existing semantic colors.
- Docker daemon and disposable PostgreSQL URL are unavailable; no concurrency
  acceptance, production deployment or database reset was performed.
- Final follow-up checks: 10 focused unit tests, 11 E2E passed; 64 mobile/desktop
  axe scans on initial role states returned zero violations. Three duplicate
  role cases intentionally skipped. Lint/typecheck/build/whitespace passed.
- User screenshot corrections and member chat redesign:
  `docs/UX_FIXES_MEMBER_CHAT_2026.md`. Natural verification word wrapping,
  explicit GPS action column, direct reviewer attendance and shorter process CTA.
  Compact room entry and desktop-rail/mobile-selector chat preserve backend gates.
  Browser screenshots and send/access regressions passed; no production changes.
- Delivery #388 CI regression repair: restore compact server-confirmed admin
  chat access label; wait for acknowledged preparation before draft creation;
  reset preparation between critical-journey attempts; update dashboard theme
  checks to real account surfaces and scope priority-action checks to their
  region. No save/access guard was weakened and no timeout increased.
- Repair validation: all 945 frontend tests / 228 files passed; 11 focused
  desktop/mobile E2E cases passed with five intentional viewport skips;
  focused ESLint, typecheck and whitespace checks passed.
- Delivery #389: quality and desktop E2E passed; the mobile hero test still
  expected retired login/register hero controls. It now checks nomination and
  discovery destinations, 44px touch height and above-fold visibility. Existing
  public session/menu coverage remains unchanged. Complete shell/session files
  passed on desktop/mobile: 15 cases, seven intentional viewport skips; lint
  and formatting passed. No application UI or timeout was changed for this fix.
