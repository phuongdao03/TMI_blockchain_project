# Homepage refinements — 2026-10-31

User correction supersedes the earlier navigation brief: remove the About anchor
menu and hero organization badge. Keep existing section IDs/direct links intact.
Render the 53-page proposal inline when its section approaches the viewport,
with page/zoom/fullscreen controls; downloading is optional. Compact the gallery
on phones with a category select, 44px controls and a short thumbnail strip.
Replace the community block with two balanced, illustrated entry points using
existing photos and valid routes. Verify 320–1440px, both themes, inline reading
and mobile photo controls. No API or business-rule changes.

Implemented; see `../HOME_REFINEMENTS_2026.md`. Inline reader loads on approach;
download is below it. Mobile gallery uses 3×2 thumbnails and a native select.
Drawer now contains utility destinations rather than duplicate bottom tabs. 48
relevant unit tests, 7 E2E/1 viewport skip, 12 clean axe scans, typecheck, lint
and production build passed. Final gallery interaction test waits for hydration
and disables trace recording on the local dev server. Screenshots:
`../screenshots/home-refinements-2026/`. Original section IDs and guards
retained.

Pre-push verification: all 1,035 frontend tests across 241 files passed with
two workers; root configuration tests 6/6, repository formatting and frontend
typecheck passed. Frontend lint: zero errors, four existing membership-chat
warnings. Updated remaining E2E helpers to the dialog role, current mobile
theme breakpoint and renamed discovery tab. Temporary audit scripts/logs are
ignored; source, tests, docs and screenshots are included in the delivery.
