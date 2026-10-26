from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.notifications.models import Notification
from app.modules.payments.errors import (
    PaymentAmountMismatchError,
    PaymentConflictError,
    PaymentNotFoundError,
    PaymentProviderError,
)
from app.modules.payments.gateway import (
    PaymentGateway,
    PaymentGatewayError,
    ProviderOrder,
    VerifiedPaymentEvent,
)
from app.modules.wallet.models import (
    Wallet,
    WalletJournal,
    WalletTopup,
    WalletTopupEvent,
)


def valid_key(key: str) -> str:
    key = key.strip()
    if not key or len(key) > 128:
        raise PaymentConflictError("Khóa xác nhận giao dịch không hợp lệ.")
    return key


@dataclass(frozen=True, slots=True)
class WalletCheckoutDetails:
    qr_payload: str | None
    bank_bin: str | None
    bank_account_number: str | None
    bank_account_name: str | None
    transfer_description: str | None


async def read_wallet(
    session: AsyncSession, user_id: UUID, provider: str
) -> dict[str, object]:
    """Read owner-scoped history without constructing a payment gateway."""
    async with session.begin():
        balance = await session.scalar(
            select(Wallet.balance_minor).where(Wallet.user_id == user_id)
        )
        rows = list(
            await session.scalars(
                select(WalletJournal)
                .where(WalletJournal.user_id == user_id)
                .order_by(WalletJournal.created_at.desc(), WalletJournal.id.desc())
                .limit(50)
            )
        )
        topups = list(
            await session.scalars(
                select(WalletTopup)
                .where(WalletTopup.user_id == user_id)
                .order_by(WalletTopup.created_at.desc())
                .limit(20)
            )
        )
        return {
            "balance_minor": balance or 0,
            "currency": "VND",
            "transactions": rows,
            "topups": topups,
            "provider": provider,
        }


class WalletLedger:
    """Join the caller's business transaction; never commit independently."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def lock(self, user_id: UUID) -> Wallet:
        dialect = self.session.get_bind().dialect.name
        insert = sqlite_insert if dialect == "sqlite" else pg_insert
        await self.session.execute(
            insert(Wallet)
            .values(user_id=user_id, balance_minor=0)
            .on_conflict_do_nothing(index_elements=["user_id"])
        )
        wallet = await self.session.scalar(
            select(Wallet)
            .where(Wallet.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        assert wallet is not None
        return wallet

    async def post(
        self,
        *,
        user_id: UUID,
        delta: int,
        kind: str,
        key: str,
        reference: str,
        description: str,
    ) -> WalletJournal:
        if type(delta) is not int or delta == 0:
            raise ValueError("A posting requires a nonzero integer VND amount.")
        key = valid_key(key)
        await self.lock(user_id)
        replay = await self.session.scalar(
            select(WalletJournal).where(
                WalletJournal.user_id == user_id, WalletJournal.idempotency_key == key
            )
        )
        if replay is not None:
            if (replay.wallet_delta, replay.kind, replay.source_reference) != (
                delta,
                kind,
                reference,
            ):
                raise PaymentConflictError(
                    "Khóa giao dịch đã được sử dụng cho khoản khác."
                )
            return replay
        balance = await self.session.scalar(
            update(Wallet)
            .where(Wallet.user_id == user_id, Wallet.balance_minor + delta >= 0)
            .values(balance_minor=Wallet.balance_minor + delta)
            .returning(Wallet.balance_minor)
        )
        if balance is None:
            raise DomainError(
                code="WALLET_INSUFFICIENT_FUNDS",
                message=(
                    "Số dư ví chưa đủ. Vui lòng nạp thêm tiền trước khi thanh toán."
                ),
                status_code=409,
            )
        posting = WalletJournal(
            user_id=user_id,
            wallet_delta=delta,
            counter_delta=-delta,
            balance_after=balance,
            kind=kind,
            idempotency_key=key,
            source_reference=reference,
            description=description[:255],
        )
        self.session.add(posting)
        await self.session.flush()
        await self.session.refresh(posting)
        return posting


class WalletService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        gateway: PaymentGateway,
        provider: str,
        ttl_seconds: int = 1800,
    ):
        self.session = session
        self.gateway = gateway
        self.provider = provider
        self.ttl = ttl_seconds
        self.ledger = WalletLedger(session)

    async def resume(self, user_id: UUID, identifier: UUID) -> WalletTopup:
        async with self.session.begin():
            order = await self._required(identifier, user_id)
            amount, key = order.amount_minor, order.idempotency_key
        return await self.topup(user_id, amount, key)

    async def reconcile_pending(self, limit: int) -> int:
        async with self.session.begin():
            rows = list(
                (
                    await self.session.execute(
                        select(WalletTopup.user_id, WalletTopup.id, WalletTopup.status)
                        .where(
                            WalletTopup.status != "PAID",
                            WalletTopup.created_at
                            >= datetime.now(UTC) - timedelta(days=7),
                        )
                        .order_by(WalletTopup.updated_at)
                        .limit(limit)
                    )
                ).all()
            )
        count = 0
        for user_id, identifier, status in rows:
            try:
                if status in {"PENDING", "PROCESSING"}:
                    await self.resume(user_id, identifier)
                await self.reconcile(user_id, identifier)
            except (
                PaymentProviderError,
                PaymentAmountMismatchError,
                PaymentConflictError,
            ):
                async with self.session.begin():
                    order = await self._required(identifier, user_id)
                    order.updated_at = datetime.now(UTC)
                continue
            count += 1
        return count

    async def summary(self, user_id: UUID) -> dict[str, object]:
        return await read_wallet(self.session, user_id, self.provider)

    async def checkout_details(
        self, user_id: UUID, identifier: UUID
    ) -> WalletCheckoutDetails | None:
        async with self.session.begin():
            order = await self._required(identifier, user_id)
            if order.provider_order_id is None or order.status == "PAID":
                return None
            provider_order_id = order.provider_order_id
            order_code = order.order_code
            amount = order.amount_minor
            details = await self.session.scalar(
                select(WalletTopupEvent).where(
                    WalletTopupEvent.topup_id == identifier,
                    WalletTopupEvent.event_type == "checkout.details",
                )
            )
            if details is not None:

                def optional_text(key: str) -> str | None:
                    value = details.payload_redacted.get(key)
                    if value is not None and not isinstance(value, str):
                        raise PaymentProviderError()
                    return value

                return WalletCheckoutDetails(
                    qr_payload=optional_text("qr_payload"),
                    bank_bin=optional_text("bank_bin"),
                    bank_account_number=optional_text("bank_account_number"),
                    bank_account_name=optional_text("bank_account_name"),
                    transfer_description=optional_text("transfer_description"),
                )
        try:
            provider_order = await self.gateway.get_order(provider_order_id)
        except PaymentGatewayError as exc:
            raise PaymentProviderError() from exc
        self._validate(provider_order, order_code, amount)
        return WalletCheckoutDetails(
            qr_payload=provider_order.qr_payload,
            bank_bin=provider_order.bank_bin,
            bank_account_number=provider_order.bank_account_number,
            bank_account_name=provider_order.bank_account_name,
            transfer_description=provider_order.transfer_description,
        )

    async def topup(self, user_id: UUID, amount: int, key: str) -> WalletTopup:
        key = valid_key(key)
        if type(amount) is not int or not 1000 <= amount <= 1_000_000_000:
            raise PaymentConflictError("Số tiền nạp không hợp lệ.")
        async with self.session.begin():
            await self.ledger.lock(user_id)
            order = await self.session.scalar(
                select(WalletTopup).where(
                    WalletTopup.user_id == user_id, WalletTopup.idempotency_key == key
                )
            )
            if order is not None and order.amount_minor != amount:
                raise PaymentConflictError(
                    "Khóa giao dịch đã được sử dụng cho số tiền khác."
                )
            if order is None:
                identifier = uuid4()
                # Top-up code space is disjoint from legacy <= 2^31 order codes.
                code = str(2_147_483_648 + identifier.int % (2**53 - 2_147_483_649))
                order = WalletTopup(
                    id=identifier,
                    user_id=user_id,
                    order_code=code,
                    provider=self.provider,
                    amount_minor=amount,
                    idempotency_key=key,
                    expires_at=datetime.now(UTC) + timedelta(seconds=self.ttl),
                    status="PROCESSING",
                )
                self.session.add(order)
                await self.session.flush()
            order_id, code, expires = order.id, order.order_code, order.expires_at
            if order.checkout_url or order.status == "PAID":
                return order
        try:
            try:
                provider_order = await self.gateway.get_order(code)
            except PaymentGatewayError:
                provider_order = await self.gateway.create_order(
                    order_code=code,
                    amount_minor=amount,
                    currency="VND",
                    expires_at=expires,
                )
            self._validate(provider_order, code, amount)
        except PaymentGatewayError as exc:
            raise PaymentProviderError() from exc
        async with self.session.begin():
            saved = await self._required(order_id, user_id)
            if saved.provider_order_id not in {None, provider_order.provider_order_id}:
                raise PaymentConflictError("Mã giao dịch của nhà cung cấp không khớp.")
            saved.provider_order_id = provider_order.provider_order_id
            saved.checkout_url = provider_order.checkout_url
            if provider_order.qr_payload:
                existing_details = await self.session.scalar(
                    select(WalletTopupEvent).where(
                        WalletTopupEvent.topup_id == order_id,
                        WalletTopupEvent.event_type == "checkout.details",
                    )
                )
                if existing_details is None:
                    self.session.add(
                        WalletTopupEvent(
                            topup_id=order_id,
                            provider=self.provider,
                            provider_event_id=f"checkout:{order_id}",
                            event_type="checkout.details",
                            payload_redacted={
                                "qr_payload": provider_order.qr_payload,
                                "bank_bin": provider_order.bank_bin,
                                "bank_account_number": (
                                    provider_order.bank_account_number
                                ),
                                "bank_account_name": provider_order.bank_account_name,
                                "transfer_description": (
                                    provider_order.transfer_description
                                ),
                            },
                        )
                    )
            if saved.status == "PROCESSING":
                saved.status = "PENDING"
            await self.session.flush()
            await self.session.refresh(saved)
            return saved

    async def _required(self, identifier: UUID, user_id: UUID) -> WalletTopup:
        order = await self.session.scalar(
            select(WalletTopup)
            .where(WalletTopup.id == identifier, WalletTopup.user_id == user_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None:
            raise PaymentNotFoundError()
        return order

    @staticmethod
    def _validate(provider: ProviderOrder, code: str, amount: int) -> None:
        if (
            provider.order_code != code
            or provider.amount_minor != amount
            or provider.currency != "VND"
        ):
            raise PaymentAmountMismatchError()

    async def settle_event(self, event: VerifiedPaymentEvent) -> bool:
        """Signature must already be verified; caller owns the transaction."""
        order = await self.session.scalar(
            select(WalletTopup)
            .where(
                WalletTopup.order_code == event.order_code,
                WalletTopup.provider == self.provider,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if order is None:
            return False
        if (
            event.amount_minor != order.amount_minor
            or event.currency != "VND"
            or order.provider_order_id not in {None, event.provider_order_id}
        ):
            raise PaymentAmountMismatchError()
        duplicate = await self.session.scalar(
            select(WalletTopupEvent).where(
                WalletTopupEvent.provider == self.provider,
                WalletTopupEvent.provider_event_id == event.provider_event_id,
            )
        )
        if duplicate is not None:
            if duplicate.topup_id != order.id:
                raise PaymentConflictError(
                    "Mã xác nhận đã được dùng cho giao dịch khác."
                )
            return True
        self.session.add(
            WalletTopupEvent(
                topup_id=order.id,
                provider=self.provider,
                provider_event_id=event.provider_event_id,
                event_type=event.event_type,
                payload_redacted=dict(event.payload_redacted),
            )
        )
        if order.status == "PAID":
            return True
        if event.event_type == "payment.paid":
            # A verified late payment is still money received, even after expiry.
            posting = await self.ledger.post(
                user_id=order.user_id,
                delta=order.amount_minor,
                kind="TOPUP",
                key=f"topup:{order.id}",
                reference=f"topup:{order.id}",
                description="Nạp tiền vào ví",
            )
            order.status = "PAID"
            order.provider_order_id = event.provider_order_id
            order.paid_at = datetime.now(UTC)
            self.session.add(
                Notification(
                    user_id=order.user_id,
                    source_event_id=posting.id,
                    type="WALLET_TOPUP_PAID",
                    title="Nạp tiền vào ví thành công",
                    body=f"Ví của bạn đã được cộng {order.amount_minor:,} VNĐ.",
                    data_json={"actionPath": "/wallet", "topupId": str(order.id)},
                    created_at=datetime.now(UTC),
                )
            )
        elif event.event_type == "payment.failed" and order.status in {
            "PENDING",
            "PROCESSING",
        }:
            order.status = "FAILED"
        await self.session.flush()
        return True

    async def reconcile(self, user_id: UUID, identifier: UUID) -> WalletTopup:
        async with self.session.begin():
            order = await self._required(identifier, user_id)
            if order.status == "PAID":
                return order
            code, amount, provider_id = (
                order.order_code,
                order.amount_minor,
                order.provider_order_id,
            )
        try:
            result = await self.gateway.get_order(provider_id or code)
            self._validate(result, code, amount)
        except PaymentGatewayError as exc:
            raise PaymentProviderError() from exc
        async with self.session.begin():
            if result.status == "PAID":
                await self.settle_event(
                    VerifiedPaymentEvent(
                        provider_event_id=f"reconcile:{identifier}",
                        event_type="payment.paid",
                        provider_order_id=result.provider_order_id,
                        amount_minor=amount,
                        currency="VND",
                        payload_redacted={},
                        order_code=code,
                    )
                )
            order = await self._required(identifier, user_id)
            order.updated_at = datetime.now(UTC)
            if order.status != "PAID" and result.status in {
                "FAILED",
                "CANCELLED",
                "EXPIRED",
            }:
                order.status = result.status
            await self.session.flush()
            await self.session.refresh(order)
            return order
