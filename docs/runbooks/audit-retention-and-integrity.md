# Audit retention and integrity runbook

## Operating rules

- Production requires `AUDIT_INTEGRITY_KEY` with at least 32 characters and an explicit `AUDIT_INTEGRITY_KEY_ID`. `AUDIT_INTEGRITY_VERIFICATION_KEYS` is a JSON object of historical key IDs to managed-secret values.
- Keep the active key in managed secret storage, separate from JWT, PII, payment and blockchain keys.
- Audit rows stay append-only in the primary database. Archive is a controlled export to separately governed, access-logged storage; it is not an application delete operation.
- The default retention deadline is seven years. Legal or incident holds override routine expiry.

## Daily integrity check

1. A `SUPER_ADMIN` opens **Lịch sử vận hành** and runs **Kiểm tra ngay**.
2. `VERIFIED` needs no action. `UNSEALED` is expected only for approved legacy rows.
3. Treat `TAMPERED` as a security incident. Freeze exports, preserve database and application evidence, and follow the incident-response runbook.
4. `KEY_UNAVAILABLE` means the row's key identifier is absent from the active/historical verification keyring. Restore the governed historical key; never rewrite the row or its key identifier.
5. Record the check ticket/reference outside the audit database. The application also writes `audit.integrity_checked`.

## Controlled export

1. Apply the narrowest date/action/resource filters needed.
2. Export is capped at 10,000 rows and writes `audit.exported` in the same request transaction.
3. Store the CSV encrypted with access logging and the approved retention policy.
4. Do not treat CSV as integrity evidence; verify rows in the application before export and preserve the database backup/checkpoint used.

## Key rotation

1. Create a new managed secret and a new key ID; do not reuse an ID with different key material.
2. Before switching the active key, add the old ID/material to `AUDIT_INTEGRITY_VERIFICATION_KEYS`, for example `{"audit-v1":"<managed-secret>"}`. Key material must contain at least 32 characters; IDs are limited to 64 safe characters.
3. Deploy the new `AUDIT_INTEGRITY_KEY` and `AUDIT_INTEGRITY_KEY_ID` together. New rows use only the new active key; existing rows remain unchanged and verify through the historical keyring.
4. Run an integrity check covering rows sealed by both IDs. Roll back the configuration change if either key reports `KEY_UNAVAILABLE` or `TAMPERED`.
5. Retain every historical key until all rows bearing its ID have passed retention and legal-hold review.

## Recovery constraints

- Never disable the database UPDATE/DELETE guards to repair a row.
- Never backfill a seal onto a legacy `UNSEALED` row and represent it as historical evidence.
- Restore from an approved backup or replica when primary evidence is damaged, then reconcile by row ID and integrity status.
