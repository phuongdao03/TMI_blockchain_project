import hashlib
from datetime import UTC, datetime
from uuid import UUID

from app.modules.certificates.metadata import (
    CertificateMetadataBuilder,
    CertificateNumberingService,
)
from app.modules.certificates.pdf import CertificatePdfRenderer


def test_numbering_is_deterministic_and_concurrency_safe() -> None:
    certificate_id = UUID("7eaec2d2-c99a-42c9-8f1e-71462ba01ea0")
    issued_at = datetime(2026, 7, 31, tzinfo=UTC)
    service = CertificateNumberingService()

    values = {service.generate(certificate_id, issued_at) for _ in range(100)}

    assert values == {"TMI-2026-7EAEC2D2C99A"}


def test_metadata_is_versioned_deterministic_and_excludes_private_fields() -> None:
    snapshot = {
        "dossier": {
            "code": "TMI-2026-0001",
            "title": "Bộ nhận diện TMI",
            "summary": "Tài sản thương hiệu.",
            "visibility": "PUBLIC",
            "ownerUserId": "private-user-id",
            "category": {"code": "BRAND", "name": "Thương hiệu"},
        },
        "evidences": [
            {
                "title": "Giấy chứng nhận",
                "evidenceType": "LEGAL",
                "isPublic": True,
                "mediaAssetId": "private-media-id",
                "media": {"sha256": "ab" * 32},
            },
            {
                "title": "Private",
                "evidenceType": "INTERNAL",
                "isPublic": False,
            },
        ],
    }
    builder = CertificateMetadataBuilder()
    metadata, digest = builder.build(
        certificate_number="TMI-2026-7EAEC2D2C99A",
        certificate_version=1,
        dossier_version=1,
        snapshot=snapshot,
        issued_at=datetime(2026, 7, 31, tzinfo=UTC),
        expires_at=None,
    )

    assert metadata["schemaVersion"] == 1
    assert metadata["publicEvidences"] == [
        {
            "title": "Giấy chứng nhận",
            "type": "LEGAL",
            "sha256": "ab" * 32,
        }
    ]
    assert "private-user-id" not in str(metadata)
    assert "private-media-id" not in str(metadata)
    assert digest == hashlib.sha256(
        builder.canonical_bytes(metadata)
    ).hexdigest()


def test_pdf_contains_certificate_fields_qr_and_stable_hash() -> None:
    renderer = CertificatePdfRenderer(
        template_version="certificate-red-gold-v1",
        generator_version="reportlab-5.0.0",
    )
    metadata = {
        "certificateNumber": "TMI-2026-7EAEC2D2C99A",
        "asset": {
            "title": "Bo nhan dien TMI",
            "category": "Thuong hieu",
            "subject": "TMI Group",
        },
        "issuedAt": "2026-07-31T00:00:00Z",
        "expiresAt": None,
        "blockchain": {
            "network": "local",
            "contractAddress": "0x" + "12" * 20,
            "transactionHash": "0x" + "34" * 32,
        },
    }
    rendered = renderer.render(
        metadata=metadata,
        verification_url="https://tmi.example/kiem-tra/token",
    )

    assert rendered.content.startswith(b"%PDF")
    assert rendered.qr_png.startswith(b"\x89PNG")
    assert rendered.sha256 == hashlib.sha256(rendered.content).hexdigest()
    assert rendered.template_version == "certificate-red-gold-v1"
