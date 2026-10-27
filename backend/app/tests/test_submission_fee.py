import asyncio
from dataclasses import replace
from datetime import timedelta
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import func, select

from app.modules.auth.security import OutboxPayloadCipher
from app.modules.billing.models import (
    PriceCatalogEntry,
    PriceCatalogStatus,
    PriceCatalogVersion,
)
from app.modules.dossiers.errors import DossierForbiddenError, DossierInvalidStateError
from app.modules.dossiers.models import Dossier, DossierStatus, DossierType
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


def test_submission_charge_is_once_and_payment_enters_review_not_issuance() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service(
            submission_fee_amount_minor=5_000_000
        )
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(service, principal, media)
        submitted = await service.submit_dossier(
            principal, draft.id, idempotency_key="submit-once"
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


def test_catalog_price_is_snapshotted_and_another_owner_cannot_retry() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner, media = await _build_service(
            submission_fee_amount_minor=5_000_000
        )
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(service, principal, media)
        type_id, catalog_id, price_id = uuid4(), uuid4(), uuid4()
        async with sessions() as session:
            stored = await session.get(Dossier, draft.id)
            assert stored is not None
            session.add(
                DossierType(
                    id=type_id,
                    category_id=stored.category_id,
                    code="FEE-TEST",
                    name="Fee test",
                )
            )
            session.add(
                PriceCatalogVersion(
                    id=catalog_id,
                    version_no=1,
                    status=PriceCatalogStatus.PUBLISHED,
                    effective_from=NOW - timedelta(days=1),
                    published_at=NOW - timedelta(days=1),
                )
            )
            await session.flush()
            session.add(
                PriceCatalogEntry(
                    id=price_id,
                    catalog_version_id=catalog_id,
                    dossier_type_id=type_id,
                    service_code="STANDARD",
                    display_name="Configured fee",
                    amount_minor=6_000_000,
                    currency="VND",
                    tax_mode="UNSPECIFIED",
                )
            )
            stored.dossier_type_id = type_id
            await session.commit()
        quote = await service.submission_fee_quote(principal, draft.id)
        assert quote["amountMinor"] == 6_000_000
        await service.submit_dossier(
            principal, draft.id, idempotency_key="submit-priced"
        )
        async with sessions() as session:
            price = await session.get(PriceCatalogEntry, price_id)
            assert price is not None
            price.amount_minor = 7_000_000
            await session.commit()
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
        service, sessions, engine, owner, media = await _build_service(
            submission_fee_amount_minor=5_000_000
        )
        principal = _principal(owner)
        draft, _ = await _draft_with_evidence(service, principal, media)
        await service.submit_dossier(principal, draft.id, idempotency_key="submit")
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
