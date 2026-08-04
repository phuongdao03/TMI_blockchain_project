from collections.abc import Mapping, Sequence
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.models import AuditLog
from app.modules.audit.repository import AuditRepository

SENSITIVE_KEYS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "otp",
        "private_key",
        "secret",
        "phone",
        "email",
        "body_html",
    }
)


def redact(value: object, *, key: str | None = None) -> object:
    if key is not None and key.lower() in SENSITIVE_KEYS:
        return "[REDACTED]"
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value


class AuditService:
    def __init__(self, session: AsyncSession) -> None:
        self._repository = AuditRepository(session)

    def record(
        self,
        *,
        actor_user_id: UUID | None,
        action: str,
        resource_type: str,
        resource_id: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        row = AuditLog(
            actor_user_id=actor_user_id,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_json=redact(before) if before is not None else None,
            after_json=redact(after) if after is not None else None,
            request_id=request_id,
            ip_hash=ip_hash,
            user_agent=user_agent,
        )
        self._repository.add(row)
        return row

    async def search(self, **filters: object) -> tuple[tuple[AuditLog, ...], int]:
        return await self._repository.list(**filters)  # type: ignore[arg-type]
