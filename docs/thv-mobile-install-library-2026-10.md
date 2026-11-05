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

## Follow-up: restore help content and direct PWA installation (2026-11-05)

### Acceptance criteria

- The help center always offers detailed public, task-focused guides while the
  role-filtered CMS catalog loads, is empty, or is unavailable.
- Every built-in guide link opens a complete article without requiring a CMS row;
  private role-specific CMS articles remain protected by the existing API.
- Android and desktop show a real install action that calls the browser's saved
  `beforeinstallprompt` event when available. If the browser cannot provide that
  event, the action explains the platform's manual installation steps.
- iOS continues to use Safari's required “Thêm vào Màn hình chính” confirmation.

### Implementation plan

1. Add a small set of verified Vietnamese starter guides and use them as a
   visible fallback without replacing role-filtered CMS results.
2. Resolve built-in guide routes locally when the CMS request is missing or
   pending, while preferring a published CMS article when it exists.
3. Keep an install button visible on supported mobile/desktop browsers; use the
   native prompt when available and show manual instructions otherwise.
4. Run focused lint/type checks and inspect the guide/install screens in the
   local browser. Do not query or mutate production data.

### Completed

- Added seven Vietnamese starter guides for account setup, dossiers, wallet
  top-ups, certificate lookup, community use and app installation. The public
  fallback remains available while CMS data loads or fails; CMS articles keep
  their existing audience and permission filters and take precedence when they
  contain matching content.
- Built-in guide links now render their full local article if the CMS article
  cannot be fetched. Search and topic filters also cover the fallback content.
- Android and desktop now show a prominent install button. It opens the saved
  native install prompt when available and offers clear menu steps otherwise.
  iOS still directs users to the required home-screen confirmation flow.
- Focused ESLint and TypeScript checks passed. The local guide list and article
  opened with no horizontal overflow at the 501 px mobile browser viewport.
  The local browser did not provide a native install event, so native install
  confirmation remains a real-device/browser check.
