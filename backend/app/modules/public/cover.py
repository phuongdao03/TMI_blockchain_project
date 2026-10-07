from io import BytesIO

from PIL import Image, ImageOps

from app.modules.media.models import MediaAsset


def is_editorial_cover(asset: MediaAsset) -> bool:
    """Only the server-issued upload namespace marks an editorial image."""
    return (
        asset.mime_type in {"image/jpeg", "image/png", "image/webp"}
        and "/uploads/public-cover/" in getattr(asset, "cloudinary_public_id", "")
        and asset.bytes <= 5_242_880
    )


def crop_cover(
    content: bytes, *, x: int, y: int, zoom: int, width: int = 1280
) -> bytes:
    if (
        not 0 <= x <= 100
        or not 0 <= y <= 100
        or not 100 <= zoom <= 300
        or width not in {320, 640, 960, 1280}
    ):
        raise ValueError("Invalid cover crop configuration.")
    with Image.open(BytesIO(content)) as source:
        if source.width * source.height > 25_000_000:
            raise ValueError("Cover image exceeds supported dimensions.")
        image = ImageOps.exif_transpose(source)
        source_width, source_height = image.size
        if source_width * source_height > 25_000_000:
            raise ValueError("Cover image exceeds supported dimensions.")
        crop_width = min(source_width, source_height * 16 / 9) * 100 / zoom
        crop_height = crop_width * 9 / 16
        left = (source_width - crop_width) * x / 100
        top = (source_height - crop_height) * y / 100
        image = image.crop((left, top, left + crop_width, top + crop_height))
        image = image.resize((width, width * 9 // 16), Image.Resampling.LANCZOS)
        background = Image.new("RGB", image.size, "white")
        if image.mode in {"RGBA", "LA"} or "transparency" in image.info:
            rgba = image.convert("RGBA")
            background.paste(rgba, mask=rgba.getchannel("A"))
        else:
            background.paste(image.convert("RGB"))
        output = BytesIO()
        background.save(output, "JPEG", quality=85, optimize=True)
        return output.getvalue()
