import hashlib
from datetime import UTC, datetime
from uuid import UUID

from reportlab.pdfgen.canvas import Canvas

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

    assert values == {"THV-2026-7EAEC2D2C99A"}


def test_metadata_is_versioned_deterministic_and_excludes_private_fields() -> None:
    snapshot = {
        "dossier": {
            "code": "CNS-2026-0001",
            "title": "Bộ nhận diện CNS",
            "summary": "Tài sản thương hiệu.",
            "visibility": "PUBLIC",
            "ownerUserId": "private-user-id",
            "category": {"code": "BRAND", "name": "Thương hiệu"},
        },
        "evidences": [
            {
                "title": "Giấy chứng nhận",
                "evidenceType": "LEGAL",
                "accessScope": "PUBLIC",
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
        certificate_number="CNS-2026-7EAEC2D2C99A",
        certificate_version=1,
        dossier_version=1,
        snapshot=snapshot,
        issued_at=datetime(2026, 7, 31, tzinfo=UTC),
        expires_at=None,
    )

    assert metadata["schemaVersion"] == 2
    assert metadata["publicEvidences"] == [
        {
            "title": "Giấy chứng nhận",
            "type": "LEGAL",
            "sha256": "ab" * 32,
            "accessScope": "PUBLIC",
        }
    ]
    assert "private-user-id" not in str(metadata)
    assert "private-media-id" not in str(metadata)
    assert digest == hashlib.sha256(builder.canonical_bytes(metadata)).hexdigest()


def test_pdf_contains_certificate_fields_qr_and_stable_hash() -> None:
    renderer = CertificatePdfRenderer(
        template_version="certificate-red-gold-v1",
        generator_version="reportlab-5.0.0",
    )
    metadata = {
        "certificateNumber": "CNS-2026-7EAEC2D2C99A",
        "asset": {
            "title": "Bo nhan dien CNS",
            "category": "Thuong hieu",
            "subject": "CNS Group",
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
        verification_url="https://cns.example/kiem-tra/token",
    )

    assert rendered.content.startswith(b"%PDF")
    assert rendered.qr_png.startswith(b"\x89PNG")
    assert rendered.sha256 == hashlib.sha256(rendered.content).hexdigest()
    assert rendered.template_version == "certificate-red-gold-v1"


def test_pdf_uses_public_vietnamese_details_without_dates_or_provider(
    monkeypatch,
) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    drawn: list[str] = []

    class RecordingCanvas(Canvas):
        def drawString(self, x, y, text, *args, **kwargs):
            drawn.append(text)
            return super().drawString(x, y, text, *args, **kwargs)

        def drawCentredString(self, x, y, text, *args, **kwargs):
            drawn.append(text)
            return super().drawCentredString(x, y, text, *args, **kwargs)

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    renderer = CertificatePdfRenderer(template_version="v3", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-7EAEC2D2C99A",
            "asset": {
                "title": "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt",
                "summary": (
                    "Tác phẩm giới thiệu vẻ đẹp văn hóa Việt và hành trình đề cử."
                ),
                "subject": "Trung tâm Đề cử Tinh Hoa Việt",
                "category": "Tài sản trí tuệ số",
            },
            "issuedAt": "2026-10-04T00:00:00Z",
            "expiresAt": "2027-10-04T00:00:00Z",
            "blockchain": {"network": "polygon", "transactionHash": "0x1234"},
        },
        verification_url="https://example.test/verify/THV-2026-7EAEC2D2C99A",
    )

    text = " ".join(drawn)
    assert "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt" in text
    assert "Tác phẩm giới thiệu vẻ đẹp văn hóa Việt" in text
    assert "MÔ TẢ TÁC PHẨM" in text
    assert "Mạng blockchain Polygon" in text
    assert "Ghi nhận tác phẩm · Tôn vinh giá trị Việt" in text
    assert "NGÀY PHÁT HÀNH" not in text
    assert "NGÀY HẾT HẠN" not in text
    assert "polygon" not in text
