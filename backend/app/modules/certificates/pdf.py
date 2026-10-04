import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
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
        "Bằng xác lập ghi nhận thông tin tại thời điểm phát hành. "
        "Bằng không thay thế văn bản xác lập quyền của cơ quan nhà nước."
    )
    FONT_NAME = "CNS-NotoSans"

    @classmethod
    def _fit_text(cls, value: str, *, max_width: float, font_size: float) -> str:
        if pdfmetrics.stringWidth(value, cls.FONT_NAME, font_size) <= max_width:
            return value
        trimmed = value
        while trimmed and pdfmetrics.stringWidth(
            trimmed + "…", cls.FONT_NAME, font_size
        ) > max_width:
            trimmed = trimmed[:-1]
        return trimmed.rstrip() + "…"

    @staticmethod
    def _display_date(value: object) -> str:
        if not isinstance(value, str) or not value:
            return "Chưa cập nhật"
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).strftime(
                "%d/%m/%Y"
            )
        except ValueError:
            return value[:24]

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
        blockchain = blockchain_value if isinstance(blockchain_value, Mapping) else {}
        buffer = BytesIO()
        width, height = landscape(A4)
        pdf = Canvas(
            buffer,
            pagesize=(width, height),
            pageCompression=1,
            invariant=1,
        )
        pdf.setFillColor(colors.HexColor("#fffaf0"))
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        red = colors.HexColor("#720b17")
        gold = colors.HexColor("#b7882f")
        ink = colors.HexColor("#2b1714")
        muted = colors.HexColor("#725f4f")
        pdf.setFillColor(red)
        pdf.rect(0, height - 16, width, 16, stroke=0, fill=1)
        pdf.setStrokeColor(red)
        pdf.setLineWidth(2)
        pdf.rect(26, 26, width - 52, height - 52, stroke=1, fill=0)
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(0.8)
        pdf.rect(33, 33, width - 66, height - 66, stroke=1, fill=0)

        logo = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "images"
            / "logo-tinh-hoa-viet.png"
        )
        pdf.drawImage(
            str(logo),
            61,
            height - 143,
            width=91,
            height=91,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFillColor(gold)
        pdf.setFont(self.FONT_NAME, 10)
        pdf.drawString(169, height - 75, "ĐỀ CỬ TINH HOA VIỆT")
        pdf.setFillColor(ink)
        pdf.setFont(self.FONT_NAME, 31)
        pdf.drawString(166, height - 113, "BẰNG XÁC LẬP")
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 10)
        pdf.drawString(
            169, height - 135, "Ghi nhận giá trị Việt · Kiểm tra độc lập bằng mã QR"
        )
        pdf.setStrokeColor(gold)
        pdf.line(62, height - 161, width - 62, height - 161)

        pdf.setFillColor(gold)
        pdf.setFont(self.FONT_NAME, 9)
        pdf.drawString(67, height - 188, "SỐ BẰNG XÁC LẬP")
        pdf.setFillColor(red)
        pdf.setFont(self.FONT_NAME, 16)
        pdf.drawString(
            67,
            height - 210,
            self._fit_text(
                str(metadata.get("certificateNumber", "")),
                max_width=width - 322,
                font_size=16,
            ),
        )

        fields = (
            ("TÁC PHẨM ĐƯỢC GHI NHẬN", str(asset.get("title") or "Chưa công bố")),
            (
                "TÁC GIẢ / NGƯỜI ĐƯỢC GHI NHẬN",
                str(asset.get("subject") or "Chưa công bố"),
            ),
            ("DANH MỤC", str(asset.get("category") or "Chưa công bố")),
            ("ĐƠN VỊ ĐỀ CỬ", "Đề cử Tinh Hoa Việt"),
            ("NGÀY PHÁT HÀNH", self._display_date(metadata.get("issuedAt"))),
            (
                "NGÀY HẾT HẠN",
                self._display_date(metadata["expiresAt"])
                if metadata.get("expiresAt")
                else "Không thời hạn",
            ),
        )
        y = height - 258
        for label, value in fields:
            pdf.setFillColor(muted)
            pdf.setFont(self.FONT_NAME, 8)
            pdf.drawString(67, y, label)
            pdf.setFillColor(ink)
            pdf.setFont(self.FONT_NAME, 12)
            pdf.drawString(
                67,
                y - 19,
                self._fit_text(value, max_width=width - 322, font_size=12),
            )
            y -= 43

        pdf.setStrokeColor(gold)
        pdf.line(width - 232, height - 239, width - 232, 98)
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 8)
        pdf.drawString(width - 211, height - 257, "QUÉT ĐỂ KIỂM TRA")

        pdf.drawImage(
            ImageReader(BytesIO(qr_png)),
            width - 211,
            height - 413,
            width=149,
            height=149,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 7)
        pdf.drawString(
            width - 211,
            height - 437,
            "Mạng: " + str(blockchain.get("network") or "Đang cập nhật")[:18],
        )
        pdf.drawString(67, 75, self.LEGAL_DISCLAIMER)
        pdf.drawString(
            67,
            61,
            "Mã giao dịch: "
            + str(blockchain.get("transactionHash") or "Đang cập nhật")[:74],
        )
        pdf.setFont(self.FONT_NAME, 6)
        pdf.drawRightString(
            width - 67,
            52,
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
