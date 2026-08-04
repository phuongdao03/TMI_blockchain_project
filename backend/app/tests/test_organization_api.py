import asyncio
from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx

from app.core.config import Settings
from app.core.health import HealthService
from app.main import create_application
from app.modules.auth.dependencies import (
    get_csrf_protected_principal,
    get_current_principal,
)
from app.modules.auth.session_service import AuthPrincipal
from app.modules.organizations.dependencies import get_organization_service
from app.modules.organizations.errors import OrganizationForbiddenError
from app.modules.organizations.models import (
    MembershipRole,
    MembershipStatus,
    OrganizationStatus,
)
from app.modules.organizations.types import (
    CreateOrganization,
    MemberView,
    OrganizationChanges,
    OrganizationView,
    Page,
    UpsertMember,
)


class StubOrganizationService:
    def __init__(self, principal: AuthPrincipal) -> None:
        self.principal = principal
        self.organization_id = uuid4()
        self.member_id = uuid4()
        self.forbidden = False
        self.created: CreateOrganization | None = None
        self.updated: OrganizationChanges | None = None
        self.member: UpsertMember | None = None

    def _require_access(self) -> None:
        if self.forbidden:
            raise OrganizationForbiddenError()

    def _organization(self) -> OrganizationView:
        return OrganizationView(
            id=self.organization_id,
            code="TMI-LAB",
            legal_name="Công ty TMI Lab",
            display_name="TMI Lab",
            tax_code="0312345678",
            status=OrganizationStatus.ACTIVE,
            owner_user_id=self.principal.user_id,
            current_role=MembershipRole.OWNER,
            can_manage_members=True,
        )

    async def create_organization(
        self,
        principal: AuthPrincipal,
        payload: CreateOrganization,
    ) -> OrganizationView:
        self.created = payload
        return self._organization()

    async def list_organizations(
        self,
        principal: AuthPrincipal,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[OrganizationView]:
        return Page(items=(self._organization(),), total=1)

    async def get_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
    ) -> OrganizationView:
        self._require_access()
        return self._organization()

    async def update_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
        changes: OrganizationChanges,
    ) -> OrganizationView:
        self.updated = changes
        return self._organization()

    async def archive_organization(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
    ) -> None:
        return None

    async def list_members(
        self,
        principal: AuthPrincipal,
        organization_id: UUID,
        *,
        page: int = 1,
        page_size: int = 20,
    ) -> Page[MemberView]:
        return Page(
            items=(
                MemberView(
                    user_id=self.member_id,
                    email="member@tmigroup.vn",
                    role_code=MembershipRole.MEMBER,
                    status=MembershipStatus.ACTIVE,
                    joined_at=datetime(2026, 7, 30, 8, 0, tzinfo=UTC),
                ),
            ),
            total=1,
        )

    async def add_member(
        self,
        principal: AuthPrincipal,
        *,
        organization_id: UUID,
        member: UpsertMember,
    ) -> MemberView:
        self.member = member
        return (await self.list_members(principal, organization_id)).items[0]

    async def remove_member(
        self,
        principal: AuthPrincipal,
        *,
        organization_id: UUID,
        user_id: UUID,
    ) -> None:
        return None


async def _request(
    method: str,
    path: str,
    service: StubOrganizationService,
    principal: AuthPrincipal,
    *,
    json: dict[str, object] | None = None,
) -> httpx.Response:
    app = create_application(
        settings=Settings.model_validate({"app_env": "local"}),
        health_service=HealthService({}),
    )
    app.dependency_overrides[get_organization_service] = lambda: service
    app.dependency_overrides[get_current_principal] = lambda: principal
    app.dependency_overrides[get_csrf_protected_principal] = lambda: principal
    transport = httpx.ASGITransport(app=app)
    async with app.router.lifespan_context(app):
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.request(method, path, json=json)


def test_organization_crud_contract() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubOrganizationService(principal)
    base = "/api/v1/organizations"

    created = asyncio.run(
        _request(
            "POST",
            base,
            service,
            principal,
            json={
                "code": "TMI-LAB",
                "legalName": "Công ty TMI Lab",
                "displayName": "TMI Lab",
                "taxCode": "0312345678",
            },
        )
    )
    listed = asyncio.run(_request("GET", base, service, principal))
    detail = asyncio.run(
        _request("GET", f"{base}/{service.organization_id}", service, principal)
    )
    updated = asyncio.run(
        _request(
            "PATCH",
            f"{base}/{service.organization_id}",
            service,
            principal,
            json={"displayName": "TMI Lab mới"},
        )
    )
    archived = asyncio.run(
        _request(
            "DELETE",
            f"{base}/{service.organization_id}",
            service,
            principal,
        )
    )

    assert created.status_code == 201
    assert created.json()["data"]["canManageMembers"] is True
    assert listed.status_code == detail.status_code == updated.status_code == 200
    assert listed.json()["meta"]["total"] == 1
    assert archived.json()["data"] == {"status": "archived"}
    assert service.created is not None
    assert service.created.tax_code == "0312345678"
    assert service.updated is not None
    assert service.updated.provided_fields == {"display_name"}


def test_membership_contract_and_forbidden_response() -> None:
    principal = AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="owner@tmigroup.vn",
        roles=("APPLICANT",),
    )
    service = StubOrganizationService(principal)
    members = f"/api/v1/organizations/{service.organization_id}/members"

    added = asyncio.run(
        _request(
            "POST",
            members,
            service,
            principal,
            json={
                "email": "member@tmigroup.vn",
                "roleCode": "MEMBER",
                "status": "INVITED",
            },
        )
    )
    listed = asyncio.run(_request("GET", members, service, principal))
    removed = asyncio.run(
        _request(
            "DELETE",
            f"{members}/{service.member_id}",
            service,
            principal,
        )
    )
    invalid = asyncio.run(
        _request(
            "POST",
            members,
            service,
            principal,
            json={
                "email": "member@tmigroup.vn",
                "roleCode": "OWNER",
                "status": "ACTIVE",
            },
        )
    )
    service.forbidden = True
    forbidden = asyncio.run(
        _request(
            "GET",
            f"/api/v1/organizations/{service.organization_id}",
            service,
            principal,
        )
    )

    assert added.status_code == 201
    assert listed.status_code == 200
    assert listed.json()["meta"]["pageSize"] == 20
    assert removed.json()["data"] == {"status": "removed"}
    assert invalid.status_code == 422
    assert forbidden.status_code == 403
