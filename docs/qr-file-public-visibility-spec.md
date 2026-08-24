# QR Verification, Upload & Public Visibility

## Goal

Make dossier evidence safe to upload, rule-driven by dossier type, immutable once
submitted, and understandable to the public without exposing private material.

## Existing foundation retained

- `media_assets` already provides authenticated Cloudinary uploads, a
  quarantine/inspection worker, byte-derived SHA-256, private-file encryption,
  and short-lived delivery authorization.
- `dossier_evidences` already belongs to a dossier and frozen dossier version;
  `dossier_versions` already carries a canonical snapshot and hash claims.
- Certificate verification already checks frozen metadata against the chain and
  performs browser-side SHA-256 comparison for public evidence.
- Dossier-type versions already store dynamic JSON schema. New document rules
  belong in that schema rather than a duplicate document-type table.

## Contract additions

`schema_json.documentRules` is an array of rules. Each rule has a stable
`key`, `label`, `documentType`, `required`, `allowedMimeTypes`, `maxBytes`,
`maxCount`, and `defaultVisibility`.

Accepted visibility values for new evidence are:

- `PRIVATE`: applicant and authorized internal users only.
- `INTERNAL`: authorized internal users only; never returned by public APIs.
- `PUBLIC_PREVIEW`: a safe public preview only; the source remains protected.
- `PUBLIC`: a public rendition may be returned after publication.

Legacy `REVIEWER_ONLY` and `ADMIN_ONLY` values remain readable for migration
compatibility and are treated as internal, never public.

Public response rules are backend rules:

- only published public dossiers/work projections are resolvable publicly;
- only explicitly public schema fields are serialized;
- only `PUBLIC`/`PUBLIC_PREVIEW` evidence is serialized;
- private storage identifiers, source URLs, review notes, account identifiers,
  and non-public evidence hashes are excluded.

## QR contract

- Stable dossier verification URL: `/xac-minh/{dossier-code}`.
- Certificate QR URL: `/verify/{opaque-token}`.
- QR payloads contain a URL only, never private IDs, hashes, tokens other than
  the existing opaque certificate token, or signed media URLs.
- Legacy `/kiem-tra/{token}` and `/tai-san/{slug}` browser paths redirect to
  `/verify/{token}` and `/works/{slug}` respectively.

## Security boundaries

- MIME, extension, actual bytes, magic bytes, scan state, size and count are
  enforced on the backend before evidence may be attached/submitted.
- Quarantined, rejected, deleted, or untrusted media cannot be attached.
- A submitted/frozen dossier version cannot have its evidence replaced; a
  correction creates the next version through the existing resubmission flow.
- Cloudinary URLs are never used as integrity hashes.
- Private and internal files stay authenticated/encrypted; public preview is a
  distinct derivative, never an overwrite of the source file.

## Acceptance checks

1. Invalid extension/MIME/magic bytes, size, count and required-document cases
   fail with structured validation errors.
2. Public endpoints cannot expose private/internal metadata or files.
3. QR routes resolve in the frontend and certificate PDF routes are canonical.
4. A frozen version rejects evidence mutation and verification detects proof
   mismatch rather than trusting a database flag.
5. Browser file integrity check remains local-first and shows a clear result.
