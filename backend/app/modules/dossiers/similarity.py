from dataclasses import dataclass
from io import BytesIO
from typing import cast

from PIL import Image, ImageOps, UnidentifiedImageError

from app.modules.dossiers.canonical import normalized_identity_text

SIMILARITY_POLICY_VERSION = "near-duplicate-v1"
MAX_IMAGE_PIXELS = 40_000_000


class SimilarityInputError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SimilarityPolicy:
    text_threshold: float = 0.82
    image_max_hamming_distance: int = 8
    version: str = SIMILARITY_POLICY_VERSION

    def __post_init__(self) -> None:
        if not 0 <= self.text_threshold <= 1:
            raise ValueError("Text threshold must be between zero and one.")
        if not 0 <= self.image_max_hamming_distance <= 64:
            raise ValueError("Image distance threshold must be between 0 and 64.")

    def text_is_candidate(self, score: float) -> bool:
        return score >= self.text_threshold

    def image_is_candidate(self, distance: int) -> bool:
        return distance <= self.image_max_hamming_distance


def normalized_text_similarity(left: str, right: str) -> float:
    left_ngrams = _character_ngrams(normalized_identity_text(left))
    right_ngrams = _character_ngrams(normalized_identity_text(right))
    if not left_ngrams or not right_ngrams:
        return 0.0
    return len(left_ngrams & right_ngrams) / len(left_ngrams | right_ngrams)


def image_dhash(content: bytes) -> str:
    try:
        with Image.open(BytesIO(content)) as source:
            if source.width * source.height > MAX_IMAGE_PIXELS:
                raise SimilarityInputError("Image pixel limit exceeded.")
            image = ImageOps.exif_transpose(source).convert("L")
            resized = image.resize((9, 8), Image.Resampling.LANCZOS)
            pixels = cast(tuple[int, ...], tuple(resized.get_flattened_data()))
    except (UnidentifiedImageError, OSError) as exc:
        raise SimilarityInputError("Image cannot be decoded.") from exc
    value = 0
    for row in range(8):
        offset = row * 9
        for column in range(8):
            value = (value << 1) | int(
                pixels[offset + column] > pixels[offset + column + 1]
            )
    return f"{value:016x}"


def perceptual_hash_distance(left: str, right: str) -> int:
    if len(left) != 16 or len(right) != 16:
        raise SimilarityInputError("Perceptual hashes must contain 64 bits.")
    try:
        return (int(left, 16) ^ int(right, 16)).bit_count()
    except ValueError as exc:
        raise SimilarityInputError("Perceptual hash is invalid.") from exc


def _character_ngrams(value: str, *, size: int = 3) -> frozenset[str]:
    if not value:
        return frozenset()
    padded = f"  {value}  "
    return frozenset(
        padded[index : index + size]
        for index in range(len(padded) - size + 1)
    )
