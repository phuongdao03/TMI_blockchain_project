# Mobile Google OAuth on the public site

## Cause

Mobile browsers can open the Firebase popup helper in a separate storage
context. Its initial `sessionStorage` state can then be missing, leaving the
user on a blank Firebase page or showing “missing initial state”. On the
canonical production hostname, the app uses the proxied Firebase helper on
the same origin and redirects in the current window on Android and iOS.
Desktop uses the established Firebase popup handler.

## Production activation order

1. In Google Cloud Console, open the OAuth 2.0 **Web client** used by Firebase
   Authentication's Google provider. Add the exact authorized redirect URI
   `https://decu.tinhhoaviet.org.vn/__/auth/handler`. Keep the existing
   `https://tmi-blockchain.firebaseapp.com/__/auth/handler` URI. The live Google
   error identified client ID
   `739050817519-ethqmff3ta4fp1huk40s8m33ulo7pphv.apps.googleusercontent.com`;
   check this exact client, including URI scheme, hostname, path, and no
   trailing slash.
2. Confirm `decu.tinhhoaviet.org.vn` is in Firebase Authentication → Settings →
   Authorized domains.
3. Install the `location ^~ /__/auth/` block from
   `infrastructure/nginx/decu.tinhhoaviet.org.vn.conf.example` into the active
   VPS Nginx site. Run `sudo nginx -t && sudo systemctl reload nginx`. Verify
   `/__/auth/iframe` returns through the app hostname without a 302 to
   `firebaseapp.com`, and is not served with `X-Frame-Options: DENY` or
   `frame-ancestors 'none'`.
4. Keep `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=tmi-blockchain.firebaseapp.com` in the
   GitHub image build inputs. The canonical hostname
   `decu.tinhhoaviet.org.vn` uses its same-origin helper automatically on
   mobile. Desktop keeps the Firebase-hosted popup helper.
   `NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH=true` enables the same behavior on
   another hostname after its proxy and OAuth URI are configured. Build a new
   frontend image through Delivery and deploy it; changing only the VPS `.env`
   is insufficient.
5. Test Google sign-in and registration on Android and iOS. Confirm the helper
   iframe loads from `decu.tinhhoaviet.org.vn`, the URL returns to that host,
   and the backend Firebase token exchange completes.

If the OAuth URI or proxy must be rolled back, restore the previous frontend
image before removing either production dependency.
