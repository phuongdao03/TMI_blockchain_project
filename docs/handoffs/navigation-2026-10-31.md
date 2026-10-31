# Navigation handoff — 2026-10-31

- Spec/audit: `../NAVIGATION_REDESIGN_2026.md`,
  `../NAVIGATION_ROUTE_AUDIT_2026.md` (97 pages).
- Vietnamese delivery report: `../NAVIGATION_REDESIGN_REPORT_2026.md`.
- Public group configuration/matcher: `components/layout/navigation-config.ts`.
- Public/workspace mobile navigation lives in `shells.tsx`; reviewer tasks use a
  separate bar. Preview filtering retained.
- Shared overlay hook closes on path/query/hash/history/auth/capability changes,
  traps focus, locks/restores body scroll.
- Search reuses autocomplete and `/works?query=`; portal remains inside the
  public shell for inherited theme tokens.
- `use-navigation-anchor.ts` waits for streamed anchor content before scrolling.
  Keep existing homepage IDs.
- Admin groups default collapsed except the active group; shared shell state
  persists through drawer remounts. Multi-role entry points are additive.
  API/RoleGate unchanged.
- Dossier recovery has an owner-scoped volatile fallback when browser storage
  fails; existing session cleanup clears it. Warn for unsafe links, retain
  beforeunload and revision conflict behavior.
- Reviewer submit bar uses the shared bottom-navigation inset. No backend, route
  or package changes.
- QA uses local mock 4097 + Next dev 3197, separate dist `.next-uiux-20261030`.
  Do not parallelize reset/submission E2E against the same mock.
- Full test/build results and limits are recorded in the delivery report. No
  physical-device or staging-API acceptance claim.
- Final: production build/typecheck/changed-file lint/diff check passed;
  full-suite checkpoint 1,033 tests (241 files), final focused files 63 tests
  passed; deduplicated final E2E 24 passed/4 viewport skips; 16 scoped axe scans
  clean. Screenshots: `../screenshots/navigation-2026/` (14 PNGs).
