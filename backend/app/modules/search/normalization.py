import unicodedata
from dataclasses import dataclass

from app.modules.search.errors import SearchQueryInvalidError


@dataclass(frozen=True, slots=True)
class NormalizedSearchQuery:
    raw: str
    normalized: str
    unaccented: str
    is_empty: bool


class SearchQueryNormalizer:
    MIN_LENGTH = 2
    MAX_LENGTH = 200
    _REJECTED_UNICODE_CATEGORIES = frozenset({"Cc", "Cf", "Cs"})

    def normalize(self, value: str | None) -> NormalizedSearchQuery:
        if value is None:
            return self._empty()
        self._validate_unicode(value)
        compatible = unicodedata.normalize("NFKC", value)
        raw = " ".join(compatible.split())
        if not raw:
            return self._empty()
        self._validate_unicode(raw)
        length = len(raw)
        if length < self.MIN_LENGTH:
            raise SearchQueryInvalidError(
                "too_short",
                limit=self.MIN_LENGTH,
            )
        if length > self.MAX_LENGTH:
            raise SearchQueryInvalidError(
                "too_long",
                limit=self.MAX_LENGTH,
            )
        normalized = raw.casefold()
        unaccented = self._unaccent(normalized)
        return NormalizedSearchQuery(
            raw=raw,
            normalized=normalized,
            unaccented=unaccented,
            is_empty=False,
        )

    @classmethod
    def _validate_unicode(cls, value: str) -> None:
        for character in value:
            if character.isspace():
                continue
            if unicodedata.category(character) in cls._REJECTED_UNICODE_CATEGORIES:
                raise SearchQueryInvalidError("invalid_unicode")

    @staticmethod
    def _unaccent(value: str) -> str:
        decomposed = unicodedata.normalize("NFKD", value)
        without_marks = "".join(
            character
            for character in decomposed
            if unicodedata.category(character) != "Mn"
        )
        return unicodedata.normalize("NFC", without_marks).replace("đ", "d")

    @staticmethod
    def _empty() -> NormalizedSearchQuery:
        return NormalizedSearchQuery(
            raw="",
            normalized="",
            unaccented="",
            is_empty=True,
        )
