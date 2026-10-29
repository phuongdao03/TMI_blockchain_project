from app.core.errors import DomainError
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal


def require_promotion_access(principal: AuthPrincipal, *, write: bool = True) -> None:
    if not write and AuthorizationPolicy.allows_capability(
        principal, PolicyRequirement("promotions.manage")
    ):
        return
    AuthorizationPolicy.require_capability(
        principal,
        PolicyRequirement("promotions.manage" if write else "promotions.read"),
        lambda: DomainError(
            code="PROMOTION_FORBIDDEN",
            message="Bạn không có quyền quản lý khuyến mại.",
            status_code=403,
        ),
    )
