"""Add PostgreSQL public-work search foundation.

Revision ID: 0018_search_foundation
Revises: 0017_content_reports
Create Date: 2026-08-01
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0018_search_foundation"
down_revision: str | None = "0017_content_reports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

PUBLIC_PREDICATE = (
    "publication_status = 'PUBLISHED' AND visibility = 'PUBLIC' AND deleted_at IS NULL"
)
HELPER_COLUMNS = (
    "search_organization_text",
    "search_taxonomy_text",
    "search_certificate_text",
)


def upgrade() -> None:
    dialect = op.get_bind().dialect.name
    existing_columns = (
        {
            column["name"]
            for column in sa.inspect(op.get_bind()).get_columns("public_works")
        }
        if dialect != "postgresql"
        else set()
    )
    for column_name in HELPER_COLUMNS:
        if column_name not in existing_columns:
            op.add_column(
                "public_works",
                sa.Column(
                    column_name,
                    sa.Text(),
                    nullable=False,
                    server_default="",
                ),
                if_not_exists=dialect == "postgresql",
            )
    vector_type: sa.types.TypeEngine[object] = (
        postgresql.TSVECTOR() if dialect == "postgresql" else sa.Text()
    )
    vector_default = (
        sa.text("''::tsvector") if dialect == "postgresql" else sa.text("''")
    )
    if "search_vector" not in existing_columns:
        op.add_column(
            "public_works",
            sa.Column(
                "search_vector",
                vector_type,
                nullable=False,
                server_default=vector_default,
            ),
            if_not_exists=dialect == "postgresql",
        )

    if dialect == "postgresql":
        _upgrade_postgresql()
    else:
        _upgrade_portable()


def _upgrade_postgresql() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent")
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.immutable_unaccent(value text)
        RETURNS text
        LANGUAGE sql
        IMMUTABLE PARALLEL SAFE STRICT
        AS $$ SELECT public.unaccent('public.unaccent', value) $$
        """
    )
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.refresh_public_work_search_vector()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $$
        BEGIN
          NEW.search_vector :=
            setweight(to_tsvector('simple', public.immutable_unaccent(
              concat_ws(' ', NEW.title, NEW.search_certificate_text)
            )), 'A') ||
            setweight(to_tsvector('simple', public.immutable_unaccent(
              concat_ws(' ', NEW.author_display_name,
                NEW.search_organization_text, NEW.search_taxonomy_text)
            )), 'B') ||
            setweight(to_tsvector('simple', public.immutable_unaccent(
              concat_ws(' ', NEW.short_description, NEW.full_description)
            )), 'C');
          RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1
            FROM pg_trigger
            WHERE tgname = 'trg_public_works_search_vector'
              AND tgrelid = 'public_works'::regclass
          ) THEN
            CREATE TRIGGER trg_public_works_search_vector
            BEFORE INSERT OR UPDATE OF title, short_description, full_description,
              author_display_name, search_organization_text, search_taxonomy_text,
              search_certificate_text
            ON public_works
            FOR EACH ROW EXECUTE FUNCTION public.refresh_public_work_search_vector();
          END IF;
        END
        $$
        """
    )
    op.execute(
        """
        DO $$
        DECLARE affected integer;
        BEGIN
          LOOP
            WITH batch AS (
              SELECT id FROM public_works
              WHERE search_vector = ''::tsvector
              ORDER BY id
              LIMIT 1000
              FOR UPDATE SKIP LOCKED
            )
            UPDATE public_works AS work
            SET
              search_organization_text = COALESCE((
                SELECT organization.display_name
                FROM organizations AS organization
                WHERE organization.id = work.organization_id
              ), ''),
              search_taxonomy_text = concat_ws(' ',
                (SELECT category.name FROM categories AS category
                 WHERE category.id = work.category_id),
                (SELECT string_agg(tag.name, ' ' ORDER BY tag.name)
                 FROM public_work_tags AS work_tag
                 JOIN public_tags AS tag ON tag.id = work_tag.tag_id
                 WHERE work_tag.public_work_id = work.id AND tag.is_active)
              ),
              search_certificate_text = COALESCE((
                SELECT certificate.certificate_number
                FROM certificates AS certificate
                WHERE certificate.id = work.certificate_id
              ), '')
            FROM batch
            WHERE work.id = batch.id;
            GET DIAGNOSTICS affected = ROW_COUNT;
            EXIT WHEN affected = 0;
          END LOOP;
        END
        $$
        """
    )
    context = op.get_context()
    with context.autocommit_block():
        op.create_index(
            "ix_public_works_search_vector_public",
            "public_works",
            ["search_vector"],
            unique=False,
            if_not_exists=True,
            postgresql_using="gin",
            postgresql_where=sa.text(PUBLIC_PREDICATE),
            postgresql_concurrently=True,
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_public_works_title_trgm_public
            ON public_works USING gin
            (public.immutable_unaccent(lower(title)) gin_trgm_ops)
            WHERE publication_status = 'PUBLISHED' AND visibility = 'PUBLIC'
              AND deleted_at IS NULL
            """
        )
        op.execute(
            """
            CREATE INDEX CONCURRENTLY IF NOT EXISTS ix_public_works_author_trgm_public
            ON public_works USING gin
            (public.immutable_unaccent(lower(author_display_name)) gin_trgm_ops)
            WHERE publication_status = 'PUBLISHED' AND visibility = 'PUBLIC'
              AND deleted_at IS NULL AND author_display_name IS NOT NULL
            """
        )
        op.create_index(
            "ix_public_works_search_visibility_published_id",
            "public_works",
            ["publication_status", "visibility", "published_at", "id"],
            unique=False,
            if_not_exists=True,
            postgresql_concurrently=True,
        )


def _upgrade_portable() -> None:
    op.execute(
        """
        UPDATE public_works
        SET search_vector = trim(
          coalesce(title, '') || ' ' || coalesce(author_display_name, '') || ' ' ||
          coalesce(short_description, '') || ' ' || coalesce(full_description, '')
        )
        """
    )
    op.create_index(
        "ix_public_works_search_vector_public",
        "public_works",
        ["search_vector"],
        if_not_exists=True,
        sqlite_where=sa.text(PUBLIC_PREDICATE),
    )
    op.create_index(
        "ix_public_works_title_trgm_public",
        "public_works",
        ["title"],
        if_not_exists=True,
        sqlite_where=sa.text(PUBLIC_PREDICATE),
    )
    op.create_index(
        "ix_public_works_author_trgm_public",
        "public_works",
        ["author_display_name"],
        if_not_exists=True,
        sqlite_where=sa.text(f"{PUBLIC_PREDICATE} AND author_display_name IS NOT NULL"),
    )
    op.create_index(
        "ix_public_works_search_visibility_published_id",
        "public_works",
        ["publication_status", "visibility", "published_at", "id"],
        if_not_exists=True,
    )


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    if dialect == "postgresql":
        context = op.get_context()
        with context.autocommit_block():
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS "
                "ix_public_works_search_visibility_published_id"
            )
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_public_works_author_trgm_public"
            )
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_public_works_title_trgm_public"
            )
            op.execute(
                "DROP INDEX CONCURRENTLY IF EXISTS ix_public_works_search_vector_public"
            )
        op.execute(
            "DROP TRIGGER IF EXISTS trg_public_works_search_vector ON public_works"
        )
        op.execute("DROP FUNCTION IF EXISTS public.refresh_public_work_search_vector()")
        op.execute("DROP FUNCTION IF EXISTS public.immutable_unaccent(text)")
    else:
        op.drop_index(
            "ix_public_works_search_visibility_published_id",
            table_name="public_works",
        )
        op.drop_index(
            "ix_public_works_author_trgm_public",
            table_name="public_works",
        )
        op.drop_index(
            "ix_public_works_title_trgm_public",
            table_name="public_works",
        )
        op.drop_index(
            "ix_public_works_search_vector_public",
            table_name="public_works",
        )
    op.drop_column("public_works", "search_vector")
    for column_name in reversed(HELPER_COLUMNS):
        op.drop_column("public_works", column_name)
