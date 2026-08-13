from datetime import datetime
from typing import cast
from uuid import UUID

from sqlalchemy import exists, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.council.models import (
    CouncilCase,
    CouncilCaseConflict,
    CouncilSession,
    CouncilSessionMember,
    CouncilSessionStatus,
    CouncilVote,
)
from app.modules.dossiers.models import Dossier, DossierVersion


class CouncilRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    def add_session(self, council_session: CouncilSession) -> None:
        self._session.add(council_session)

    def add_member(self, member: CouncilSessionMember) -> None:
        self._session.add(member)

    def add_case(self, council_case: CouncilCase) -> None:
        self._session.add(council_case)

    def add_conflict(self, conflict: CouncilCaseConflict) -> None:
        self._session.add(conflict)

    def add_vote(self, vote: CouncilVote) -> None:
        self._session.add(vote)

    async def get_active_member(self, user_id: UUID) -> User | None:
        return cast(
            User | None,
            await self._session.scalar(
                select(User)
                .join(UserRole, UserRole.user_id == User.id)
                .join(Role, Role.id == UserRole.role_id)
                .where(
                    User.id == user_id,
                    User.status == UserStatus.ACTIVE,
                    Role.code == "COUNCIL_MEMBER",
                )
            ),
        )

    async def get_session(
        self,
        session_id: UUID,
        *,
        for_update: bool = False,
    ) -> CouncilSession | None:
        statement = select(CouncilSession).where(CouncilSession.id == session_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(CouncilSession | None, await self._session.scalar(statement))

    async def get_membership(
        self,
        session_id: UUID,
        member_user_id: UUID,
        *,
        for_update: bool = False,
    ) -> CouncilSessionMember | None:
        statement = select(CouncilSessionMember).where(
            CouncilSessionMember.session_id == session_id,
            CouncilSessionMember.member_user_id == member_user_id,
        )
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(
            CouncilSessionMember | None,
            await self._session.scalar(statement),
        )

    async def count_members(self, session_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(CouncilSessionMember)
            .where(CouncilSessionMember.session_id == session_id)
        )
        return int(total or 0)

    async def count_attendees(self, session_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(CouncilSessionMember)
            .where(
                CouncilSessionMember.session_id == session_id,
                CouncilSessionMember.attendance_confirmed_at.is_not(None),
            )
        )
        return int(total or 0)

    async def list_members(
        self,
        session_id: UUID,
    ) -> tuple[CouncilSessionMember, ...]:
        rows = await self._session.scalars(
            select(CouncilSessionMember)
            .where(CouncilSessionMember.session_id == session_id)
            .order_by(CouncilSessionMember.member_user_id)
        )
        return tuple(rows.all())

    async def get_case(
        self,
        case_id: UUID,
        *,
        for_update: bool = False,
    ) -> CouncilCase | None:
        statement = select(CouncilCase).where(CouncilCase.id == case_id)
        if for_update:
            statement = statement.with_for_update().execution_options(
                populate_existing=True
            )
        return cast(CouncilCase | None, await self._session.scalar(statement))

    async def get_session_case_for_version(
        self,
        session_id: UUID,
        dossier_version_id: UUID,
    ) -> CouncilCase | None:
        return cast(
            CouncilCase | None,
            await self._session.scalar(
                select(CouncilCase).where(
                    CouncilCase.session_id == session_id,
                    CouncilCase.dossier_version_id == dossier_version_id,
                )
            ),
        )

    async def list_cases(self, session_id: UUID) -> tuple[CouncilCase, ...]:
        rows = await self._session.scalars(
            select(CouncilCase)
            .where(CouncilCase.session_id == session_id)
            .order_by(CouncilCase.id)
        )
        return tuple(rows.all())

    async def count_cases(self, session_id: UUID) -> int:
        total = await self._session.scalar(
            select(func.count())
            .select_from(CouncilCase)
            .where(CouncilCase.session_id == session_id)
        )
        return int(total or 0)

    async def get_conflict(
        self,
        case_id: UUID,
        member_user_id: UUID,
    ) -> CouncilCaseConflict | None:
        return cast(
            CouncilCaseConflict | None,
            await self._session.scalar(
                select(CouncilCaseConflict).where(
                    CouncilCaseConflict.case_id == case_id,
                    CouncilCaseConflict.member_user_id == member_user_id,
                )
            ),
        )

    async def list_conflicts(
        self,
        case_ids: tuple[UUID, ...],
    ) -> tuple[CouncilCaseConflict, ...]:
        if not case_ids:
            return ()
        rows = await self._session.scalars(
            select(CouncilCaseConflict)
            .where(CouncilCaseConflict.case_id.in_(case_ids))
            .order_by(
                CouncilCaseConflict.case_id,
                CouncilCaseConflict.member_user_id,
            )
        )
        return tuple(rows.all())

    async def get_vote(
        self,
        case_id: UUID,
        member_user_id: UUID,
    ) -> CouncilVote | None:
        return cast(
            CouncilVote | None,
            await self._session.scalar(
                select(CouncilVote).where(
                    CouncilVote.case_id == case_id,
                    CouncilVote.member_user_id == member_user_id,
                )
            ),
        )

    async def list_votes(
        self,
        case_ids: tuple[UUID, ...],
    ) -> tuple[CouncilVote, ...]:
        if not case_ids:
            return ()
        rows = await self._session.scalars(
            select(CouncilVote)
            .where(CouncilVote.case_id.in_(case_ids))
            .order_by(CouncilVote.case_id, CouncilVote.member_user_id)
        )
        return tuple(rows.all())

    async def get_dossier(self, dossier_id: UUID) -> Dossier | None:
        return cast(
            Dossier | None,
            await self._session.scalar(
                select(Dossier).where(
                    Dossier.id == dossier_id,
                    Dossier.deleted_at.is_(None),
                )
            ),
        )

    async def get_version(
        self,
        dossier_id: UUID,
        version_no: int,
    ) -> DossierVersion | None:
        return cast(
            DossierVersion | None,
            await self._session.scalar(
                select(DossierVersion).where(
                    DossierVersion.dossier_id == dossier_id,
                    DossierVersion.version_no == version_no,
                )
            ),
        )

    async def list_sessions(
        self,
        *,
        member_user_id: UUID | None,
        status: CouncilSessionStatus | None,
        offset: int,
        limit: int,
    ) -> tuple[
        tuple[tuple[CouncilSession, int, int, datetime | None], ...],
        int,
    ]:
        criteria = []
        if status is not None:
            criteria.append(CouncilSession.status == status)
        if member_user_id is not None:
            criteria.append(
                exists(
                    select(CouncilSessionMember.id).where(
                        CouncilSessionMember.session_id == CouncilSession.id,
                        CouncilSessionMember.member_user_id == member_user_id,
                    )
                )
            )
        total = await self._session.scalar(
            select(func.count()).select_from(CouncilSession).where(*criteria)
        )
        sessions = tuple(
            (
                await self._session.scalars(
                    select(CouncilSession)
                    .where(*criteria)
                    .order_by(
                        CouncilSession.scheduled_at.desc(),
                        CouncilSession.id.desc(),
                    )
                    .offset(offset)
                    .limit(limit)
                )
            ).all()
        )
        if not sessions:
            return (), int(total or 0)
        session_ids = tuple(item.id for item in sessions)
        counts = await self._session.execute(
            select(
                CouncilSessionMember.session_id,
                func.count().label("member_count"),
                func.count(CouncilSessionMember.attendance_confirmed_at).label(
                    "attendance_count"
                ),
            )
            .where(CouncilSessionMember.session_id.in_(session_ids))
            .group_by(CouncilSessionMember.session_id)
        )
        count_map = {
            row.session_id: (int(row.member_count), int(row.attendance_count))
            for row in counts
        }
        attendance_map: dict[UUID, datetime | None] = {}
        if member_user_id is not None:
            rows = await self._session.execute(
                select(
                    CouncilSessionMember.session_id,
                    CouncilSessionMember.attendance_confirmed_at,
                ).where(
                    CouncilSessionMember.session_id.in_(session_ids),
                    CouncilSessionMember.member_user_id == member_user_id,
                )
            )
            attendance_map = {
                row.session_id: row.attendance_confirmed_at for row in rows
            }
        return (
            tuple(
                (
                    item,
                    count_map[item.id][0],
                    count_map[item.id][1],
                    attendance_map.get(item.id),
                )
                for item in sessions
            ),
            int(total or 0),
        )

    async def list_case_rows(
        self,
        session_id: UUID,
    ) -> tuple[tuple[CouncilCase, Dossier, DossierVersion], ...]:
        rows = await self._session.execute(
            select(CouncilCase, Dossier, DossierVersion)
            .join(Dossier, Dossier.id == CouncilCase.dossier_id)
            .join(
                DossierVersion,
                DossierVersion.id == CouncilCase.dossier_version_id,
            )
            .where(CouncilCase.session_id == session_id)
            .order_by(CouncilCase.id)
        )
        return tuple(rows.tuples().all())
