import json

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.blockchain.gateway import CertificateRecord


class RedisVerificationCache:
    def __init__(self, client: Redis, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> CertificateRecord | None:
        try:
            raw = await self._client.get(f"public:verification:{key}")
        except (RedisError, OSError, TimeoutError):
            return None
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            return CertificateRecord(
                dossier_hash=bytes.fromhex(payload["dossierHash"]),
                metadata_hash=bytes.fromhex(payload["metadataHash"]),
                revocation_reason_hash=bytes.fromhex(
                    payload["revocationReasonHash"]
                ),
                issued_at=int(payload["issuedAt"]),
                expires_at=int(payload["expiresAt"]),
                version=int(payload["version"]),
                revoked=bool(payload["revoked"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    async def set(self, key: str, record: CertificateRecord) -> None:
        payload = json.dumps(
            {
                "dossierHash": record.dossier_hash.hex(),
                "metadataHash": record.metadata_hash.hex(),
                "revocationReasonHash": record.revocation_reason_hash.hex(),
                "issuedAt": record.issued_at,
                "expiresAt": record.expires_at,
                "version": record.version,
                "revoked": record.revoked,
            },
            separators=(",", ":"),
        )
        try:
            await self._client.set(
                f"public:verification:{key}",
                payload,
                ex=self._ttl_seconds,
            )
        except (RedisError, OSError, TimeoutError):
            return
