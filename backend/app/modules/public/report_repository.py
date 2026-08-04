from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.public.models import ContentReport, ContentReportStatus, PublicWork


@dataclass(frozen=True, slots=True)
class ContentReportRow:
    report: ContentReport
    work_title: str
    work_slug: str
    work_version: int


class ContentReportRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add(self, report: ContentReport) -> None:
        self._session.add(report)

    async def duplicate_exists(self, dedup_key: str) -> bool:
        return bool(
            await self._session.scalar(
                select(func.count(ContentReport.id)).where(
                    ContentReport.dedup_key == dedup_key
                )
            )
        )

    async def get(
        self, report_id: UUID, *, for_update: bool = False
    ) -> ContentReportRow | None:
        statement = (
            select(ContentReport, PublicWork.title, PublicWork.slug, PublicWork.version)
            .join(PublicWork, PublicWork.id == ContentReport.public_work_id)
            .where(ContentReport.id == report_id)
        )
        if for_update:
            statement = statement.with_for_update()
        row = (await self._session.execute(statement)).one_or_none()
        return ContentReportRow(row[0], row[1], row[2], row[3]) if row else None

    async def list(
        self,
        *,
        status: ContentReportStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[tuple[ContentReportRow, ...], int]:
        filters = (ContentReport.status == status,) if status else ()
        statement = (
            select(ContentReport, PublicWork.title, PublicWork.slug, PublicWork.version)
            .join(PublicWork, PublicWork.id == ContentReport.public_work_id)
            .where(*filters)
            .order_by(ContentReport.created_at.desc(), ContentReport.id)
            .offset(offset)
            .limit(limit)
        )
        rows = (await self._session.execute(statement)).all()
        total = await self._session.scalar(
            select(func.count(ContentReport.id)).where(*filters)
        )
        return tuple(
            ContentReportRow(row[0], row[1], row[2], row[3]) for row in rows
        ), int(total or 0)
