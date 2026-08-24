"""Add server-owned document rules and scoped evidence visibility.

Revision ID: 0059_document_rule_visibility
Revises: 0058_four_product_roles
Create Date: 2026-08-24
"""

from __future__ import annotations

import copy
import json
from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0059_document_rule_visibility"
down_revision: str | None = "0058_four_product_roles"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_TYPE_CODES = (
    "ARTWORK",
    "CERTIFICATE",
    "CULTURAL_HERITAGE",
    "CULTURAL_WORK",
    "DOCUMENT",
    "INITIATIVE",
    "INTELLECTUAL_ASSET",
    "ORGANIZATION",
    "OTHER",
    "PERSON",
    "PRODUCT",
    "TRADEMARK",
)
DEFAULT_VERSION_IDS = {
    code: UUID(f"30000000-0000-4000-8000-{index:012d}")
    for index, code in enumerate(DEFAULT_TYPE_CODES, start=1)
}


def _rules_for(code: str) -> list[dict[str, object]]:
    rules: list[dict[str, object]] = [
        {
            "key": "OWNERSHIP_PROOF",
            "label": "Tài liệu chứng minh quyền gửi hồ sơ",
            "documentType": "OWNERSHIP_PROOF",
            "required": True,
            "allowedMimeTypes": ["application/pdf"],
            "maxBytes": 30 * 1024 * 1024,
            "maxCount": 3,
            "defaultVisibility": "INTERNAL",
        },
        {
            "key": "SUPPORTING_DOCUMENT",
            "label": "Tài liệu bổ sung",
            "documentType": "SUPPORTING_DOCUMENT",
            "required": False,
            "allowedMimeTypes": [
                "application/pdf",
                "image/jpeg",
                "image/png",
                "image/webp",
            ],
            "maxBytes": 30 * 1024 * 1024,
            "maxCount": 8,
            "defaultVisibility": "INTERNAL",
        },
    ]
    if code in {
        "ARTWORK",
        "CULTURAL_HERITAGE",
        "CULTURAL_WORK",
        "INITIATIVE",
        "INTELLECTUAL_ASSET",
        "PRODUCT",
        "TRADEMARK",
    }:
        rules.insert(
            0,
            {
                "key": "PUBLIC_PRESENTATION",
                "label": "Ảnh hoặc bản trình bày có thể công khai",
                "documentType": "PUBLIC_PRESENTATION",
                "required": False,
                "allowedMimeTypes": ["image/jpeg", "image/png", "image/webp"],
                "maxBytes": 20 * 1024 * 1024,
                "maxCount": 8,
                "defaultVisibility": "PUBLIC_PREVIEW",
            },
        )
    return rules


def _tables() -> tuple[sa.TableClause, sa.TableClause]:
    return (
        sa.table(
            "dossier_types",
            sa.column("id", sa.Uuid()),
            sa.column("code", sa.String()),
        ),
        sa.table(
            "dossier_type_versions",
            sa.column("id", sa.Uuid()),
            sa.column("dossier_type_id", sa.Uuid()),
            sa.column("version_no", sa.Integer()),
            sa.column("schema_json", sa.JSON()),
        ),
    )


def _as_schema(value: object) -> dict[str, object]:
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict):
        raise RuntimeError("Default dossier type schema is not an object.")
    return copy.deepcopy(value)


def upgrade() -> None:
    with op.batch_alter_table("dossier_evidences") as batch:
        batch.drop_constraint("dossier_evidence_access_scope_valid", type_="check")
        batch.create_check_constraint(
            "dossier_evidence_access_scope_valid",
            "access_scope IN ('PUBLIC', 'PRIVATE', 'INTERNAL', 'PUBLIC_PREVIEW', "
            "'REVIEWER_ONLY', 'ADMIN_ONLY')",
        )

    dossier_types, dossier_type_versions = _tables()
    bind = op.get_bind()
    inserts: list[dict[str, object]] = []
    for code in DEFAULT_TYPE_CODES:
        type_row = bind.execute(
            sa.select(dossier_types.c.id).where(dossier_types.c.code == code)
        ).mappings().one_or_none()
        if type_row is None:
            continue
        latest = bind.execute(
            sa.select(
                dossier_type_versions.c.version_no,
                dossier_type_versions.c.schema_json,
            )
            .where(dossier_type_versions.c.dossier_type_id == type_row["id"])
            .order_by(dossier_type_versions.c.version_no.desc())
            .limit(1)
        ).mappings().one_or_none()
        # Preserve any type definition already managed by an operator.  Only
        # seed a new v2 for the untouched, built-in v1 catalog.
        if latest is None or latest["version_no"] != 1:
            continue
        schema = _as_schema(latest["schema_json"])
        if schema.get("documentRules"):
            continue
        schema["documentRules"] = _rules_for(code)
        inserts.append(
            {
                "id": DEFAULT_VERSION_IDS[code],
                "dossier_type_id": type_row["id"],
                "version_no": 2,
                "schema_json": schema,
            }
        )
    if inserts:
        op.bulk_insert(dossier_type_versions, inserts)


def downgrade() -> None:
    dossier_types, dossier_type_versions = _tables()
    del dossier_types
    op.execute(
        sa.delete(dossier_type_versions).where(
            dossier_type_versions.c.id.in_(tuple(DEFAULT_VERSION_IDS.values()))
        )
    )
    # Map the new private/public policy labels into their legacy equivalents
    # before reapplying the former database constraint.
    op.execute(
        sa.text(
            "UPDATE dossier_evidences SET access_scope = CASE "
            "WHEN access_scope = 'INTERNAL' THEN 'PRIVATE' "
            "WHEN access_scope = 'PUBLIC_PREVIEW' THEN 'PUBLIC' "
            "ELSE access_scope END"
        )
    )
    with op.batch_alter_table("dossier_evidences") as batch:
        batch.drop_constraint("dossier_evidence_access_scope_valid", type_="check")
        batch.create_check_constraint(
            "dossier_evidence_access_scope_valid",
            "access_scope IN ('PUBLIC', 'PRIVATE', 'REVIEWER_ONLY', 'ADMIN_ONLY')",
        )
