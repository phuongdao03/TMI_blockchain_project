import asyncio
from uuid import uuid4

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.payments.errors import PaymentConflictError
from app.modules.wallet.models import Wallet, WalletJournal
from app.modules.wallet.service import WalletLedger
from app.tests.test_payment_service import DOSSIER_ID, _service, _webhook


def test_gateway_reservation_blocks_a_wallet_payment_during_checkout() -> None:
    from app.modules.auth.session_service import AuthPrincipal
    from app.modules.payments.gateway import MockPaymentGateway
    from app.tests.test_payment_service import ADMIN_ID

    async def exercise() -> None:
        class ProbeGateway(MockPaymentGateway):
            probed = False

            async def create_order(self, **kwargs):
                self.probed = True
                with pytest.raises(PaymentConflictError):
                    await service.pay_with_wallet(
                        owner, order.id, idempotency_key="competing-wallet"
                    )
                return await super().create_order(**kwargs)

        gateway = ProbeGateway(
            webhook_secret="payment-secret", uuid_factory=lambda: "provider-order"
        )
        service, sessions, engine, owner = await _service(gateway=gateway)
        try:
            admin = AuthPrincipal(
                user_id=ADMIN_ID,
                session_id=owner.session_id,
                email="admin@example.vn",
                roles=("SUPER_ADMIN",),
            )
            order = await service.issue_order(
                admin,
                DOSSIER_ID,
                idempotency_key="issued",
                amount_minor=50_000,
                currency="VND",
                description="Phí xác lập hồ sơ",
                due_at=None,
            )
            async with sessions() as session, session.begin():
                # Exercise a legacy gateway order: newly issued fees now use wallets.
                from app.modules.payments.models import PaymentOrder

                saved = await session.get(PaymentOrder, order.id)
                assert saved is not None
                saved.provider = "mock"
                await WalletLedger(session).post(
                    user_id=owner.user_id,
                    delta=100_000,
                    kind="TOPUP",
                    key="seed",
                    reference="topup:race",
                    description="Nạp tiền",
                )
            await service._ensure_checkout(order.id)
            assert gateway.probed
            async with sessions() as session, session.begin():
                assert await session.scalar(select(Wallet.balance_minor)) == 100_000
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_concurrent_debits_and_retries_share_one_atomic_balance(
    tmp_path, monkeypatch
) -> None:
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.tests import test_payment_service as fixtures

    url = f"sqlite+aiosqlite:///{(tmp_path / 'concurrent-wallet.sqlite3').as_posix()}"
    monkeypatch.setattr(
        fixtures, "create_async_engine", lambda _: create_async_engine(url)
    )

    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session, session.begin():
                await WalletLedger(session).post(
                    user_id=owner.user_id,
                    delta=100_000,
                    kind="TOPUP",
                    key="funds",
                    reference="topup:concurrent",
                    description="Nạp tiền",
                )

            async def debit(key, amount):
                async with sessions() as session, session.begin():
                    result = await WalletLedger(session).post(
                        user_id=owner.user_id,
                        delta=-amount,
                        kind="PAYMENT",
                        key=key,
                        reference=f"payment:{key}",
                        description="Phí dịch vụ",
                    )
                    return result.id

            results = await asyncio.gather(
                debit("first", 80_000), debit("second", 80_000), return_exceptions=True
            )
            assert sum(isinstance(result, DomainError) for result in results) == 1
            retries = await asyncio.gather(
                debit("same-key", 10_000), debit("same-key", 10_000)
            )
            assert retries[0] == retries[1]
            async with sessions() as session, session.begin():
                assert await session.scalar(select(Wallet.balance_minor)) == 10_000
                assert len(list(await session.scalars(select(WalletJournal)))) == 3
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_wallet_pays_a_server_order_once_and_preserves_the_fee_amount() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            order = await service.create_order(
                owner, DOSSIER_ID, idempotency_key="fee-order"
            )
            # Existing create_order opens a provider checkout, which must not be
            # payable again from a wallet. Use an unstarted server-issued order.
            from app.modules.payments.models import PaymentOrder

            async with sessions() as session, session.begin():
                saved = await session.get(PaymentOrder, order.id)
                assert saved is not None
                saved.provider_order_id = None
                saved.metadata_json = {"description": "Phí xác lập"}
                await WalletLedger(session).post(
                    user_id=owner.user_id,
                    delta=2_000_000,
                    kind="TOPUP",
                    key="funds",
                    reference="topup:funds",
                    description="Nạp tiền",
                )
            paid = await service.pay_with_wallet(
                owner, order.id, idempotency_key="confirm-fee"
            )
            assert paid.status == "PAID"
            assert paid.provider == "wallet"
            replay = await service.pay_with_wallet(
                owner, order.id, idempotency_key="confirm-fee"
            )
            assert replay.id == paid.id
            async with sessions() as session, session.begin():
                assert await session.scalar(select(Wallet.balance_minor)) == 1_000_000
                assert len(list(await session.scalars(select(WalletJournal)))) == 2
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_wallet_postings_are_balanced_idempotent_and_never_overdraw() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                ledger = WalletLedger(session)
                async with session.begin():
                    credit = await ledger.post(
                        user_id=owner.user_id,
                        delta=100_000,
                        kind="TOPUP",
                        key="deposit",
                        reference="topup:verified",
                        description="Nạp tiền",
                    )
                    assert credit.wallet_delta + credit.counter_delta == 0
                    assert credit.balance_after == 100_000
                async with session.begin():
                    replay = await ledger.post(
                        user_id=owner.user_id,
                        delta=100_000,
                        kind="TOPUP",
                        key="deposit",
                        reference="topup:verified",
                        description="Nạp tiền",
                    )
                    assert replay.id == credit.id
                async with session.begin():
                    await ledger.post(
                        user_id=owner.user_id,
                        delta=-80_000,
                        kind="PAYMENT",
                        key="fee",
                        reference="payment:order",
                        description="Phí hồ sơ",
                    )
                with pytest.raises(DomainError, match="Số dư"):
                    async with session.begin():
                        await ledger.post(
                            user_id=owner.user_id,
                            delta=-30_000,
                            kind="PAYMENT",
                            key="fee-2",
                            reference="payment:other",
                            description="Phí hồ sơ",
                        )
                async with session.begin():
                    assert await session.scalar(select(Wallet.balance_minor)) == 20_000
                    assert len(list(await session.scalars(select(WalletJournal)))) == 2
                with pytest.raises(PaymentConflictError):
                    async with session.begin():
                        await ledger.post(
                            user_id=owner.user_id,
                            delta=200_000,
                            kind="TOPUP",
                            key="deposit",
                            reference="topup:verified",
                            description="Nạp tiền",
                        )
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_wallet_balance_rolls_back_with_the_business_transaction() -> None:
    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                with pytest.raises(RuntimeError):
                    async with session.begin():
                        await WalletLedger(session).post(
                            user_id=owner.user_id,
                            delta=50_000,
                            kind="TOPUP",
                            key=str(uuid4()),
                            reference="topup:rollback",
                            description="Nạp tiền",
                        )
                        raise RuntimeError("business action failed")
                async with session.begin():
                    assert await session.scalar(select(Wallet.balance_minor)) in {
                        None,
                        0,
                    }
                    assert not list(await session.scalars(select(WalletJournal)))
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_reconciliation_recovers_a_late_paid_topup_after_failure() -> None:
    from dataclasses import replace

    from app.modules.payments.gateway import MockPaymentGateway
    from app.modules.wallet.models import WalletTopup

    async def exercise() -> None:
        class LateGateway(MockPaymentGateway):
            async def get_order(self, provider_order_id):
                return replace(
                    await super().get_order(provider_order_id), status="PAID"
                )

        gateway = LateGateway(webhook_secret="payment-secret")
        service, sessions, engine, owner = await _service(gateway=gateway)
        try:
            topup = await service.wallet_service().topup(
                owner.user_id, 50_000, "late-topup"
            )
            async with sessions() as session, session.begin():
                saved = await session.get(WalletTopup, topup.id)
                assert saved is not None
                saved.status = "FAILED"
            assert await service.wallet_service().reconcile_pending(10) == 1
            assert (await service.wallet_service().summary(owner.user_id))[
                "balance_minor"
            ] == 50_000
            assert await service.wallet_service().reconcile_pending(10) == 0
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_verified_topup_webhook_credits_once_and_rejects_wrong_amount() -> None:
    from app.modules.payments.errors import PaymentAmountMismatchError

    async def exercise() -> None:
        service, sessions, engine, owner = await _service()
        try:
            topup = await service.wallet_service().topup(
                owner.user_id, 50_000, "deposit-order"
            )
            topup_id, topup_code = topup.id, topup.order_code
            summary = await service.wallet_service().summary(owner.user_id)
            assert summary["balance_minor"] == 0
            replay = await service.wallet_service().topup(
                owner.user_id, 50_000, "deposit-order"
            )
            assert replay.id == topup.id
            body, signature, stamp = _webhook(
                amount_minor=49_000, order_code=topup_code
            )
            with pytest.raises(PaymentAmountMismatchError):
                await service.process_webhook(
                    raw_body=body, signature=signature, timestamp=stamp
                )
            body, signature, stamp = _webhook(
                amount_minor=50_000, order_code=topup_code
            )
            assert (
                await service.process_webhook(
                    raw_body=body, signature=signature, timestamp=stamp
                )
                is None
            )
            assert (
                await service.process_webhook(
                    raw_body=body, signature=signature, timestamp=stamp
                )
                is None
            )
            summary = await service.wallet_service().summary(owner.user_id)
            assert summary["balance_minor"] == 50_000
            assert len(summary["transactions"]) == 1
            with pytest.raises(PaymentConflictError):
                await service.wallet_service().topup(
                    owner.user_id, 60_000, "deposit-order"
                )
            from app.modules.payments.errors import PaymentNotFoundError

            with pytest.raises(PaymentNotFoundError):
                await service.wallet_service().reconcile(uuid4(), topup_id)
        finally:
            await service.close()
            await engine.dispose()

    asyncio.run(exercise())
