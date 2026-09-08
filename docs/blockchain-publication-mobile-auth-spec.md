# Spec: Blockchain completion, publication handoff, and mobile Google auth

## Objective

Make the production signing journey recoverable across reloads, create the
editorial record after a certificate is issued, and use Firebase's supported
redirect domain on mobile browsers.

## Required behavior

- The signing workspace restores the already-authorized browser wallet without
  requiring the signer to press **Kết nối ví** again after every reload.
- A `BROADCAST` transaction keeps polling the server and can be checked
  manually. It is never presented as confirmed until the backend verifies the
  Polygon receipt, canonical block, event, proof state, and confirmation count.
- Certificate issuance idempotently creates one private `DRAFT` public work.
  The work appears in **Nội dung công bố** for editorial review.
- Signing does not bypass editorial control. A work appears in **Thư viện đề
  cử** only after the existing publication workflow changes it to `PUBLISHED`
  and `PUBLIC`.
- Firebase Auth always uses `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN`. Production must
  not replace this value with the application hostname.
- Mobile Google sign-in uses Firebase redirect authentication; desktop keeps
  popup authentication. Login and registration actions remain full-width,
  readable, and touch-safe on narrow screens.

## Configuration contract

- `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=<firebase-project>.firebaseapp.com`
- Firebase Authentication Authorized domains includes
  `decu.tinhhoaviet.org.vn`.
- The Google OAuth client used by Firebase includes
  `https://<firebase-project>.firebaseapp.com/__/auth/handler`.
- If `/__/auth/*` is proxied on the application origin, the custom-domain
  handler may be registered in addition, but it does not replace Firebase's
  configured `authDomain` without a complete custom-auth-domain setup.

## Verification

- Unit: production Firebase config preserves the configured auth domain.
- Component: a previously connected wallet is restored on mount and a pending
  transaction can be refreshed without reconnecting.
- Backend: successful certificate issuance creates exactly one private draft,
  including on worker replay.
- Responsive UI: mobile drawer account actions stack cleanly and auth controls
  meet a 48px touch target.
