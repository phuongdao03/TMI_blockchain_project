# Dossier upload experience

## Goal

Make dossier evidence upload understandable, resilient, and efficient for people
who need to add several files over multiple selections.

## User experience

- The interface uses provider-neutral language. Infrastructure vendor names are
  never shown to users.
- A user can select files more than once. New selections are appended until the
  dossier's remaining file limit is reached.
- Every queued file shows its name, size, progress, and current state.
- A queued or failed file can be removed without affecting the other files.
- Uploading continues past a failed file. Retrying uploads only failed or
  still-pending files, so completed evidence is not duplicated.
- The primary action states the exact work, for example `Tải lên 3 tệp`; an
  explicit `Thêm tệp` action remains available whenever capacity remains.
- Validation and service failures are specific and actionable while hiding
  provider response details.
- Motion is limited to opacity, transform, icon state, and progress;
  reduced-motion preferences are respected.

## Constraints

- The configured size limit remains a per-file limit (currently 100 MB for
  dossier evidence).
- Existing MIME allowlists, signed-upload flow, malware inspection,
  authenticated delivery, and dossier attachment rules remain unchanged.
- The uploader remains reusable for avatars and public work media; multi-file
  queue behavior is enabled only when `multiple` is true.

## Acceptance criteria

1. No user-facing upload state or error contains `Cloudinary`.
2. Selecting one file and then selecting another retains both in the queue.
3. Exceeding the remaining count or file policy does not erase already valid
   queued files.
4. Partial failure preserves successful uploads and retry does not upload them
   again.
5. The user can remove an individual queued/failed file and add another.
6. Desktop and mobile layouts provide accessible named controls and a live
   status region.
7. Focused component tests, formatting, type checking, and browser-level
   verification pass.
