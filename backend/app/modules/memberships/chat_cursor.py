import base64
import binascii
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from app.core.errors import DomainError


class MembershipChatCursorInvalidError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="MEMBERSHIP_CHAT_CURSOR_INVALID",
            message="Chat history cursor is invalid.",
            status_code=422,
        )


@dataclass(frozen=True, slots=True)
class MembershipChatCursor:
    room: str
    created_at: datetime
    message_id: UUID


class MembershipChatCursorCodec:
    VERSION = 1

    def encode(self, *, room: str, created_at: datetime, message_id: UUID) -> str:
        payload = json.dumps(
            {
                "v": self.VERSION,
                "r": room,
                "t": self._as_utc(created_at).isoformat(),
                "i": str(message_id),
            },
            separators=(",", ":"),
            sort_keys=True,
        ).encode()
        return base64.urlsafe_b64encode(payload).rstrip(b"=").decode()

    def decode(self, value: str, *, expected_room: str) -> MembershipChatCursor:
        try:
            padding = "=" * (-len(value) % 4)
            payload_bytes = base64.b64decode(
                value + padding,
                altchars=b"-_",
                validate=True,
            )
            payload = json.loads(payload_bytes)
            if (
                not isinstance(payload, dict)
                or payload.get("v") != self.VERSION
                or payload.get("r") != expected_room
            ):
                raise ValueError
            created_at = datetime.fromisoformat(payload["t"])
            if created_at.tzinfo is None:
                raise ValueError
            return MembershipChatCursor(
                room=expected_room,
                created_at=self._as_utc(created_at),
                message_id=UUID(payload["i"]),
            )
        except (
            binascii.Error,
            KeyError,
            TypeError,
            ValueError,
            UnicodeDecodeError,
            json.JSONDecodeError,
        ) as error:
            raise MembershipChatCursorInvalidError() from error

    @staticmethod
    def _as_utc(value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)
