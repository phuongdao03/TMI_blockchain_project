from io import BytesIO
from uuid import uuid4

import pytest
from PIL import Image

from app.modules.media.models import MediaAsset
from app.modules.public.cover import crop_cover, is_editorial_cover


def test_crop_cover_returns_landscape_without_changing_source() -> None:
    output = BytesIO()
    Image.new("RGB", (800, 800), "red").save(output, format="PNG")
    original = output.getvalue()
    result = crop_cover(original, x=50, y=50, zoom=100)
    image = Image.open(BytesIO(result))
    assert image.size == (1280, 720)
    assert original == output.getvalue()


@pytest.mark.parametrize("x,y,zoom", [(-1, 50, 100), (50, 101, 100), (50, 50, 301)])
def test_crop_cover_rejects_invalid_configuration(x: int, y: int, zoom: int) -> None:
    with pytest.raises(ValueError):
        crop_cover(b"", x=x, y=y, zoom=zoom)


def test_editorial_marker_cannot_match_a_regular_evidence_filename() -> None:
    asset = MediaAsset(
        owner_user_id=uuid4(),
        cloudinary_public_id="tmi/prod/owners/test/uploads/dossier-evidence/cover.png",
        resource_type="image",
        access_mode="authenticated",
        original_filename="public-cover.png",
        mime_type="image/png",
        bytes=100,
    )
    assert not is_editorial_cover(asset)
    asset.cloudinary_public_id = "tmi/prod/owners/test/uploads/public-cover/asset"
    assert is_editorial_cover(asset)
