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

Firebase TOTP is no longer an application requirement. Remove obsolete staff
MFA feature flags and age settings from every runtime, secret store and
deployment environment. Administrators and reviewers now use the same
verified-email Firebase exchange as other accounts; role and permission checks
still determine access after the session is issued.

The former staff MFA recovery endpoints and enrollment screens are removed.
Historical MFA database fields and migrations remain in place for audit and
rollback compatibility, but active authentication does not read or update them.
