import base64
import json
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from uuid import UUID

from app.modules.search.errors import SearchQueryInvalidError
from app.modules.search.types import SearchCursor, SearchSort


class SearchCursorCodec:
    VERSION = 2

    def encode(self, cursor: SearchCursor) -> str:
        payload = json.dumps(
            {
                "v": self.VERSION,
                "e": cursor.exact_match,
                "r": format(cursor.relevance, "f"),
                "p": self._as_utc(cursor.published_at).isoformat(),
                "i": str(cursor.work_id),
                "s": cursor.sort.value,
                "w": cursor.view_count,
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()

    def decode(
        self,
        value: str,
        *,
        expected_sort: SearchSort | None = None,
    ) -> SearchCursor:
        try:
            padding = "=" * (-len(value) % 4)
            payload = json.loads(base64.urlsafe_b64decode(value + padding))
            if payload["v"] != self.VERSION or payload["e"] not in {0, 1}:
                raise ValueError
            sort = SearchSort(payload["s"])
            if expected_sort is not None and sort is not expected_sort:
                raise ValueError
            view_count = int(payload["w"])
            if view_count < 0:
                raise ValueError
            relevance = Decimal(payload["r"])
            published_at = datetime.fromisoformat(payload["p"])
            if published_at.tzinfo is None or not relevance.is_finite():
                raise ValueError
            return SearchCursor(
                exact_match=int(payload["e"]),
                relevance=relevance,
                published_at=self._as_utc(published_at),
                work_id=UUID(payload["i"]),
                sort=sort,
                view_count=view_count,
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
            InvalidOperation,
        ) as error:
            raise SearchQueryInvalidError("invalid_cursor") from error

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.astimezone(UTC)
