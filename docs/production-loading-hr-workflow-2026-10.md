# Mobile loading, account and work allocation repair

## Scope and acceptance

- Dossier and operations requests return data or a true empty result; server errors remain retryable and identifiable. Do not present a failed request as an empty list.
- Mobile navigation and data loads show immediate, readable progress. Respect the device's reduced motion preference.
- A linked employee can edit their personal contact details from Account; work controlled by HR stays read only. The account view must not be blocked by an unrelated organization request.
- A Super Admin can complete or cancel an open work allocation. Closed work leaves the active queue and remains available in history. Only valid state transitions are accepted and audited.

## Plan

1. Reproduce the API failures from the VPS traceback and add regression coverage.
2. Repair the backend queries and account load boundary.
3. Add allocation state transitions, filtering, and clear controls.
4. Polish mobile loading and explicit empty states.
5. Run focused backend/frontend tests, type checks and builds; review the diff.

## Confirmed production failures

- `GET /api/v1/admin/operations/metrics` raised SQLAlchemy `InvalidRequestError` because `reviewer_workload` joined `User` without an explicit `ReviewAssignment` source. The query now names that source, including when the database has no review assignments.
- The running backend reports both `PII_ENCRYPTION_KEY` and `AUTH_OUTBOX_ENCRYPTION_KEY` as invalid. The former prevents account and organization services from constructing their PII cipher. The latter prevents dossier dependencies from constructing their outbox cipher. Frontend empty states cannot repair these server errors.
- The production database contains one encrypted profile phone and 73 encrypted outbox events. The two keys in `infrastructure/.env.production.before-cns-image-prefix.20260916151954` were verified against that database (`PII MATCH`, `OUTBOX 73/73`). Preserve those original keys; replacing them with new random keys would make those records unreadable. Restore only the two key lines to `infrastructure/.env.production` after backing it up. Do not print or commit key values.
- Release scripts now reject malformed encryption keys before deploying. After restoring the original keys, recreate the backend, worker and scheduler containers that use them. Verify `/api/v1/users/me`, the dossier list, and `/api/v1/admin/operations/metrics` through authenticated sessions. The operations query fix still requires deploying the new backend image.

## Verification

- Focused backend regression tests cover the operations query, work allocation lifecycle, and environment key gate.
- Frontend tests cover loading and allocation actions; typecheck, lint and production build provide release checks.
