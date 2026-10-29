import hashlib
import json
from collections import Counter
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.promotions.distribution_models import (
    PromotionAudiencePreview,
    PromotionDistributionJob,
)
from app.modules.promotions.models import VoucherCampaign, VoucherClaim
from app.modules.promotions.schemas import PromotionPolicy

MAX_AUDIENCE = 50_000


def _conflict(message: str) -> DomainError:
    return DomainError(
        code="PROMOTION_DISTRIBUTION_CONFLICT", message=message, status_code=409
    )


def _selector_hash(user_ids: list[str] | None) -> str:
    return hashlib.sha256(
        json.dumps(
            sorted(set(user_ids)) if user_ids is not None else None,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


class PromotionDistributionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def _campaign(self, campaign_id: UUID) -> VoucherCampaign:
        row = await self.session.get(VoucherCampaign, campaign_id)
        if row is None:
            raise DomainError(
                code="PROMOTION_NOT_FOUND",
                message="Không tìm thấy chiến dịch.",
                status_code=404,
            )
        return row

    async def preview(
        self, campaign_id: UUID, *, actor_id: UUID, user_ids: list[str] | None = None
    ) -> dict[str, object]:
        from app.modules.promotions.audience import recipient_eligibility
        from app.modules.promotions.schemas import PromotionPolicy

        recent = await self.session.scalar(
            select(func.count())
            .select_from(PromotionAudiencePreview)
            .where(
                PromotionAudiencePreview.actor_id == actor_id,
                PromotionAudiencePreview.created_at
                >= datetime.now(UTC) - timedelta(minutes=1),
            )
        )
        if int(recent or 0) >= 10:
            raise DomainError(
                code="PROMOTION_PREVIEW_RATE_LIMIT",
                message="Bạn xem trước quá nhanh. Vui lòng thử lại sau một phút.",
                status_code=429,
            )

        campaign = await self._campaign(campaign_id)
        policy = PromotionPolicy.model_validate(campaign.policy_json or {})
        counts: Counter[str] = Counter()
        candidates: list[UUID] = []
        if user_ids is not None:
            seen: set[UUID] = set()
            for raw in user_ids:
                try:
                    candidate = UUID(raw.strip())
                except (ValueError, AttributeError):
                    counts["INVALID_USER_ID"] += 1
                    continue
                if candidate in seen:
                    counts["DUPLICATE_USER_ID"] += 1
                    continue
                seen.add(candidate)
                candidates.append(candidate)
        else:
            count = await self.session.scalar(select(func.count()).select_from(User))
            if int(count or 0) > MAX_AUDIENCE:
                raise DomainError(
                    code="PROMOTION_AUDIENCE_TOO_LARGE",
                    message=(
                        "Vui lòng thu hẹp đối tượng hoặc chia thành danh "
                        "sách tối đa 50.000 tài khoản."
                    ),
                    status_code=422,
                )
            candidates = list(
                await self.session.scalars(select(User.id).order_by(User.id))
            )
        if len(candidates) > MAX_AUDIENCE:
            raise DomainError(
                code="PROMOTION_AUDIENCE_TOO_LARGE",
                message="Danh sách tối đa 50.000 tài khoản.",
                status_code=422,
            )
        eligible: list[str] = []
        sample: list[dict[str, str]] = []
        for user_id in candidates:
            allowed, reason = await recipient_eligibility(self.session, user_id, policy)
            if allowed:
                # Repeated bulk issuing should not present already-issued
                # vouchers as new benefits or inflate issuance counters.
                existing = await self.session.scalar(
                    select(VoucherClaim.id).where(
                        VoucherClaim.user_id == user_id,
                        VoucherClaim.campaign_id == campaign_id,
                    )
                )
                if existing is not None:
                    allowed, reason = False, "ALREADY_ISSUED"
            if allowed:
                eligible.append(str(user_id))
            else:
                counts[reason] += 1
            if len(sample) < 20:
                user = await self.session.get(User, user_id)
                sample.append(
                    {
                        "id": str(user_id),
                        "email": user.email if user else "",
                        "reason": "ELIGIBLE" if allowed else reason,
                    }
                )
        preview = PromotionAudiencePreview(
            campaign_id=campaign_id,
            actor_id=actor_id,
            policy_version=campaign.policy_version,
            selector_hash=_selector_hash(user_ids),
            candidates_json=eligible,
            eligible_count=len(eligible),
            excluded_count=sum(counts.values()),
            expires_at=datetime.now(UTC) + timedelta(minutes=15),
        )
        self.session.add(preview)
        await self.session.commit()
        await self.session.refresh(preview)
        return {
            "eligibleCount": len(eligible),
            "excludedCount": sum(counts.values()),
            "nominalValueVnd": len(eligible)
            * campaign.amount_vnd
            * PromotionPolicy.model_validate(campaign.policy_json).vouchers_per_user,
            "exclusionReasons": dict(counts),
            "sample": sample,
            "previewToken": str(preview.id),
            "expiresAt": _utc(preview.expires_at).isoformat(),
        }

    async def issue(
        self,
        campaign_id: UUID,
        *,
        actor_id: UUID,
        preview_token: UUID,
        idempotency_key: str,
        reason: str,
        user_ids: list[str] | None = None,
    ) -> PromotionDistributionJob:
        if not 8 <= len(idempotency_key) <= 128 or not 5 <= len(reason.strip()) <= 255:
            raise DomainError(
                code="PROMOTION_ISSUE_INVALID",
                message="Cần khóa yêu cầu hợp lệ và lý do cấp từ 5 đến 500 ký tự.",
                status_code=422,
            )
        # Serialize same-admin requests, including requests from another tab.
        await self.session.scalar(
            select(User.id).where(User.id == actor_id).with_for_update()
        )
        existing = await self.session.scalar(
            select(PromotionDistributionJob).where(
                PromotionDistributionJob.actor_id == actor_id,
                PromotionDistributionJob.idempotency_key == idempotency_key,
            )
        )
        if existing is not None:
            if (
                existing.campaign_id != campaign_id
                or existing.preview_id != preview_token
            ):
                raise _conflict("Khóa yêu cầu đã được dùng cho một lần phát khác.")
            return existing
        campaign = await self._campaign(campaign_id)
        preview = await self.session.get(PromotionAudiencePreview, preview_token)
        if (
            preview is None
            or preview.actor_id != actor_id
            or preview.campaign_id != campaign_id
            or _utc(preview.expires_at) <= datetime.now(UTC)
            or preview.policy_version != campaign.policy_version
            or preview.selector_hash != _selector_hash(user_ids)
        ):
            raise _conflict(
                "Bản xem trước không hợp lệ hoặc đã hết hạn. Vui lòng xem trước lại."
            )
        if campaign.status not in {"ACTIVE", "SCHEDULED"}:
            raise _conflict("Chỉ phát voucher sau khi chiến dịch được xuất bản.")
        job = PromotionDistributionJob(
            campaign_id=campaign_id,
            actor_id=actor_id,
            preview_id=preview.id,
            idempotency_key=idempotency_key,
            reason=reason.strip(),
            candidates_json=list(preview.candidates_json),
            total=preview.eligible_count,
        )
        self.session.add(job)
        await self.session.flush()
        AuditService(self.session).record(
            actor_user_id=actor_id,
            action="promotion.distribution.started",
            resource_type="promotion",
            resource_id=str(campaign_id),
            after={"job_id": str(job.id), "total": job.total, "reason": job.reason},
        )
        await self.session.commit()
        await self.session.refresh(job)
        return job

    async def run_batch(self, job_id: UUID, *, batch_size: int = 100) -> bool:
        from app.modules.promotions.service import VoucherService

        # The job row and all claims in a batch commit together. A crashed
        # worker safely repeats the batch, while the unique claim constraint
        # prevents duplicates from other jobs or manual issuance.
        job = await self.session.scalar(
            select(PromotionDistributionJob)
            .where(PromotionDistributionJob.id == job_id)
            .with_for_update()
        )
        if job is None or job.status == "COMPLETED":
            return True
        campaign = await self._campaign(job.campaign_id)
        preview = await self.session.get(PromotionAudiencePreview, job.preview_id)
        if preview is None or preview.policy_version != campaign.policy_version:
            job.status = "FAILED"
            job.errors_json = [{"code": "POLICY_CHANGED", "userId": ""}]
            await self.session.commit()
            return True
        now = datetime.now(UTC)
        if campaign.status not in {"ACTIVE", "SCHEDULED"} or (
            campaign.starts_at and _utc(campaign.starts_at) > now
        ):
            job.status = "PAUSED"
            await self.session.commit()
            return True
        job.status = "RUNNING"
        errors = list(job.errors_json)
        stop = min(job.cursor + min(max(batch_size, 1), 500), len(job.candidates_json))
        while job.cursor < stop:
            user_id = UUID(job.candidates_json[job.cursor])
            issued = 0
            try:
                async with self.session.begin_nested():
                    policy = PromotionPolicy.model_validate(campaign.policy_json)
                    for slot in range(1, policy.vouchers_per_user + 1):
                        existing = await self.session.scalar(
                            select(VoucherClaim.id).where(
                                VoucherClaim.campaign_id == job.campaign_id,
                                VoucherClaim.user_id == user_id,
                                VoucherClaim.issuance_slot == slot,
                            )
                        )
                        if existing is None:
                            await VoucherService(self.session).issue(
                                user_id,
                                job.campaign_id,
                                reason=job.reason,
                                commit=False,
                                issuance_slot=slot,
                            )
                            issued += 1
            except DomainError as error:
                issued = 0
                job.failed_count += 1
                if len(errors) < 100:
                    errors.append({"userId": str(user_id), "code": error.code})
            if issued:
                job.issued_count += issued
            else:
                job.skipped_count += 1
            job.cursor += 1
        job.errors_json = errors
        if job.cursor >= len(job.candidates_json):
            job.status = "COMPLETED"
            AuditService(self.session).record(
                actor_user_id=job.actor_id,
                action="promotion.distribution.completed",
                resource_type="promotion",
                resource_id=str(job.campaign_id),
                after={
                    "job_id": str(job.id),
                    "issued": job.issued_count,
                    "skipped": job.skipped_count,
                },
            )
        await self.session.commit()
        return job.status == "COMPLETED"

    async def jobs(
        self, campaign_id: UUID, *, page: int, page_size: int
    ) -> tuple[list[PromotionDistributionJob], int]:
        total = await self.session.scalar(
            select(func.count())
            .select_from(PromotionDistributionJob)
            .where(PromotionDistributionJob.campaign_id == campaign_id)
        )
        rows = await self.session.scalars(
            select(PromotionDistributionJob)
            .where(PromotionDistributionJob.campaign_id == campaign_id)
            .order_by(PromotionDistributionJob.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        return list(rows), int(total or 0)
