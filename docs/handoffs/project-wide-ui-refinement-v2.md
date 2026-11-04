# Mobile home and navigation refinement — handoff

## Delivered

- Replaced account-only compact hero text with a purpose statement that appears
  for guests and signed-in users. Session-specific CTA links and access rules
  are unchanged.
- Kept submission and discovery actions full width; placed process and
  establishment links side by side on compact screens. Their labels and
  destinations remain unchanged.
- Added deliberate horizontal swipe navigation to the inline heritage gallery;
  vertical scroll and pinch zoom remain available. The selected photo fades in
  after loading, with spinner and error/retry states intact.
- Added reduced-motion-aware mobile menu entry and touch press feedback.
  Reduced motion removes movement while preserving 120ms color/opacity
  feedback.

## Key files

- `frontend/src/components/public/home-account-experience.tsx`
- `frontend/src/components/public/home-editorial.css`
- `frontend/src/components/public/heritage-gallery.tsx`
- `frontend/src/components/layout/navigation.css`
- `frontend/src/app/globals.css`
- Focused tests: `frontend/src/app/home-page.test.tsx` and
  `frontend/src/components/public/heritage-gallery.test.tsx`

## Verification

- Full frontend test suite: 241 files, 1,037 tests passed with
  `npm.cmd test -- --configLoader runner`.
- TypeScript: `npx.cmd tsc --noEmit --incremental false` passed. The plain
  `tsc --noEmit` form cannot write its incremental metadata in this workspace.
- Full frontend ESLint passed with 0 errors and 4 existing warnings in
  `membership-chat-access-admin.tsx`.
- Browser checked at 320, 360, 375, 390, 430, 768, 1024, and 1440 CSS px;
  `scrollWidth` did not exceed `clientWidth`. Browser checks covered dark/light
  themes, reduced motion, menu Escape/focus restore, establishment evidence,
  and the loaded gallery image. Guest and signed-in states are covered by the
  home page tests.
- Vite config bundling is blocked by a Windows `EPERM` under
  `frontend/node_modules/.vite-temp`; using `--configLoader runner` avoids that
  write and tests pass. CSS Prettier warnings also reproduce on the baseline
  versions of both touched CSS files; no broad reformat was applied.
- Build was not run because the existing local development server uses the
  shared `.next` directory.

## Follow-up

`animation-plans/003-dossier-progress-transform.md` records the separate
dossier progress-bar width animation improvement; it remains deferred. No
commit, push, deployment, API, authentication, or business-rule changes were
made.
