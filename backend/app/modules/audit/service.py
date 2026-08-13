import hashlib
import hmac
import json
import re
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import Settings, get_settings
from app.core.logging import request_id_context
from app.modules.audit.models import AuditActorType, AuditLog
from app.modules.audit.repository import AuditRepository

SENSITIVE_KEY_PARTS = frozenset(
    {
        "password",
        "password_hash",
        "token",
        "credential",
        "apikey",
        "authorization",
        "cookie",
        "otp",
        "private_key",
        "secret",
        "phone",
        "email",
        "body_html",
    }
)

REDACTED = "[REDACTED]"
MAX_USER_AGENT_LENGTH = 512


class AuditIntegrityStatus(StrEnum):
    VERIFIED = "VERIFIED"
    TAMPERED = "TAMPERED"
    UNSEALED = "UNSEALED"
    KEY_UNAVAILABLE = "KEY_UNAVAILABLE"


def _normalized_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.casefold())


def _is_sensitive_key(key: str) -> bool:
    normalized = _normalized_key(key)
    return any(_normalized_key(part) in normalized for part in SENSITIVE_KEY_PARTS)


def redact(value: object, *, key: str | None = None) -> object:
    if key is not None and _is_sensitive_key(key):
        return REDACTED
    if isinstance(value, Mapping):
        return {
            str(item_key): redact(item, key=str(item_key))
            for item_key, item in value.items()
        }
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [redact(item) for item in value]
    return value


class AuditService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        settings: Settings | None = None,
    ) -> None:
        self._repository = AuditRepository(session)
        self._settings = settings or get_settings()

    @staticmethod
    def _utc_iso(value: datetime) -> str:
        normalized = value.replace(tzinfo=UTC) if value.tzinfo is None else value
        return normalized.astimezone(UTC).isoformat()

    @staticmethod
    def _canonical_payload(row: AuditLog) -> bytes:
        payload = {
            "id": str(row.id),
            "actor_user_id": str(row.actor_user_id) if row.actor_user_id else None,
            "actor_type": row.actor_type.value,
            "actor_service": row.actor_service,
            "action": row.action,
            "resource_type": row.resource_type,
            "resource_id": row.resource_id,
            "before": row.before_json,
            "after": row.after_json,
            "request_id": row.request_id,
            "ip_hash": row.ip_hash,
            "user_agent": row.user_agent,
            "created_at": AuditService._utc_iso(row.created_at),
            "retention_until": (
                AuditService._utc_iso(row.retention_until)
                if row.retention_until
                else None
            ),
            "integrity_version": row.integrity_version,
            "integrity_key_id": row.integrity_key_id,
        }
        return json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        ).encode("utf-8")

    def _seal(self, row: AuditLog) -> None:
        key = self._settings.audit_integrity_key
        if key is None or not key.get_secret_value():
            return
        row.integrity_version = 1
        row.integrity_key_id = self._settings.audit_integrity_key_id
        row.integrity_hash = hmac.new(
            key.get_secret_value().encode("utf-8"),
            self._canonical_payload(row),
            hashlib.sha256,
        ).hexdigest()

    def verify_integrity(self, row: AuditLog) -> AuditIntegrityStatus:
        if not row.integrity_hash or not row.integrity_key_id:
            return AuditIntegrityStatus.UNSEALED
        key = self._settings.audit_integrity_verification_keys.get(row.integrity_key_id)
        if (
            row.integrity_key_id == self._settings.audit_integrity_key_id
            and self._settings.audit_integrity_key is not None
        ):
            key = self._settings.audit_integrity_key
        if key is None or not key.get_secret_value():
            return AuditIntegrityStatus.KEY_UNAVAILABLE
        expected = hmac.new(
            key.get_secret_value().encode("utf-8"),
            self._canonical_payload(row),
            hashlib.sha256,
        ).hexdigest()
        return (
            AuditIntegrityStatus.VERIFIED
            if hmac.compare_digest(expected, row.integrity_hash)
            else AuditIntegrityStatus.TAMPERED
        )

    def record(
        self,
        *,
        actor_user_id: UUID | None,
        actor_service: str | None = None,
        action: str,
        resource_type: str,
        resource_id: str,
        before: dict[str, object] | None = None,
        after: dict[str, object] | None = None,
        request_id: str | None = None,
        ip_hash: str | None = None,
        user_agent: str | None = None,
    ) -> AuditLog:
        if actor_user_id is not None and actor_service:
            raise ValueError("An audit actor cannot be both a user and a service.")
        created_at = datetime.now(UTC)
        actor_type = (
            AuditActorType.USER
            if actor_user_id is not None
            else AuditActorType.SERVICE
            if actor_service
            else AuditActorType.ANONYMOUS
        )
        request_id_candidate = (
            request_id if request_id is not None else request_id_context.get()
        )
        effective_request_id = (
            request_id_candidate[:128]
            if request_id_candidate and request_id_candidate != "unknown"
            else None
        )
        row = AuditLog(
            id=uuid4(),
            actor_user_id=actor_user_id,
            actor_type=actor_type,
            actor_service=actor_service,
            action=action,
            resource_type=resource_type,
            resource_id=resource_id,
            before_json=redact(before) if before is not None else None,
            after_json=redact(after) if after is not None else None,
            request_id=effective_request_id,
            ip_hash=ip_hash,
            user_agent=(
                user_agent[:MAX_USER_AGENT_LENGTH] if user_agent is not None else None
            ),
            created_at=created_at,
            retention_until=created_at
            + timedelta(days=self._settings.audit_retention_days),
        )
        self._seal(row)
        self._repository.add(row)
        return row

    async def search(self, **filters: object) -> tuple[tuple[AuditLog, ...], int]:
        return await self._repository.list(**filters)  # type: ignore[arg-type]
