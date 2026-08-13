# Firebase TOTP MFA runbook

## Production prerequisites

1. Upgrade Firebase Authentication to Google Cloud Identity Platform.
2. Enable Google and Email/Password providers as required by the product.
3. Enable TOTP under Authentication > Sign-in method > Multi-factor authentication.
4. Add every production hostname to Authorized domains.
5. Set `FIREBASE_TOTP_ENABLED=true` and `STAFF_MFA_MAX_AGE_SECONDS=43200` in the backend runtime.

The backend refuses to start with `APP_ENV=production` unless the TOTP flag is
enabled. The flag is an operator attestation; deployment approval must also
capture a screenshot or exported Identity Platform configuration because the
runtime service account currently has read-only token-verification scope.

Firebase requirements and APIs:

- <https://firebase.google.com/docs/auth/web/totp-mfa>
- <https://firebase.google.com/docs/reference/admin/node/firebase-admin.auth.decodedidtoken>

## Enrollment and sign-in

- A super administrator sends an invitation from the staff account workspace.
- The employee opens `/staff-invitation`, signs in with the exact verified email,
  and accepts the one-time invitation.
- No application session is issued yet. The browser creates a TOTP secret and
  requires a valid six-digit code before enrollment completes.
- On later sign-ins Firebase presents the TOTP challenge. The backend only issues
  a privileged session when the ID token contains `firebase.sign_in_second_factor
  = "totp"` and recent `auth_time` evidence.
- MFA evidence is copied to the server session. Refresh and authenticated access
  are rejected after the configured maximum age.

The local Firebase Auth Emulator does not provide the production TOTP journey.
Keep `FIREBASE_TOTP_ENABLED=false` only in local Docker. Staging and production
must use a real Identity Platform tenant with the flag enabled.

## Lost-device recovery

Recovery never removes a role or silently lowers authentication assurance.

1. Verify the employee through the approved support channel and record a reason.
2. A super administrator calls
   `POST /api/v1/admin/staff-accounts/{userId}/mfa-recovery`. The backend
   immediately suspends the account, revokes active sessions, opens a 24-hour
   recovery window, and writes an audit event.
3. An Identity administrator removes the lost TOTP enrollment in Firebase. This
   requires a separate privileged operator and must be recorded in the ticket.
4. Send the employee the canonical URL `/staff-mfa-recovery`.
5. The employee signs in with the same verified Firebase identity. The backend
   consumes the recovery authorization and the page forces enrollment of a new
   TOTP factor before redirecting to login.
6. Confirm the next login contains a TOTP challenge and close the ticket with the
   two audit event IDs.

If any identity, email, status, role, or 24-hour check fails, the account stays
suspended. Do not reactivate it through the generic status control as a recovery
shortcut.

Firebase does not supply recovery codes for TOTP MFA. Removing an enrolled
factor is an administrative Identity Platform operation:
<https://cloud.google.com/identity-platform/docs/work-with-mfa-users>.

## Verification

Run:

```text
python -m pytest backend/app/tests/test_staff_mfa.py -q
docker compose exec frontend npm test -- src/components/auth/google-oauth-button.test.tsx src/components/auth/staff-invitation-form.test.tsx
```

For staging, verify invitation enrollment, later TOTP challenge, stale-MFA denial,
lost-device recovery, audit records, and session revocation with two test users.
