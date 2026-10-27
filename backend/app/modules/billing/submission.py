"""Reserve submission payments inside the caller's locked dossier transaction."""

from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.repository import PriceCatalogRepository
from app.modules.billing.service import PriceCatalogService
from app.modules.dossiers.errors import DossierInvalidStateError
from app.modules.dossiers.models import Dossier, DossierStatus
from app.modules.payments.models import (
    PaymentOrder,
    PaymentStatus,
    PaymentStatusHistory,
)
from app.modules.payments.repository import PaymentRepository


class SubmissionFeeService:
    def __init__(
        self, session: AsyncSession, *, fallback_amount: int, now: datetime
    ) -> None:
        if fallback_amount <= 0:
            raise ValueError("Submission fee must be positive.")
        self.session = session
        self.fallback_amount = fallback_amount
        self.now = now
        self.payments = PaymentRepository(session)

    async def quote(self, dossier: Dossier) -> dict[str, object]:
        if dossier.submission_fee_snapshot is not None:
            return dict(dossier.submission_fee_snapshot)
        configured = (
            ()
            if dossier.dossier_type_id is None
            else await PriceCatalogRepository(self.session).effective_entries(
                dossier_type_id=dossier.dossier_type_id,
                service_code="STANDARD",
                effective_at=self.now,
            )
        )
        if dossier.dossier_type_id is not None and configured:
            price = await PriceCatalogService(self.session).resolve_price(
                dossier_type_id=dossier.dossier_type_id,
                service_code="STANDARD",
                effective_at=self.now,
            )
            return {
                "amountMinor": price.amount_minor,
                "currency": price.currency,
                "description": "Phí nộp hồ sơ đề cử",
                "catalogVersionId": str(price.catalog_version_id),
                "entryId": str(price.entry_id),
                "taxMode": price.tax_mode,
            }
        return {
            "amountMinor": self.fallback_amount,
            "currency": "VND",
            "description": "Phí nộp hồ sơ đề cử",
        }

    async def reserve(self, dossier: Dossier, *, actor: UUID, key: str) -> PaymentOrder:
        if (
            not dossier.submission_fee_required
            or dossier.submission_fee_paid_at is not None
        ):
            raise DossierInvalidStateError("This dossier has no unpaid submission fee.")
        if dossier.status not in {
            DossierStatus.SUBMITTED,
            DossierStatus.PAYMENT_PENDING,
        }:
            raise DossierInvalidStateError("Submit the dossier before paying its fee.")
        replay = await self.payments.get_by_idempotency(key)
        if replay is not None:
            if replay.dossier_id != dossier.id:
                raise DossierInvalidStateError("Payment key is already in use.")
            return replay
        active = await self.payments.get_active_for_dossier(dossier.id)
        if active is not None:
            expires = active.expires_at
            if expires.tzinfo is None:
                expires = expires.replace(tzinfo=UTC)
            if expires > self.now:
                return active
            active.status = PaymentStatus.EXPIRED
            self.session.add(
                PaymentStatusHistory(
                    payment_order_id=active.id,
                    from_status="PENDING",
                    to_status="EXPIRED",
                    source="SUBMISSION_FEE_EXPIRED",
                    actor_user_id=actor,
                    changed_at=self.now,
                )
            )
        quote = await self.quote(dossier)
        amount = quote["amountMinor"]
        if not isinstance(amount, int) or quote["currency"] != "VND":
            raise DossierInvalidStateError(
                "Submission wallet payments require a VND price."
            )
        dossier.submission_fee_snapshot = quote
        identifier = uuid4()
        order = PaymentOrder(
            id=identifier,
            order_code=str(identifier.int % 10**31),
            dossier_id=dossier.id,
            initiated_by_user_id=actor,
            provider="wallet",
            amount_minor=amount,
            currency="VND",
            status=PaymentStatus.PENDING,
            expires_at=self.now + timedelta(days=7),
            idempotency_key=key,
            metadata_json={
                "description": quote["description"],
                "purpose": "SUBMISSION_FEE",
            },
        )
        self.session.add(order)
        self.session.add(
            PaymentStatusHistory(
                payment_order_id=identifier,
                from_status=None,
                to_status="PENDING",
                source="SUBMISSION_FEE_CREATED",
                actor_user_id=actor,
                changed_at=self.now,
            )
        )
        await self.session.flush()
        return order
