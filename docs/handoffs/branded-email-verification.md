# Email verification for password accounts

Firebase email/password registration and resend call `POST /api/v1/auth/firebase/verification-email` with the current Firebase ID token. The backend verifies that the token belongs to an enabled, unverified password account, applies an IP and email rate limit, generates a Firebase one-time code, and sends a Vietnamese email through the configured SMTP service. The email links to `/auth/action` on `APP_BASE_URL`; the client applies the code and shows the result in Vietnamese.

Production needs working `SMTP_*` settings, Firebase Admin credentials, `FIREBASE_PROJECT_ID`, and `APP_BASE_URL=https://decu.tinhhoaviet.org.vn`. A failed SMTP send returns 503 so registration does not claim the mail was sent. The new account can sign in again to request another verification email.

Firebase's own email templates, such as the password reset message, still use the Firebase Console sender name, template, and action URL settings. Update those settings and the sender domain in Firebase Console to remove the previous project name from messages outside this custom verification flow.
