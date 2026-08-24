# QR, file upload and public visibility handoff

## Outcome

The dossier upload and public verification flow is now rule-driven, private by
default, and immutable by certificate version.

- Each dossier-type schema owns its `documentRules`: type, required flag, MIME
  allowlist, size/count limits and default visibility.
- The backend verifies MIME, extension, file bytes, inspection status and
  provenance before evidence can be attached or submitted.
- Public responses expose only explicitly public fields and public evidence
  metadata. They never expose original files, signed URLs, storage locators,
  review data or internal/private hashes.
- The public verification page compares a selected file with Web Crypto SHA-256
  in the browser only (25 MB maximum). It never falls back to uploading that
  file to the server.
- Each confirmed certificate version has its own opaque QR URL and frozen
  display identity. A historic QR always uses the title, category and dossier
  code stored in that version's signed metadata, not mutable current records.

## Database release

Run Alembic before deploying API and workers:

```bash
cd backend
alembic upgrade head
```

This includes:

1. `0059_document_rule_visibility` — schema document rules and safe defaults.
2. `0060_certificate_version_qr` — version-bound QR token/hash/payload fields.

The QR migration backfills only the active version from an existing certificate
QR. Historic versions without an independently issued QR remain without one;
they are not falsely assigned a current QR.

## Contract release

`CertificateRegistry` now exposes immutable version records through
`getCertificateVersion(bytes32,uint32)`. A new deployment is required for
on-chain verification of historic QR links; do not point the new ABI at the old
certificate-only runtime.

After an Amoy qualification and a production dry run, deploy the new contract,
verify its source, grant the designated human signer only `ISSUER_ROLE`, then
update the VPS secret store:

```dotenv
CERTIFICATE_CONTRACT_ADDRESS=<new verified contract address>
BLOCKCHAIN_ALLOWED_CONTRACT_ADDRESSES=<new verified contract address>
```

Keep the signer key or custody-provider credentials outside Git. The existing
release procedure is documented in `docs/runbooks/blockchain-release.md`.
Until the new runtime is deployed, a historic QR is shown as awaiting chain
confirmation instead of being reported as valid from an incompatible contract.

## Production checks

- Set canonical `APP_BASE_URL` to the public HTTPS domain before issuing new
  certificates; it is embedded in future QR payloads.
- Keep public document visibility explicit. `PRIVATE`, `INTERNAL` and legacy
  internal scopes are never public.
- Align the schema upload limits with the deployed storage provider. A 300 MB
  schema limit does not replace provider-side limits or required chunked-upload
  support.
- Retain the normal database backup, migration and rollback controls in
  `docs/runbooks/deployment-and-rollback.md`.

## Verification performed

- Backend QR, migration, document-rule, public visibility and certificate tests:
  **55 passed**.
- Frontend QR/file uploader unit tests: **14 passed**.
- Playwright public verification and data-leakage checks: **4 passed** across
  desktop and mobile Chrome.
- Solidity registry tests and invariants: **16 passed**.
- Frontend typecheck and optimized production build: passed.
- Ruff on the changed backend QR/verification paths: passed.
