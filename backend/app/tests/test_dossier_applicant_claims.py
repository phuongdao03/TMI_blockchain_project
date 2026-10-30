import asyncio
from uuid import uuid4

import pytest

from app.modules.billing import models as billing_models  # noqa: F401
from app.modules.dossiers.errors import DossierInvalidStateError, DossierValidationError
from app.modules.dossiers.models import Dossier, DossierType, DossierTypeVersion
from app.modules.dossiers.service import DossierService
from app.modules.dossiers.types import CreateDossier, CreateEvidence, DossierClaim
from app.tests.test_dossier_submission import CATEGORY_ID, _build_service, _principal


def test_claims_are_revision_checked_bound_to_evidence_and_frozen() -> None:
    async def exercise() -> None:
        service, factory, engine, user, media = await _build_service()
        principal = _principal(user)
        dossier = await service.create_dossier(
            principal, CreateDossier(category_id=CATEGORY_ID, title="Claim dossier")
        )
        type_id, version_id = uuid4(), uuid4()
        async with factory() as session:
            session.add(
                DossierType(
                    id=type_id,
                    category_id=CATEGORY_ID,
                    code="CLAIM_TEST",
                    name="Claim test",
                )
            )
            session.add(
                DossierTypeVersion(
                    id=version_id,
                    dossier_type_id=type_id,
                    version_no=1,
                    schema_json={
                        "fields": [],
                        "reviewRubric": {
                            "version": "1",
                            "assessmentMethod": "VERDICT",
                            "title": "Review",
                            "gates": [],
                            "criteria": [
                                {
                                    "key": "origin",
                                    "label": "Origin",
                                    "description": "Compare origin",
                                }
                            ],
                        },
                    },
                )
            )
            row = await session.get(Dossier, dossier.id)
            row.dossier_type_id = type_id
            row.dossier_type_version_id = version_id
            await session.commit()
        await service.attach_evidence(
            principal,
            dossier.id,
            CreateEvidence(
                media_asset_id=media.id,
                evidence_type="PRIMARY",
                title="Source manuscript",
            ),
        )
        pinned = await service.get_active_dossier_type_version(principal, version_id)
        assert pinned.id == version_id
        claim = DossierClaim(
            id=uuid4(),
            criterion_key="origin",
            statement="The original manuscript records the creation process.",
            evidence_media_ids=(media.id,),
        )
        saved = await service.replace_claims(
            principal, dossier.id, expected_revision=0, claims=(claim,)
        )
        assert saved.claims_revision == 1
        assert saved.claims == (claim,)
        with pytest.raises(DossierInvalidStateError, match="changed"):
            await service.replace_claims(
                principal, dossier.id, expected_revision=0, claims=()
            )
        invalid = DossierClaim(
            id=uuid4(),
            criterion_key="origin",
            statement="Source belonging to another dossier",
            evidence_media_ids=(uuid4(),),
        )
        with pytest.raises(DossierValidationError, match="evidence"):
            await service.replace_claims(
                principal, dossier.id, expected_revision=1, claims=(invalid,)
            )
        submitted = await service.submit_dossier(
            principal, dossier.id, idempotency_key="claims-test-submit"
        )
        frozen = submitted.version.snapshot_json["dossier"]["claims"]
        assert frozen[0]["statement"] == claim.statement
        assert frozen[0]["evidenceMediaIds"] == [str(media.id)]
        with pytest.raises(DossierInvalidStateError):
            await service.replace_claims(
                principal, dossier.id, expected_revision=1, claims=()
            )
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


@pytest.mark.parametrize(
    "problem",
    ["criterion", "foreign_media", "duplicate_id", "duplicate_media", "incomplete"],
)
def test_claim_boundary_rejects_invalid_or_unproven_submission(problem: str) -> None:
    media_id = uuid4()
    claim = DossierClaim(
        id=uuid4(),
        criterion_key="origin",
        statement="Original statement documented by the manuscript.",
        evidence_media_ids=(media_id,),
    )
    claims = (claim,)
    if problem == "criterion":
        claim = DossierClaim(
            id=claim.id, criterion_key="not_in_rubric", statement=claim.statement
        )
        claims = (claim,)
    elif problem == "foreign_media":
        claims = (
            DossierClaim(
                id=claim.id,
                criterion_key="origin",
                statement=claim.statement,
                evidence_media_ids=(uuid4(),),
            ),
        )
    elif problem == "duplicate_id":
        claims = (claim, claim)
    elif problem == "duplicate_media":
        claims = (
            DossierClaim(
                id=claim.id,
                criterion_key="origin",
                statement=claim.statement,
                evidence_media_ids=(media_id, media_id),
            ),
        )
    elif problem == "incomplete":
        claims = (DossierClaim(id=claim.id, criterion_key="origin", statement="Draft"),)
    with pytest.raises(DossierValidationError):
        DossierService._validated_claims(
            claims,
            schema={"reviewRubric": {"criteria": [{"key": "origin"}]}},
            evidence_ids={media_id},
            complete=True,
        )
