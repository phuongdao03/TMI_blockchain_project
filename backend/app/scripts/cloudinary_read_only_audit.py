"""Read-only Cloudinary inventory and application registry comparison."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import re
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.pool import NullPool

try:
    from dotenv import dotenv_values
except ImportError:  # Container deployments normally inject the environment.
    dotenv_values = cast(Any, None)

_RESOURCE_TYPES = ("image", "video", "raw")
_DELIVERY_TYPES = ("authenticated", "private", "upload")
_PART_SUFFIX = re.compile(r"\.part-\d{5}$")


class CloudinaryAuditError(RuntimeError):
    """Safe, non-secret Cloudinary audit failure detail."""


_TRACKED_SQL = text(
    """
    SELECT resource_type, access_mode AS delivery_type,
           cloudinary_public_id AS public_id
    FROM media_assets WHERE storage_provider = 'CLOUDINARY'
    UNION
    SELECT 'raw', 'authenticated', encrypted_object_public_id
    FROM media_assets WHERE encrypted_object_public_id IS NOT NULL
    UNION
    SELECT CASE WHEN media_kind::text = 'VIDEO' THEN 'video' ELSE 'image' END,
           'upload', derivative_public_id
    FROM public_work_media WHERE derivative_public_id IS NOT NULL
    """
)
_SUMMARY_SQL = text(
    """
    SELECT
      (SELECT count(*) FROM media_assets WHERE status = 'PENDING'
        AND created_at < now() - make_interval(hours => :age_hours)) AS stale_pending,
      (SELECT count(*) FROM (
        SELECT sha256 FROM media_assets
        WHERE status = 'ACTIVE' AND sha256 IS NOT NULL
        GROUP BY sha256 HAVING count(*) > 1
      ) repeated_hashes) AS duplicate_hash_groups
    """
)


def _config() -> dict[str, str]:
    values = dict(os.environ)
    env_file = Path(__file__).resolve().parents[3] / ".env"
    if dotenv_values is not None and env_file.is_file():
        for key, value in dotenv_values(env_file).items():
            if value and not values.get(key):
                values[key] = value
    names = (
        "DATABASE_URL",
        "CLOUDINARY_CLOUD_NAME",
        "CLOUDINARY_API_KEY",
        "CLOUDINARY_API_SECRET",
    )
    missing = [name for name in names if not values.get(name)]
    if missing:
        raise RuntimeError(f"Missing required environment keys: {', '.join(missing)}")
    return {name: values[name] for name in (*names, "APP_ENV") if values.get(name)}


async def _page(
    client: httpx.AsyncClient,
    *,
    config: dict[str, str],
    resource_type: str,
    delivery_type: str,
    prefix: str,
    request_count: list[int],
    request_limit: int,
) -> tuple[list[dict[str, Any]], bool]:
    resources: list[dict[str, Any]] = []
    cursor: str | None = None
    while True:
        if request_count[0] >= request_limit:
            return resources, False
        params: dict[str, str | int] = {"max_results": 500, "prefix": prefix}
        if cursor:
            params["next_cursor"] = cursor
        response = await client.get(
            f"https://api.cloudinary.com/v1_1/{config['CLOUDINARY_CLOUD_NAME']}"
            f"/resources/{resource_type}/{delivery_type}",
            params=params,
            auth=(config["CLOUDINARY_API_KEY"], config["CLOUDINARY_API_SECRET"]),
        )
        request_count[0] += 1
        try:
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise CloudinaryAuditError(
                "Cloudinary Admin API returned HTTP "
                f"{response.status_code} for {resource_type}/{delivery_type}."
            ) from exc
        payload = response.json()
        rows = payload.get("resources", [])
        if not isinstance(rows, list):
            raise RuntimeError("Cloudinary resource response was invalid.")
        resources.extend(row for row in rows if isinstance(row, dict))
        cursor = payload.get("next_cursor")
        if not isinstance(cursor, str) or not cursor:
            return resources, True


async def _audit(args: argparse.Namespace) -> dict[str, Any]:
    config = _config()
    environment = config.get("APP_ENV", "unknown").strip().lower()
    prefixes = (
        f"cns/{environment}/",
        f"ip-certificate/{environment}/certificates/",
    )
    engine = create_async_engine(
        config["DATABASE_URL"],
        poolclass=NullPool,
        connect_args={
            "server_settings": {
                "application_name": "cloudinary-read-only-audit",
                "default_transaction_read_only": "on",
            }
        },
    )
    try:
        async with engine.connect() as connection:
            await connection.execute(text("SET TRANSACTION READ ONLY"))
            tracked_result = await connection.execute(_TRACKED_SQL)
            tracked = {
                (str(row[0]), str(row[1]), str(row[2]))
                for row in tracked_result.all()
                if row[0] and row[1] and row[2]
            }
            summary = await connection.execute(
                _SUMMARY_SQL, {"age_hours": args.min_age_hours}
            )
            stale_pending, duplicate_hash_groups = summary.one()
    finally:
        await engine.dispose()

    if args.database_only:
        return {
            "generated_at": datetime.now(UTC).isoformat(),
            "environment": environment,
            "read_only": True,
            "automatic_deletion": False,
            "database": {
                "tracked_asset_keys": len(tracked),
                "stale_pending_media_candidates": int(stale_pending),
                "duplicate_active_sha256_groups": int(duplicate_hash_groups),
            },
            "cloudinary": {"inventory": "skipped by --database-only"},
        }

    requests = [0]
    seen: set[tuple[str, str, str]] = set()
    candidate_ids: list[dict[str, str]] = []
    scopes: list[dict[str, Any]] = []
    inventory_complete = True
    cloudinary_error: str | None = None
    asset_count = byte_count = candidate_count = candidate_bytes = 0
    async with httpx.AsyncClient(timeout=20.0) as client:
        for prefix in prefixes:
            for resource_type in _RESOURCE_TYPES:
                for delivery_type in _DELIVERY_TYPES:
                    try:
                        rows, scope_complete = await _page(
                            client,
                            config=config,
                            resource_type=resource_type,
                            delivery_type=delivery_type,
                            prefix=prefix,
                            request_count=requests,
                            request_limit=args.max_requests,
                        )
                    except CloudinaryAuditError as exc:
                        rows, scope_complete = [], False
                        cloudinary_error = str(exc)
                    inventory_complete &= scope_complete
                    scope_assets = scope_bytes = scope_candidates = 0
                    for row in rows:
                        public_id = row.get("public_id")
                        if not isinstance(public_id, str):
                            continue
                        key = (resource_type, delivery_type, public_id)
                        if key in seen:
                            continue
                        seen.add(key)
                        size = row.get("bytes", 0)
                        size = size if isinstance(size, int) else 0
                        scope_assets += 1
                        scope_bytes += size
                        asset_count += 1
                        byte_count += size
                        base_id = _PART_SUFFIX.sub("", public_id)
                        registered = key in tracked or (
                            base_id != public_id
                            and (resource_type, delivery_type, base_id) in tracked
                        )
                        if registered:
                            continue
                        scope_candidates += 1
                        candidate_count += 1
                        candidate_bytes += size
                        created_at = row.get("created_at")
                        if isinstance(created_at, str):
                            try:
                                created = datetime.fromisoformat(
                                    created_at.replace("Z", "+00:00")
                                )
                            except ValueError:
                                continue
                            if created.tzinfo is None:
                                created = created.replace(tzinfo=UTC)
                            if created <= datetime.now(UTC) - timedelta(
                                hours=args.min_age_hours
                            ):
                                candidate_ids.append(
                                    {
                                        "resource_type": resource_type,
                                        "delivery_type": delivery_type,
                                        "public_id": public_id,
                                    }
                                )
                    scopes.append(
                        {
                            "prefix": prefix,
                            "resource_type": resource_type,
                            "delivery_type": delivery_type,
                            "assets_seen": scope_assets,
                            "bytes_seen": scope_bytes,
                            "unregistered_candidates": scope_candidates,
                            "complete": scope_complete,
                            "error": cloudinary_error,
                        }
                    )
                    if cloudinary_error or requests[0] >= args.max_requests:
                        break
                if cloudinary_error or requests[0] >= args.max_requests:
                    break
            if cloudinary_error or requests[0] >= args.max_requests:
                break
    expected_scopes = len(prefixes) * len(_RESOURCE_TYPES) * len(_DELIVERY_TYPES)
    inventory_complete = inventory_complete and len(scopes) == expected_scopes

    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(),
        "environment": environment,
        "read_only": True,
        "automatic_deletion": False,
        "inventory_complete": inventory_complete,
        "cloudinary_admin_get_requests": requests[0],
        "minimum_age_hours": args.min_age_hours,
        "database": {
            "tracked_asset_keys": len(tracked),
            "stale_pending_media_candidates": int(stale_pending),
            "duplicate_active_sha256_groups": int(duplicate_hash_groups),
        },
        "cloudinary": {
            "assets_seen": asset_count,
            "bytes_seen": byte_count,
            "unregistered_candidates_seen": candidate_count,
            "unregistered_candidate_bytes_seen": candidate_bytes,
            "age_qualified_candidates": len(candidate_ids),
            "error": cloudinary_error,
            "scopes": scopes,
        },
    }
    if args.candidate_file:
        target = Path(args.candidate_file).resolve()
        target.write_text(
            json.dumps(candidate_ids, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        report["candidate_file"] = str(target)
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--min-age-hours",
        type=int,
        choices=range(24, 721),
        default=48,
    )
    parser.add_argument(
        "--max-requests",
        type=int,
        choices=range(1, 101),
        default=100,
    )
    parser.add_argument("--candidate-file")
    parser.add_argument(
        "--database-only",
        action="store_true",
        help="Run only the read-only Neon registry queries; skip Cloudinary API calls.",
    )
    args = parser.parse_args()
    try:
        result = asyncio.run(_audit(args))
    except CloudinaryAuditError as exc:
        print(
            json.dumps(
                {
                    "read_only": True,
                    "automatic_deletion": False,
                    "error_type": type(exc).__name__,
                    "detail": str(exc),
                }
            ),
            file=sys.stderr,
        )
        return 1
    except Exception as exc:
        print(
            json.dumps(
                {
                    "read_only": True,
                    "automatic_deletion": False,
                    "error_type": type(exc).__name__,
                }
            ),
            file=sys.stderr,
        )
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
