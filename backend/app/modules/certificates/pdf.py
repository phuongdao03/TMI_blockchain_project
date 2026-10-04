import hashlib
from collections.abc import Mapping
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path
from unicodedata import normalize

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
    FONT_NAME = "THV-NotoSans"
    SERIF_FONT_NAME = "THV-NotoSerif-Regular"
    SERIF_BOLD_FONT_NAME = "THV-NotoSerif-Bold"

    @classmethod
    def _fit_text(
        cls,
        value: str,
        *,
        max_width: float,
        font_size: float,
        font_name: str | None = None,
    ) -> str:
        value = normalize("NFC", value)
        font = font_name or cls.FONT_NAME
        if pdfmetrics.stringWidth(value, font, font_size) <= max_width:
            return value
        trimmed = value
        while (
            trimmed
            and pdfmetrics.stringWidth(trimmed + "…", font, font_size) > max_width
        ):
            trimmed = trimmed[:-1]
        return trimmed.rstrip() + "…"

    @classmethod
    def _wrap_text(
        cls,
        value: str,
        *,
        max_width: float,
        font_size: float,
        max_lines: int,
        font_name: str | None = None,
    ) -> list[str]:
        font = font_name or cls.FONT_NAME
        words = normalize("NFC", value).split()
        lines: list[str] = []
        line = ""
        for word in words:
            candidate = f"{line} {word}".strip()
            if pdfmetrics.stringWidth(candidate, font, font_size) <= max_width:
                line = candidate
                continue
            if line:
                lines.append(line)
                line = word
            else:
                lines.append(
                    cls._fit_text(
                        word, max_width=max_width, font_size=font_size, font_name=font
                    )
                )
                line = ""
            if len(lines) == max_lines:
                break
        if len(lines) < max_lines and line:
            lines.append(line)
        if len(lines) == max_lines and " ".join(lines) != " ".join(words):
            lines[-1] = cls._fit_text(
                lines[-1] + "…",
                max_width=max_width,
                font_size=font_size,
                font_name=font,
            )
        return lines

    def __init__(self, *, template_version: str, generator_version: str) -> None:
        self._template_version = template_version
        self._generator_version = generator_version
        font_dir = Path(__file__).resolve().parents[2] / "assets" / "fonts"
        for name, filename in (
            (self.FONT_NAME, "NotoSans.ttf"),
            (self.SERIF_FONT_NAME, "NotoSerif-Regular.ttf"),
            (self.SERIF_BOLD_FONT_NAME, "NotoSerif-Bold.ttf"),
        ):
            if name not in pdfmetrics.getRegisteredFontNames():
                pdfmetrics.registerFont(TTFont(name, font_dir / filename))

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
        pdf.setTitle("Bằng xác lập Tinh Hoa Việt")
        pdf.setAuthor("Đề cử Tinh Hoa Việt")
        pdf.setFillColor(colors.HexColor("#fffcf5"))
        pdf.rect(0, 0, width, height, stroke=0, fill=1)
        drum = (
            Path(__file__).resolve().parents[2] / "assets" / "images" / "trong-dong.png"
        )
        pdf.saveState()
        pdf.setFillAlpha(0.07)
        pdf.drawImage(str(drum), width - 530, 45, width=500, height=500, mask="auto")
        pdf.restoreState()
        red = colors.HexColor("#720b17")
        gold = colors.HexColor("#b7882f")
        ink = colors.HexColor("#2b1714")
        muted = colors.HexColor("#725f4f")
        pdf.setFillColor(red)
        pdf.rect(0, height - 12, width, 12, stroke=0, fill=1)
        pdf.setStrokeColor(red)
        pdf.setLineWidth(1.5)
        pdf.rect(25, 22, width - 50, height - 52, stroke=1, fill=0)
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(0.7)
        pdf.rect(31, 28, width - 62, height - 64, stroke=1, fill=0)

        logo = (
            Path(__file__).resolve().parents[2]
            / "assets"
            / "images"
            / "logo-tinh-hoa-viet.png"
        )
        pdf.setFillColor(gold)
        pdf.setFont(self.FONT_NAME, 10)
        pdf.drawCentredString(width / 2, height - 56, "ĐỀ CỬ TINH HOA VIỆT")
        pdf.setFillColor(ink)
        pdf.setFont(self.SERIF_BOLD_FONT_NAME, 30)
        pdf.drawCentredString(width / 2, height - 100, "BẰNG XÁC LẬP")

        # The supplied artwork has a square burgundy background. Clip it to the
        # actual round seal so the square never appears on the certificate.
        seal_size = 142
        seal_x = (width - seal_size) / 2
        seal_y = height - 250
        pdf.saveState()
        seal_clip = pdf.beginPath()
        seal_clip.circle(width / 2, seal_y + seal_size / 2, seal_size * 0.405)
        pdf.clipPath(seal_clip, stroke=0, fill=0)
        pdf.drawImage(str(logo), seal_x, seal_y, seal_size, seal_size, mask="auto")
        pdf.restoreState()
        pdf.setStrokeColor(gold)
        pdf.setLineWidth(1.5)
        pdf.circle(
            width / 2, seal_y + seal_size / 2, seal_size * 0.405, stroke=1, fill=0
        )
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 9)
        pdf.drawCentredString(
            width / 2,
            height - 267,
            "Ghi nhận tác phẩm · Tôn vinh giá trị Việt",
        )
        pdf.setStrokeColor(gold)
        pdf.line(63, height - 283, width - 63, height - 283)

        pdf.setFillColor(gold)
        pdf.setFont(self.FONT_NAME, 8)
        pdf.drawString(65, height - 305, "SỐ BẰNG XÁC LẬP")
        pdf.setFillColor(red)
        pdf.setFont(self.FONT_NAME, 15)
        pdf.drawString(
            65,
            height - 326,
            self._fit_text(
                str(metadata.get("certificateNumber", "")),
                max_width=width - 330,
                font_size=15,
            ),
        )

        def field(label: str, value: str, y: float, *, size: float = 10) -> None:
            pdf.setFillColor(muted)
            pdf.setFont(self.FONT_NAME, 7)
            pdf.drawString(65, y, label)
            pdf.setFillColor(ink)
            pdf.setFont(self.FONT_NAME, size)
            pdf.drawString(
                65,
                y - 17,
                self._fit_text(value, max_width=width - 339, font_size=size),
            )

        pdf.setFillColor(colors.HexColor("#f8f0dc"))
        pdf.rect(63, 169, width - 333, 91, stroke=0, fill=1)
        pdf.setFillColor(gold)
        pdf.rect(63, 169, 3, 91, stroke=0, fill=1)
        pdf.setFont(self.FONT_NAME, 9)
        pdf.drawString(77, 245, "TÁC PHẨM ĐƯỢC GHI NHẬN")
        pdf.setFillColor(ink)
        pdf.setFont(self.SERIF_FONT_NAME, 19)
        title = str(asset.get("title") or "Chưa công bố")
        title_lines = self._wrap_text(
            title,
            max_width=width - 368,
            font_size=19,
            max_lines=3,
            font_name=self.SERIF_FONT_NAME,
        )
        title_y = 220 - (3 - len(title_lines)) * 11.5
        for index, line in enumerate(title_lines):
            pdf.drawString(77, title_y - index * 23, line)
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 7)
        pdf.drawString(65, 155, "MÔ TẢ TÁC PHẨM")
        pdf.setFillColor(ink)
        pdf.setFont(self.FONT_NAME, 8)
        summary = str(asset.get("summary") or "Chưa có mô tả công khai")
        for index, line in enumerate(
            self._wrap_text(summary, max_width=width - 339, font_size=8, max_lines=3)
        ):
            pdf.drawString(65, 141 - index * 12, line)
        field(
            "TÁC GIẢ / NGƯỜI ĐƯỢC GHI NHẬN",
            str(asset.get("subject") or "Chưa công bố"),
            105,
        )
        field("DANH MỤC", str(asset.get("category") or "Chưa công bố"), 76)

        pdf.setStrokeColor(gold)
        pdf.line(width - 232, 57, width - 232, 260)
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 8)
        pdf.drawString(width - 211, 241, "QUÉT ĐỂ KIỂM TRA")

        pdf.drawImage(
            ImageReader(BytesIO(qr_png)),
            width - 211,
            89,
            width=132,
            height=132,
            preserveAspectRatio=True,
            mask="auto",
        )
        pdf.setFillColor(muted)
        pdf.setFont(self.FONT_NAME, 8)
        network_label = (
            "Mạng blockchain Polygon"
            if str(blockchain.get("network") or "").lower() == "polygon"
            else "Mạng blockchain"
        )
        pdf.drawString(width - 211, 72, network_label)
        pdf.setFont(self.FONT_NAME, 6)
        pdf.drawString(65, 37, self.LEGAL_DISCLAIMER)
        pdf.drawString(
            width - 211,
            57,
            "Mã GD: " + str(blockchain.get("transactionHash") or "Đang cập nhật")[:22],
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
