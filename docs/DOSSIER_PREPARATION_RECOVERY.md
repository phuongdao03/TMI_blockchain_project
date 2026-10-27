# Recover dossier preparation before draft creation

## Goal

Preserve selected type, incomplete core fields, dynamic fields and wizard step
before `POST /dossiers`. Existing dossier draft/edit/submit contracts remain.
One active preparation belongs to each authenticated applicant account.

## Contract

- `GET /api/v1/dossiers/preparation`: own revision, payload and update time;
  revision 0 / null payload means no preparation.
- `PUT /api/v1/dossiers/preparation`: CSRF-protected, owner identity and expected
  revision required; bounded incomplete input is allowed. Conflicting devices
  receive 409 and must choose explicitly which copy to continue.
- `POST /dossiers` accepts optional `preparationRevision`. Creation consumes that
  revision atomically and retains an idempotent reference to the created dossier.
  Retrying a lost create response must not create a second draft.
- Additive migration 0144; existing dossier data and clients remain valid.

## Client behavior

Bootstrap before editing, debounce server saves, serialize writes, retain edits
made during an in-flight save, and show saved only for acknowledged content.
Keep an account-scoped session-only recovery copy for refresh/network failure;
never store credentials or files. Distinguish local recovery from server sync.
Do not overwrite a newer server revision silently. Clear recovery after confirmed
creation. Block creation while the preparation is unsaved/conflicted.

## Checks and boundaries

Backend tests: account isolation, size/type validation, revision conflicts,
atomic consume, lost-response replay and rollback. Client tests: refresh recovery,
in-flight edits, save errors, storage failure and cross-account isolation.
Playwright: reload and resume across browser contexts, narrow layouts, conflicts.
Run focused tests first, then lint/typecheck/build and broader regression.
No production migration, real payment or staging access is implied.

## Implemented and verified — 2026-10-27

Implemented authenticated GET/PUT, owner identity validation, 64 KiB payload
limit, serialized revision writes and atomic creation consumption. A user-row
lock also serializes the first preparation insert. A consumed revision replays
only the same creation fingerprint; changed requests return conflict.

The client blocks initial editing until recovery completes, retains unsaved
input in session storage, stops old-account writes on session changes, and
offers explicit local/server conflict choices. No files or credentials are
stored in the recovery payload. Saved status means server acknowledgement.

Backend recovery/API/migration checks passed, and mypy passed all 454 source
files. Nine hook cases cover restoration, in-flight edits, failure, conflict,
refresh, storage failure, logout, account changes and mismatched response owners. Chrome desktop/mobile
tests verified reload, a fresh browser context and conflicting device edits.
Screenshots: `ux-evidence-2026-10-27/preparation-conflict-*.png`.

Migration 0144 must follow 0143 in the deployment process; neither was applied
to production. PostgreSQL concurrent transaction behavior and real account
sessions still require staging verification. Downgrade refuses active input.
