import asyncio
import hashlib
import hmac
import json
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.auth.models import User, UserStatus
from app.modules.auth.session_service import AuthPrincipal
from app.modules.billing.models import FeeObligation, FeeObligationStatus
from app.modules.dossiers.models import Category, Dossier, DossierStatus
from app.modules.media.models import MediaAsset  # noqa: F401
from app.modules.payments.gateway import MockPaymentGateway, ProviderOrder
from app.modules.payments.models import PaymentStatus
from app.modules.payments.service import PaymentService

NOW = datetime(2026, 8, 30, 10, 0, tzinfo=UTC)


class ProviderRecheckGateway(MockPaymentGateway):
    paid = False
    create_count = 0

    async def create_order(self, **kwargs: object) -> ProviderOrder:
        self.create_count += 1
        return await super().create_order(**kwargs)  # type: ignore[arg-type]

    async def get_order(self, provider_order_id: str) -> ProviderOrder:
        order = await super().get_order(provider_order_id)
        if not self.paid:
            return order
        return ProviderOrder(
            provider_order_id=order.provider_order_id,
            checkout_url=order.checkout_url,
            qr_payload=order.qr_payload,
            status="PAID",
            order_code=order.order_code,
            amount_minor=1_750_000,
            currency="VND",
        )


def test_owner_checkout_uses_locked_obligation_amount_and_replays() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="checkout-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="CHECKOUT", name="Checkout")
        dossier = Dossier(
            id=uuid4(),
            code="DOS-CHECKOUT",
            owner_user_id=owner.id,
            category_id=category.id,
            title="Checkout dossier",
        )
        dossier._set_status_from_workflow(DossierStatus.PAYMENT_PENDING)
        obligation = FeeObligation(
            id=uuid4(),
            dossier_id=dossier.id,
            owner_user_id=owner.id,
            price_catalog_version_id=uuid4(),
            price_catalog_entry_id=uuid4(),
            service_code="STANDARD",
            description="Phí xác lập và phát hành chứng thư",
            amount_minor=1_750_000,
            currency="VND",
            tax_mode="UNSPECIFIED",
            status=FeeObligationStatus.OPEN,
            due_at=NOW + timedelta(days=7),
            price_snapshot_json={"amountMinor": 1_750_000},
        )
        async with sessions() as session:
            session.add_all([owner, category, dossier, obligation])
            await session.commit()

        ids = iter(
            (
                UUID("30000000-0000-4000-8000-000000000001"),
                UUID("30000000-0000-4000-8000-000000000002"),
            )
        )
        service = PaymentService(
            session=sessions(),
            gateway=MockPaymentGateway(
                webhook_secret="payment-secret",
                uuid_factory=lambda: "billing-checkout",
            ),
            provider_name="mock",
            amount_minor=999_999,
            currency="VND",
            order_ttl_seconds=1_800,
            clock=lambda: NOW,
            uuid_factory=lambda: next(ids),
        )
        principal = AuthPrincipal(
            user_id=owner.id,
            session_id=uuid4(),
            email=owner.email,
            roles=("USER",),
        )

        obligation_view = await service.get_fee_obligation_for_dossier(
            principal, dossier.id
        )
        assert obligation_view.id == obligation.id
        assert obligation_view.amount_minor == 1_750_000

        first = await service.create_checkout_for_obligation(
            principal,
            obligation.id,
            idempotency_key="checkout-obligation-1",
        )
        replay = await service.create_checkout_for_obligation(
            principal,
            obligation.id,
            idempotency_key="checkout-obligation-1",
        )

        assert first.id == replay.id
        assert first.fee_obligation_id == obligation.id
        assert first.amount_minor == 1_750_000
        assert first.status is PaymentStatus.PENDING
        assert first.expires_at == NOW + timedelta(minutes=30)
        timestamp = int(NOW.timestamp())
        body = json.dumps(
            {
                "event_id": "billing-paid-1",
                "event_type": "payment.paid",
                "provider_order_id": "mock-billing-checkout",
                "amount_minor": 1_750_000,
                "currency": "VND",
            },
            separators=(",", ":"),
        ).encode()
        signature = hmac.new(
            b"payment-secret",
            str(timestamp).encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        paid = await service.process_webhook(
            raw_body=body,
            signature=signature,
            timestamp=timestamp,
        )
        async with sessions() as session:
            settled = await session.get(FeeObligation, obligation.id)
        assert paid.status is PaymentStatus.PAID
        assert settled is not None
        assert settled.status is FeeObligationStatus.PAID
        assert settled.paid_at is not None
        assert settled.paid_at.replace(tzinfo=UTC) == NOW
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_expired_checkout_rechecks_provider_before_replacement() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        owner = User(
            id=uuid4(),
            email="recheck-owner@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        category = Category(id=uuid4(), code="RECHECK", name="Recheck")
        dossier = Dossier(
            id=uuid4(),
            code="DOS-RECHECK",
            owner_user_id=owner.id,
            category_id=category.id,
            title="Recheck dossier",
        )
        dossier._set_status_from_workflow(DossierStatus.PAYMENT_PENDING)
        obligation = FeeObligation(
            id=uuid4(),
            dossier_id=dossier.id,
            owner_user_id=owner.id,
            price_catalog_version_id=uuid4(),
            price_catalog_entry_id=uuid4(),
            service_code="STANDARD",
            description="Phí xác lập và phát hành chứng thư",
            amount_minor=1_750_000,
            currency="VND",
            tax_mode="UNSPECIFIED",
            status=FeeObligationStatus.OPEN,
            due_at=NOW + timedelta(days=7),
            price_snapshot_json={"amountMinor": 1_750_000},
        )
        async with sessions() as session:
            session.add_all([owner, category, dossier, obligation])
            await session.commit()
        gateway = ProviderRecheckGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "recheck"
        )
        current = [NOW]
        service = PaymentService(
            session=sessions(),
            gateway=gateway,
            provider_name="mock",
            amount_minor=999_999,
            currency="VND",
            order_ttl_seconds=60,
            clock=lambda: current[0],
            uuid_factory=lambda: uuid4(),
        )
        principal = AuthPrincipal(
            user_id=owner.id,
            session_id=uuid4(),
            email=owner.email,
            roles=("USER",),
        )
        first = await service.create_checkout_for_obligation(
            principal, obligation.id, idempotency_key="recheck-first"
        )
        current[0] = NOW + timedelta(seconds=61)
        gateway.paid = True

        resolved = await service.create_checkout_for_obligation(
            principal, obligation.id, idempotency_key="recheck-second"
        )

        assert resolved.id == first.id
        assert resolved.status is PaymentStatus.PAID
        assert gateway.create_count == 1
        async with sessions() as session:
            settled = await session.get(FeeObligation, obligation.id)
            stored_dossier = await session.get(Dossier, dossier.id)
        assert settled is not None
        assert settled.status is FeeObligationStatus.PAID
        assert stored_dossier is not None
        assert stored_dossier.status is DossierStatus.PAID
        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
