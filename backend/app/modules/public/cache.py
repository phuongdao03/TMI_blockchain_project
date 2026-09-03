import json

from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.modules.blockchain.proof_registry_gateway import THVProofRecord


class RedisVerificationCache:
    def __init__(self, client: Redis, *, ttl_seconds: int) -> None:
        self._client = client
        self._ttl_seconds = ttl_seconds

    async def get(self, key: str) -> THVProofRecord | None:
        try:
            raw = await self._client.get(f"public:verification:{key}")
        except (RedisError, OSError, TimeoutError):
            return None
        if raw is None:
            return None
        try:
            payload = json.loads(raw)
            return THVProofRecord(
                asset_id=bytes.fromhex(payload["assetId"]),
                proof_hash=bytes.fromhex(payload["proofHash"]),
                version=int(payload["version"]),
                recorded_at=int(payload["recordedAt"]),
                signer=str(payload["signer"]),
                exists=bool(payload["exists"]),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            return None

    async def set(self, key: str, record: THVProofRecord) -> None:
        payload = json.dumps(
            {
                "assetId": record.asset_id.hex(),
                "proofHash": record.proof_hash.hex(),
                "version": record.version,
                "recordedAt": record.recorded_at,
                "signer": record.signer,
                "exists": record.exists,
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
