import hashlib
import json
from collections.abc import Mapping
from datetime import UTC, datetime
from uuid import UUID


def _iso_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


class CertificateNumberingService:
    """Generates a collision-resistant number without a shared counter."""

    def generate(self, certificate_id: UUID, issued_at: datetime) -> str:
        return f"TMI-{issued_at.astimezone(UTC).year}-{certificate_id.hex[:12].upper()}"


class CertificateMetadataBuilder:
    SCHEMA_VERSION = 1

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
            if not isinstance(value, dict) or value.get("isPublic") is not True:
                continue
            media_value = value.get("media")
            media = media_value if isinstance(media_value, dict) else {}
            public_evidences.append(
                {
                    "title": str(value.get("title", "")),
                    "type": str(value.get("evidenceType", "")),
                    "sha256": str(media.get("sha256", "")),
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
            "publicEvidences": public_evidences,
            "blockchain": dict(blockchain or {}),
        }
        digest = hashlib.sha256(self.canonical_bytes(metadata)).hexdigest()
        return metadata, digest
