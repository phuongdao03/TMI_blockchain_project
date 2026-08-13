# Credential Rotation

Use this runbook whenever a credential is downloaded into a workspace, appears
in logs, or may have been shared outside the intended secret store. Never paste
the old or replacement value into an issue, commit, chat, screenshot or report.

## Immediate containment

1. Stop using the affected credential.
2. Confirm the exact provider, project, client/channel and environments that use it.
3. Revoke or rotate it in the provider console before distributing a replacement.
4. Remove downloaded credential files from every developer workspace.
5. Store the replacement only in the approved local or deployment secret store.

Deleting a local file is containment, not rotation. The credential remains live
until the provider confirms revocation or replacement.

## Google and Firebase

For the downloaded Google OAuth client-secret JSON currently identified in the
workspace:

1. Open Google Cloud Console for the Firebase project.
2. Locate the OAuth 2.0 Web client by its client ID.
3. Because the application is migrating to Firebase-only authentication, revoke
   the legacy client secret. Create a replacement only if a verified legacy
   consumer still requires it during the migration window.
4. Confirm Firebase Authentication Google sign-in uses the Web app's public
   Firebase configuration and does not depend on a server OAuth client-secret
   file.
5. Test Firebase login and backend ID-token exchange after revocation.

Record only: operator, UTC time, provider resource identifier, affected
environment, verification result and follow-up owner.

## Repository and history checks

Run checks that report file paths or rule identifiers, never secret values:

```powershell
git ls-files | Select-String -Pattern 'client_secret_|service-account|firebase-adminsdk'
git log --all --name-only --pretty=format: | Select-String -Pattern 'client_secret_|service-account|firebase-adminsdk'
```

If a live credential was committed, rotate it first. Then use an approved Git
history-rewrite procedure and coordinate the required clone/rebase recovery with
every contributor. Adding `.gitignore` does not remove existing history.

## Verification checklist

- [ ] Provider shows the old credential revoked or replaced.
- [ ] Application works with Firebase-only authentication.
- [ ] No credential file is tracked or present in repository history.
- [ ] Local downloaded copies are removed.
- [ ] Ignore rules and automated secret scanning pass.
- [ ] Rotation evidence contains no secret value.
