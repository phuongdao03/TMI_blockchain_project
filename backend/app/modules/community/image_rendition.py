from io import BytesIO

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.media.types import MediaContentView


def community_image_etag(digest: str, width: int | None) -> str:
    return f'"{digest}-{width or 0}"'


def community_image_rendition(
    image: MediaContentView, width: int | None
) -> MediaContentView:
    if width is None:
        return image
    try:
        with Image.open(BytesIO(image.content)) as source:
            if source.width * source.height > 40_000_000:
                return image
            rendered = ImageOps.exif_transpose(source)
            rendered.thumbnail((width, width * 4), Image.Resampling.LANCZOS)
            if rendered.mode not in ("RGB", "RGBA"):
                mode = "RGBA" if "A" in rendered.getbands() else "RGB"
                rendered = rendered.convert(mode)
            output = BytesIO()
            rendered.save(output, format="WEBP", quality=78, method=4)
            content = output.getvalue()
    except (OSError, UnidentifiedImageError, ValueError):
        return image
    if len(content) >= len(image.content):
        return image
    return MediaContentView(
        content=content, mime_type="image/webp", filename="community.webp"
    )
