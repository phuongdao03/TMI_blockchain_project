# Media storage portability

## Canonical asset hierarchy

New public derivatives use a provider-neutral identity derived from the dossier
and the certified dossier version:

```text
cns/{environment}/dossiers/{dossier-id}/versions/{version}/
  public/{public-media-relation-id}
  posters/{poster-id}
  previews/{preview-id}
  certificates/{certificate-version-id}
```

Original evidence remains private and immutable at its existing object identity.
Publishing creates a derivative; it never asks the owner or administrator to
upload the source again and never changes the evidence hash.

## Export manifest

An export to another media provider must retain these fields for every object:

- dossier UUID and dossier version;
- media asset UUID and public-media relation UUID;
- provider public ID and delivery URL;
- original filename, MIME type and byte length;
- SHA-256 captured during ingestion;
- derivative transformation/profile;
- certificate number and blockchain transaction hash when applicable.

The UUIDs and SHA-256 values are the portable identities. Provider URLs are
delivery locations only and must not be used as proof of integrity.

## Migration procedure

1. Export the manifest and compare its row count with active media records.
2. Copy objects without changing source bytes or canonical UUID keys.
3. Recompute SHA-256 for originals and compare it with the manifest.
4. Generate public derivatives on the target provider from verified originals.
5. Switch delivery URLs in a transaction; keep old URLs during the rollback
   window.
6. Verify a sample of image, video/HLS, document, certificate and QR journeys.

Legacy Cloudinary public IDs are supported in place. Do not bulk-rename
originals: that creates avoidable risk and provides no integrity benefit. Move
them only as a separately audited migration with a reversible mapping table.

## Rollback

Restore the previous delivery URLs from the export manifest. No dossier,
certificate, transaction, hash or original media record should be changed during
rollback.
