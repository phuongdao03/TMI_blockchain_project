# Spec: Recoverable certificate delivery and mobile account experience

## Objective

Make a confirmed Polygon proof reliably produce a visible certificate, give
mobile applicants a direct path to that certificate, and keep Google sign-in
inside the application origin on storage-partitioned browsers.

## Required behavior

- The signing workspace restores the already-authorized browser wallet without
  requiring the signer to press **Kết nối ví** again after every reload.
- A `BROADCAST` transaction keeps polling the server and can be checked
  manually. It is never presented as confirmed until the backend verifies the
  Polygon receipt, canonical block, event, proof state, and confirmation count.
- Certificate issuance idempotently creates one private `DRAFT` public work. The
  work appears in **Nội dung công bố** for editorial review.
- Signing does not bypass editorial control. A work appears in **Thư viện đề
  cử** only after the existing publication workflow changes it to `PUBLISHED`
  and `PUBLIC`.
- Reconciliation re-enqueues certificate issuance while a confirmed proof is
  still attached to a `PAID` or `ANCHORED` dossier. Issuance remains idempotent
  and stops being requeued after the dossier reaches `CERTIFICATE_ISSUED`.
- Applicant mobile navigation exposes **Chứng thư** directly; notifications
  remain available from the header bell and full navigation drawer.
- Compact mobile headers show only navigation and notification actions. Theme
  and logout actions remain available in the full drawer.
- Production Firebase Auth uses the application hostname as `authDomain` and
  proxies `/__/auth/*` to the configured Firebase Hosting domain. Popup stays
  first; same-origin redirect remains the blocked-popup fallback.
- Login and registration actions remain full-width, readable, and touch-safe on
  narrow screens, with no raw Firebase error page.

## Configuration contract

- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<firebase-project>.firebaseapp.com` remains
  the trusted proxy upstream baked into the frontend image.
- Firebase Authentication Authorized domains includes `decu.tinhhoaviet.org.vn`.
- The Google OAuth client used by Firebase includes
  `https://decu.tinhhoaviet.org.vn/__/auth/handler`.
- Next.js transparently proxies `/__/auth/*` to the configured
  `<firebase-project>.firebaseapp.com` origin; it must not issue a 302 redirect.

## Verification

- Unit: production Firebase config resolves to the application hostname while
  local/test builds preserve the configured Firebase domain.
- Backend: reconciling an already-confirmed proof requeues unfinished
  certificate issuance without creating another blockchain event.
- Component: applicant quick navigation contains **Chứng thư**, and mobile
  account controls remain available in the full drawer.
- Backend: successful certificate issuance creates exactly one private draft,
  including on worker replay.
- Responsive UI: compact header actions do not overflow at 320px and auth
  controls meet a 48px touch target.

## Implementation plan

1. Guard the confirmed-proof recovery path with a backend regression test and
   wire the scheduler to requeue only unfinished certificate issuance.
2. Guard same-origin Firebase auth resolution and applicant quick navigation
   with focused frontend tests, then implement the smallest UI/config changes.
3. Verify focused tests, full formatting/type checks, production build, and
   browser E2E at mobile and desktop breakpoints.
