# Exact document hash claims

The service treats equal trusted SHA-256 values as exact original-byte matches.
This signal is separate from perceptual or semantic similarity and does not, by
itself, prove that a physical asset is authentic.

## Normal submission

1. Media inspection establishes current trusted provenance and SHA-256.
2. Submission atomically resolves or creates one global hash anchor.
3. The first media claim is linked to its dossier version and claimant scope.
4. Replaying the same media returns the same claim.
5. A different media item in the same claimant scope may reuse the anchor.
6. A cross-scope match returns `DOSSIER_DOCUMENT_CONFLICT` without disclosing
   the hash, original claimant, dossier or media identity.

Claims are append-only through application interfaces. An adjudication never
updates or deletes the original claim.

## Controlled override

`POST /api/v1/dossiers/{dossierId}/document-claim-overrides`

- Requires CSRF protection and `document_claim.override` (or `SUPER_ADMIN`).
- Accepts `mediaAssetId` and a 10–1000 character review reason.
- Only draft/supplement dossiers with current trusted media are eligible.
- Creates one idempotent `ALLOW_REANCHOR` decision and one audit event.
- Returns only the decision and target IDs; it does not expose the conflicting
  claimant or hash.

Operators should grant an override only after reviewing ownership evidence and
conflict-of-interest requirements. Similar-looking but byte-different files
remain in the separate similarity-review workflow.
