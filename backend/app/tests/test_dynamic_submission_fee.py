import asyncio
from datetime import timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.modules.auth.models import User, UserStatus
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.fees import FeePolicyService
from app.modules.billing.models import (
    FeeObligation,
    FeeObligationStatus,
    FeeWaiver,
    FeeWaiverStatus,
)
from app.modules.dossiers.models import Dossier, DossierStatus, DossierType
from app.modules.dossiers.schemas import SubmissionFeeQuoteData
from app.modules.payments.models import PaymentOrder
from app.tests.test_dossier_submission import (
    NOW,
    _build_service,
    _draft_with_evidence,
    _principal,
)


async def _install_policy(service, sessions, owner, dossier_id, *, amount_minor):
    async with sessions() as session:
        stored = await session.get(Dossier, dossier_id)
        assert stored is not None
        category_id = stored.category_id
    admin = User(
        id=uuid4(),
        email=f"fee-approver-{uuid4().hex}@example.test",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    dossier_type = DossierType(
        id=uuid4(),
        category_id=category_id,
        code=f"FEE-{uuid4().hex[:8].upper()}",
        name="Dynamic fee test",
    )
    async with sessions() as session:
        dossier = await session.get(Dossier, dossier_id)
        session.add_all([admin, dossier_type])
        assert dossier is not None
        dossier.dossier_type_id = dossier_type.id
        await session.commit()
    async with sessions() as session:
        policies = FeePolicyService(session, clock=lambda: service._clock())
        draft = await policies.create_draft(
            actor_user_id=owner.id,
            fee_type="DOSSIER_SUBMISSION",
            dossier_type_id=dossier_type.id,
            amount_minor=amount_minor,
            starts_at=NOW,
            ends_at=None,
            reason="Test approved policy",
        )
        approved = await policies.approve(draft.id, actor_user_id=admin.id)
    return admin, dossier_type, approved


def test_quote_is_read_only_and_submit_requires_current_policy_consent() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        _, _, policy = await _install_policy(
            service, sessions, owner, draft.id, amount_minor=5_000_000
        )

        quote = await service.submission_fee_quote(principal, draft.id)
        assert quote["amountMinor"] == 5_000_000
        assert quote["policyVersionNo"] == 1
        async with sessions() as session:
            assert await session.scalar(select(func.count(FeeObligation.id))) == 0
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 0

        with pytest.raises(PriceCatalogConflictError) as stale:
            await service.submit_dossier(
                principal, draft.id, idempotency_key="needs-consent"
            )
        assert stale.value.code == "FEE_QUOTE_STALE"
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None and stored.status is DossierStatus.DRAFT

        submitted = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="consented-submit",
            accepted_fee_policy_version=1,
        )
        assert submitted.dossier.status is DossierStatus.PAYMENT_PENDING
        async with sessions() as session:
            obligation = await session.scalar(select(FeeObligation))
            order = await session.scalar(select(PaymentOrder))
            assert obligation is not None and order is not None
            assert obligation.fee_type == "DOSSIER_SUBMISSION"
            assert obligation.fee_policy_id == policy.id
            assert obligation.fee_policy_version_no == 1
            assert obligation.gross_amount_minor == 5_000_000
            assert obligation.waiver_amount_minor == 0
            assert obligation.amount_minor == order.amount_minor == 5_000_000
            assert order.fee_obligation_id == obligation.id
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_missing_policy_fails_closed_without_free_submission() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None
            dossier_type = DossierType(
                id=uuid4(),
                category_id=stored.category_id,
                code=f"NOFEE-{uuid4().hex[:8]}",
                name="No policy test",
            )
            session.add(dossier_type)
            stored.dossier_type_id = dossier_type.id
            await session.commit()

        quote = await service.submission_fee_quote(principal, draft.id)
        assert quote["feeAvailable"] is False
        assert quote["feeRequired"] is True
        assert SubmissionFeeQuoteData.model_validate(quote).fee_available is False
        with pytest.raises(PriceCatalogConflictError) as unavailable:
            await service.submit_dossier(
                principal,
                draft.id,
                idempotency_key="no-policy-submit",
                accepted_fee_policy_version=None,
            )
        assert unavailable.value.code == "FEE_POLICY_UNAVAILABLE"
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None and stored.status is DossierStatus.DRAFT
            assert await session.scalar(select(func.count(FeeObligation.id))) == 0
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_stale_preview_requotes_without_changing_old_obligation_amount() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        admin, dossier_type, first = await _install_policy(
            service, sessions, owner, draft.id, amount_minor=5_000_000
        )
        service._clock = lambda: NOW + timedelta(days=1)
        async with sessions() as session:
            policies = FeePolicyService(session, clock=lambda: service._clock())
            second_draft = await policies.create_draft(
                actor_user_id=owner.id,
                fee_type="DOSSIER_SUBMISSION",
                dossier_type_id=dossier_type.id,
                amount_minor=6_000_000,
                starts_at=NOW + timedelta(days=1),
                ends_at=None,
                reason="Scheduled rate change",
            )
            second = await policies.approve(second_draft.id, actor_user_id=admin.id)
        with pytest.raises(PriceCatalogConflictError) as stale:
            await service.submit_dossier(
                principal,
                draft.id,
                idempotency_key="stale-consent",
                accepted_fee_policy_version=first.version_no,
            )
        assert stale.value.details["currentQuote"]["policyVersionNo"] == 2
        submitted = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="new-consent",
            accepted_fee_policy_version=second.version_no,
        )
        assert submitted.dossier.status is DossierStatus.PAYMENT_PENDING
        async with sessions() as session:
            obligation = await session.scalar(select(FeeObligation))
            assert obligation is not None
            assert obligation.fee_policy_id == second.id
            assert obligation.amount_minor == 6_000_000
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_full_waiver_is_approved_separately_and_redeemed_once() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        admin, _, policy = await _install_policy(
            service, sessions, owner, draft.id, amount_minor=5_000_000
        )
        async with sessions() as session:
            policies = FeePolicyService(session, clock=lambda: service._clock())
            waiver = await policies.request_waiver(
                dossier_id=draft.id,
                fee_type="DOSSIER_SUBMISSION",
                amount_minor=5_000_000,
                reason="Approved exception test",
                actor_user_id=owner.id,
            )
            with pytest.raises(PriceCatalogConflictError, match="different approver"):
                await policies.decide_waiver(
                    waiver.id, actor_user_id=owner.id, approve=True
                )
            approved = await policies.decide_waiver(
                waiver.id, actor_user_id=admin.id, approve=True
            )
            assert approved.status is FeeWaiverStatus.APPROVED

        submitted = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="waived-submit",
            accepted_fee_policy_version=policy.version_no,
        )
        assert submitted.dossier.status is DossierStatus.SUBMITTED
        async with sessions() as session:
            obligation = await session.scalar(select(FeeObligation))
            stored = await session.get(Dossier, draft.id)
            stored_waiver = await session.scalar(select(FeeWaiver))
            assert (
                obligation is not None
                and obligation.status is FeeObligationStatus.WAIVED
            )
            assert obligation.amount_minor == 0
            assert obligation.gross_amount_minor == 5_000_000
            assert obligation.waiver_amount_minor == 5_000_000
            assert stored is not None and stored.submission_fee_waived_at is not None
            assert stored_waiver is not None
            assert stored_waiver.status is FeeWaiverStatus.REDEEMED
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
