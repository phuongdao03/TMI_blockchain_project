from typing import cast

from sqlalchemy import Table, UniqueConstraint

from app.modules.dossiers.models import (
    Dossier,
    DossierEvidence,
    DossierType,
    DossierTypeVersion,
    EvidenceVisibility,
)
from app.modules.reviews.models import Review, ReviewAssignment


def test_dossier_supports_versioned_dynamic_types() -> None:
    assert {
        "dossier_type_id",
        "dossier_type_version_id",
        "form_data_json",
    }.issubset(Dossier.__table__.c.keys())

    assert {"category_id", "code", "name", "is_active"}.issubset(
        DossierType.__table__.c.keys()
    )
    assert {"dossier_type_id", "version_no", "schema_json"}.issubset(
        DossierTypeVersion.__table__.c.keys()
    )
    version_table = cast(Table, DossierTypeVersion.__table__)
    assert any(
        isinstance(constraint, UniqueConstraint)
        and {column.name for column in constraint.columns}
        == {"dossier_type_id", "version_no"}
        for constraint in version_table.constraints
    )


def test_evidence_has_explicit_role_and_visibility() -> None:
    assert {item.value for item in EvidenceVisibility} == {
        "PUBLIC",
        "PRIVATE",
        "INTERNAL",
        "PUBLIC_PREVIEW",
        "REVIEWER_ONLY",
        "ADMIN_ONLY",
    }
    assert {"evidence_role", "access_scope"}.issubset(
        DossierEvidence.__table__.c.keys()
    )


def test_review_separates_internal_and_applicant_feedback() -> None:
    assert "is_primary" in ReviewAssignment.__table__.c
    assignments_table = cast(Table, ReviewAssignment.__table__)
    assert any(
        index.unique
        and {column.name for column in index.columns} == {"dossier_version_id"}
        and index.dialect_options["postgresql"].get("where") is not None
        for index in assignments_table.indexes
    )
    assert {"checklist_answers", "applicant_feedback", "private_note"}.issubset(
        Review.__table__.c.keys()
    )
