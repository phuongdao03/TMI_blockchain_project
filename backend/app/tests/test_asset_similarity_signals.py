from io import BytesIO

from PIL import Image, ImageDraw

from app.modules.dossiers.similarity import (
    SimilarityPolicy,
    image_dhash,
    normalized_text_similarity,
    perceptual_hash_distance,
)


def _artwork(*, size: tuple[int, int], quality: int) -> bytes:
    image = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle(
        (size[0] // 5, size[1] // 5, size[0] * 4 // 5, size[1] * 4 // 5),
        fill="black",
    )
    output = BytesIO()
    image.save(output, format="JPEG", quality=quality)
    return output.getvalue()


def test_recompressed_and_resized_image_crosses_explainable_policy() -> None:
    original = image_dhash(_artwork(size=(400, 300), quality=95))
    transformed = image_dhash(_artwork(size=(200, 150), quality=55))
    distance = perceptual_hash_distance(original, transformed)

    assert distance == 3
    assert SimilarityPolicy().image_is_candidate(distance)


def test_unrelated_text_stays_below_threshold_and_boundary_is_inclusive() -> None:
    score = normalized_text_similarity(
        "Bản hòa tấu Mùa Thu Hà Nội",
        "Thiết kế nhận diện thương hiệu doanh nghiệp",
    )
    policy = SimilarityPolicy(text_threshold=0.82)

    assert score < policy.text_threshold
    assert not policy.text_is_candidate(score)
    assert policy.text_is_candidate(0.82)
