import asyncio
from dataclasses import replace
from uuid import uuid4

import pytest

from app.modules.dossiers.errors import (
    DossierForbiddenError,
    DossierInvalidStateError,
    DossierNotFoundError,
    DossierValidationError,
)
from app.modules.dossiers.types import CreateDossier
from app.tests.test_dossier_submission import CATEGORY_ID, _build_service, _principal


def test_prep_revision_and_creation_are_recoverable_without_duplicate_drafts() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, _ = await _build_service()
        principal = _principal(owner)
        assert (await service.get_preparation(principal))["revision"] == 0
        payload = {
            "dossierTypeVersionId": None,
            "step": 1,
            "values": {
                "title": "Incomplete dossier",
                "summary": "Still preparing",
                "visibility": "PRIVATE",
            },
            "formData": {"origin": "Typing"},
        }
        first = await service.save_preparation(
            principal, owner_user_id=owner.id, expected_revision=0, payload=payload
        )
        assert first["revision"] == 1
        assert (await service.get_preparation(principal))["payload"] == payload
        with pytest.raises(DossierInvalidStateError):
            await service.save_preparation(
                principal, owner_user_id=owner.id, expected_revision=0, payload=payload
            )
        with pytest.raises(DossierForbiddenError):
            await service.save_preparation(
                principal, owner_user_id=uuid4(), expected_revision=1, payload=payload
            )
        draft_input = CreateDossier(
            category_id=CATEGORY_ID, title="Incomplete dossier", preparation_revision=1
        )
        with pytest.raises(DossierNotFoundError):
            await service.create_dossier(
                principal, replace(draft_input, category_id=uuid4())
            )
        assert (await service.get_preparation(principal))["revision"] == 1
        created = await service.create_dossier(principal, draft_input)
        replay = await service.create_dossier(principal, draft_input)
        assert created.id == replay.id
        with pytest.raises(DossierInvalidStateError):
            await service.create_dossier(
                principal, replace(draft_input, title="Different request")
            )
        cleared = await service.get_preparation(principal)
        assert cleared["payload"] is None and cleared["revision"] == 2
        with pytest.raises(DossierInvalidStateError):
            await service.save_preparation(
                principal, owner_user_id=owner.id, expected_revision=1, payload=payload
            )
        assert (await service.get_preparation(replace(principal, user_id=uuid4())))[
            "payload"
        ] is None
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_prep_rejects_oversized_json_and_non_applicant_roles() -> None:
    async def exercise() -> None:
        service, _, engine, owner, _ = await _build_service()
        principal = _principal(owner)
        with pytest.raises(DossierValidationError):
            await service.save_preparation(
                principal,
                owner_user_id=owner.id,
                expected_revision=0,
                payload={"text": "x" * 70000},
            )
        with pytest.raises(DossierValidationError):
            await service.save_preparation(
                principal,
                owner_user_id=owner.id,
                expected_revision=0,
                payload={"number": float("nan")},
            )
        with pytest.raises(DossierForbiddenError):
            await service.get_preparation(replace(principal, roles=("VIEWER",)))
        assert (await service.get_preparation(principal))["revision"] == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
