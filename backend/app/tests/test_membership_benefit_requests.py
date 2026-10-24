import asyncio
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.core.errors import DomainError
from app.modules.auth.session_service import AuthPrincipal
from app.modules.memberships.models import (
    MembershipBenefitRequest,
    MembershipDiamondApplication,
    MembershipPlan,
    UserMembership,
)
from app.modules.memberships.service import MembershipService
from app.modules.payments.errors import PaymentForbiddenError
from app.tests.test_payment_service import ADMIN_ID, _service


def test_membership_benefit_requests_enforce_tier_quota_and_admin_review() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        admin = AuthPrincipal(
            user_id=ADMIN_ID,
            session_id=owner.session_id,
            email="admin@example.vn",
            roles=("SUPER_ADMIN",),
        )
        expires_at = datetime.now(UTC) + timedelta(days=365)
        try:
            async with sessions() as session:
                async with session.begin():
                    companion = MembershipPlan(
                        name="Đồng hành",
                        tier="COMPANION",
                        amount_minor=1_490_000,
                        duration_days=365,
                    )
                    diamond = MembershipPlan(
                        name="Kim cương",
                        tier="PRESTIGE",
                        amount_minor=3_990_000,
                        duration_days=365,
                    )
                    session.add_all([companion, diamond])
                    await session.flush()
                    diamond_id = diamond.id
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=companion.id,
                            tier="COMPANION",
                            expires_at=expires_at,
                        )
                    )
                membership = MembershipService(session)
                need = await membership.submit_benefit_request(
                    owner,
                    benefit="COLLABORATION_NEED",
                    statement="Tìm đối tác phân phối sản phẩm thủ công.",
                )
                need_id = need.id
                need_statement = need.statement
                with pytest.raises(PaymentForbiddenError):
                    await membership.submit_benefit_request(
                        owner,
                        benefit="ADVISORY_SESSION",
                        statement="Xin tư vấn.",
                    )
                approved = await membership.review_benefit_request(
                    admin,
                    need_id,
                    decision="approve",
                    note="Nhu cầu đã được duyệt để hiển thị.",
                )
                assert approved.status == "APPROVED"
                board = await membership.collaboration_needs(owner)
                assert board[0]["statement"] == need_statement

                async with session.begin():
                    membership_row = await session.get(UserMembership, owner.user_id)
                    assert membership_row is not None
                    membership_row.plan_id = diamond_id
                    membership_row.tier = "PRESTIGE"
                    session.add(
                        MembershipDiamondApplication(
                            user_id=owner.user_id,
                            statement="Approved member.",
                            status="APPROVED",
                        )
                    )
                advisory = await membership.submit_benefit_request(
                    owner,
                    benefit="ADVISORY_SESSION",
                    statement="Cần tư vấn chiến lược phát triển.",
                )
                assert advisory.status == "PENDING"
                with pytest.raises(DomainError):
                    await membership.submit_benefit_request(
                        owner,
                        benefit="ADVISORY_SESSION",
                        statement="Gửi lần hai trong cùng chu kỳ.",
                    )
                intro_requests = [
                    await membership.submit_benefit_request(
                        owner,
                        benefit="FACILITATED_INTRODUCTION",
                        statement=f"Đề xuất kết nối {index}.",
                    )
                    for index in range(2)
                ]
                assert len(intro_requests) == 2
                with pytest.raises(DomainError):
                    await membership.submit_benefit_request(
                        owner,
                        benefit="FACILITATED_INTRODUCTION",
                        statement="Đề xuất thứ ba.",
                    )
                rows = await session.scalars(
                    select(MembershipBenefitRequest).where(
                        MembershipBenefitRequest.user_id == owner.user_id
                    )
                )
                assert len(list(rows)) == 4
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
