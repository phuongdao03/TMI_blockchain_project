# Certificate content review and mobile loading

- Council approval creates `certificate_content_drafts` from the approved dossier version. Migration: `0098_certificate_content_drafts`.
- `SUPER_ADMIN` reviews title, summary, recognized subject, and category at `/admin/certificates`. The API also accepts staff with `public_content.manage`, matching existing certificate endpoints. Summary and subject can be cleared. Saving clears prior confirmation.
- New dossiers with an unconfirmed draft stay pending after payment. The migration also creates drafts for existing approved, payment-pending, and paid dossiers without a certificate. Confirmation enqueues issuance when payment is complete. Other legacy dossiers without a draft retain their existing issuance path.
- Issuance copies confirmed content into immutable certificate metadata. PDF and public verification card read those same values. Long PDF content continues on appendix pages.
- Active THV certificates with a confirmed `recordProof` can receive a content-only correction. Administrators search at `/admin/certificates/corrections`, open a dedicated editor, preview changes, and submit a reason. A different administrator approves from the existing version queue. The old version and PDF remain available in history, and the new PDF is rendered through the outbox with scheduled recovery. CNS/TMI certificates require THV conversion first.
- Approval switches the current version before the new PDF worker finishes. During that short interval, the current PDF download returns a pending response; the old PDF remains downloadable from version history.
- `NavigationLoading` shows mobile feedback for internal page navigation while the next route loads; page and data loading states remain in their respective components.

Verification: 60 focused backend tests, 12 focused frontend tests, Ruff, frontend ESLint, and TypeScript checking passed on 2026-10-06. The backend PDF is stored asynchronously after approval.
