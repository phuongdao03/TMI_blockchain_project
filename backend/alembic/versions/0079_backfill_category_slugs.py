"""Backfill stable public slugs for legacy categories.

Revision ID: 0079_backfill_category_slugs
Revises: 0078_editorial_covers
Create Date: 2026-09-16
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0079_backfill_category_slugs"
down_revision: str | None = "0078_editorial_covers"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    existing_slugs = {
        slug.strip()
        for (slug,) in bind.execute(sa.text("SELECT slug FROM categories"))
        if slug and slug.strip()
    }
    legacy_categories = bind.execute(
        sa.text(
            "SELECT id FROM categories "
            "WHERE slug IS NULL OR trim(slug) = '' ORDER BY id"
        )
    )
    for (category_id,) in legacy_categories:
        base_slug = f"legacy-category-{category_id}"
        slug = base_slug
        suffix = 2
        while slug in existing_slugs:
            slug = f"{base_slug}-{suffix}"
            suffix += 1
        bind.execute(
            sa.text("UPDATE categories SET slug = :slug WHERE id = :id"),
            {"id": category_id, "slug": slug},
        )
        existing_slugs.add(slug)


def downgrade() -> None:
    # Backfilled slugs are public identifiers and cannot be safely removed.
    pass
