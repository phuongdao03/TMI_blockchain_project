import re

EMAIL = re.compile(r"\b[^\s@]+@[^\s@]+\.[^\s@]+\b", re.IGNORECASE)
PHONE = re.compile(r"(?<!\d)(?:\+?84|0)[\s.-]?(?:\d[\s.-]?){8,10}(?!\d)")
URL = re.compile(r"(?:https?://|www\.)\S+", re.IGNORECASE)
LONG_IDENTIFIER = re.compile(r"\b[A-Za-z0-9_-]{24,}\b")


def is_safe_aggregate_query(value: str) -> bool:
    """Allow only phrases suitable for anonymous public aggregation."""
    if not 2 <= len(value) <= 200:
        return False
    return not any(
        pattern.search(value) for pattern in (EMAIL, PHONE, URL, LONG_IDENTIFIER)
    )
