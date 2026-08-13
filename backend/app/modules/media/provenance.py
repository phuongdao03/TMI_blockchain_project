import re
from collections.abc import Mapping
from datetime import datetime
from typing import Any

from app.modules.media.models import MediaAsset, MediaEncryptionStatus, MediaStatus

CURRENT_INSPECTION_POLICY_VERSION = "media-inspection-v1"
HASH_ALGORITHM = "SHA-256"


def has_current_trusted_provenance(asset: MediaAsset) -> bool:
    storage_version = (
        asset.encrypted_object_version
        if asset.encryption_status is MediaEncryptionStatus.ENCRYPTED
        else asset.cloudinary_version
    )
    return bool(
        asset.status is MediaStatus.ACTIVE
        and asset.deleted_at is None
        and asset.sha256 is not None
        and re.fullmatch(r"[0-9a-f]{64}", asset.sha256) is not None
        and asset.hash_algorithm == HASH_ALGORITHM
        and asset.hash_byte_length == asset.bytes
        and asset.inspection_policy_version == CURRENT_INSPECTION_POLICY_VERSION
        and asset.hash_storage_version is not None
        and asset.hash_storage_version == storage_version
        and asset.hash_computed_at is not None
    )


def snapshot_has_current_trusted_provenance(snapshot: Mapping[str, Any]) -> bool:
    evidences = snapshot.get("evidences")
    if not isinstance(evidences, list) or not evidences:
        return False
    return all(_snapshot_media_is_trusted(evidence) for evidence in evidences)


def _snapshot_media_is_trusted(evidence: object) -> bool:
    if not isinstance(evidence, dict):
        return False
    media = evidence.get("media")
    if not isinstance(media, dict):
        return False
    sha256 = media.get("sha256")
    byte_length = media.get("bytes")
    computed_at = media.get("hashComputedAt")
    return bool(
        isinstance(sha256, str)
        and re.fullmatch(r"[0-9a-f]{64}", sha256) is not None
        and media.get("hashAlgorithm") == HASH_ALGORITHM
        and isinstance(byte_length, int)
        and byte_length >= 0
        and media.get("hashByteLength") == byte_length
        and media.get("inspectionPolicyVersion")
        == CURRENT_INSPECTION_POLICY_VERSION
        and isinstance(media.get("storageObjectVersion"), int)
        and media["storageObjectVersion"] >= 0
        and isinstance(computed_at, str)
        and _is_iso_datetime(computed_at)
    )


def _is_iso_datetime(value: str) -> bool:
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True
