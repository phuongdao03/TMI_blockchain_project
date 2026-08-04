from app.core.errors import DomainError


class OrganizationNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_NOT_FOUND",
            message="Organization was not found.",
            status_code=404,
        )


class OrganizationForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_FORBIDDEN",
            message="You cannot manage this organization.",
            status_code=403,
        )


class OrganizationCodeExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_CODE_EXISTS",
            message="Organization code is already in use.",
            status_code=409,
        )


class MembershipExistsError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_MEMBERSHIP_EXISTS",
            message="The user is already an organization member.",
            status_code=409,
        )


class OrganizationMemberNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_MEMBER_NOT_FOUND",
            message="Organization member was not found.",
            status_code=404,
        )


class OrganizationOwnerOrphanError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ORGANIZATION_OWNER_CANNOT_BE_REMOVED",
            message="The organization owner cannot be removed.",
            status_code=409,
        )
