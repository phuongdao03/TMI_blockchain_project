# Publication and media recovery specification

## Objective

Recover every approved dossier whose proof was recorded on Polygon into a visible,
private editorial draft, then let a content administrator configure a portable,
performant video presentation before publication.

## Invariants

- The dossier version and its SHA-256 digest remain the immutable source of truth.
- A Cloudinary asset is storage/delivery infrastructure, not the identity of a work.
- Recovery is idempotent: one dossier has at most one public-work projection and one
  relation to each retained media asset.
- Recovery never publishes automatically. It creates or repairs a `DRAFT` with
  `PRIVATE` visibility.
- Only an authorized content administrator may change presentation settings.
- Provider credentials, private public IDs, and signed delivery URLs never enter the
  public API response.

## Recovery flow

1. Reconcile locally known proof transactions. A confirmed transaction may belong to
   a dossier still marked `PAID` or `ANCHORED`.
2. Link the active certificate version to that confirmed transaction and resume
   certificate rendering/finalization.
3. Create or repair the private public-work draft.
4. Attach active evidence from the signed dossier version. The primary work is
   available to the editor even when an older dossier type stored it as private;
   publication remains blocked until the administrator explicitly selects it.
5. Generate public delivery derivatives asynchronously and expose their status in the
   editor.

## Video presentation contract

Each public video relation may store:

- a poster relation selected from retained image evidence;
- a controls preset (`FULL`, `MINIMAL`, or `NONE`);
- fit mode (`CONTAIN` or `COVER`);
- maximum delivery width and quality profile;

Defaults favor mobile playback: a bounded progressive rendition with automatic codec
and quality, metadata-only preload, inline playback, and an optional poster image. The
UI must show processing/failure state instead of presenting an unavailable video as
ready.

## Portable storage convention

New provider objects use the logical key:

Source upload: `tmi/{environment}/owners/{owner-id}/uploads/{purpose}/{asset-id}`

Public derivative:
`tmi/{environment}/public/works/{work-id}/media/{relation-id}`

The database retains the provider-neutral asset UUID, SHA-256 digest, MIME type, byte
size, dossier/version relationship, purpose, and provenance. Provider public ID,
version, and derived URLs are replaceable delivery metadata. A migration inventory can
therefore map every provider object back to the same immutable logical asset.

## Acceptance criteria

- A confirmed proof attached to a `PAID` dossier is selected by recovery and reaches
  `CERTIFICATE_ISSUED` without another wallet signature.
- Existing issued dossiers missing a public-work row appear as private drafts in
  **Nội dung công bố** after one recovery run.
- Re-running recovery creates no duplicate work or media relation.
- The editor can save validated video presentation settings and preview the result.
- Public video responses use an optimized delivery rendition and do not expose source
  storage identifiers.
- Focused backend/frontend tests, type checks, and the relevant browser test pass.

## Assumptions

- Existing Cloudinary originals are retained and must not be renamed destructively.
- Legacy private primary-work evidence may be attached to the private editorial draft,
  but never becomes publicly downloadable until the publication workflow approves it.
- Production repair is executed through the normal worker/deployment path; no
  dossier-specific IDs are hard-coded.
