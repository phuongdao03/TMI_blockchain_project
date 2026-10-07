# Certificate content and public media follow-up

## Objective

Give the existing certificate administrator one clear action to correct an
issued THV certificate, keep its previous version for audit, and generate a
fresh PDF. The same corrected content must appear in public web verification and
the downloadable PDF. Draft and correction category choices come from active
system categories.

Improve perceived and actual loading of public work covers and videos. Old
retained videos must remain playable while their public derivative is being
prepared; future videos should use the adaptive stream whenever it is ready.

## Acceptance criteria

- Only a `SUPER_ADMIN` with `public_content.manage` can edit draft or issued
  certificate content. A content correction becomes the active version from that
  admin's submission without another person's approval; PDF generation remains
  asynchronous and previous versions remain available.
- Category inputs are selectors populated from active system categories; the API
  rejects a category that is not active. Historical category text remains
  visible until an admin chooses a current category.
- Admin pages accurately describe the one-admin action and distinguish web
  verification from PDF download.
- Public catalog covers avoid unnecessary repeated transfers and show useful
  loading feedback. Adaptive video uses streaming first when available; retained
  MP4 remains a fallback.
- Existing applicant-initiated dossier version requests keep their separate
  approval rule.

## Verification

- Focused backend certificate version/content tests and frontend certificate
  editor/video tests.
- Frontend type, lint, and production build gates.
- Review public media authorization and caching behavior before release.

## Constraints

- No direct mutation of an issued version's metadata or PDF.
- No public caching of unpublished or revoked assets.
- Production media latency and Cloudinary derivative readiness require
  post-deploy observation; local tests cannot guarantee mobile network
  throughput.
