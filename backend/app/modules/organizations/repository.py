from typing import cast
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import User
from app.modules.organizations.models import Organization, OrganizationMember


class OrganizationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_by_code(self, code: str) -> Organization | None:
        return cast(
            Organization | None,
            await self._session.scalar(
                select(Organization).where(Organization.code == code)
            ),
        )

    async def get_by_id(
        self,
        organization_id: UUID,
        *,
        for_update: bool = False,
    ) -> Organization | None:
        statement = select(Organization).where(
            Organization.id == organization_id,
            Organization.deleted_at.is_(None),
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(Organization | None, await self._session.scalar(statement))

    async def get_membership(
        self,
        organization_id: UUID,
        user_id: UUID,
        *,
        for_update: bool = False,
    ) -> OrganizationMember | None:
        statement = select(OrganizationMember).where(
            OrganizationMember.organization_id == organization_id,
            OrganizationMember.user_id == user_id,
        )
        if for_update:
            statement = statement.with_for_update()
        return cast(
            OrganizationMember | None,
            await self._session.scalar(statement),
        )

    async def list_for_user(
        self,
        user_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[tuple[Organization, OrganizationMember], ...], int]:
        criteria = (
            OrganizationMember.user_id == user_id,
            Organization.deleted_at.is_(None),
        )
        total = await self._session.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .join(
                Organization,
                Organization.id == OrganizationMember.organization_id,
            )
            .where(*criteria)
        )
        statement = (
            select(Organization, OrganizationMember)
            .join(
                OrganizationMember,
                OrganizationMember.organization_id == Organization.id,
            )
            .where(*criteria)
            .order_by(Organization.display_name)
            .offset(offset)
            .limit(limit)
        )
        rows = tuple((await self._session.execute(statement)).tuples().all())
        return rows, int(total or 0)

    async def list_members(
        self,
        organization_id: UUID,
        *,
        offset: int,
        limit: int,
    ) -> tuple[tuple[tuple[OrganizationMember, str], ...], int]:
        total = await self._session.scalar(
            select(func.count())
            .select_from(OrganizationMember)
            .where(OrganizationMember.organization_id == organization_id)
        )
        statement = (
            select(OrganizationMember, User.email)
            .join(User, User.id == OrganizationMember.user_id)
            .where(OrganizationMember.organization_id == organization_id)
            .order_by(User.email)
            .offset(offset)
            .limit(limit)
        )
        rows = tuple((await self._session.execute(statement)).tuples().all())
        return rows, int(total or 0)

    async def get_user_by_email(self, email: str) -> User | None:
        return cast(
            User | None,
            await self._session.scalar(select(User).where(User.email == email)),
        )

    def add_organization(self, organization: Organization) -> None:
        self._session.add(organization)

    def add_membership(self, membership: OrganizationMember) -> None:
        self._session.add(membership)

    async def remove_membership(self, membership: OrganizationMember) -> None:
        await self._session.delete(membership)
