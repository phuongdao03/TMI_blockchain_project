# Mobile performance audit

Date: 2026-10-11. Scope: Next.js frontend at `decu.tinhhoaviet.org.vn` and the matching local production build. Preserve visual design, routes, permissions, and API contracts.

## Baseline and evidence

- Chrome mobile emulation: 390 x 844 CSS px, device scale 3, 4x CPU slowdown, Fast 4G. This is synthetic evidence, not a physical Android or iPhone measurement.
- Live homepage navigation: LCP 2,148 ms, CLS 0.00. Live menu opening trace: INP 402 ms (34 ms input delay, 261 ms processing, 106 ms presentation); forced reflow 123 ms. A separate local production trace measured menu INP 661 ms (60/455/146 ms) and forced reflow 231 ms. The variation means a single run is not a stable score.
- The local menu trace recalculated style for 537 elements (62 ms). Source inspection finds `PublicShell` changes `document.body.style.overflow` and immediately focuses a link when opening the drawer. A full-document style change followed by focus is a plausible cause of the reflow; verify with the same trace after the fix.
- The homepage renders 38 gallery thumbnails and a spinning `ImageLoadingStatus` while the stage image is lazy loaded roughly 4,800 px below the initial viewport. Three featured-work skeletons also pulse before their offscreen section enters the viewport. These animations run while invisible and create avoidable work. The gallery spinner is dismissed by image load or error, so its continuing presence before scrolling is explained by lazy loading, not evidence of an animation CSS defect.
- Existing `auth-activity-spinner` and Tailwind `animate-spin` use transform rotation. No frame-by-frame JavaScript rotation or infinite state update was found in the inspected loading components. No proof yet that the auth spinner itself is the root cause of the reported freeze.

## Implementation slices

1. Remove the whole-body overflow mutation on public menu open, preserving background touch scroll blocking with the fixed backdrop and contained navigation. Verify focus trap, close behavior, and mobile scrolling.
2. Start gallery loading animation only when the stage approaches the viewport; keep image lazy loading, loading/error copy, all 38 thumbnails, and modal behavior. Stop offscreen featured skeleton pulses until the section approaches.
3. Rebuild and measure the local production bundle with the same mobile emulation, checking menu INP/reflow, spinner state before and after scrolling, console errors, desktop and reduced-motion behavior.

## Result of this pass

- Removed the full-page `body.style.overflow` write when the public mobile menu opens. The fixed backdrop blocks background touch gestures; the drawer keeps vertical touch scrolling and scroll containment. Focus trap and close behavior still pass component tests. Physical Safari touch behavior is unverified.
- The gallery now waits until 400 px before its stage enters view before showing the loading spinner and mounting 38 thumbnail buttons/images. The thumbnail strip keeps reserved height. Offscreen featured-work skeletons do not pulse until their existing observer activates.
- Local production homepage before the gallery change: 655 DOM elements, with 38 children in the thumbnail strip. After: 579 elements, with zero offscreen thumbnail buttons; all 38 appear when the gallery is reached. Chrome's style recalculation insight changed from 537 affected elements to 461 in the respective traces. This is a reduction in initial work, not proof of a proportional frame-rate gain.
- Menu traces varied. A local navigation-and-menu run recorded INP 661 ms before and 419/491 ms after initial changes; a settled-page comparison recorded 632 ms on the live site and 328 ms on the local build. All are single synthetic runs, and the final value remains above the 200 ms good threshold. The traces do not isolate one exclusive cause of the reported stalls.
- On Slow 3G at the visible gallery, the CSS `spin` animation reported `running` and the loading status disappeared after the image loaded. At initial load 4,790 px above the gallery, the final build rendered no gallery loading status or thumbnail buttons. At 390 and 1280 px, the local page had no horizontal overflow; gallery arrows still selected another photo and mounted the full thumbnail strip. No console error was observed. A local image-preload warning was seen.
- After the final code change, the full frontend suite passed (656/656), as did lint, typecheck, production build and `git diff --check`. Chrome checked the final production build at 390 px: the offscreen gallery rendered no loading status, all 38 thumbnails appeared on approach, and no console error or horizontal overflow occurred.

## Verification commands

From `frontend/`: `npm.cmd test -- --run`, `npm.cmd run lint`, `npm.cmd run typecheck`, `npm.cmd run build`. Use focused component tests during each slice and Chrome DevTools traces for runtime checks.

## Limits

Authenticated submit/upload/review flows require test accounts and a suitable nonproduction backend. Safari/iOS and physical low-end Android cannot be certified from Chrome emulation. No production forms or transactions are submitted in this audit.

## Navigation and loading follow-up (2026-10-11)

- The global route indicator previously waited 120 ms before showing its mobile message and cleared itself after 15 seconds, even if the route had not arrived. It now shows a spinner and message at navigation start, changes the message after 8 seconds, and stays until the pathname or query changes. The top progress bar uses a single transform animation; reduced-motion mode disables its animations.
- Public and dashboard layouts now place their server-side session lookup inside Suspense. Their `PageLoading` fallback can stream while that lookup waits; the dashboard authorization check and redirect still occur before protected children render.
- Programmatic navigation from autocomplete, dossier creation, checkout and staff invitation now starts the same feedback. The full-screen sign-in status no longer uses a viewport-wide backdrop blur, reducing repaint work on mobile.
- Chrome production build at 390 × 844, 4× CPU slowdown, Slow 3G showed the route loading status during home-to-login navigation. This confirms feedback appears in that tested route, not a measured improvement to physical-device frame rate or authenticated flows.
- Focused navigation tests, lint, typecheck and production build passed. The full suite passed with two Vitest workers (658/658). Default worker concurrency produced timing failures in unrelated UI tests, including when run without lint/build; limiting workers removed them. No review or HR component source changed in this pass.
