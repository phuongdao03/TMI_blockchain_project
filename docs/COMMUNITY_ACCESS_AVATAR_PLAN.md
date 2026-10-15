# Community access and avatar plan

Date: 2026-10-15

## Contract

- Anonymous visitors may read published posts, public profiles, categories, and search results.
- Every participation or community write action requires a signed-in session; backend mutations keep their CSRF-protected principal dependency.
- A member can upload a JPEG, PNG, or WebP avatar directly from the device through the existing inspected `AVATAR` media flow (maximum 5 MiB by default, backend setting authoritative).
- The backend accepts only an active, inspected asset owned by that member. Public delivery is allowed only while the asset is attached to an active community profile.
- Members can keep a legacy HTTPS avatar, replace it with an uploaded avatar, or clear it. Unattached uploads are deleted when canceled or replaced before save.

## Implementation slices

1. Make guest read-only status visible in the public feed; confirm existing mutation routes remain session and CSRF protected.
2. Add nullable community profile media association and migration; validate owner, purpose, inspection state, and size on update.
3. Add public avatar delivery guarded by active profile association and retained private media checks.
4. Replace avatar URL editing with device file selection, upload progress/preview, remove/cancel cleanup, and media ID submission.
5. Update API/spec/handoff docs and mark acceptance state.

## Acceptance

- Guest feed clearly explains read-only access and directs participation to sign-in.
- Guests can still read published content; write endpoints reject anonymous requests.
- A signed-in member can upload and save an avatar, then see it in profile, feed, and comment author projections.
- Another member cannot attach the upload; unassociated/inactive/deleted assets cannot be delivered.
- Replacing, removing, or canceling an unsaved upload cleans up the unattached asset when possible.
