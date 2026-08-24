from dataclasses import dataclass
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.audit.service import AuditService
from app.modules.auth.errors import ApplicantUpgradeNotAllowedError
from app.modules.auth.models import AccountType, Role, UserRole, UserStatus
from app.modules.auth.repositories import AuthRepository
from app.modules.auth.session_service import AuthPrincipal

APPLICANT_ACCOUNT_TYPES = frozenset(
    {AccountType.INDIVIDUAL_APPLICANT, AccountType.ORGANIZATION_APPLICANT}
)


@dataclass(frozen=True, slots=True)
class ApplicantUpgradeResult:
    user_id: UUID
    email: str
    account_type: AccountType
    roles: tuple[str, ...]


class ApplicantUpgradeService:
    def __init__(self, *, session: AsyncSession) -> None:
        self._session = session
        self._repository = AuthRepository(session)
        self._audit_service = AuditService(session)

    async def upgrade(
        self,
        principal: AuthPrincipal,
        *,
        account_type: AccountType,
    ) -> ApplicantUpgradeResult:
        if account_type not in APPLICANT_ACCOUNT_TYPES:
            raise ApplicantUpgradeNotAllowedError()

        async with self._session.begin():
            user = await self._repository.get_user_by_id_for_update(principal.user_id)
            if (
                user is None
                or user.status is not UserStatus.ACTIVE
                or user.email_verified_at is None
            ):
                raise ApplicantUpgradeNotAllowedError()

            existing_roles = await self._repository.get_role_codes(user.id)
            if user.account_type is not AccountType.PUBLIC_USER:
                if user.account_type is account_type and "USER" in existing_roles:
                    result = ApplicantUpgradeResult(
                        user_id=user.id,
                        email=user.email,
                        account_type=user.account_type,
                        roles=existing_roles,
                    )
                else:
                    raise ApplicantUpgradeNotAllowedError()
            else:
                role = await self._repository.get_role_by_code("USER")
                if role is None:
                    role = Role(code="USER")
                    self._repository.add_role(role)
                    await self._session.flush()
                for user_role, existing_role in await self._repository.list_user_roles(
                    user.id
                ):
                    if existing_role.code == "VIEWER":
                        await self._repository.delete_user_role(
                            user.id,
                            user_role.role_id,
                        )
                if "USER" not in existing_roles:
                    self._repository.add_user_role(
                        UserRole(user_id=user.id, role_id=role.id)
                    )
                user.account_type = account_type
                await self._session.flush()
                roles = await self._repository.get_role_codes(user.id)
                result = ApplicantUpgradeResult(
                    user_id=user.id,
                    email=user.email,
                    account_type=account_type,
                    roles=roles,
                )
                self._audit_service.record(
                    actor_user_id=user.id,
                    action="auth.account.applicant_upgraded",
                    resource_type="user",
                    resource_id=str(user.id),
                    after={"account_type": account_type.value},
                )
        return result
