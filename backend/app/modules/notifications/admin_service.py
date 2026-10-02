from datetime import UTC, datetime
from enum import StrEnum
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.hr.models import Employee, EmploymentStatus
from app.modules.notifications.models import Notification


class AnnouncementAudience(StrEnum):
    ALL = "ALL"
    USERS = "USERS"
    EMPLOYEES = "EMPLOYEES"
    INDIVIDUAL = "INDIVIDUAL"


class AdminAnnouncementService:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _recipients(audience: AnnouncementAudience, recipient_user_id: UUID | None):
        employee_exists = exists(
            select(Employee.id).where(
                Employee.user_id == User.id,
                Employee.employment_status == EmploymentStatus.ACTIVE,
            )
        )
        query = select(User.id).where(User.status == UserStatus.ACTIVE)
        if audience == AnnouncementAudience.EMPLOYEES:
            query = query.where(employee_exists)
        elif audience == AnnouncementAudience.USERS:
            query = query.where(~employee_exists)
        elif audience == AnnouncementAudience.INDIVIDUAL:
            if recipient_user_id is None:
                raise DomainError(
                    code="ANNOUNCEMENT_RECIPIENT_REQUIRED",
                    message="Select an account to notify.",
                    status_code=422,
                )
            query = query.where(User.id == recipient_user_id)
        elif recipient_user_id is not None:
            raise DomainError(
                code="ANNOUNCEMENT_RECIPIENT_UNEXPECTED",
                message=(
                    "A recipient can only be selected for an individual announcement."
                ),
                status_code=422,
            )
        return query

    async def preview(
        self, audience: AnnouncementAudience, recipient_user_id: UUID | None = None
    ) -> int:
        async with self._session.begin():
            query = self._recipients(audience, recipient_user_id)
            return int(
                await self._session.scalar(
                    select(func.count()).select_from(query.subquery())
                )
                or 0
            )

    async def send(
        self,
        *,
        audience: AnnouncementAudience,
        recipient_user_id: UUID | None,
        campaign_id: UUID,
        title: str,
        body: str,
        actor_user_id: UUID,
        request_id: str,
        user_agent: str | None,
    ) -> int:
        query = self._recipients(audience, recipient_user_id)
        async with self._session.begin():
            previous = await self._session.scalar(
                select(Notification)
                .where(Notification.source_event_id == campaign_id)
                .limit(1)
            )
            if previous is not None:
                if (
                    previous.type != "admin.announcement"
                    or previous.title != title
                    or previous.body != body
                    or previous.data_json.get("audience") != audience.value
                    or previous.data_json.get("recipientUserId")
                    != (str(recipient_user_id) if recipient_user_id else None)
                ):
                    raise DomainError(
                        code="ANNOUNCEMENT_CAMPAIGN_CONFLICT",
                        message=(
                            "This announcement ID was already used for other content."
                        ),
                        status_code=409,
                    )
                return int(
                    await self._session.scalar(
                        select(func.count(Notification.id)).where(
                            Notification.source_event_id == campaign_id
                        )
                    )
                    or 0
                )

            recipient_ids = (await self._session.scalars(query)).all()
            if not recipient_ids:
                raise DomainError(
                    code="ANNOUNCEMENT_NO_RECIPIENTS",
                    message="No active accounts match the selected audience.",
                    status_code=422,
                )
            now = datetime.now(UTC)
            metadata = {
                "actionPath": "/notifications",
                "audience": audience.value,
                "recipientUserId": str(recipient_user_id)
                if recipient_user_id
                else None,
            }
            self._session.add_all(
                Notification(
                    user_id=user_id,
                    source_event_id=campaign_id,
                    type="admin.announcement",
                    title=title,
                    body=body,
                    data_json=metadata,
                    created_at=now,
                )
                for user_id in recipient_ids
            )
            AuditService(self._session).record(
                actor_user_id=actor_user_id,
                action="admin.announcement.sent",
                resource_type="announcement",
                resource_id=str(campaign_id),
                after={
                    "audience": audience.value,
                    "recipient_count": len(recipient_ids),
                },
                request_id=request_id,
                user_agent=user_agent,
            )
            return len(recipient_ids)
