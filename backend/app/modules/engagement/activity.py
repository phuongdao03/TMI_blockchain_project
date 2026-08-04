import base64
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from app.core.errors import DomainError


class ActivityKind(StrEnum):
    FAVORITE = "FAVORITE"
    SHARE = "SHARE"


@dataclass(frozen=True, slots=True)
class ActivityCursor:
    created_at: datetime
    activity_id: UUID


class ActivityCursorInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ENGAGEMENT_CURSOR_INVALID",
            message="Activity cursor is invalid.",
            status_code=422,
        )


class ActivityCursorCodec:
    VERSION = 1

    def encode(self, cursor: ActivityCursor) -> str:
        payload = json.dumps(
            {
                "v": self.VERSION,
                "t": self._as_utc(cursor.created_at).isoformat(),
                "i": str(cursor.activity_id),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()

    def decode(self, value: str) -> ActivityCursor:
        try:
            padding = "=" * (-len(value) % 4)
            payload = json.loads(base64.urlsafe_b64decode(value + padding))
            if payload["v"] != self.VERSION:
                raise ValueError
            created_at = datetime.fromisoformat(payload["t"])
            if created_at.tzinfo is None:
                raise ValueError
            return ActivityCursor(
                created_at=self._as_utc(created_at),
                activity_id=UUID(payload["i"]),
            )
        except (
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise ActivityCursorInvalidError() from error

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        return value.astimezone(UTC)
