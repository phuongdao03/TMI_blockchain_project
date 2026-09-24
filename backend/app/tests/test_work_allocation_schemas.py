from datetime import UTC, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.modules.work_allocations.schemas import (
    CreateWorkAllocationRequest,
    WorkScopeData,
)


def test_work_scope_contract_includes_a_read_only_document_title() -> None:
    scope = WorkScopeData.model_validate(
        {
            "id": uuid4(),
            "allocationId": uuid4(),
            "scopeType": "EVIDENCE",
            "dossierEvidenceId": uuid4(),
            "dossierEvidenceTitle": "Bản thảo chính",
            "groupLabel": None,
            "requiresDualReview": False,
            "createdAt": datetime.now(UTC),
            "updatedAt": datetime.now(UTC),
        }
    )

    assert scope.dossier_evidence_title == "Bản thảo chính"


def test_dossier_allocation_contract_requires_an_immutable_version_and_scope() -> None:
    request = CreateWorkAllocationRequest.model_validate(
        {
            "kind": "DOSSIER_REVIEW",
            "objective": "Thẩm định tài liệu hỗ trợ",
            "dossierId": str(uuid4()),
            "dossierVersionId": str(uuid4()),
            "dueAt": "2026-09-30T17:00:00+07:00",
            "scopes": [
                {
                    "scopeType": "EVIDENCE",
                    "dossierEvidenceId": str(uuid4()),
                    "requiresDualReview": True,
                }
            ],
            "members": [{"userId": str(uuid4()), "responsibility": "REVIEWER"}],
        }
    )

    assert request.dossier_version_id is not None
    assert request.scopes[0].requires_dual_review is True
    assert request.members[0].responsibility.value == "REVIEWER"


@pytest.mark.parametrize(
    "payload",
    [
        {
            "kind": "DOSSIER_REVIEW",
            "objective": "Thiếu phiên bản",
            "dossierId": str(uuid4()),
            "scopes": [],
        },
        {
            "kind": "GENERIC",
            "objective": "Không được gắn hồ sơ",
            "dossierId": str(uuid4()),
        },
        {
            "kind": "DOSSIER_REVIEW",
            "objective": "Không có phạm vi tài liệu",
            "dossierId": str(uuid4()),
            "dossierVersionId": str(uuid4()),
            "scopes": [],
        },
    ],
)
def test_work_allocation_contract_rejects_ambiguous_dossier_scope(
    payload: dict[str, object],
) -> None:
    with pytest.raises(ValidationError):
        CreateWorkAllocationRequest.model_validate(payload)
