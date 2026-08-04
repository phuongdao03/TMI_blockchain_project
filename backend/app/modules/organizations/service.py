import logging
from collections.abc import Callable
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.session_service import AuthPrincipal
from app.modules.organizations.errors import (
    MembershipExistsError,
    OrganizationCodeExistsError,
    OrganizationForbiddenError,
    OrganizationMemberNotFoundError,
    OrganizationNotFoundError,
    OrganizationOwnerOrphanError,
)
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    Organization,
    OrganizationMember,
    OrganizationStatus,
)
from app.modules.organizations.repository import OrganizationRepository
from app.modules.organizations.types import (
    CreateOrganization,
    MemberView,
    OrganizationChanges,
    OrganizationView,
    Page,
    UpsertMember,
)
from app.modules.users.security import SensitiveFieldCipher

logger = logging.getLogger(__name__)


class OrganizationService:
    def __init__(
        self,
        *,
        session: AsyncSession,
        cipher: SensitiveFieldCipher,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._session = session
        self._repository = OrganizationRepository(session)
        self._cipher = cipher
        self._clock = clock or (lambda: datetime.now(UTC))

    async def create_organization(
        self,
        principal: AuthPrincipal,
        payload: CreateOrganization,
    ) -> OrganizationView:
        code = payload.code.strip().upper()
        async with self._session.begin():
            if await self._repository.get_by_code(code) is not None:
                raise OrganizationCodeExistsError()
            organization = Organization(
                code=code,
                legal_name=payload.legal_name,
                display_name=payload.display_name,
                tax_code_encrypted=(
                    self._cipher.encrypt(payload.tax_code)
                    if payload.tax_code is not None
                    else None
                ),
                owner_user_id=principal.user_id,
            )
            self._repository.add_organization(organization)
            await self._session.flush()
            membership = OrganizationMember(
                organization_id=organization.id,
                user_id=principal.user_id,
                role_code=MembershipRole.OWNER,
                status=MembershipStatus.ACTIVE,
                joined_at=self._clock(),
            )
            self._repository.add_membership(membership)
            await self._session.flush()
            view = self._view(organization, membership)
        self._audit("organization.created", principal.user_id, organization.id)
        return view

    async def list_organizations(
        self,
        principal: AuthPrincipal,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[OrganizationView]:
        async with self._session.begin():
            rows, total = await self._repository.list_for_user(
                principal.user_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return Page(
                items=tuple(self._view(org, membership) for org, membership in rows),
                total=total,
            )

    async def get_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
    ) -> OrganizationView:
        async with self._session.begin():
            organization, membership = await self._access(
                principal,
                organization_id,
            )
            return self._view(organization, membership)

    async def update_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
        changes: OrganizationChanges,
    ) -> OrganizationView:
        async with self._session.begin():
            organization, membership = await self._access(
                principal,
                organization_id,
                for_update=True,
            )
            self._require_manager(membership)
            if "legal_name" in changes.provided_fields:
                organization.legal_name = changes.legal_name or organization.legal_name
            if "display_name" in changes.provided_fields:
                organization.display_name = (
                    changes.display_name or organization.display_name
                )
            if "tax_code" in changes.provided_fields:
                organization.tax_code_encrypted = (
                    self._cipher.encrypt(changes.tax_code)
                    if changes.tax_code is not None
                    else None
                )
            await self._session.flush()
            view = self._view(organization, membership)
        self._audit("organization.updated", principal.user_id, organization_id)
        return view

    async def archive_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
    ) -> None:
        async with self._session.begin():
            organization, membership = await self._access(
                principal,
                organization_id,
                for_update=True,
            )
            if membership.role_code is not MembershipRole.OWNER:
                raise OrganizationForbiddenError()
            organization.status = OrganizationStatus.ARCHIVED
            organization.deleted_at = self._clock()
        self._audit("organization.archived", principal.user_id, organization_id)

    async def list_members(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[MemberView]:
        async with self._session.begin():
            await self._access(principal, organization_id)
            rows, total = await self._repository.list_members(
                organization_id,
                offset=(page - 1) * page_size,
                limit=page_size,
            )
            return Page(
                items=tuple(
                    MemberView(
                        user_id=membership.user_id,
                        email=email,
                        role_code=membership.role_code,
                        status=membership.status,
                        joined_at=membership.joined_at,
                    )
                    for membership, email in rows
                ),
                total=total,
            )

    async def add_member(
        self,
        principal: AuthPrincipal,
        *,
        organization_id: UUID,
        member: UpsertMember,
    ) -> MemberView:
        async with self._session.begin():
            _, actor_membership = await self._access(
                principal,
                organization_id,
                for_update=True,
            )
            self._require_manager(actor_membership)
            user = await self._repository.get_user_by_email(
                member.email.strip().lower()
            )
            if user is None:
                raise OrganizationMemberNotFoundError()
            if (
                await self._repository.get_membership(organization_id, user.id)
                is not None
            ):
                raise MembershipExistsError()
            membership = OrganizationMember(
                organization_id=organization_id,
                user_id=user.id,
                role_code=member.role_code,
                status=member.status,
                joined_at=(
                    self._clock() if member.status is MembershipStatus.ACTIVE else None
                ),
            )
            self._repository.add_membership(membership)
            await self._session.flush()
            view = MemberView(
                user_id=user.id,
                email=user.email,
                role_code=membership.role_code,
                status=membership.status,
                joined_at=membership.joined_at,
            )
        self._audit("organization.member.added", principal.user_id, organization_id)
        return view

    async def remove_member(
        self,
        principal: AuthPrincipal,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        async with self._session.begin():
            organization, actor_membership = await self._access(
                principal,
                organization_id,
                for_update=True,
            )
            self._require_manager(actor_membership)
            target = await self._repository.get_membership(
                organization_id,
                user_id,
                for_update=True,
            )
            if target is None:
                raise OrganizationMemberNotFoundError()
            if target.user_id == organization.owner_user_id:
                raise OrganizationOwnerOrphanError()
            await self._repository.remove_membership(target)
        self._audit("organization.member.removed", principal.user_id, organization_id)

    async def _access(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
        *,
        for_update: bool = False,
    ) -> tuple[Organization, OrganizationMember]:
        organization = await self._repository.get_by_id(
            organization_id,
            for_update=for_update,
        )
        if organization is None:
            raise OrganizationNotFoundError()
        membership = await self._repository.get_membership(
            organization_id,
            principal.user_id,
            for_update=for_update,
        )
        if membership is None or membership.status is not MembershipStatus.ACTIVE:
            raise OrganizationForbiddenError()
        return organization, membership

    @staticmethod
    def _require_manager(membership: OrganizationMember) -> None:
        if (
            membership.status is not MembershipStatus.ACTIVE
            or membership.role_code
            not in (MembershipRole.OWNER, MembershipRole.ORG_MANAGER)
        ):
            raise OrganizationForbiddenError()

    def _view(
        self,
        organization: Organization,
        membership: OrganizationMember,
    ) -> OrganizationView:
        can_manage = (
            membership.status is MembershipStatus.ACTIVE
            and membership.role_code
            in (MembershipRole.OWNER, MembershipRole.ORG_MANAGER)
        )
        return OrganizationView(
            id=organization.id,
            code=organization.code,
            legal_name=organization.legal_name,
            display_name=organization.display_name,
            tax_code=(
                self._cipher.decrypt(organization.tax_code_encrypted)
                if can_manage and organization.tax_code_encrypted is not None
                else None
            ),
            status=organization.status,
            owner_user_id=organization.owner_user_id,
            current_role=membership.role_code,
            can_manage_members=can_manage,
        )

    @staticmethod
    def _audit(action: str, user_id: UUID, organization_id: UUID) -> None:
        logger.info(
            "security_audit",
            extra={
                "action": action,
                "user_id": str(user_id),
                "organization_id": str(organization_id),
            },
        )

    async def close(self) -> None:
        await self._session.close()


__all__ = [
    "CreateOrganization",
    "OrganizationChanges",
    "OrganizationService",
    "UpsertMember",
]
