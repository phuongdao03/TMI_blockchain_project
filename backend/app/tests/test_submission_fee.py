import asyncio
from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from fastapi.routing import APIRoute
from sqlalchemy import func, select

from app.api.v1.dossiers import router as dossier_router
from app.db.outbox import OutboxEvent
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.fees import FeePolicyService
from app.modules.billing.models import (
    FeeObligation,
    FeeObligationStatus,
    FeePolicy,
)
from app.modules.dossiers.errors import DossierForbiddenError, DossierInvalidStateError
from app.modules.dossiers.models import (
    Dossier,
    DossierStatus,
    DossierType,
    DossierVersion,
)
from app.modules.dossiers.types import CreateEvidence
from app.modules.payments.errors import PaymentNotFoundError
from app.modules.payments.gateway import MockPaymentGateway
from app.modules.payments.models import PaymentOrder
from app.modules.payments.service import PaymentService
from app.modules.reviews.precheck_service import PrecheckService
from app.modules.wallet.models import Wallet, WalletJournal
from app.tests.test_dossier_submission import (
    NOW,
    _build_service,
    _draft_with_evidence,
    _principal,
)


async def _install_policy(service, sessions, owner, dossier_id, amount_minor):
    async with sessions() as session:
        dossier = await session.get(Dossier, dossier_id)
        assert dossier is not None
        category_id = dossier.category_id
    approver = User(
        id=uuid4(),
        email=f"fee-approver-{uuid4().hex}@example.test",
        password_hash="not-used",
        status=UserStatus.ACTIVE,
    )
    dossier_type = DossierType(
        id=uuid4(),
        category_id=category_id,
        code=f"FEE-{uuid4().hex[:8].upper()}",
        name="Submission fee test",
    )
    async with sessions() as session:
        dossier = await session.get(Dossier, dossier_id)
        session.add_all([approver, dossier_type])
        assert dossier is not None
        dossier.dossier_type_id = dossier_type.id
        await session.commit()
    async with sessions() as session:
        policies = FeePolicyService(session, clock=lambda: service._clock())
        draft = await policies.create_draft(
            actor_user_id=owner.id,
            fee_type="DOSSIER_SUBMISSION",
            dossier_type_id=None,
            amount_minor=amount_minor,
            starts_at=NOW,
            ends_at=None,
            reason="Test fee policy",
        )
        return await policies.approve(
            draft.id,
            actor_user_id=approver.id,
            confirm_activation=True,
        )


def test_submission_charge_is_once_and_payment_enters_review_not_issuance() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        cipher = OutboxPayloadCipher(key=b"x" * 32, key_id="test-only")
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        policy = await _install_policy(service, sessions, owner, draft.id, 5_000_000)
        submitted = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="submit-once",
            accepted_fee_policy_version=policy.version_no,
        )
        replay = await service.submit_dossier(
            principal, draft.id, idempotency_key="submit-once"
        )
        assert submitted.dossier.status is DossierStatus.PAYMENT_PENDING
        assert replay.version.id == submitted.version.id
        precheck = PrecheckService(
            session=sessions(),
            payload_cipher=OutboxPayloadCipher(key=b"x" * 32, key_id="test-only"),
        )
        with pytest.raises(DossierInvalidStateError, match="fee must be paid"):
            await precheck.start_precheck(
                replace(principal, roles=("SUPER_ADMIN",)),
                draft.id,
                reason="Check paid intake",
            )
        async with sessions() as session:
            orders = tuple((await session.scalars(select(PaymentOrder))).all())
            assert len(orders) == 1
            order = orders[0]
            assert order.provider == "wallet"
            assert order.amount_minor == 5_000_000
            stored_dossier = await session.get(Dossier, draft.id)
            version = await session.scalar(select(DossierVersion))
            assert stored_dossier is not None and stored_dossier.submitted_at is None
            assert version is not None and version.submitted_at is None
            assert await session.scalar(select(func.count(OutboxEvent.id))) == 0
            session.add(Wallet(user_id=owner.id, balance_minor=6_000_000))
            await session.commit()
        issue = Mock()
        payment = PaymentService(
            session=sessions(),
            gateway=MockPaymentGateway(webhook_secret="payment-secret"),
            provider_name="mock",
            amount_minor=1_000_000,
            currency="VND",
            order_ttl_seconds=3600,
            clock=lambda: NOW,
            enqueue_certificate_issue=issue,
            payload_cipher=cipher,
        )
        from app.tests.test_payment_service import _webhook

        body, signature, timestamp = _webhook(
            amount_minor=5_000_000, order_code=order.order_code
        )
        with pytest.raises(PaymentNotFoundError):
            await payment.process_webhook(
                raw_body=body, signature=signature, timestamp=timestamp
            )
        await payment.pay_with_wallet(
            principal, order.id, idempotency_key="wallet-once"
        )
        await payment.pay_with_wallet(
            principal, order.id, idempotency_key="wallet-once"
        )
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None and stored.status is DossierStatus.SUBMITTED
            assert stored.submission_fee_paid_at is not None
            assert stored.submitted_at == stored.submission_fee_paid_at
            assert await session.scalar(select(func.count(OutboxEvent.id))) == 1
            version = await session.scalar(select(DossierVersion))
            assert version is not None and version.submitted_at == stored.submitted_at
            assert (await session.get(Wallet, owner.id)).balance_minor == 1_000_000
            assert await session.scalar(select(func.count(WalletJournal.id))) == 1
            stored._set_status_from_workflow(DossierStatus.NEEDS_SUPPLEMENT)
            await session.commit()
        await service.attach_evidence(
            principal,
            draft.id,
            CreateEvidence(
                media_asset_id=media.id,
                evidence_type="OWNERSHIP_DOCUMENT",
                title="Updated evidence",
            ),
        )
        supplemented = await service.resubmit_dossier(
            principal, draft.id, idempotency_key="supplement"
        )
        assert supplemented.dossier.status is DossierStatus.SUBMITTED
        async with sessions() as session:
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 1
        issue.assert_not_called()
        await payment.close()
        await precheck.close()
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_existing_user_exemption_waives_only_submission_fee_without_payment() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service,
            principal,
            media,
            fee_policy_mode="DYNAMIC",
            title="Existing account fee exemption",
        )
        policy = await _install_policy(service, sessions, owner, draft.id, 5_000_000)
        async with sessions() as session:
            user = await session.get(User, owner.id)
            assert user is not None and not user.is_test_account
            user.submission_fee_test_exemption = True
            await session.commit()
        quote = await service.submission_fee_quote(principal, draft.id)
        assert quote["feeRequired"] is False
        assert quote["feeAvailable"] is True
        assert quote["feeWaived"] is True
        assert quote["amountMinor"] == 0
        assert quote["grossAmountMinor"] == 5_000_000
        assert quote["waiverReason"] == "TEST_SUBMISSION_FEE_EXEMPTION"

        submitted = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="existing-user-exempt-submit",
            accepted_fee_policy_version=policy.version_no,
            expected_fee_test_exemption=True,
        )
        replay = await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="existing-user-exempt-submit",
            expected_fee_test_exemption=True,
        )
        assert submitted.dossier.status is DossierStatus.SUBMITTED
        assert replay.version.id == submitted.version.id
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None
            assert not stored.is_test and stored.status is DossierStatus.SUBMITTED
            assert stored.submission_fee_waived_at is not None
            assert stored.submission_fee_paid_at is None
            assert stored.submission_fee_snapshot is not None
            assert (
                stored.submission_fee_snapshot["waiverReason"]
                == "TEST_SUBMISSION_FEE_EXEMPTION"
            )
            obligation = await session.scalar(select(FeeObligation))
            assert obligation is not None
            assert obligation.status is FeeObligationStatus.WAIVED
            assert obligation.amount_minor == 0
            assert obligation.gross_amount_minor == 5_000_000
            assert obligation.price_snapshot_json["waiverReason"] == (
                "TEST_SUBMISSION_FEE_EXEMPTION"
            )
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 0
            assert await session.scalar(select(func.count(WalletJournal.id))) == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_submission_rechecks_exemption_and_rejects_stale_waived_quote() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        policy = await _install_policy(service, sessions, owner, draft.id, 5_000_000)
        async with sessions() as session:
            user = await session.get(User, owner.id)
            assert user is not None
            user.submission_fee_test_exemption = True
            await session.commit()
        waived_quote = await service.submission_fee_quote(principal, draft.id)
        assert waived_quote["feeWaived"] is True
        async with sessions() as session:
            user = await session.get(User, owner.id)
            assert user is not None
            user.submission_fee_test_exemption = False
            await session.commit()

        with pytest.raises(PriceCatalogConflictError) as error:
            await service.submit_dossier(
                principal,
                draft.id,
                idempotency_key="exemption-was-revoked",
                accepted_fee_policy_version=policy.version_no,
                expected_fee_test_exemption=True,
            )
        assert error.value.code == "FEE_QUOTE_STALE"
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_submission_api_does_not_accept_test_payment_mode() -> None:
    route = next(
        route
        for route in dossier_router.routes
        if isinstance(route, APIRoute) and route.endpoint.__name__ == "submit_dossier"
    )
    header_names = {field.alias for field in route.dependant.header_params}
    assert "X-Test-Payment-Mode" not in header_names
    assert "X-Submission-Fee-Test-Exemption" in header_names


def test_catalog_price_is_snapshotted_and_another_owner_cannot_retry() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        policy = await _install_policy(service, sessions, owner, draft.id, 6_000_000)
        quote = await service.submission_fee_quote(principal, draft.id)
        assert quote["amountMinor"] == 6_000_000
        await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="submit-priced",
            accepted_fee_policy_version=policy.version_no,
        )
        async with sessions() as session:
            obligation = await session.scalar(select(FeeObligation))
            assert obligation is not None
            assert obligation.gross_amount_minor == 6_000_000
            policy_row = await session.get(FeePolicy, policy.id)
            assert policy_row is not None and policy_row.amount_minor == 6_000_000
        assert (await service.submission_fee_quote(principal, draft.id))[
            "amountMinor"
        ] == 6_000_000
        with pytest.raises(DossierForbiddenError):
            await service.retry_submission_payment(
                replace(principal, user_id=uuid4()), draft.id, key="forbidden"
            )
        async with sessions() as session:
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 1
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_cancel_and_expiry_keep_review_locked_and_retry_preserves_price() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service()
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(
            service, principal, media, fee_policy_mode="DYNAMIC"
        )
        policy = await _install_policy(service, sessions, owner, draft.id, 5_000_000)
        await service.submit_dossier(
            principal,
            draft.id,
            idempotency_key="submit",
            accepted_fee_policy_version=policy.version_no,
        )
        async with sessions() as session:
            order = await session.scalar(select(PaymentOrder))
            assert order is not None
        payment = PaymentService(
            session=sessions(),
            gateway=MockPaymentGateway(webhook_secret="test"),
            provider_name="mock",
            amount_minor=1_000_000,
            currency="VND",
            order_ttl_seconds=3600,
            clock=lambda: NOW,
        )
        await payment.cancel_order(
            principal, order.id, reason="Cancel this attempt only"
        )
        retry_id = await service.retry_submission_payment(
            principal, draft.id, key="retry-one"
        )
        assert retry_id != order.id
        assert (
            await service.retry_submission_payment(principal, draft.id, key="retry-one")
            == retry_id
        )
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            retry = await session.get(PaymentOrder, retry_id)
            assert stored is not None and stored.status is DossierStatus.PAYMENT_PENDING
            assert retry is not None and retry.amount_minor == 5_000_000
            retry.expires_at = NOW - timedelta(seconds=1)
            await session.commit()
        replacement_id = await service.retry_submission_payment(
            principal, draft.id, key="retry-expired"
        )
        assert replacement_id != retry_id
        async with sessions() as session:
            assert await session.scalar(select(func.count(WalletJournal.id))) == 0
        await payment.close()
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_prepaid_approval_does_not_create_another_charge() -> None:
    from app.modules.council.models import CouncilCaseDecision
    from app.tests.test_council_session_service import _principal as council_principal
    from app.tests.test_council_session_service import _setup

    async def exercise() -> None:
        service, sessions, engine, users, dossier, _ = await _setup()
        async with sessions() as session:
            stored = await session.get(Dossier, dossier.id)
            assert stored is not None
            stored.submission_fee_required = True
            await session.commit()
        principal = council_principal(users["secretary"], "SUPER_ADMIN")
        from app.modules.council.errors import CouncilConflictError

        with pytest.raises(CouncilConflictError, match="fee must be paid"):
            await service.record_admin_decision(
                principal,
                dossier.id,
                decision=CouncilCaseDecision.APPROVE,
                reason="All review evidence accepted",
                confirm_no_conflict=True,
            )
        async with sessions() as session:
            stored = await session.get(Dossier, dossier.id)
            assert stored is not None and stored.status is DossierStatus.UNDER_REVIEW
            stored.submission_fee_paid_at = NOW
            await session.commit()
        result = await service.record_admin_decision(
            principal,
            dossier.id,
            decision=CouncilCaseDecision.APPROVE,
            reason="All review evidence accepted",
            confirm_no_conflict=True,
        )
        assert result.status is DossierStatus.PAID
        async with sessions() as session:
            assert await session.scalar(select(func.count(PaymentOrder.id))) == 0
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
