import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.db.base import Base
from app.db.outbox import OutboxEvent
from app.modules.auth.models import Role, User, UserRole, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.council.errors import (
    CouncilConflictError,
    CouncilForbiddenError,
    CouncilValidationError,
)
from app.modules.council.models import (
    CouncilCase,
    CouncilCaseConflict,
    CouncilCaseDecision,
    CouncilSession,
    CouncilSessionStatus,
    CouncilVote,
    CouncilVoteChoice,
)
from app.modules.council.service import CouncilService
from app.modules.council.types import CouncilCaseView
from app.modules.dossiers.models import (
    Category,
    Dossier,
    DossierStatus,
    DossierVersion,
)

NOW = datetime(2026, 8, 2, 8, 0, tzinfo=UTC)
OUTBOX_KEY = b"council-outbox-encryption-key!!!"


async def _setup() -> tuple[
    CouncilService,
    async_sessionmaker[AsyncSession],
    AsyncEngine,
    dict[str, User],
    Dossier,
    DossierVersion,
]:
    engine = create_async_engine("sqlite+aiosqlite://")
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)

    users = {
        name: User(
            id=uuid4(),
            email=f"{name}@tmigroup.vn",
            password_hash="not-used",
            status=UserStatus.ACTIVE,
        )
        for name in ("owner", "secretary", "member1", "member2", "outsider")
    }
    category = Category(id=uuid4(), code="COUNCIL", name="Council")
    dossier = Dossier(
        id=uuid4(),
        code="TMI-2026-COUNCIL0001",
        owner_user_id=users["owner"].id,
        category_id=category.id,
        title="Dossier awaiting council",
        current_version_no=1,
        submitted_at=NOW,
    )
    dossier._set_status_from_workflow(DossierStatus.UNDER_REVIEW)
    version = DossierVersion(
        id=uuid4(),
        dossier_id=dossier.id,
        version_no=1,
        snapshot_json={"schemaVersion": 1, "dossier": {"title": dossier.title}},
        canonical_hash="b" * 64,
        submitted_by=users["owner"].id,
        submitted_at=NOW,
    )
    member_role = Role(id=uuid4(), code="COUNCIL_MEMBER")
    async with sessions() as session:
        session.add_all(
            [
                *users.values(),
                category,
                dossier,
                version,
                member_role,
                UserRole(
                    user_id=users["member1"].id,
                    role_id=member_role.id,
                ),
                UserRole(
                    user_id=users["member2"].id,
                    role_id=member_role.id,
                ),
            ]
        )
        await session.commit()

    return (
        CouncilService(
            session=sessions(),
            payload_cipher=OutboxPayloadCipher(
                key=OUTBOX_KEY,
                key_id="test-council-key",
            ),
            clock=lambda: NOW,
        ),
        sessions,
        engine,
        users,
        dossier,
        version,
    )


def _principal(user: User, *roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=user.id,
        session_id=uuid4(),
        email=user.email,
        roles=roles,
    )


def test_secretary_creates_session_adds_case_and_opens_with_quorum() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, version = await _setup()
        secretary = _principal(users["secretary"], "COUNCIL_SECRETARY")
        created = await service.create_session(
            secretary,
            code="HD-2026-001",
            title="August council",
            scheduled_at=NOW + timedelta(days=1),
            quorum_required=2,
            member_user_ids=(users["member1"].id, users["member2"].id),
        )
        case = await service.add_case(secretary, created.id, dossier.id)

        assert created.status is CouncilSessionStatus.DRAFT
        assert created.member_count == 2
        assert case.dossier_version_id == version.id

        for name in ("member1", "member2"):
            member = _principal(users[name], "COUNCIL_MEMBER")
            attendance = await service.confirm_attendance(member, created.id)
            assert attendance.attendance_confirmed_at == NOW

        opened = await service.open_session(secretary, created.id)
        assert opened.status is CouncilSessionStatus.OPEN
        assert opened.opened_at == NOW

        async with sessions() as session:
            stored_dossier = await session.get(Dossier, dossier.id)
            assert stored_dossier is not None
            assert stored_dossier.status is DossierStatus.COUNCIL_REVIEW
            assert (
                await session.scalar(select(func.count()).select_from(CouncilCase))
                == 1
            )

        with pytest.raises(CouncilConflictError):
            await service.add_case(secretary, created.id, dossier.id)
        with pytest.raises(CouncilConflictError):
            await service.confirm_attendance(
                _principal(users["member1"], "COUNCIL_MEMBER"),
                created.id,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_session_creation_and_open_enforce_role_members_and_quorum() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, _ = await _setup()
        outsider = _principal(users["outsider"], "APPLICANT")
        secretary = _principal(users["secretary"], "COUNCIL_SECRETARY")

        with pytest.raises(CouncilForbiddenError):
            await service.create_session(
                outsider,
                code="HD-2026-001",
                title="Forbidden",
                scheduled_at=NOW,
                quorum_required=1,
                member_user_ids=(users["member1"].id,),
            )
        with pytest.raises(CouncilValidationError):
            await service.create_session(
                secretary,
                code="HD-2026-001",
                title="Invalid member",
                scheduled_at=NOW,
                quorum_required=1,
                member_user_ids=(users["outsider"].id,),
            )
        with pytest.raises(CouncilValidationError):
            await service.create_session(
                secretary,
                code="HD-2026-001",
                title="Invalid quorum",
                scheduled_at=NOW,
                quorum_required=2,
                member_user_ids=(users["member1"].id,),
            )

        created = await service.create_session(
            secretary,
            code="HD-2026-001",
            title="Quorum protected",
            scheduled_at=NOW,
            quorum_required=2,
            member_user_ids=(users["member1"].id, users["member2"].id),
        )
        await service.add_case(secretary, created.id, dossier.id)
        await service.confirm_attendance(
            _principal(users["member1"], "COUNCIL_MEMBER"),
            created.id,
        )
        with pytest.raises(CouncilConflictError):
            await service.open_session(secretary, created.id)

        async with sessions() as session:
            stored = await session.get(CouncilSession, created.id)
            assert stored is not None
            assert stored.status is CouncilSessionStatus.DRAFT

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


async def _open_two_member_case(
    service: CouncilService,
    users: dict[str, User],
    dossier: Dossier,
) -> tuple[AuthPrincipal, CouncilCaseView]:
    secretary = _principal(users["secretary"], "COUNCIL_SECRETARY")
    created = await service.create_session(
        secretary,
        code="HD-2026-001",
        title="Voting session",
        scheduled_at=NOW,
        quorum_required=2,
        member_user_ids=(users["member1"].id, users["member2"].id),
    )
    council_case = await service.add_case(secretary, created.id, dossier.id)
    for name in ("member1", "member2"):
        await service.confirm_attendance(
            _principal(users[name], "COUNCIL_MEMBER"),
            created.id,
        )
    await service.open_session(secretary, created.id)
    return secretary, council_case


def test_votes_are_conflict_gated_unique_and_close_with_absolute_majority() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, _ = await _setup()
        secretary, council_case = await _open_two_member_case(
            service,
            users,
            dossier,
        )
        member1 = _principal(users["member1"], "COUNCIL_MEMBER")
        member2 = _principal(users["member2"], "COUNCIL_MEMBER")

        with pytest.raises(CouncilConflictError):
            await service.cast_vote(
                member1,
                council_case.id,
                choice=CouncilVoteChoice.APPROVE,
                reason="No declaration yet",
            )

        first_conflict = await service.declare_conflict(
            member1,
            council_case.id,
            has_conflict=False,
            reason=None,
        )
        assert first_conflict.has_conflict is False
        await service.declare_conflict(
            member2,
            council_case.id,
            has_conflict=False,
            reason=None,
        )
        for principal in (member1, member2):
            vote = await service.cast_vote(
                principal,
                council_case.id,
                choice=CouncilVoteChoice.APPROVE,
                reason="The dossier meets every council requirement.",
            )
            assert vote.choice is CouncilVoteChoice.APPROVE

        with pytest.raises(CouncilConflictError):
            await service.cast_vote(
                member1,
                council_case.id,
                choice=CouncilVoteChoice.REJECT,
                reason="A second vote must never replace the first one.",
            )

        closed = await service.close_session(secretary, council_case.session_id)
        assert closed.status is CouncilSessionStatus.CLOSED
        assert closed.minutes_hash is not None
        assert len(closed.minutes_hash) == 64

        minutes = await service.get_minutes(secretary, council_case.session_id)
        assert minutes.minutes_hash == closed.minutes_hash
        assert minutes.cases[0].decision is CouncilCaseDecision.APPROVE
        assert minutes.cases[0].quorum_met is True
        assert minutes.cases[0].vote_counts[CouncilVoteChoice.APPROVE] == 2

        async with sessions() as session:
            stored_dossier = await session.get(Dossier, dossier.id)
            assert stored_dossier is not None
            assert stored_dossier.status is DossierStatus.APPROVED
            assert stored_dossier.approved_at is not None
            assert stored_dossier.approved_at.replace(tzinfo=UTC) == NOW
            assert (
                await session.scalar(select(func.count()).select_from(CouncilVote))
                == 2
            )
            assert (
                await session.scalar(
                    select(func.count()).select_from(CouncilCaseConflict)
                )
                == 2
            )
            events = tuple((await session.scalars(select(OutboxEvent))).all())
            assert [event.event_type for event in events] == ["council.decided"]

        with pytest.raises(CouncilConflictError):
            await service.declare_conflict(
                member1,
                council_case.id,
                has_conflict=False,
                reason=None,
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_abstention_counts_for_quorum_but_not_as_a_decision() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, _ = await _setup()
        secretary, council_case = await _open_two_member_case(
            service,
            users,
            dossier,
        )
        choices = (
            ("member1", CouncilVoteChoice.APPROVE),
            ("member2", CouncilVoteChoice.ABSTAIN),
        )
        for name, choice in choices:
            principal = _principal(users[name], "COUNCIL_MEMBER")
            await service.declare_conflict(
                principal,
                council_case.id,
                has_conflict=False,
                reason=None,
            )
            await service.cast_vote(
                principal,
                council_case.id,
                choice=choice,
                reason="Recorded for the official council minutes.",
            )

        await service.close_session(secretary, council_case.session_id)
        minutes = await service.get_minutes(secretary, council_case.session_id)
        result = minutes.cases[0]
        assert result.valid_vote_count == 2
        assert result.quorum_met is True
        assert result.decision is None

        async with sessions() as session:
            stored_dossier = await session.get(Dossier, dossier.id)
            stored_case = await session.get(CouncilCase, council_case.id)
            assert stored_dossier is not None
            assert stored_case is not None
            assert stored_dossier.status is DossierStatus.COUNCIL_REVIEW
            assert stored_case.decision is None

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_conflicted_member_cannot_vote_and_insufficient_votes_do_not_decide() -> None:
    async def exercise() -> None:
        service, _, engine, users, dossier, _ = await _setup()
        secretary, council_case = await _open_two_member_case(
            service,
            users,
            dossier,
        )
        conflicted = _principal(users["member1"], "COUNCIL_MEMBER")
        voter = _principal(users["member2"], "COUNCIL_MEMBER")
        await service.declare_conflict(
            conflicted,
            council_case.id,
            has_conflict=True,
            reason="A direct financial relationship exists.",
        )
        with pytest.raises(CouncilConflictError):
            await service.cast_vote(
                conflicted,
                council_case.id,
                choice=CouncilVoteChoice.APPROVE,
                reason="This vote must not be accepted.",
            )
        await service.declare_conflict(
            voter,
            council_case.id,
            has_conflict=False,
            reason=None,
        )
        await service.cast_vote(
            voter,
            council_case.id,
            choice=CouncilVoteChoice.REJECT,
            reason="The submitted evidence is not sufficient.",
        )

        await service.close_session(secretary, council_case.session_id)
        minutes = await service.get_minutes(secretary, council_case.session_id)
        assert minutes.cases[0].valid_vote_count == 1
        assert minutes.cases[0].quorum_met is False
        assert minutes.cases[0].decision is None

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())


def test_request_more_information_returns_dossier_to_supplement() -> None:
    async def exercise() -> None:
        service, sessions, engine, users, dossier, _ = await _setup()
        secretary, council_case = await _open_two_member_case(
            service,
            users,
            dossier,
        )
        for name in ("member1", "member2"):
            principal = _principal(users[name], "COUNCIL_MEMBER")
            await service.declare_conflict(
                principal,
                council_case.id,
                has_conflict=False,
                reason=None,
            )
            await service.cast_vote(
                principal,
                council_case.id,
                choice=CouncilVoteChoice.REQUEST_MORE_INFO,
                reason="The ownership chain requires one additional document.",
            )

        await service.close_session(secretary, council_case.session_id)
        async with sessions() as session:
            stored_dossier = await session.get(Dossier, dossier.id)
            stored_case = await session.get(CouncilCase, council_case.id)
            assert stored_dossier is not None
            assert stored_case is not None
            assert stored_dossier.status is DossierStatus.NEEDS_SUPPLEMENT
            assert (
                stored_case.decision
                is CouncilCaseDecision.REQUEST_MORE_INFO
            )

        await service.close()
        await engine.dispose()

    asyncio.run(exercise())
