from datetime import UTC, datetime
from uuid import uuid4

from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.models import DossierEvidence, DossierVersion
from app.modules.dossiers.provenance import version_has_trusted_provenance
from app.modules.media.models import MediaAsset, MediaStatus
from app.modules.media.provenance import CURRENT_INSPECTION_POLICY_VERSION

NOW = datetime(2026, 8, 10, 8, 0, tzinfo=UTC)


def test_version_provenance_rejects_storage_version_change() -> None:
    dossier_id = uuid4()
    media = MediaAsset(
        id=uuid4(),
        owner_user_id=uuid4(),
        cloudinary_public_id="evidence/trusted",
        cloudinary_version=4,
        resource_type="raw",
        access_mode="authenticated",
        original_filename="trusted.pdf",
        mime_type="application/pdf",
        bytes=128,
        sha256="a" * 64,
        hash_algorithm="SHA-256",
        hash_byte_length=128,
        inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
        hash_storage_version=4,
        hash_computed_at=NOW,
        status=MediaStatus.ACTIVE,
    )
    evidence = DossierEvidence(
        id=uuid4(),
        dossier_id=dossier_id,
        media_asset_id=media.id,
        evidence_type="OWNERSHIP_DOCUMENT",
        title="Trusted evidence",
    )
    snapshot = {
        "schemaVersion": 1,
        "evidences": [
            {
                "mediaAssetId": str(media.id),
                "media": {
                    "mimeType": media.mime_type,
                    "bytes": media.bytes,
                    "sha256": media.sha256,
                    "hashAlgorithm": media.hash_algorithm,
                    "hashByteLength": media.hash_byte_length,
                    "inspectionPolicyVersion": media.inspection_policy_version,
                    "storageObjectVersion": media.hash_storage_version,
                    "hashComputedAt": "2026-08-10T08:00:00Z",
                },
            }
        ],
    }
    version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier_id,
        version_no=1,
        snapshot_json=snapshot,
        canonical_hash=snapshot_sha256(snapshot),
        submitted_by=media.owner_user_id,
    )

    assert version_has_trusted_provenance(version, ((evidence, media),))

    media.cloudinary_version = 5
    assert not version_has_trusted_provenance(version, ((evidence, media),))
