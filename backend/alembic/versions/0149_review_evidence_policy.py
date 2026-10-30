"""Publish evidence decision policy in new built-in template versions.

Existing templates, dossiers, snapshots, reviews and payment rules are unchanged.
"""

from copy import deepcopy
from uuid import UUID, uuid5

import sqlalchemy as sa

from alembic import op

revision = "0149_review_evidence_policy"
down_revision = "0148_promotion_distribution_media"
branch_labels = None
depends_on = None

NAMESPACE = UUID("e92ba559-dd45-4579-998f-eed45b08c690")
BUILTIN_CODES = (
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


def _tables() -> tuple[sa.TableClause, sa.TableClause]:
    types = sa.table(
        "dossier_types", sa.column("id", sa.Uuid()), sa.column("code", sa.String())
    )
    versions = sa.table(
        "dossier_type_versions",
        sa.column("id", sa.Uuid()),
        sa.column("dossier_type_id", sa.Uuid()),
        sa.column("version_no", sa.Integer()),
        sa.column("schema_json", sa.JSON()),
    )
    return types, versions


def upgrade() -> None:
    types, versions = _tables()
    bind = op.get_bind()
    for type_id in bind.scalars(
        sa.select(types.c.id).where(types.c.code.in_(BUILTIN_CODES))
    ):
        latest = bind.execute(
            sa.select(versions.c.version_no, versions.c.schema_json)
            .where(versions.c.dossier_type_id == type_id)
            .order_by(versions.c.version_no.desc())
            .limit(1)
        ).first()
        if latest is None:
            continue
        schema = deepcopy(latest.schema_json)
        rubric = schema.get("reviewRubric") if isinstance(schema, dict) else None
        if not isinstance(rubric, dict) or rubric.get("assessmentMethod") != "VERDICT":
            continue
        rubric["version"] = f"{str(rubric['version'])[:96]}.evidence-2026.1"
        rubric["evidencePolicyVersion"] = "2026.1"
        for criterion in rubric["criteria"]:
            criterion.setdefault("allowNotApplicable", False)
            criterion.setdefault("verificationRequired", False)
        bind.execute(
            versions.insert().values(
                id=uuid5(NAMESPACE, str(type_id)),
                dossier_type_id=type_id,
                version_no=latest.version_no + 1,
                schema_json=schema,
            )
        )


def downgrade() -> None:
    types, versions = _tables()
    bind = op.get_bind()
    ids = [
        uuid5(NAMESPACE, str(value)) for value in bind.scalars(sa.select(types.c.id))
    ]
    dossiers = sa.table("dossiers", sa.column("dossier_type_version_id", sa.Uuid()))
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(dossiers)
        .where(dossiers.c.dossier_type_version_id.in_(ids))
    ):
        raise RuntimeError(
            "Evidence-policy templates are in use; retain them and roll forward."
        )
    preparations = sa.table(
        "dossier_preparations", sa.column("payload_json", sa.JSON())
    )
    id_strings = {identifier.hex for identifier in ids}
    if bind.scalar(
        sa.select(sa.func.count())
        .select_from(preparations)
        .where(
            sa.func.lower(
                sa.func.replace(
                    preparations.c.payload_json["dossierTypeVersionId"].as_string(),
                    "-",
                    "",
                )
            ).in_(id_strings)
        )
    ):
        raise RuntimeError(
            "Evidence-policy templates are in use by saved preparations; "
            "retain them and roll forward."
        )
    bind.execute(versions.delete().where(versions.c.id.in_(ids)))
