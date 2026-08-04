import argparse
import asyncio
import json

from redis.asyncio import Redis

from app.core.config import get_settings
from app.modules.public.catalog_cache import (
    GENERATION_KEY,
    RedisPublicCatalogCache,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Invalidate all versioned public catalog cache entries."
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Increment the cache generation. Without this flag, only inspect it.",
    )
    parser.add_argument(
        "--reason",
        default="",
        help="Required operational reason when --apply is used.",
    )
    return parser


async def _run(*, apply: bool, reason: str) -> int:
    normalized_reason = " ".join(reason.split())
    if apply and not normalized_reason:
        raise ValueError("--reason is required with --apply")
    settings = get_settings()
    redis_client: Redis = Redis.from_url(settings.redis_url)
    try:
        before_value = await redis_client.get(GENERATION_KEY)
        before = (
            before_value.decode()
            if isinstance(before_value, bytes)
            else str(before_value or "0")
        )
        after: int | None = None
        if apply:
            after = await RedisPublicCatalogCache(
                redis_client,
                ttl_seconds=settings.public_catalog_cache_ttl_seconds,
            ).invalidate(reason=f"emergency:{normalized_reason[:120]}")
            if after is None:
                return 1
        print(
            json.dumps(
                {
                    "applied": apply,
                    "generationBefore": before,
                    "generationAfter": after,
                },
                sort_keys=True,
            )
        )
        return 0
    finally:
        await redis_client.aclose()


def main() -> int:
    args = _parser().parse_args()
    try:
        return asyncio.run(_run(apply=bool(args.apply), reason=str(args.reason)))
    except ValueError as error:
        _parser().error(str(error))


if __name__ == "__main__":
    raise SystemExit(main())
