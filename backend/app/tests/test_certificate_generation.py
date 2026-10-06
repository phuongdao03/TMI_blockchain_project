import hashlib
import unicodedata
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


def test_pdf_preserves_long_approved_content_on_continuation_page(monkeypatch) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    drawn: list[str] = []
    page_count = 0

    class RecordingCanvas(Canvas):
        def drawString(self, x, y, value, *args, **kwargs):
            drawn.append(value)
            return super().drawString(x, y, value, *args, **kwargs)

        def showPage(self):
            nonlocal page_count
            page_count += 1
            return super().showPage()

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    renderer = CertificatePdfRenderer(template_version="v3", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-TEST",
            "asset": {
                "title": "Đồng diễn múa Saravan",
                "summary": "Mô tả đầy đủ " * 60 + "KẾT THÚC",
                "subject": "Trường Đại học Trà Vinh",
                "category": "Tài sản trí tuệ số",
            },
        },
        verification_url="https://example.test/verify/token",
    )
    assert page_count == 2
    assert any("KẾT THÚC" in line for line in drawn)


def test_pdf_keeps_maximum_length_summary_across_multiple_pages(monkeypatch) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    drawn: list[str] = []
    page_count = 0

    class RecordingCanvas(Canvas):
        def drawString(self, x, y, value, *args, **kwargs):
            drawn.append(value)
            return super().drawString(x, y, value, *args, **kwargs)

        def showPage(self):
            nonlocal page_count
            page_count += 1
            return super().showPage()

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    renderer = CertificatePdfRenderer(template_version="v3", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-TEST",
            "asset": {
                "title": "Tác phẩm",
                "summary": "Mô tả đầy đủ " * 300 + "KẾT THÚC",
                "category": "Tài sản trí tuệ số",
            },
        },
        verification_url="https://example.test/verify/token",
    )
    assert page_count >= 3
    assert any("KẾT THÚC" in line for line in drawn)


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


def test_pdf_highlights_full_work_title_over_drum_watermark(monkeypatch) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    title = "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt và di sản văn hóa dân tộc"
    title_lines: list[tuple[str, float]] = []
    images: list[str] = []

    class RecordingCanvas(Canvas):
        def drawString(self, x, y, text, *args, **kwargs):
            if 169 <= y <= 220 and self._fontsize >= 19:
                title_lines.append((text, self._fontsize))
            return super().drawString(x, y, text, *args, **kwargs)

        def drawImage(self, image, x, y, *args, **kwargs):
            if isinstance(image, str):
                images.append(image)
            return super().drawImage(image, x, y, *args, **kwargs)

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    renderer = CertificatePdfRenderer(template_version="v4", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-7EAEC2D2C99A",
            "asset": {"title": title, "category": "Thương hiệu"},
            "blockchain": {},
        },
        verification_url="https://example.test/verify/test",
    )

    assert " ".join(line for line, _ in title_lines) == title
    assert len(title_lines) >= 2
    assert all(size >= 19 for _, size in title_lines)
    assert any(image.endswith("trong-dong.png") for image in images)


def test_pdf_normalizes_vietnamese_display_text(monkeypatch) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    drawn: list[str] = []

    class RecordingCanvas(Canvas):
        def drawString(self, x, y, text, *args, **kwargs):
            drawn.append(text)
            return super().drawString(x, y, text, *args, **kwargs)

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    expected = ("Đề cử Tinh Hoa Việt", "Văn hóa Việt", "Trung tâm Đề cử", "Thương hiệu")
    renderer = CertificatePdfRenderer(template_version="v4", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-TEST",
            "asset": {
                "title": unicodedata.normalize("NFD", expected[0]),
                "summary": unicodedata.normalize("NFD", expected[1]),
                "subject": unicodedata.normalize("NFD", expected[2]),
                "category": unicodedata.normalize("NFD", expected[3]),
            },
            "blockchain": {},
        },
        verification_url="https://example.test/verify/test",
    )

    assert all(value in drawn for value in expected)
    assert all(unicodedata.is_normalized("NFC", value) for value in drawn)


def test_pdf_uses_serif_type_for_headline_and_work_title(monkeypatch) -> None:
    import app.modules.certificates.pdf as certificate_pdf

    title = "Video chào mừng thương hiệu Đề cử Tinh Hoa Việt"
    display_fonts: dict[str, str] = {}
    rendered_title_lines: list[str] = []

    class RecordingCanvas(Canvas):
        def drawCentredString(self, x, y, text, *args, **kwargs):
            if text == "BẰNG XÁC LẬP":
                display_fonts["headline"] = self._fontname
            return super().drawCentredString(x, y, text, *args, **kwargs)

        def drawString(self, x, y, text, *args, **kwargs):
            if 169 <= y <= 220 and self._fontsize >= 19:
                display_fonts["work_title"] = self._fontname
                rendered_title_lines.append(text)
            return super().drawString(x, y, text, *args, **kwargs)

    monkeypatch.setattr(certificate_pdf, "Canvas", RecordingCanvas)
    renderer = CertificatePdfRenderer(template_version="v4", generator_version="test")
    renderer.render(
        metadata={
            "certificateNumber": "THV-2026-TEST",
            "asset": {"title": title},
            "blockchain": {},
        },
        verification_url="https://example.test/verify/test",
    )

    assert display_fonts == {
        "headline": "THV-NotoSerif-Bold",
        "work_title": "THV-NotoSerif-Regular",
    }
    assert rendered_title_lines == [title]
