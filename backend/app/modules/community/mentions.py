import re

MAX_COMMUNITY_MENTIONS = 20
_MENTION_PATTERN = re.compile(
    r"(?<![\w@])@([a-z0-9_-]{3,40})(?![a-z0-9_-])",
    re.IGNORECASE,
)


def extract_community_mentions(content: str) -> tuple[str, ...]:
    """Return distinct, case-folded profile handles in appearance order."""
    usernames: list[str] = []
    seen: set[str] = set()
    for match in _MENTION_PATTERN.finditer(content):
        username = match.group(1).casefold()
        if username not in seen:
            usernames.append(username)
            seen.add(username)
        if len(usernames) == MAX_COMMUNITY_MENTIONS:
            break
    return tuple(usernames)
