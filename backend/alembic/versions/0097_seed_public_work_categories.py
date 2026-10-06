"""Expose the existing dossier taxonomy as public work categories.

Revision ID: 0097_seed_public_work_categories
Revises: 0096_attendance_worked_duration
"""

from collections.abc import Sequence
from uuid import UUID

import sqlalchemy as sa

from alembic import op

revision: str = "0097_seed_public_work_categories"
down_revision: str | None = "0096_attendance_worked_duration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# The digital asset category already exists and is used by submitted dossiers.
_SLUGS = {
    "CULTURAL_WORK": "tac-pham-van-hoa",
    "TRADEMARK": "nhan-hieu-va-thuong-hieu",
    "ARTWORK": "tac-pham-nghe-thuat",
    "DOCUMENT": "tai-lieu-va-tu-lieu",
    "CERTIFICATE": "van-bang-chung-nhan",
    "PERSON": "ca-nhan-tieu-bieu",
    "ORGANIZATION": "to-chuc-doanh-nghiep",
    "PRODUCT": "san-pham-va-giai-phap",
    "CULTURAL_HERITAGE": "di-san-van-hoa",
    "INITIATIVE": "sang-kien",
    "OTHER": "loai-ho-so-khac",
}


def upgrade() -> None:
    bind = op.get_bind()
    categories = sa.table(
        "categories",
        sa.column("id", sa.Uuid()),
        sa.column("code", sa.String()),
        sa.column("slug", sa.String()),
        sa.column("name", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("display_order", sa.Integer()),
    )
    dossier_types = sa.table(
        "dossier_types", sa.column("code", sa.String()), sa.column("name", sa.String())
    )
    existing = bind.execute(sa.select(categories.c.code, categories.c.slug)).all()
    used_codes = {row.code for row in existing}
    used_slugs = {row.slug for row in existing}
    type_names = dict(
        bind.execute(sa.select(dossier_types.c.code, dossier_types.c.name)).all()
    )
    for order, (code, slug) in enumerate(_SLUGS.items(), start=1):
        if code not in type_names or code in used_codes or slug in used_slugs:
            continue
        bind.execute(
            sa.insert(categories).values(
                id=UUID(f"30000000-0000-4000-8000-{order:012d}"),
                code=code,
                slug=slug,
                name=type_names[code],
                is_active=True,
                display_order=order,
            )
        )


def downgrade() -> None:
    # Categories may already be assigned to published works; preserve them.
    pass
