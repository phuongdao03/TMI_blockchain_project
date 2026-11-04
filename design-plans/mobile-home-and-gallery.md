# Mobile home and gallery refinement

Written against: `1b99685`

## Evidence chain

- Surface: public home `/`, exact mobile viewport 390×844, light and dark.
- Problem: mobile hero text only requests account creation; at 390px the four
  action rows stack vertically and push the establishment evidence behind the
  fixed bottom navigation.
- Design evidence: rendered local and production pages; the desktop hero copy
  describes the public registry purpose. The fixed navigation reserves
  `--mobile-navigation-inset` in the public shell.
- Owner: `frontend/src/components/public/home-account-experience.tsx`,
  `frontend/src/components/public/home-editorial.css`,
  `frontend/src/app/globals.css`.
- Scope and affected surfaces: public home compact hero and shared public
  mobile navigation.
- Uncertainty: none; verify 320px wrapping and 390px section placement.

## Design decision

Use a concise public-purpose sentence in the compact hero independent of
session state. Keep session-sensitive actions intact. Keep the main submission
and discovery CTAs full width; place process and establishment links side by
side so the evidence section enters the first screen sooner.

## Reuse

- Existing `.registry-hero__action-row`, `.registry-hero__document-link`,
  `--mobile-navigation-inset`, `--motion-fast`, and `--ease-standard`.
- Exemplar: existing desktop public hero copy in
  `frontend/src/app/(public)/page.tsx` and selected navigation styling in
  `frontend/src/app/globals.css`.

## Changes

1. `frontend/src/components/public/home-account-experience.tsx`
   - Change: render the public-purpose compact copy for guest, authenticated,
     and loading sessions.
   - Preserve: dynamic primary actions and all current route/role checks.
   - Verify: home tests assert purpose copy in guest and signed-in states.
2. `frontend/src/components/public/home-editorial.css` and
   `frontend/src/app/globals.css`
   - Change: use two columns for the compact action row; span the primary and
     discovery CTAs across both columns; keep the two document links in one
     column each.
   - Preserve: existing labels, targets, touch heights, desktop layout, and
     shell bottom padding.
   - Verify: 320px labels wrap cleanly and 390px establishment heading clears
     the fixed navigation.
3. `frontend/src/components/public/heritage-gallery.tsx` and its CSS/tests
   - Change: recognize deliberate horizontal swipes on the image button and
     fade a selected image from opacity 0 to 1 after load.
   - Preserve: vertical scrolling, pinch zoom, lightbox, arrows, lazy loading,
     and error/retry handling.
   - Verify: horizontal swipe advances, vertical gesture does not, and failed
     image state remains available to assistive technology.
4. `frontend/src/app/globals.css`
   - Change: add a 0.96 pressed scale over 150ms ease-out to coarse-pointer
     public controls and bottom navigation only when reduced motion is not
     requested.
   - Preserve: selected route styling, safe-area spacing, and focus indication.
5. `frontend/src/components/layout/navigation.css`
   - Change: fade in the public mobile menu backdrop over 150ms ease-out and
     slide/fade the drawer from 12px over 180ms with `--ease-standard`, only
     when reduced motion is not requested.
   - Preserve: menu focus management, backdrop dismissal, and reduced-motion
     behavior.

## Scope

- Inherit: public home compact layout and shared public navigation.
- Verify: public home in guest and signed-in states; gallery loading/error and
  fullscreen behavior; light/dark themes and all requested viewport sizes.
- Exclude: authentication flows, other route families, APIs, and dossier
  progress-bar motion.

## Validation

- Product: purpose copy and key establishment evidence are visible in the
  mobile home journey.
- Interface: test horizontal/vertical gallery gestures and all existing
  gallery controls at the specified mobile and desktop widths.
- System: retain current navigation owner and theme/motion tokens.
- Repository: `npx.cmd vitest run src/app/home-page.test.tsx
  src/components/public/heritage-gallery.test.tsx`, targeted ESLint, and
  `npx.cmd tsc --noEmit` → all pass.

## Stop conditions

- Stop if a page-specific action owner or route differs from the inspected
  runtime path, or if 320px requires changing CTA labels or route behavior.

## Design documentation

- After validation: record the completed mobile home refinements in
  `docs/handoffs/project-wide-ui-refinement-v2.md`.
