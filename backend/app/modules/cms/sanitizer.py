from html import escape
from html.parser import HTMLParser
from urllib.parse import urlparse

ALLOWED_TAGS = frozenset(
    {"p", "br", "strong", "em", "ul", "ol", "li", "h2", "h3", "blockquote", "a"}
)
VOID_TAGS = frozenset({"br"})


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.blocked_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in {"script", "style"}:
            self.blocked_depth += 1
            return
        if self.blocked_depth or tag not in ALLOWED_TAGS:
            return
        safe_attrs = ""
        if tag == "a":
            href = next((value for name, value in attrs if name == "href"), None)
            if href and urlparse(href).scheme in {"", "http", "https", "mailto"}:
                safe_attrs = (
                    f' href="{escape(href, quote=True)}" rel="noopener noreferrer"'
                )
        self.parts.append(f"<{tag}{safe_attrs}>")

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style"} and self.blocked_depth:
            self.blocked_depth -= 1
            return
        if not self.blocked_depth and tag in ALLOWED_TAGS and tag not in VOID_TAGS:
            self.parts.append(f"</{tag}>")

    def handle_data(self, data: str) -> None:
        if not self.blocked_depth:
            self.parts.append(escape(data))


def sanitize_rich_text(value: str) -> str:
    parser = _Sanitizer()
    parser.feed(value)
    parser.close()
    return "".join(parser.parts).strip()
