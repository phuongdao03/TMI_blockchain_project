import hashlib
import json
import math
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID

PUBLIC_EVIDENCE_SCOPES = frozenset({"PUBLIC", "PUBLIC_PREVIEW"})
MAX_PUBLIC_FIELD_VALUE_LENGTH = 5_000
MAX_PUBLIC_FIELD_LIST_ITEMS = 100
MAX_PUBLIC_FIELD_LIST_ITEM_LENGTH = 500


def public_fields_from_snapshot(
    snapshot: Mapping[str, object],
) -> list[dict[str, object]]:
    """Return the immutable, explicitly approved public field projection.

    Raw dynamic form data is deliberately ignored.  This defensive parser also
    protects metadata generation for records created before server-side schema
    enforcement was introduced.
    """
    dossier_value = snapshot.get("dossier")
    dossier = dossier_value if isinstance(dossier_value, dict) else {}
    dossier_type_value = dossier.get("dossierType")
    dossier_type = dossier_type_value if isinstance(dossier_type_value, dict) else {}
    fields = dossier_type.get("publicFields")
    if not isinstance(fields, list):
        return []

    result: list[dict[str, object]] = []
    for field in fields:
        if not isinstance(field, dict):
            continue
        key = field.get("key")
        label = field.get("label")
        value = field.get("value")
        if (
            not isinstance(key, str)
            or not 1 <= len(key) <= 120
            or not isinstance(label, str)
            or not 1 <= len(label.strip()) <= 255
        ):
            continue
        if isinstance(value, str):
            if len(value) > MAX_PUBLIC_FIELD_VALUE_LENGTH:
                continue
            safe_value: str | int | float | bool | list[str] = value
        elif isinstance(value, bool):
            safe_value = value
        elif isinstance(value, int):
            safe_value = value
        elif isinstance(value, float):
            if not math.isfinite(value):
                continue
            safe_value = value
        elif (
            isinstance(value, list)
            and len(value) <= MAX_PUBLIC_FIELD_LIST_ITEMS
            and all(
                isinstance(item, str) and len(item) <= MAX_PUBLIC_FIELD_LIST_ITEM_LENGTH
                for item in value
            )
        ):
            safe_value = list(value)
        else:
            continue
        result.append(
            {
                "key": key,
                "label": label.strip(),
                "value": safe_value,
            }
        )
    return result


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CertificateNumberingService:
    """Generates a collision-resistant number without a shared counter."""

    def generate(self, certificate_id: UUID, issued_at: datetime) -> str:
        return f"TMI-{issued_at.astimezone(UTC).year}-{certificate_id.hex[:12].upper()}"


class CertificateMetadataBuilder:
    SCHEMA_VERSION = 2

    @staticmethod
    def canonical_bytes(payload: object) -> bytes:
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")

    def build(
        self,
        *,
        certificate_number: str,
        certificate_version: int,
        dossier_version: int,
        snapshot: Mapping[str, object],
        issued_at: datetime,
        expires_at: datetime | None,
        subject: str = "Chủ thể hồ sơ TMI",
        blockchain: Mapping[str, object] | None = None,
    ) -> tuple[dict[str, object], str]:
        dossier_value = snapshot.get("dossier")
        dossier = dossier_value if isinstance(dossier_value, dict) else {}
        category_value = dossier.get("category")
        category = category_value if isinstance(category_value, dict) else {}
        evidences_value = snapshot.get("evidences")
        evidences = evidences_value if isinstance(evidences_value, list) else []
        public_evidences: list[dict[str, object]] = []
        for value in evidences:
            if not isinstance(value, dict):
                continue
            access_scope = value.get("accessScope")
            if (
                not isinstance(access_scope, str)
                or access_scope not in PUBLIC_EVIDENCE_SCOPES
            ):
                continue
            media_value = value.get("media")
            media = media_value if isinstance(media_value, dict) else {}
            public_evidences.append(
                {
                    "title": str(value.get("title", "")),
                    "type": str(value.get("evidenceType", "")),
                    "sha256": str(media.get("sha256", "")),
                    "accessScope": access_scope,
                }
            )
        metadata: dict[str, object] = {
            "schemaVersion": self.SCHEMA_VERSION,
            "certificateNumber": certificate_number,
            "certificateVersion": certificate_version,
            "dossierVersion": dossier_version,
            "dossierCode": str(dossier.get("code", "")),
            "asset": {
                "title": str(dossier.get("title", "")),
                "summary": (
                    str(dossier["summary"])
                    if dossier.get("summary") is not None
                    else None
                ),
                "category": str(category.get("name", "")),
                "categoryCode": str(category.get("code", "")),
                "subject": subject,
            },
            "issuedAt": _iso_utc(issued_at),
            "expiresAt": _iso_utc(expires_at),
            "publicFields": public_fields_from_snapshot(snapshot),
            "publicEvidences": public_evidences,
            "blockchain": dict(blockchain or {}),
        }
        digest = hashlib.sha256(self.canonical_bytes(metadata)).hexdigest()
        return metadata, digest
