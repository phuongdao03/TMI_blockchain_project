"""Expand video-capable dossier evidence rules to 100 MB.

Revision ID: 0074_expand_video_evidence_limit
Revises: 0073_verdict_based_reviews
Create Date: 2026-09-05
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0074_expand_video_evidence_limit"
down_revision: str | None = "0073_verdict_based_reviews"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_LIMIT = 30 * 1024 * 1024
NEW_LIMIT = 100 * 1024 * 1024
VIDEO_TYPES = {"video/mp4", "video/webm"}


def _versions() -> sa.TableClause:
    return sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("schema_json", sa.JSON()),
    )


def _schema(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("Dossier type schema is not an object.")
    return copy.deepcopy(value)


def _rewrite_limit(source: int, destination: int) -> None:
    versions = _versions()
    bind = op.get_bind()
    for row in bind.execute(
        sa.select(versions.c.id, versions.c.schema_json)
    ).mappings():
        schema = _schema(row["schema_json"])
        changed = False
        rules = schema.get("documentRules")
        if not isinstance(rules, list):
            continue
        for rule in rules:
            if not isinstance(rule, dict):
                continue
            mime_types = rule.get("allowedMimeTypes")
            if (
                rule.get("maxBytes") == source
                and isinstance(mime_types, list)
                and VIDEO_TYPES.intersection(mime_types)
            ):
                rule["maxBytes"] = destination
                changed = True
        if changed:
            bind.execute(
                sa.update(versions)
                .where(versions.c.id == row["id"])
                .values(schema_json=schema)
            )


def upgrade() -> None:
    _rewrite_limit(OLD_LIMIT, NEW_LIMIT)


def downgrade() -> None:
    _rewrite_limit(NEW_LIMIT, OLD_LIMIT)
