# Certificate content review and mobile loading

- Council approval creates `certificate_content_drafts` from the approved dossier version. Migration: `0098_certificate_content_drafts`.
- `SUPER_ADMIN` reviews title, summary, recognized subject, and category at `/admin/certificates`. Draft and issued-content editing now require that role; a staff permission alone is insufficient. Category selection uses active system categories, and the server derives the matching category code. Summary and subject can be cleared. Saving clears prior confirmation.
- New dossiers with an unconfirmed draft stay pending after payment. The migration also creates drafts for existing approved, payment-pending, and paid dossiers without a certificate. Confirmation enqueues issuance when payment is complete. Other legacy dossiers without a draft retain their existing issuance path.
- Issuance copies confirmed content into immutable certificate metadata. PDF and public verification card read those same values. Long PDF content continues on appendix pages.
- Active THV certificates with a confirmed `recordProof` can receive a content-only correction. Administrators search at `/admin/certificates/corrections`, open a dedicated editor, preview changes, and submit a reason. One `SUPER_ADMIN` submission activates the new version; applicant dossier-version requests retain their separate approval rule. The old version and PDF remain available in history, and the new PDF is rendered through the outbox with scheduled recovery. CNS/TMI certificates require THV conversion first.
- Activation switches the public verification content before the new PDF worker finishes. During that short interval, the current PDF download returns a pending response; the old PDF remains downloadable from version history. Both outputs use the corrected version's `asset` metadata.
- `NavigationLoading` shows mobile feedback for internal page navigation while the next route loads; page and data loading states remain in their respective components.

Verification: 60 focused backend tests, 12 focused frontend tests, Ruff, frontend ESLint, and TypeScript checking passed on 2026-10-06. The backend PDF is stored asynchronously after approval.

2026-10-07 follow-up: 27 focused certificate/media backend tests, 46 nearby API and visibility tests, 586 frontend tests, Ruff, mypy, ESLint, TypeScript and the frontend production build passed locally. Production PDF generation still requires the running worker.
