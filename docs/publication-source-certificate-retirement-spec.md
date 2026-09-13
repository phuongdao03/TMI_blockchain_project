# Publication source, certificate, and voting retirement

## Outcome

Create one continuous path from a user's locked dossier version to review, blockchain proof, certificate, and publication. Administrators reuse the submitted data and media; they do not create a second copy of the work by uploading it again.

## Roles

- User: creates a dossier and uploads source evidence.
- Reviewer: reads the locked version and records an assessment.
- Administrator: signs an approved version, selects its source media, edits public presentation metadata, and publishes it.

## Canonical data

- A locked `DossierVersion.snapshot` is the canonical record for title, summary, explicitly public form fields, and evidence membership.
- A public work references media assets from that version. Attaching media creates a publication relation and derivative, not a new source upload.
- Publication metadata may format the presentation but must retain the source dossier/version relationship and immutable hashes.
- Existing certificate, media, proof, and retired-voting rows remain available for audit and migration. Runtime voting routes are removed.

## Requirements

1. The public editor shows the selected locked version and reusable values entered by the user. Administrators can apply those values without retyping them.
2. The editor's media library lists source evidence from the locked version. The duplicate public upload control is removed.
3. Images from source evidence can be selected as cover art. A selected video can use its automatically generated frame as the cover.
4. Public video delivery provides adaptive HLS where available and an optimized MP4 fallback. Playback is lazy and uses metadata/poster before play.
5. Certificate notifications, including historical notifications that only contain `certificate_id`, open the correct certificate.
6. Certificate detail shows verification state, blockchain identifiers, a stable public verification URL, and a working QR image. The PDF download surface and endpoint are removed.
7. Public voting pages, user navigation, client APIs, backend routes, and scheduled voting jobs are unavailable. Council adjudication votes are unaffected.

## API contract

- Public-work editor data adds the immutable source version number and `sourceFields` (`key`, `label`, `value`). Only fields explicitly marked public in the snapshot are returned.
- Public media responses may include `streamingUrl` and `posterUrl`; the existing optimized `url` remains the fallback.
- Video presentation updates accept an optional submitted image as cover art; otherwise Cloudinary generates a representative video frame.
- `GET /api/v1/certificates/{certificate_id}/qr` returns a no-store PNG after the normal certificate authorization check.
- `GET /api/v1/certificates/{certificate_id}/download` and `/api/v1/voting*` are removed from the active application contract.

## Security and integrity

- Never expose raw `formData`; only the dossier title, summary, and snapshot `publicFields` are reusable.
- Never expose original Cloudinary source identifiers or private source URLs through public APIs.
- QR payloads use the existing opaque verification token URL.
- Media must belong to the work's current locked version before it can be attached.

## Acceptance criteria

- An approved/signed dossier can be edited and published without another upload or re-entry of its public data.
- Public playback starts from an optimized poster and selects HLS on supporting mobile browsers, with MP4 fallback elsewhere.
- Clicking an old or new certificate notification reaches a populated certificate page whose QR resolves to its verification URL.
- No voting navigation/page/API route or voting background schedule remains active.
- Focused backend/frontend tests and production builds pass.
