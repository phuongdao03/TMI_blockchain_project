# Android Google OAuth in the installed web app

## Cause

Android opens the Firebase popup helper in a separate browser context. With the
helper on `tmi-blockchain.firebaseapp.com`, its initial `sessionStorage` state
can be missing, leaving the user on a blank Firebase page or showing “missing
initial state”. When the proxy flag is enabled, Android uses Firebase redirect
in the current window and the helper shares the application origin. iOS keeps
the popup path that already works.

## Production activation order

1. In Google Cloud Console, open the OAuth 2.0 **Web client** used by Firebase
   Authentication's Google provider. Add the exact authorized redirect URI
   `https://decu.tinhhoaviet.org.vn/__/auth/handler`. Keep the existing
   `https://tmi-blockchain.firebaseapp.com/__/auth/handler` URI.
2. Confirm `decu.tinhhoaviet.org.vn` is in Firebase Authentication → Settings →
   Authorized domains.
3. Install the `location ^~ /__/auth/` block from
   `infrastructure/nginx/decu.tinhhoaviet.org.vn.conf.example` into the active
   VPS Nginx site. Run `sudo nginx -t && sudo systemctl reload nginx`. Verify
   `/__/auth/iframe` returns through the app hostname without a 302 to
   `firebaseapp.com`, and is not served with `X-Frame-Options: DENY` or
   `frame-ancestors 'none'`.
4. Set GitHub repository variable `NEXT_PUBLIC_FIREBASE_SAME_ORIGIN_AUTH=true`.
   Keep `NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN=tmi-blockchain.firebaseapp.com`.
   Build a new frontend image through Delivery and deploy it. These values are
   compiled into the frontend; changing only the VPS `.env` is insufficient.
5. Test Google sign-in and registration from the installed Android app and from
   Safari on iOS. Confirm the URL returns to `decu.tinhhoaviet.org.vn` and the
   backend Firebase token exchange completes. Do not use the Firebase helper
   in a separate Chrome tab as the success criterion.

The flag defaults to `false` until the OAuth redirect URI and VPS proxy are
ready. This keeps the existing iOS flow working during the configuration
change. To roll back, set the GitHub variable to `false`, rebuild, and deploy.
