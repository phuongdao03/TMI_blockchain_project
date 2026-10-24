from datetime import datetime
from typing import Any, cast
from uuid import UUID

from sqlalchemy import and_, case, exists, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import aliased

from app.modules.auth.models import User
from app.modules.dossiers.models import Dossier
from app.modules.organizations.models import (
    MembershipStatus,
    OrganizationMember,
)
from app.modules.payments.models import (
    PaymentEvent,
    PaymentOrder,
    PaymentStatus,
    PaymentStatusHistory,
)


class PaymentRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_order(self, order: PaymentOrder) -> None:
        self._session.add(order)

    def add_event(self, event: PaymentEvent) -> None:
        self._session.add(event)

    def add_status_history(self, item: PaymentStatusHistory) -> None:
        self._session.add(item)

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

    async def get_by_order_code(
        self, order_code: str, *, for_update: bool = False
    ) -> PaymentOrder | None:
        statement = select(PaymentOrder).where(PaymentOrder.order_code == order_code)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(PaymentOrder | None, await self._session.scalar(statement))

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
                or_(
                    PaymentOrder.status == PaymentStatus.PROCESSING,
                    and_(
                        PaymentOrder.status == PaymentStatus.PENDING,
                        PaymentOrder.provider_order_id.is_not(None),
                    ),
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
    ) -> tuple[tuple[PaymentOrder, str, str], ...]:
        statement = select(PaymentOrder, Dossier.code, Dossier.title).join(
            Dossier,
            Dossier.id == PaymentOrder.dossier_id,
        )
        if status is not None:
            statement = statement.where(PaymentOrder.status == status)
        rows = await self._session.execute(
            statement.order_by(PaymentOrder.created_at.desc(), PaymentOrder.id.desc())
            .limit(limit)
        )
        return tuple((row[0], row[1], row[2]) for row in rows.all())

    async def list_history_for_admin(
        self,
        *,
        status: PaymentStatus | None,
        created_from: datetime | None,
        created_to: datetime | None,
        query: str | None,
        offset: int = 0,
        limit: int | None = 50,
    ) -> tuple[tuple[tuple[Any, ...], ...], int, dict[str, int], int, int]:
        owner = aliased(User, name="payment_applicant")
        initiator = aliased(User, name="payment_initiator")
        statement = (
            select(
                PaymentOrder,
                Dossier.code,
                Dossier.title,
                Dossier.owner_user_id,
                owner.email,
                initiator.email,
            )
            .join(Dossier, Dossier.id == PaymentOrder.dossier_id)
            .join(owner, owner.id == Dossier.owner_user_id)
            .outerjoin(initiator, initiator.id == PaymentOrder.initiated_by_user_id)
        )
        filters = self._history_filters(
            status=status,
            created_from=created_from,
            created_to=created_to,
            query=query,
            owner=owner,
            initiator=initiator,
        )
        statement = statement.where(*filters).order_by(
            PaymentOrder.created_at.desc(), PaymentOrder.id.desc()
        )
        if limit is not None:
            statement = statement.offset(offset).limit(limit)
        rows = tuple(
            tuple(row) for row in (await self._session.execute(statement)).all()
        )

        base = (
            select(PaymentOrder.id)
            .join(Dossier, Dossier.id == PaymentOrder.dossier_id)
            .join(owner, owner.id == Dossier.owner_user_id)
            .outerjoin(initiator, initiator.id == PaymentOrder.initiated_by_user_id)
            .where(*filters)
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(base.subquery())
            )
            or 0
        )
        totals = await self._session.execute(
            select(
                PaymentOrder.status,
                func.count(PaymentOrder.id),
                func.coalesce(func.sum(PaymentOrder.amount_minor), 0),
                func.coalesce(
                    func.sum(
                        case(
                            (
                                PaymentOrder.status == PaymentStatus.PAID,
                                PaymentOrder.amount_minor,
                            ),
                            else_=0,
                        )
                    ),
                    0,
                ),
            )
            .join(Dossier, Dossier.id == PaymentOrder.dossier_id)
            .join(owner, owner.id == Dossier.owner_user_id)
            .outerjoin(initiator, initiator.id == PaymentOrder.initiated_by_user_id)
            .where(*filters)
            .group_by(PaymentOrder.status)
        )
        status_counts: dict[str, int] = {}
        total_amount_minor = 0
        paid_amount_minor = 0
        for item_status, count, amount, paid_amount in totals.all():
            status_counts[item_status.value] = int(count)
            total_amount_minor += int(amount)
            paid_amount_minor += int(paid_amount)
        return rows, total, status_counts, total_amount_minor, paid_amount_minor

    async def get_history_detail_for_admin(
        self, order_id: UUID
    ) -> tuple[
        tuple[Any, ...] | None,
        tuple[tuple[PaymentStatusHistory, str | None], ...],
    ]:
        owner = aliased(User, name="payment_applicant")
        initiator = aliased(User, name="payment_initiator")
        row = await self._session.execute(
            select(
                PaymentOrder,
                Dossier.code,
                Dossier.title,
                Dossier.owner_user_id,
                owner.email,
                initiator.email,
            )
            .join(Dossier, Dossier.id == PaymentOrder.dossier_id)
            .join(owner, owner.id == Dossier.owner_user_id)
            .outerjoin(initiator, initiator.id == PaymentOrder.initiated_by_user_id)
            .where(PaymentOrder.id == order_id)
        )
        detail_row = row.first()
        detail = tuple(detail_row) if detail_row is not None else None
        actor = aliased(User, name="payment_status_actor")
        history = await self._session.execute(
            select(PaymentStatusHistory, actor.email)
            .outerjoin(actor, actor.id == PaymentStatusHistory.actor_user_id)
            .where(PaymentStatusHistory.payment_order_id == order_id)
            .order_by(
                PaymentStatusHistory.changed_at.asc(), PaymentStatusHistory.id.asc()
            )
        )
        return detail, tuple((item[0], item[1]) for item in history.all())

    @staticmethod
    def _history_filters(
        *,
        status: PaymentStatus | None,
        created_from: object | None,
        created_to: object | None,
        query: str | None,
        owner: Any,
        initiator: Any,
    ) -> tuple[Any, ...]:
        filters: list[object] = []
        if status is not None:
            filters.append(PaymentOrder.status == status)
        if created_from is not None:
            filters.append(PaymentOrder.created_at >= created_from)
        if created_to is not None:
            filters.append(PaymentOrder.created_at <= created_to)
        if query:
            escaped_query = query.replace("%", "\\%").replace("_", "\\_")
            pattern = f"%{escaped_query}%"
            filters.append(
                or_(
                    PaymentOrder.order_code.ilike(pattern, escape="\\"),
                    Dossier.code.ilike(pattern, escape="\\"),
                    Dossier.title.ilike(pattern, escape="\\"),
                    owner.email.ilike(pattern, escape="\\"),
                    initiator.email.ilike(pattern, escape="\\"),
                )
            )
        return tuple(filters)
