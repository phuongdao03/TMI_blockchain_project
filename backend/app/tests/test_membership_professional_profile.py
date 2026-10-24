import asyncio
from datetime import UTC, datetime, timedelta

import pytest

import app.modules.blockchain.models  # noqa: F401
from app.modules.community.engagement_schemas import CommunityMemberProfileEditRequest
from app.modules.community.engagement_service import CommunityEngagementService
from app.modules.community.errors import CommunityForbiddenError
from app.modules.memberships.models import MembershipPlan, UserMembership
from app.tests.test_payment_service import _service


def test_professional_profile_fields_require_silver_and_are_public() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                service = CommunityEngagementService(session)
                denied_payload = CommunityMemberProfileEditRequest(
                    professional_title="Designer",
                    activity_fields="Craft and heritage",
                )
                with pytest.raises(CommunityForbiddenError):
                    await service.update_member_profile(owner, denied_payload)

                async with session.begin():
                    plan = MembershipPlan(
                        name="Kết nối Bạc",
                        tier="SILVER",
                        amount_minor=490_000,
                        duration_days=365,
                    )
                    session.add(plan)
                    await session.flush()
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=plan.id,
                            tier="SILVER",
                            expires_at=datetime.now(UTC) + timedelta(days=365),
                        )
                    )

                payload = CommunityMemberProfileEditRequest(
                    professional_title="Nhà thiết kế thủ công",
                    organization="Xưởng Việt",
                    activity_fields="Sơn mài, thủ công mỹ nghệ",
                    professional_links=["https://example.vn/portfolio"],
                )
                view = await service.update_member_profile(owner, payload)
                assert view.member.profile.professional_title == "Nhà thiết kế thủ công"
                assert view.member.profile.organization == "Xưởng Việt"
                assert view.member.profile.professional_links == [
                    "https://example.vn/portfolio"
                ]
                public = await service.member_profile(
                    owner.user_id, viewer_user_id=None
                )
                assert public.member.profile.activity_fields == (
                    "Sơn mài, thủ công mỹ nghệ"
                )
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())


def test_professional_profile_rejects_non_https_links() -> None:
    with pytest.raises(ValueError, match="HTTPS URLs"):
        CommunityMemberProfileEditRequest(
            professional_links=["javascript:alert(1)"]
        )


def test_member_directory_requires_gold_and_matches_public_activity_fields() -> None:
    async def exercise() -> None:
        payment, sessions, engine, owner = await _service()
        try:
            async with sessions() as session:
                service = CommunityEngagementService(session)
                with pytest.raises(CommunityForbiddenError):
                    await service.member_directory(
                        owner, query="Design", page=1, page_size=20
                    )

                async with session.begin():
                    plan = MembershipPlan(
                        name="Gold",
                        tier="COMPANION",
                        amount_minor=1_490_000,
                        duration_days=365,
                    )
                    session.add(plan)
                    await session.flush()
                    session.add(
                        UserMembership(
                            user_id=owner.user_id,
                            plan_id=plan.id,
                            tier="COMPANION",
                            expires_at=datetime.now(UTC) + timedelta(days=365),
                        )
                    )

                await service.update_member_profile(
                    owner,
                    CommunityMemberProfileEditRequest(
                        professional_title="Designer",
                        organization="TMI",
                        activity_fields="Craft design",
                    ),
                )
                members, total = await service.member_directory(
                    owner, query="design", page=1, page_size=20
                )
                assert total == 1
                assert members[0].profile.activity_fields == "Craft design"
        finally:
            await payment.close()
            await engine.dispose()

    asyncio.run(exercise())
