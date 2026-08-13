from collections.abc import Sequence

from app.modules.dossiers.canonical import snapshot_sha256
from app.modules.dossiers.models import DossierEvidence, DossierVersion
from app.modules.media.models import MediaAsset
from app.modules.media.provenance import (
    has_current_trusted_provenance,
    snapshot_has_current_trusted_provenance,
)


def version_has_trusted_provenance(
    version: DossierVersion,
    rows: Sequence[tuple[DossierEvidence, MediaAsset]],
) -> bool:
    if snapshot_sha256(version.snapshot_json) != version.canonical_hash:
        return False
    if not snapshot_has_current_trusted_provenance(version.snapshot_json):
        return False
    snapshot_evidences = version.snapshot_json.get("evidences")
    if not isinstance(snapshot_evidences, list) or len(snapshot_evidences) != len(rows):
        return False
    by_media_id = {
        item.get("mediaAssetId"): item.get("media")
        for item in snapshot_evidences
        if isinstance(item, dict)
    }
    for _, media in rows:
        if not has_current_trusted_provenance(media):
            return False
        snapshot_media = by_media_id.get(str(media.id))
        if not isinstance(snapshot_media, dict):
            return False
        if (
            snapshot_media.get("sha256") != media.sha256
            or snapshot_media.get("hashAlgorithm") != media.hash_algorithm
            or snapshot_media.get("hashByteLength") != media.hash_byte_length
            or snapshot_media.get("inspectionPolicyVersion")
            != media.inspection_policy_version
            or snapshot_media.get("storageObjectVersion") != media.hash_storage_version
        ):
            return False
    return True
