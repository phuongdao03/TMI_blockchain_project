import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import qrcode
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.pdfgen.canvas import Canvas


@dataclass(frozen=True, slots=True)
class RenderedCertificate:
    content: bytes
    qr_png: bytes
    sha256: str
    template_version: str
    generator_version: str


class CertificatePdfRenderer:
    LEGAL_DISCLAIMER = (
        "Chứng thư xác nhận trạng thái dữ liệu tại thời điểm phát hành. "
        "Chứng thư không thay thế văn bản xác lập quyền của cơ quan nhà nước."
    )
    FONT_NAME = "TMI-NotoSans"

    def __init__(self, *, template_version: str, generator_version: str) -> None:
        self._template_version = template_version
        self._generator_version = generator_version
        if self.FONT_NAME not in pdfmetrics.getRegisteredFontNames():
            font_path = (
                Path(__file__).resolve().parents[2]
                / "assets"
                / "fonts"
                / "NotoSans.ttf"
            )
            pdfmetrics.registerFont(TTFont(self.FONT_NAME, font_path))

    def render(
        self,
        *,
        metadata: Mapping[str, object],
        verification_url: str,
    ) -> RenderedCertificate:
        qr_buffer = BytesIO()
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_Q,
            box_size=8,
            border=3,
        )
        qr.add_data(verification_url)
        qr.make(fit=True)
        qr.make_image(fill_color="#0f172a", back_color="white").save(
            qr_buffer,
        )
        qr_png = qr_buffer.getvalue()

        asset_value = metadata.get("asset")
        asset = asset_value if isinstance(asset_value, Mapping) else {}
        blockchain_value = metadata.get("blockchain")
        blockchain = (
            blockchain_value if isinstance(blockchain_value, Mapping) else {}
        )
        buffer = BytesIO()
        width, height = landscape(A4)
        pdf = Canvas(
            buffer,
            pagesize=(width, height),
            pageCompression=1,
            invariant=1,
        )
        pdf.setFillColor(colors.HexColor("#f8fafc"))
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        pdf.setStrokeColor(colors.HexColor("#b91c1c"))
        pdf.setLineWidth(3)
        pdf.roundRect(28, 28, width - 56, height - 56, 14, stroke=1, fill=0)
        pdf.setStrokeColor(colors.HexColor("#d4a72c"))
        pdf.setLineWidth(1)
        pdf.roundRect(38, 38, width - 76, height - 76, 10, stroke=1, fill=0)

        pdf.setFillColor(colors.HexColor("#b91c1c"))
        pdf.setFont(self.FONT_NAME, 13)
        pdf.drawString(62, height - 80, "TMI GROUP")
        pdf.setFillColor(colors.HexColor("#0f172a"))
        pdf.setFont(self.FONT_NAME, 28)
        pdf.drawCentredString(width / 2, height - 128, "CHỨNG THƯ TÀI SẢN SỐ")
        pdf.setFillColor(colors.HexColor("#b91c1c"))
        pdf.setFont(self.FONT_NAME, 15)
        pdf.drawCentredString(
            width / 2,
            height - 158,
            str(metadata.get("certificateNumber", "")),
        )

        fields = (
            ("Chủ thể", str(asset.get("subject", ""))),
            ("Tài sản", str(asset.get("title", ""))),
            ("Danh mục", str(asset.get("category", ""))),
            ("Ngày phát hành", str(metadata.get("issuedAt", ""))),
            ("Ngày hết hạn", str(metadata.get("expiresAt") or "Không thời hạn")),
            ("Mạng", str(blockchain.get("network", ""))),
            ("Hợp đồng", str(blockchain.get("contractAddress", ""))),
            ("Giao dịch", str(blockchain.get("transactionHash", ""))),
        )
        y = height - 215
        for label, value in fields:
            pdf.setFillColor(colors.HexColor("#64748b"))
            pdf.setFont(self.FONT_NAME, 9)
            pdf.drawString(70, y, label.upper())
            pdf.setFillColor(colors.HexColor("#0f172a"))
            pdf.setFont(self.FONT_NAME, 11)
            pdf.drawString(180, y, value[:82])
            y -= 30

        pdf.drawImage(
            ImageReader(BytesIO(qr_png)),
            width - 188,
            82,
            width=112,
            height=112,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFillColor(colors.HexColor("#475569"))
        pdf.setFont(self.FONT_NAME, 7.5)
        pdf.drawString(70, 68, self.LEGAL_DISCLAIMER)
        pdf.setFont(self.FONT_NAME, 6.5)
        pdf.drawRightString(
            width - 70,
            54,
            f"{self._template_version} | {self._generator_version}",
        )
        pdf.showPage()
        pdf.save()
        content = buffer.getvalue()
        return RenderedCertificate(
            content=content,
            qr_png=qr_png,
            sha256=hashlib.sha256(content).hexdigest(),
            template_version=self._template_version,
            generator_version=self._generator_version,
        )
