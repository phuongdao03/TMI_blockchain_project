# Admin dashboard P0 handoff

## Status

Completed on 2026-08-29. This slice establishes auditable fine-grained
permissions and the production `/admin/users` workflow. It deliberately does
not claim analytics, finance, blockchain, storage, or system-health modules as
production-ready.

## Authorization decision

The existing four roles remain unchanged:

| Role | Purpose | Admin behavior |
|---|---|---|
| `VIEWER` | Public/read-only identity | No admin access by default |
| `USER` | Applicant account | No admin access by default |
| `MODERATOR` | Internal operational account | Receives only explicit role/direct permissions |
| `SUPER_ADMIN` | Restricted platform authority | Protected from ordinary UI mutation |

Operational scope is extended with direct `resource.action` grants instead of
adding more roles. Effective permissions are the union of role permissions and
non-expired direct grants. Backend policy checks remain authoritative; frontend
permission checks only remove unavailable controls.

P0 user-management permissions:

| Permission | Capability |
|---|---|
| `users.read` | List and inspect masked admin user records |
| `users.suspend` | Suspend/restore eligible users with a reason |
| `users.sessions.revoke` | Catalog entry reserved for explicit session management |
| `staff.permissions.assign` | Replace another staff member's direct grants |

No migration assigns these permissions to existing accounts or automatically
promotes an account to `SUPER_ADMIN`.

## Database migrations

Apply in Alembic order:

1. `0062_user_permissions.py` adds direct grants and append-only revisions.
2. `0063_admin_permission_catalog.py` seeds the admin permission catalog only.
3. `0064_admin_user_indexes.py` adds user-list query indexes.

Before deployment, back up the database and verify the current Alembic revision.
After migration, grant the minimum required permissions through a controlled
bootstrap/administrative process and record the reason. Do not edit permission
rows manually in routine operations.

Rollback must run in reverse revision order. Downgrading `0062` destroys direct
grant and revision data, so export that data and confirm no runtime depends on it
before rollback. Catalog downgrade removes only codes inserted by `0063`; it
does not revoke unrelated permissions.

## API contract

All endpoints require an authenticated, active principal and enforce permissions
server-side.

| Method and route | Permission | Notes |
|---|---|---|
| `GET /api/v1/admin/users` | `users.read` | Page size 1–100; server search/filter/sort; stable ID tie-break |
| `GET /api/v1/admin/users/{id}` | `users.read` | Explicit masked response schema; 404 for missing user |
| `PATCH /api/v1/admin/users/{id}/status` | `users.suspend` | Requires reason and expected status; revokes sessions on suspend |
| `GET /api/v1/admin/staff-accounts/{id}/permissions` | `staff.permissions.assign` | Returns direct grants and revision version |
| `PUT /api/v1/admin/staff-accounts/{id}/permissions` | `staff.permissions.assign` | Optimistic version check and immutable audit record |

Status mutation forbids self-suspension, ordinary mutation of a Super Admin,
hard deletion, disabled-account restoration, and stale expected status. Audit
captures actor, target, old/new values, reason, request ID, and user agent.

Authentication responses now include `permissions`, allowing the browser to
render navigation and actions from the same effective permission set used by
the backend.

## Frontend behavior

`/admin/users` uses only the admin API. Desktop renders a server-paginated table;
mobile renders touch-friendly cards and a bottom-sheet confirmation dialog.
Search, status filter, sorting, pagination, loading, empty, API error, retry, and
permission-denied states are explicit. Suspension/restoration requires at least
10 characters of reason.

## Verification evidence

- Backend P0 suite: 12 passed.
- Frontend API/component/navigation suite: 29 passed at checkpoint; focused
  post-accessibility suite: 15 passed.
- Playwright: desktop Chrome and Pixel 7, 2 passed; includes axe scan and status
  mutation journey.
- TypeScript: passed.
- ESLint: passed after the final semantic change.
- Next.js production build: passed after the final change; `/admin/users` emitted.
- `git diff --check`: passed.

Warnings are limited to the existing Node `NO_COLOR`/`FORCE_COLOR` test-server
message. No production secret or private key is exposed.

## Operations and known dependencies

- A real administrator still requires a valid email-based authentication account
  and controlled role/permission bootstrap. Never seed the previously requested
  weak password into production.
- Docker was unavailable during local bootstrap; no real local admin account was
  created in this slice.
- The remaining admin modules stay tracked as P1/P2 in
  `docs/admin-dashboard-p0-plan.md`; do not expose mock metrics as production data.
