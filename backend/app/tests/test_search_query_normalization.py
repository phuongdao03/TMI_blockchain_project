import pytest

from app.modules.search.errors import SearchQueryInvalidError
from app.modules.search.normalization import SearchQueryNormalizer


@pytest.mark.parametrize(
    ("source", "raw", "normalized", "unaccented"),
    (
        (
            "  Di\u00a0sản\tVăn hóa Việt Nam  ",
            "Di sản Văn hóa Việt Nam",
            "di sản văn hóa việt nam",
            "di san van hoa viet nam",
        ),
        (
            "ĐƯỜNG đương đại",
            "ĐƯỜNG đương đại",
            "đường đương đại",
            "duong duong dai",
        ),
        (
            "ＴＭＩ－２０２６／ABC_01.2",
            "TMI-2026/ABC_01.2",
            "tmi-2026/abc_01.2",
            "tmi-2026/abc_01.2",
        ),
        (
            "Nghệ thuật 🎨 số",
            "Nghệ thuật 🎨 số",
            "nghệ thuật 🎨 số",
            "nghe thuat 🎨 so",
        ),
    ),
)
def test_normalization_is_deterministic_and_unicode_safe(
    source: str,
    raw: str,
    normalized: str,
    unaccented: str,
) -> None:
    service = SearchQueryNormalizer()
    result = service.normalize(source)
    assert result.raw == raw
    assert result.normalized == normalized
    assert result.unaccented == unaccented
    assert result.is_empty is False
    assert service.normalize(source) == result


@pytest.mark.parametrize("source", (None, "", "  \t\r\n  "))
def test_empty_query_selects_discovery_without_broad_search(source: str | None) -> None:
    assert SearchQueryNormalizer().normalize(source).is_empty is True


@pytest.mark.parametrize(
    ("source", "reason", "limit"),
    (
        ("a", "too_short", 2),
        ("a" * 201, "too_long", 200),
        ("safe\x00query", "invalid_unicode", None),
        ("safe\u202equery", "invalid_unicode", None),
        ("safe\ud800query", "invalid_unicode", None),
    ),
)
def test_invalid_queries_return_stable_non_echoing_error(
    source: str,
    reason: str,
    limit: int | None,
) -> None:
    with pytest.raises(SearchQueryInvalidError) as captured:
        SearchQueryNormalizer().normalize(source)
    error = captured.value
    assert error.code == "SEARCH_QUERY_INVALID"
    assert error.status_code == 422
    assert error.details == {
        "reason": reason,
        **({"limit": limit} if limit is not None else {}),
    }
    assert str(error) == "Search query is invalid."
    assert error.message == "Search query is invalid."
    assert source not in error.details.values()
