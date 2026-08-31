import re
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.billing.errors import PriceCatalogConflictError
from app.modules.billing.models import FeeObligation, FeeObligationStatus
from app.modules.billing.repository import BillingRepository, PriceCatalogRepository
from app.modules.dossiers.models import DossierStatus
from app.modules.dossiers.repository import DossierRepository
from app.modules.dossiers.workflow import DossierWorkflowService
from app.modules.notifications.models import Notification

SERVICE_CODE_PATTERN = re.compile(r"^[A-Z0-9][A-Z0-9_]{1,63}$")


@dataclass(frozen=True, slots=True)
class ResolvedPrice:
    catalog_version_id: UUID
    entry_id: UUID
    dossier_type_id: UUID
    service_code: str
    display_name: str
    amount_minor: int
    currency: str
    tax_mode: str


class PriceCatalogService:
    def __init__(self, session: AsyncSession) -> None:
        self._prices = PriceCatalogRepository(session)

    async def resolve_price(
        self,
        *,
        dossier_type_id: UUID,
        service_code: str,
        effective_at: datetime,
    ) -> ResolvedPrice:
        normalized_code = service_code.strip().upper()
        if not SERVICE_CODE_PATTERN.fullmatch(normalized_code):
            raise PriceCatalogConflictError("Price service code is invalid.")
        matches = await self._prices.effective_entries(
            dossier_type_id=dossier_type_id,
            service_code=normalized_code,
            effective_at=effective_at,
        )
        if not matches:
            raise PriceCatalogConflictError("No effective price is published.")
        if len(matches) > 1:
            raise PriceCatalogConflictError(
                "Price catalog contains multiple effective prices."
            )
        version, entry = matches[0]
        return ResolvedPrice(
            catalog_version_id=version.id,
            entry_id=entry.id,
            dossier_type_id=entry.dossier_type_id,
            service_code=entry.service_code,
            display_name=entry.display_name,
            amount_minor=entry.amount_minor,
            currency=entry.currency,
            tax_mode=entry.tax_mode,
        )


@dataclass(frozen=True, slots=True)
class FeeObligationView:
    id: UUID
    dossier_id: UUID
    owner_user_id: UUID
    price_catalog_version_id: UUID
    price_catalog_entry_id: UUID
    service_code: str
    description: str
    amount_minor: int
    currency: str
    tax_mode: str
    status: FeeObligationStatus
    due_at: datetime
    paid_at: datetime | None


class BillingService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        payment_term_days: int,
        clock: Callable[[], datetime] | None = None,
        uuid_factory: Callable[[], UUID] | None = None,
    ) -> None:
        if not 1 <= payment_term_days <= 30:
            raise ValueError("Payment term must be between 1 and 30 days.")
        self._session = session
        self._payment_term = timedelta(days=payment_term_days)
        self._clock = clock or (lambda: datetime.now(UTC))
        self._uuid_factory = uuid_factory or uuid4
        self._billing = BillingRepository(session)
        self._dossiers = DossierRepository(session)
        self._workflow = DossierWorkflowService(self._dossiers)
        self._prices = PriceCatalogService(session)

    async def create_for_approved_dossier(
        self, *, dossier_id: UUID, actor_user_id: UUID
    ) -> FeeObligationView:
        async with self._session.begin():
            existing = await self._billing.obligation_for_dossier(dossier_id)
            if existing is not None:
                return self._view(existing)
            dossier = await self._dossiers.get_by_id(dossier_id, for_update=True)
            if dossier is None:
                raise PriceCatalogConflictError("Dossier was not found.")
            if dossier.status is not DossierStatus.APPROVED:
                raise PriceCatalogConflictError(
                    "Only an approved dossier can receive a fee obligation."
                )
            if dossier.dossier_type_id is None:
                raise PriceCatalogConflictError(
                    "Approved dossier has no billable dossier type."
                )
            now = self._clock()
            price = await self._prices.resolve_price(
                dossier_type_id=dossier.dossier_type_id,
                service_code="STANDARD",
                effective_at=now,
            )
            obligation = FeeObligation(
                id=self._uuid_factory(),
                dossier_id=dossier.id,
                owner_user_id=dossier.owner_user_id,
                price_catalog_version_id=price.catalog_version_id,
                price_catalog_entry_id=price.entry_id,
                service_code=price.service_code,
                description=price.display_name,
                amount_minor=price.amount_minor,
                currency=price.currency,
                tax_mode=price.tax_mode,
                status=FeeObligationStatus.OPEN,
                due_at=now + self._payment_term,
                price_snapshot_json={
                    "catalogVersionId": str(price.catalog_version_id),
                    "entryId": str(price.entry_id),
                    "serviceCode": price.service_code,
                    "displayName": price.display_name,
                    "amountMinor": price.amount_minor,
                    "currency": price.currency,
                    "taxMode": price.tax_mode,
                },
            )
            self._billing.add_obligation(obligation)
            self._session.add(
                Notification(
                    user_id=dossier.owner_user_id,
                    source_event_id=obligation.id,
                    type="FEE_OBLIGATION_CREATED",
                    title="Hồ sơ đã được duyệt — vui lòng thanh toán",
                    body=(
                        f"Khoản phí {price.amount_minor:,} {price.currency} "
                        "đã được ghi nhận trong tài khoản của bạn."
                    ),
                    data_json={
                        "dossierId": str(dossier.id),
                        "feeObligationId": str(obligation.id),
                        "actionUrl": f"/billing/obligations/{obligation.id}",
                    },
                    created_at=now,
                )
            )
            self._workflow.transition(
                dossier,
                target=DossierStatus.PAYMENT_PENDING,
                actor_user_id=actor_user_id,
                allowed_sources={DossierStatus.APPROVED},
                reason_code="FEE_OBLIGATION_CREATED",
            )
            await self._session.flush()
            return self._view(obligation)

    async def close(self) -> None:
        await self._session.close()

    @staticmethod
    def _view(obligation: FeeObligation) -> FeeObligationView:
        return FeeObligationView(
            id=obligation.id,
            dossier_id=obligation.dossier_id,
            owner_user_id=obligation.owner_user_id,
            price_catalog_version_id=obligation.price_catalog_version_id,
            price_catalog_entry_id=obligation.price_catalog_entry_id,
            service_code=obligation.service_code,
            description=obligation.description,
            amount_minor=obligation.amount_minor,
            currency=obligation.currency,
            tax_mode=obligation.tax_mode,
            status=obligation.status,
            due_at=obligation.due_at,
            paid_at=obligation.paid_at,
        )
