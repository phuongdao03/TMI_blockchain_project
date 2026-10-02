# Admin announcements and employee profile

## Delivered contract

- `POST /api/v1/admin/notifications/preview` accepts `audience` (`ALL`, `USERS`, `EMPLOYEES`, `INDIVIDUAL`) and optional `recipientUserId`. Returns `recipientCount`.
- `POST /api/v1/admin/notifications` also accepts `campaignId`, `title`, and `body`. Only `SUPER_ADMIN` can call either endpoint. CSRF protection applies.
- Recipient selection uses active accounts. An employee audience requires a linked employee row with `employment_status=ACTIVE`; users are the remaining active accounts. Individual recipients must be active.
- Notifications are stored in the existing per-user table with `type=admin.announcement`; the existing bell and notification center display them. A repeated `campaignId` with the same content returns the original count; different content returns 409. Sending is audit logged.
- Admin UI: `/admin/notifications`, with recipient search, preview count, and explicit confirmation.

## Employee account

- `GET /api/v1/users/me` now fills missing personal name and phone from the linked employee record and returns an `employment` summary with code, department, position, status, and join date. Salary stays in the protected HR area.
- The account page displays this summary and keeps the personal name and phone editable. Existing profile updates propagate those fields to the employee record.

## Verification

- Backend tests cover audience counts, idempotency, super-admin guard, HTTP send, notification center visibility, and employee profile serialization.
- Frontend tests cover composer confirmation and profile editing. Run lint, typecheck, and formatting checks before delivery.
