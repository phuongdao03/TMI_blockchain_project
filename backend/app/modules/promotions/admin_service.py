from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Literal, cast
from uuid import UUID, uuid4

from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.promotions.audience import utc
from app.modules.promotions.models import VoucherCampaign, VoucherClaim
from app.modules.promotions.schemas import CampaignData, CampaignInput, PromotionPolicy

SERVICES = [
    {"code": "DOSSIER_SUBMISSION", "name": "Phí nộp hồ sơ đề cử"},
    {"code": "DOSSIER_APPROVAL", "name": "Phí xử lý sau phê duyệt"},
    {"code": "MEMBERSHIP", "name": "Hội viên"},
    {"code": "ADVERTISING", "name": "Quảng cáo"},
]


def failure(code: str, message: str, status: int = 409) -> DomainError:
    return DomainError(code=code, message=message, status_code=status)


def campaign_transition(status: str, action: str, *, scheduled: bool) -> str:
    allowed = {
        "publish": (
            {"DRAFT", "PAUSED", "SCHEDULED"},
            "SCHEDULED" if scheduled else "ACTIVE",
        ),
        "pause": ({"ACTIVE", "SCHEDULED"}, "PAUSED"),
        "end": ({"ACTIVE", "SCHEDULED", "PAUSED"}, "ENDED"),
        "archive": ({"DRAFT", "PAUSED", "ENDED"}, "ARCHIVED"),
    }
    if action not in allowed or status not in allowed[action][0]:
        raise failure(
            "PROMOTION_INVALID_TRANSITION",
            "Không thể đổi trạng thái chiến dịch theo yêu cầu.",
        )
    return allowed[action][1]


def campaign_data(row: VoucherCampaign) -> CampaignData:
    return CampaignData(
        id=row.id,
        code=row.code,
        name=row.name or row.title,
        internal_description=row.internal_description,
        title=row.title,
        description=row.description,
        terms=row.terms,
        image_path=row.image_path,
        amount_vnd=row.amount_vnd,
        validity_days=row.validity_days,
        starts_at=utc(row.starts_at) if row.starts_at else None,
        ends_at=utc(row.ends_at) if row.ends_at else None,
        program_type=cast(
            Literal["AUTO", "CLAIM", "CODE", "MANUAL", "FIRST_ORDER"], row.program_type
        ),
        policy=PromotionPolicy.model_validate(row.policy_json),
        status=row.status,
        policy_version=row.policy_version,
        created_at=row.created_at,
        updated_at=row.updated_at,
        budget_reserved_vnd=row.budget_reserved_vnd,
        budget_spent_vnd=row.budget_spent_vnd,
    )


class CampaignService:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def required(
        self, campaign_id: UUID, *, lock: bool = False
    ) -> VoucherCampaign:
        query = select(VoucherCampaign).where(VoucherCampaign.id == campaign_id)
        if lock:
            query = query.with_for_update()
        row = await self.session.scalar(query)
        if row is None:
            raise failure("PROMOTION_NOT_FOUND", "Không tìm thấy chiến dịch.", 404)
        return row

    def audit(
        self,
        actor: UUID,
        action: str,
        row: VoucherCampaign,
        before: Mapping[str, object] | None = None,
    ) -> None:
        AuditService(self.session).record(
            actor_user_id=actor,
            action=f"promotion.{action}",
            resource_type="promotion_campaign",
            resource_id=str(row.id),
            before=dict(before) if before is not None else None,
            after={
                "code": row.code,
                "status": row.status,
                "policyVersion": row.policy_version,
                "policy": row.policy_json,
            },
        )

    async def save(
        self, payload: CampaignInput, actor: UUID, campaign_id: UUID | None = None
    ) -> VoucherCampaign:
        existing = await self.session.scalar(
            select(VoucherCampaign).where(VoucherCampaign.code == payload.code)
        )
        if existing and existing.id != campaign_id:
            raise failure("PROMOTION_CODE_EXISTS", "Mã chiến dịch đã tồn tại.")
        new_policy = payload.policy.model_dump(mode="json", by_alias=False)
        if payload.policy.public_code:
            campaigns = await self.session.scalars(
                select(VoucherCampaign).where(VoucherCampaign.id != campaign_id)
                if campaign_id
                else select(VoucherCampaign)
            )
            if any(
                PromotionPolicy.model_validate(item.policy_json).public_code
                == payload.policy.public_code
                for item in campaigns
            ):
                raise failure(
                    "PROMOTION_CODE_EXISTS", "Mã voucher công khai đã tồn tại."
                )
        if campaign_id:
            row = await self.required(campaign_id, lock=True)
            if row.status in {"ENDED", "ARCHIVED"}:
                raise failure(
                    "PROMOTION_READ_ONLY", "Chiến dịch đã kết thúc chỉ có thể sao chép."
                )
            before = {
                "policy": row.policy_json,
                "title": row.title,
                "imagePath": row.image_path,
            }
            issued = await self.session.scalar(
                select(VoucherClaim.id)
                .where(VoucherClaim.campaign_id == row.id)
                .limit(1)
            )
            if issued:
                old_policy = PromotionPolicy.model_validate(row.policy_json)
                core_old = old_policy.model_dump(
                    mode="json", exclude={"presentation", "budget_vnd"}
                )
                core_new = payload.policy.model_dump(
                    mode="json", exclude={"presentation", "budget_vnd"}
                )
                if (
                    core_old != core_new
                    or row.amount_vnd != payload.amount_vnd
                    or row.validity_days != payload.validity_days
                    or row.program_type != payload.program_type
                    or row.code != payload.code
                ):
                    raise failure(
                        "PROMOTION_POLICY_LOCKED",
                        (
                            "Chiến dịch đã cấp voucher: hãy sao chép "
                            "để đổi điều kiện cốt lõi."
                        ),
                    )
                if old_policy.budget_vnd is not None and (
                    payload.policy.budget_vnd is None
                    or payload.policy.budget_vnd < old_policy.budget_vnd
                ):
                    raise failure(
                        "PROMOTION_POLICY_LOCKED",
                        "Không giảm ngân sách đã công bố sau khi cấp voucher.",
                    )
            row.policy_version += 1
        else:
            row = VoucherCampaign(
                id=uuid4(),
                status="DRAFT",
                active=False,
                created_by=actor,
                policy_version=1,
            )
            self.session.add(row)
            before = None
        for key, value in payload.model_dump(
            exclude={"policy"}, by_alias=False
        ).items():
            setattr(row, key, value)
        row.policy_json = new_policy
        row.public_code = payload.policy.public_code
        committed = (row.budget_reserved_vnd or 0) + (row.budget_spent_vnd or 0)
        if (
            payload.policy.budget_vnd is not None
            and payload.policy.budget_vnd < committed
        ):
            raise failure(
                "PROMOTION_BUDGET_COMMITTED", "Ngân sách thấp hơn số tiền đã cam kết."
            )
        try:
            await self.session.flush()
            self.audit(actor, "updated" if campaign_id else "created", row, before)
            await self.session.commit()
        except IntegrityError as error:
            await self.session.rollback()
            raise failure(
                "PROMOTION_CODE_EXISTS", "Mã chiến dịch đã tồn tại."
            ) from error
        await self.session.refresh(row)
        return row

    async def transition(
        self, campaign_id: UUID, action: str, actor: UUID
    ) -> VoucherCampaign:
        row = await self.required(campaign_id, lock=True)
        now = datetime.now(UTC)
        policy = PromotionPolicy.model_validate(row.policy_json)
        if action == "publish":
            if row.ends_at and utc(row.ends_at) <= now:
                raise failure(
                    "PROMOTION_EXPIRED", "Chiến dịch đã hết thời gian hiệu lực."
                )
            if (
                row.code == "EARLY_MEMBER_2026"
                and policy.audience.registered_before is None
            ):
                raise failure(
                    "PROMOTION_CUTOFF_REQUIRED",
                    "Hãy chọn thời điểm cutoff và xem trước đối tượng.",
                )
            if policy.fixed_expires_at and policy.fixed_expires_at <= now:
                raise failure(
                    "PROMOTION_EXPIRED", "Ngày hết hạn voucher phải ở tương lai."
                )
        before = {"status": row.status}
        row.status = campaign_transition(
            row.status,
            action,
            scheduled=bool(row.starts_at and utc(row.starts_at) > now),
        )
        row.active = row.status in {"ACTIVE", "SCHEDULED"}
        self.audit(actor, action, row, before)
        await self.session.commit()
        await self.session.refresh(row)
        return row

    async def copy(self, campaign_id: UUID, actor: UUID) -> VoucherCampaign:
        original = campaign_data(await self.required(campaign_id))
        data = original.model_dump(
            exclude={
                "id",
                "status",
                "policy_version",
                "created_at",
                "updated_at",
                "budget_reserved_vnd",
                "budget_spent_vnd",
            },
            by_alias=False,
        )
        data["code"] = f"{original.code[:45]}_COPY_{uuid4().hex[:8].upper()}"
        data["name"] = f"{original.name[:240]} (bản sao)"
        data["starts_at"] = None
        data["ends_at"] = None
        data["policy"]["public_code"] = None
        if data["program_type"] == "CODE":
            data["program_type"] = "CLAIM"
        return await self.save(CampaignInput.model_validate(data), actor)

    async def list(
        self, *, page: int, page_size: int, search: str = "", status: str | None = None
    ) -> dict[str, object]:
        conditions = []
        if search:
            conditions.append(
                or_(
                    VoucherCampaign.name.ilike(f"%{search}%"),
                    VoucherCampaign.code.ilike(f"%{search}%"),
                )
            )
        if status:
            conditions.append(VoucherCampaign.status == status)
        total = await self.session.scalar(
            select(func.count()).select_from(VoucherCampaign).where(*conditions)
        )
        rows = list(
            await self.session.scalars(
                select(VoucherCampaign)
                .where(*conditions)
                .order_by(VoucherCampaign.created_at.desc(), VoucherCampaign.id)
                .offset((page - 1) * page_size)
                .limit(page_size)
            )
        )
        return {
            "items": [campaign_data(row).model_dump(mode="json") for row in rows],
            "page": page,
            "pageSize": page_size,
            "total": total or 0,
        }
