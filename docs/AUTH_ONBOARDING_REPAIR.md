# Account entry and submission UX repair

## Scope and contract

- Email signup remains Firebase email/password with verified email required before a THV session. Account creation and email delivery are separate states; an email delivery failure must not invite duplicate registration. Bound delivery waiting and provide Firebase delivery fallback only for service/network unavailability, never rate-limit or identity failures.
- Add `POST /api/v1/auth/username-login` with `{username,password}`. Reuse the unique, case-insensitive community username; do not expose its email. Rate-limit IP and identifier before lookup. Authenticate existing local passwords through SessionService, and Firebase passwords through the official accounts:signInWithPassword API plus verified token/identity matching. Issue existing httpOnly THV cookies; never create an account or return a provider token from this endpoint.
- Users set their username in account settings using the existing community-profile update API. No database migration or identity import.
- A new public account has an overview of available actions. Choosing sender type activates submission permissions and immediately opens `/dossiers/new`, rather than showing a second overview. Deep links to dossier creation offer the same sender choice.
- Name reminders are optional, dismissible and contextual; they do not cover the public landing or dossier forms. Preserve Google-provided display names on initial account creation.
- Preparation steps: “Loại hồ sơ”, “Thông tin hồ sơ”, “Thông tin bổ sung”, “Xem lại & tạo bản nháp”. Clearly distinguish preparing a draft from submitting it.
- Notification previews and the full inbox share unread-count cache, report mutation failures and support narrow-screen scrolling without blocking page interaction.

## Ordered implementation

1. Reproduce signup state errors; add username service and credential/identity security tests; connect the login and username settings UI.
2. Repair sender onboarding and name reminders, then update preparation copy and regression tests.
3. Measure mobile loading/interaction. Remove redundant new-account requests, unbounded waits and unnecessary continuous animation only where evidence supports the change.
4. Run focused pytest/Vitest, desktop/mobile Playwright, Ruff, ESLint, TypeScript/mypy and formatting. Review changed files and record a handoff before committing.

## Performance baseline

Anonymous production landing, 390×844, Slow 4G, 4× CPU, cold reload: LCP 1.95s, TTFB 54ms, CLS 0.02. This does not reproduce authenticated navigation delays. Source inspection identifies unbounded server-session/API requests, duplicate unread-count keys and three unnecessary task queries for a completely new account; verify those paths locally with request counts and failure/latency fixtures.

## Boundaries

No production account creation, email sending, password reset or privileged role changes during local tests. Keep CSRF, verified-email checks, identity ownership and existing password/rate-limit policy. Existing API response/error envelopes and session cookies remain authoritative.

Reference: https://firebase.google.com/docs/reference/rest/auth#section-sign-in-email-password

## Delivery and verification

- Username login uses `FIREBASE_WEB_API_KEY`, falling back to the existing `NEXT_PUBLIC_FIREBASE_API_KEY` in the backend environment. If the frontend key has browser referrer restrictions, supply a dedicated key permitted for backend Identity Toolkit requests. No migration is needed. Existing public handles remain valid; customers may choose a readable username in Account settings.
- Verification delivery waits up to 12 seconds for branded mail, then uses Firebase delivery on service/network failure with a 15-second limit. Identity and rate-limit errors do not trigger fallback. Account creation succeeds independently of email delivery; the result explains how to resend by logging in.
- Verified 177 frontend tests, 22 distinct backend authentication tests, TypeScript, ESLint, Ruff and mypy. Desktop/mobile browser coverage passed email signup, email/Google/username login, password recovery, session refresh, full dossier submission and direct sender upgrade to preparation. One desktop Google-registration test is intentionally mobile-only.
- Browser inspection at 390px confirmed no horizontal overflow on login, preparation and notification pages. The display-name reminder is absent during preparation. New-account regression verifies only one dossier-list request, skipping all three priority searches.
- Performance changes bound server session checks to 4 seconds and client GET requests to 10 seconds, share unread-count queries, and replace the voucher dialog's repeated DOM polling with event observation. These are verified code paths, not a claim that production mobile latency has been fully eliminated.
- Fixed a streamed notification-page hydration mismatch caused by a header-populated unread cache. A stable initial loading shell precedes the inbox. Desktop/mobile regression opens and reloads the inbox after username login and checks for page errors and horizontal overflow.
