# Firebase-only authentication migration

The application now has one Google sign-in path: Firebase Authentication in the
browser followed by `POST /api/v1/auth/firebase/exchange`.

Remove `GOOGLE_OIDC_*` and `OAUTH_STATE_TTL_SECONDS` from every secret store.
Keep `FIREBASE_PROJECT_ID`, the public `NEXT_PUBLIC_FIREBASE_*` web values and
the backend Firebase certificate URL. Revoke the obsolete server OAuth client
secret after confirming the Firebase flow in staging.

Any client still calling the former authorization-code start, link or callback
routes must migrate before deployment; those routes now return `404`. Existing
application sessions, refresh rotation, logout and CSRF behavior are unchanged.
