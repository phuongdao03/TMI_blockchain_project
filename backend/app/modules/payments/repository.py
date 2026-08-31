from typing import cast
from uuid import UUID

from sqlalchemy import exists, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dossiers.models import Dossier
from app.modules.organizations.models import (
    MembershipStatus,
    OrganizationMember,
)
from app.modules.payments.models import PaymentEvent, PaymentOrder, PaymentStatus


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_order(self, order: PaymentOrder) -> None:
        self._session.add(order)

    def add_event(self, event: PaymentEvent) -> None:
        self._session.add(event)

    async def get_order(
        self,
        order_id: UUID,
        *,
        for_update: bool = False,
    ) -> PaymentOrder | None:
        statement = select(PaymentOrder).where(PaymentOrder.id == order_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PaymentOrder | None, await self._session.scalar(statement))

    async def get_by_idempotency(self, key: str) -> PaymentOrder | None:
        return cast(
            PaymentOrder | None,
            await self._session.scalar(
                select(PaymentOrder).where(PaymentOrder.idempotency_key == key)
            ),
        )

    async def get_by_provider_order(
        self,
        provider: str,
        provider_order_id: str,
        *,
        for_update: bool = False,
    ) -> PaymentOrder | None:
        statement = select(PaymentOrder).where(
            PaymentOrder.provider == provider,
            PaymentOrder.provider_order_id == provider_order_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PaymentOrder | None, await self._session.scalar(statement))

    async def get_active_for_dossier(
        self,
        dossier_id: UUID,
    ) -> PaymentOrder | None:
        return cast(
            PaymentOrder | None,
            await self._session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.dossier_id == dossier_id,
                    PaymentOrder.status.in_(
                        (PaymentStatus.PENDING, PaymentStatus.PROCESSING)
                    ),
                )
            ),
        )

    async def get_active_for_obligation(
        self,
        fee_obligation_id: UUID,
    ) -> PaymentOrder | None:
        return cast(
            PaymentOrder | None,
            await self._session.scalar(
                select(PaymentOrder).where(
                    PaymentOrder.fee_obligation_id == fee_obligation_id,
                    PaymentOrder.status.in_(
                        (PaymentStatus.PENDING, PaymentStatus.PROCESSING)
                    ),
                )
            ),
        )

    async def get_event(self, provider_event_id: str) -> PaymentEvent | None:
        return cast(
            PaymentEvent | None,
            await self._session.scalar(
                select(PaymentEvent).where(
                    PaymentEvent.provider_event_id == provider_event_id
                )
            ),
        )

    async def list_reconcilable(self, *, limit: int) -> tuple[PaymentOrder, ...]:
        rows = await self._session.scalars(
            select(PaymentOrder)
            .where(
                PaymentOrder.status.in_(
                    (PaymentStatus.PENDING, PaymentStatus.PROCESSING)
                )
            )
            .order_by(PaymentOrder.updated_at.asc())
            .limit(limit)
        )
        return tuple(rows.all())

    async def can_access_dossier(
        self,
        user_id: UUID,
        dossier: Dossier,
    ) -> bool:
        if dossier.owner_user_id == user_id:
            return True
        if dossier.organization_id is None:
            return False
        membership = await self._session.scalar(
            select(
                exists().where(
                    OrganizationMember.organization_id == dossier.organization_id,
                    OrganizationMember.user_id == user_id,
                    OrganizationMember.status == MembershipStatus.ACTIVE,
                )
            )
        )
        return bool(membership)

    async def list_for_admin(
        self,
        *,
        status: PaymentStatus | None,
        limit: int,
    ) -> tuple[PaymentOrder, ...]:
        statement = select(PaymentOrder)
        if status is not None:
            statement = statement.where(PaymentOrder.status == status)
        rows = await self._session.scalars(
            statement.order_by(PaymentOrder.created_at.desc()).limit(limit)
        )
        return tuple(rows.all())
