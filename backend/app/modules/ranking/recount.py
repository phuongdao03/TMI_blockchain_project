from dataclasses import dataclass
from typing import Protocol
from uuid import UUID

from app.core.errors import DomainError
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal

RANKING_RECOUNT_ROLES = frozenset({"SUPER_ADMIN"})


@dataclass(frozen=True, slots=True)
class RankingRecountRequest:
    campaign_id: UUID
    status: str = "queued"


class RankingRecountEnqueuer(Protocol):
    def __call__(
        self,
        campaign_id: UUID,
        actor_user_id: UUID,
        request_id: str | None,
    ) -> None: ...


class RankingRecountService:
    def __init__(self, *, enqueue: RankingRecountEnqueuer) -> None:
        self._enqueue = enqueue

    async def request(
        self,
        principal: AuthPrincipal,
        campaign_id: UUID,
        *,
        request_id: str | None = None,
    ) -> RankingRecountRequest:
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission="ranking.manage", compatible_roles=RANKING_RECOUNT_ROLES
            ),
            lambda: DomainError(
                code="RANKING_RECOUNT_FORBIDDEN",
                message="Ranking recount is forbidden.",
                status_code=403,
            ),
        )
        self._enqueue(campaign_id, principal.user_id, request_id)
        return RankingRecountRequest(campaign_id=campaign_id)
