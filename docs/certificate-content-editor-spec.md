# Certificate content review before issuance

## Objective

An administrator reviews and edits the fields printed on a new certificate before the first certificate metadata hash is frozen. The downloaded PDF and public verification card use the same frozen metadata. Existing certificates remain immutable and use the version correction workflow.

## Workflow

1. Council approval creates a pending content draft from the approved dossier version.
2. An administrator edits title, summary, recognized subject, and category. Empty summary or subject removes that optional text. The editor previews the exact field values used by the PDF and public verification card.
3. Paying for the dossier does not issue a certificate while its draft is pending.
4. Administrator confirmation freezes the draft and resumes issuance if payment has completed. After certificate creation the draft is read-only.
5. Migration backfills approved, payment-pending, or paid dossiers that have no certificate. Older dossiers without a draft continue through the previous issuance flow.

## Correction of issued THV certificates

1. An administrator opens `/admin/certificates/corrections`, searches certificates by number, dossier code, or title, then opens a dedicated editor for an active THV certificate. Unsupported certificates remain visible with a reason they cannot yet be edited. The editor shows the current four fields, previews proposed changes, and requires a reason.
2. The server verifies the current metadata hash and confirmed THV dossier proof, then creates a pending certificate version with the same approved dossier version, a new metadata hash, and a new QR token. The active PDF remains available during review.
3. A different administrator reviews the proposed content in the version request queue. Approval promotes the new version and queues its PDF through the durable outbox. The previous version and PDF remain in history; its QR is labeled as an older version.
4. The scheduled publication repair job retries missing PDFs for active corrected versions.
5. Legacy CNS/TMI certificates must be converted to the THV certificate format before using this content-only correction flow.

The certificate manager links to the dedicated editor. The list and editor are restricted to super administrators in the frontend; the API enforces the existing certificate content management permission. The editor does not modify the current version when the request is submitted.

## Validation and security

- The admin page is gated to `SUPER_ADMIN`. The API uses the existing `public_content.manage` certificate administration policy, which also admits granted staff principals.
- The approved dossier snapshot and its hash remain unchanged.
- Validation bounds field sizes; title and category are required.
- Confirmation and preparation lock the dossier row and enforce one certificate per dossier.

## Verification

- Test pending draft blocks issuance, confirmation resumes it, edits reach metadata and PDF, and edits are refused after issuance.
- Test content-only corrections require verified THV proof, a second approver, preserve the predecessor, and queue a replacement PDF.
- Test mobile navigation loading appears on a delayed route transition and clears on arrival.
- Run focused backend and frontend tests, lint, format, and type checks.
