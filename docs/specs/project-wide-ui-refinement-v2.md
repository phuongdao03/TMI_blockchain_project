# Project-wide UI refinement V2

## Objective

Improve the public mobile journey on the home page while preserving the Tinh
Hoa Việt red and gold identity, existing routes, authentication behavior, and
official establishment evidence. Keep the first viewport purposeful and make
the image collection usable by touch.

## Acceptance

- At 320–430 CSS px, the compact hero describes the public purpose of the site;
  guest and authenticated CTA behavior remains unchanged.
- The primary submission and discovery actions stay full width. The process
  and establishment links share a two-column row, remain readable at 320px,
  and retain their current destinations.
- At 390×844, the establishment section begins above the fixed bottom
  navigation; there is no horizontal overflow at 320, 360, 375, 390, or 430px.
- The inline heritage gallery advances on a deliberate horizontal swipe,
  ignores vertical gestures, and fades the newly loaded photo in.
- Mobile navigation provides a clear pressed response when motion is allowed.
  Reduced-motion mode keeps short color/opacity feedback and removes movement.
- Existing light/dark appearance, safe-area padding, focus behavior, account
  actions, document content, gallery filters, and lightbox controls remain
  intact.

## Structure and implementation

The public home route composes `HomeHeroAccountMessage` and
`HomeHeroAccountActions` from `frontend/src/components/public/home-account-experience.tsx`.
`home-editorial.css` owns the compact home layout; global responsive rules in
`frontend/src/app/globals.css` also affect the action row and shared navigation.
`HeritageGallery` owns the inline image stage and delegates fullscreen behavior
to `HeritageLightbox`.

Use existing `--motion-fast`, `--ease-standard`, theme colors, button styles,
and responsive breakpoints. Keep touch movement local to the inline gallery
image button, with vertical page scrolling and pinch zoom available. Use
opacity-only image feedback. Do not add dependencies or replace the navigation
composition.

## Scope boundaries

No changes to APIs, authentication, permissions, payment, submission rules,
routes, document content, or production configuration. Dossier progress-bar
layout motion is a separate follow-up. No commit, push, or deployment.

## Verification

Run focused Vitest coverage for the home page and gallery, ESLint on changed
source files, and TypeScript checking. Inspect the public home page at 320,
360, 375, 390, 430, 768, 1024, and 1440 CSS px in light and dark themes; check
reduced motion at a mobile size. Confirm guest and signed-in actions, the
establishment document, gallery swipe, no horizontal overflow, and that the
fixed navigation does not obscure the establishment section.
