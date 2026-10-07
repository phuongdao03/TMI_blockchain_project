# Mobile, installation, and nomination library follow-up

Date: 2026-10-07. Frontend-only follow-up to [the system UX audit](thv-system-ux-redesign-2026-10.md).

## Findings

- The local USER preview sets `isEmployee` implicitly, so it shows attendance, leave, and overtime although a public applicant has no employee record. Real USER navigation already gates those links on `authUser.isEmployee`.
- The header install CTA always navigates to `/install`; it does not use an available `beforeinstallprompt` event. The manifest uses only a 1254 px image even though 192 and 512 px icons already exist. Service worker registration is production-only by default.
- The catalogue has a featured API and featured section, but on narrow screens the editorial cards are long and visually similar to the result list. Generic `.public-theme-surface` overrides also remap light text and dark backgrounds inside the library, reducing contrast and emphasis.

## Ordered slices and checks

1. Preview role: USER means applicant, with no HR links. Keep real employee links controlled by `isEmployee`. Test both cases.
2. PWA: use 192/512 icons; trigger the native install dialog from the header when the browser offers it; retain a clear install guide otherwise. Test accepted, dismissed, unavailable, installed and iOS cases. Keep browser confirmation mandatory.
3. Library: one prominent featured story, compact supporting recommendations, then search/results. On mobile, expose the first recommendation and filters without a dense sidebar. Use covers when provided and an editorial fallback when missing. Test order, links, filter retention, empty/error states, and reduced motion.
4. Verify at narrow widths and desktop, with keyboard focus and production build. The in-app browser is unavailable in this environment, so visual validation on a real device remains a release check.

No API, role permission, database, or blockchain contract changes.

## Implemented and verified

- USER preview now represents an ordinary applicant; employee navigation appears only when `isEmployee` is true. The role switcher says “Người dùng”.
- The header install control opens the browser's native prompt directly when available, including on phones. Otherwise it opens the install guide; the mobile menu also links there. The theme switch moves into the phone menu to give the install control space. Manifest now serves existing 192 px and 512 px icons.
- The library leads with a large featured nomination, uses compact supporting cards, and avoids repeating those works in results. If no curated works exist, the first public work becomes the lead. Mobile filters trap focus, close with Escape, and restore focus. Cards use a reusable cover fallback; mobile avoids hover motion and respects reduced motion.
- Full frontend suite: 599 tests passed. ESLint, TypeScript, and production build pass. Local `/manifest.webmanifest`, both icons, `/sw.js`, `/works`, `/install`, and preview routes return HTTP 200.
- Visual inspection and the native Android/Desktop install confirmation still require a browser/device session. The in-app browser was unavailable in this environment.
