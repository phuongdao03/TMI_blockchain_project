"""Add criterion conclusions for verdict-based reviews.

Revision ID: 0073_verdict_based_reviews
Revises: 0072_review_evidence_assessments
Create Date: 2026-09-03
"""

from collections.abc import Mapping, Sequence
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "0073_verdict_based_reviews"
down_revision: str | None = "0072_review_evidence_assessments"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

VERDICT_NAMESPACE = UUID("53ee5673-5fbe-41d3-bd34-c46eeff1aa73")


def _verdict_version_id(dossier_type_id: UUID) -> UUID:
    return uuid5(VERDICT_NAMESPACE, str(dossier_type_id))


def _create_verdict_rubric_versions() -> None:
    dossier_types = sa.table(
        "dossier_types",
        sa.column("id", sa.Uuid()),
    )
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("dossier_type_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("schema_json", sa.JSON()),
    )
    bind = op.get_bind()
    for raw_type_id in bind.scalars(sa.select(dossier_types.c.id)):
        type_id = UUID(str(raw_type_id))
        latest = bind.execute(
            sa.select(versions.c.version_no, versions.c.schema_json)
            .where(versions.c.dossier_type_id == type_id)
            .order_by(versions.c.version_no.desc())
            .limit(1)
        ).first()
        if latest is None or not isinstance(latest.schema_json, dict):
            continue
        rubric = latest.schema_json.get("reviewRubric")
        if not isinstance(rubric, Mapping):
            continue
        criteria = rubric.get("criteria")
        if not isinstance(criteria, list) or not criteria:
            continue
        verdict_criteria = []
        for criterion in criteria:
            if not isinstance(criterion, Mapping):
                continue
            verdict_criteria.append(
                {
                    key: criterion[key]
                    for key in ("key", "label", "description")
                    if key in criterion
                }
            )
        if not verdict_criteria:
            continue
        schema = dict(latest.schema_json)
        schema["reviewRubric"] = {
            "version": "2026.2",
            "title": "Kết luận thẩm định hồ sơ",
            "assessmentMethod": "VERDICT",
            "gates": list(rubric.get("gates", [])),
            "criteria": verdict_criteria,
        }
        bind.execute(
            versions.insert().values(
                id=_verdict_version_id(type_id),
                dossier_type_id=type_id,
                version_no=int(latest.version_no) + 1,
                schema_json=schema,
            )
        )


def _remove_verdict_rubric_versions() -> None:
    dossier_types = sa.table("dossier_types", sa.column("id", sa.Uuid()))
    versions = sa.table("dossier_type_versions", sa.column("id", sa.Uuid()))
    bind = op.get_bind()
    for raw_type_id in bind.scalars(sa.select(dossier_types.c.id)):
        bind.execute(
            versions.delete().where(
                versions.c.id == _verdict_version_id(UUID(str(raw_type_id)))
            )
        )


def upgrade() -> None:
    op.add_column(
        "reviews",
        sa.Column(
            "criterion_verdicts",
            postgresql.JSONB().with_variant(sa.JSON(), "sqlite"),
            nullable=False,
            server_default=sa.text("'{}'"),
        ),
    )
    _create_verdict_rubric_versions()


def downgrade() -> None:
    _remove_verdict_rubric_versions()
    op.drop_column("reviews", "criterion_verdicts")
