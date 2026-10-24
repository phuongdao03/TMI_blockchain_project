"""Expand the artwork dossier's type-of-work options.

Revision ID: 0139_expand_artwork_type_options
Revises: 0138_advertising_delivery
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0139_expand_artwork_type_options"
down_revision: str | None = "0138_advertising_delivery"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

LEGACY_OPTIONS: list[dict[str, str]] = [
    {"value": "VISUAL_ART", "label": "Mỹ thuật"},
    {"value": "PHOTOGRAPHY", "label": "Nhiếp ảnh"},
    {"value": "MUSIC", "label": "Âm nhạc"},
]

ARTWORK_OPTIONS: list[dict[str, str]] = [
    *LEGACY_OPTIONS,
    {"value": "THEATRE", "label": "Sân khấu"},
    {"value": "DANCE", "label": "Múa"},
    {"value": "LITERATURE", "label": "Văn học"},
    {"value": "FILM", "label": "Điện ảnh"},
    {"value": "ARCHITECTURE", "label": "Kiến trúc"},
    {"value": "DESIGN", "label": "Thiết kế"},
    {"value": "CRAFT", "label": "Thủ công mỹ nghệ"},
    {"value": "MULTIMEDIA", "label": "Tác phẩm đa phương tiện"},
    {"value": "OTHER", "label": "Loại hình khác"},
]

ARTWORK_VERSION_ID = UUID("d5e9c3aa-644c-4b1d-8daf-99ebddc402d9")
ARTWORK_DESCRIPTION = (
    "Dành cho mỹ thuật, nhiếp ảnh, âm nhạc, sân khấu, múa, văn học, điện ảnh, "
    "kiến trúc, thiết kế, thủ công và tác phẩm đa phương tiện."
)


def upgrade() -> None:
    connection = op.get_bind()
    dossier_types = sa.table(
        "dossier_types",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
    )
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("dossier_type_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("schema_json", postgresql.JSONB()),
    )
    latest_versions = (
        sa.select(
            versions.c.dossier_type_id,
            sa.func.max(versions.c.version_no).label("version_no"),
        )
        .group_by(versions.c.dossier_type_id)
        .subquery()
    )
    row = connection.execute(
        sa.select(
            dossier_types.c.id.label("dossier_type_id"),
            versions.c.version_no,
            versions.c.schema_json,
        )
        .join(dossier_types, dossier_types.c.id == versions.c.dossier_type_id)
        .join(
            latest_versions,
            sa.and_(
                latest_versions.c.dossier_type_id == versions.c.dossier_type_id,
                latest_versions.c.version_no == versions.c.version_no,
            ),
        )
        .where(dossier_types.c.code == "ARTWORK")
    ).mappings().first()
    if row is None:
        return

    schema = row["schema_json"]
    fields = schema.get("fields") if isinstance(schema, dict) else None
    if not isinstance(fields, list):
        return
    form_field = next(
        (
            field
            for field in fields
            if isinstance(field, dict) and field.get("key") == "artForm"
        ),
        None,
    )
    if form_field is None or form_field.get("options") != LEGACY_OPTIONS:
        return

    updated_schema = {
        **schema,
        "description": ARTWORK_DESCRIPTION,
        "fields": [
            {**field, "options": ARTWORK_OPTIONS}
            if isinstance(field, dict) and field.get("key") == "artForm"
            else field
            for field in fields
        ],
    }
    connection.execute(
        versions.insert().values(
            id=ARTWORK_VERSION_ID,
            dossier_type_id=row["dossier_type_id"],
            version_no=row["version_no"] + 1,
            schema_json=updated_schema,
        )
    )


def downgrade() -> None:
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
    )
    op.get_bind().execute(
        versions.delete().where(versions.c.id == ARTWORK_VERSION_ID)
    )
