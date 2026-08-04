import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.dossiers.models import Category as Category
from app.modules.public.models import PublicWork as PublicWork
from app.modules.ranking.models import RankingSnapshot, RankingSnapshotItem
from app.modules.ranking.repository import (
    RankingRepository,
    RankingSnapshotRepository,
)
from app.modules.ranking.types import (
    RankingSnapshotDraft,
    RankingSnapshotItemDraft,
)
from app.modules.voting.models import CampaignStatus

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def test_repository_reads_approved_candidates_and_counts_only_valid_votes(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'ranking.sqlite3').as_posix()}"
        )
        campaign_id = uuid4()
        approved_with_votes = uuid4()
        approved_without_votes = uuid4()
        pending_work = uuid4()
        category_a = uuid4()
        category_b = uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE voting_campaigns ("
                    "id CHAR(32) PRIMARY KEY, status VARCHAR(32) NOT NULL, "
                    "rule_version INTEGER NOT NULL, end_at DATETIME NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE public_works ("
                    "id CHAR(32) PRIMARY KEY, category_id CHAR(32) NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE campaign_works ("
                    "id CHAR(32) PRIMARY KEY, campaign_id CHAR(32) NOT NULL, "
                    "work_id CHAR(32) NOT NULL, status VARCHAR(32) NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE votes ("
                    "id CHAR(32) PRIMARY KEY, campaign_id CHAR(32) NOT NULL, "
                    "work_id CHAR(32) NOT NULL, status VARCHAR(32) NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE ranking_snapshots ("
                    "id CHAR(32) PRIMARY KEY, campaign_id CHAR(32) NOT NULL, "
                    "version BIGINT NOT NULL, formula_version VARCHAR(64) NOT NULL, "
                    "campaign_rule_version INTEGER NOT NULL, "
                    "source_digest VARCHAR(64) NOT NULL, "
                    "result_digest VARCHAR(64) NOT NULL, "
                    "candidate_count INTEGER NOT NULL, "
                    "total_valid_votes BIGINT NOT NULL, created_at DATETIME NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE ranking_snapshot_items ("
                    "snapshot_id CHAR(32) NOT NULL, work_id CHAR(32) NOT NULL, "
                    "category_id CHAR(32) NOT NULL, rank INTEGER NOT NULL, "
                    "category_rank INTEGER NOT NULL, display_order INTEGER NOT NULL, "
                    "score BIGINT NOT NULL, effective_vote_count BIGINT NOT NULL, "
                    "PRIMARY KEY (snapshot_id, work_id))"
                )
            )
            await connection.execute(
                text("INSERT INTO voting_campaigns VALUES (:id, 'ENDED', 4, :end_at)"),
                {"id": campaign_id.hex, "end_at": NOW},
            )
            for work_id, status in (
                (approved_with_votes, "APPROVED"),
                (approved_without_votes, "APPROVED"),
                (pending_work, "PENDING"),
            ):
                await connection.execute(
                    text("INSERT INTO public_works VALUES (:id, :category_id)"),
                    {
                        "id": work_id.hex,
                        "category_id": (
                            category_b.hex
                            if work_id == approved_without_votes
                            else category_a.hex
                        ),
                    },
                )
                await connection.execute(
                    text("INSERT INTO campaign_works VALUES (:id, :c, :w, :s)"),
                    {
                        "id": uuid4().hex,
                        "c": campaign_id.hex,
                        "w": work_id.hex,
                        "s": status,
                    },
                )
            for work_id, status in (
                (approved_with_votes, "VALID"),
                (approved_with_votes, "VALID"),
                (approved_with_votes, "REVOKED_BY_USER"),
                (pending_work, "VALID"),
            ):
                await connection.execute(
                    text("INSERT INTO votes VALUES (:id, :c, :w, :s)"),
                    {
                        "id": uuid4().hex,
                        "c": campaign_id.hex,
                        "w": work_id.hex,
                        "s": status,
                    },
                )

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            repository = RankingRepository(session)
            campaign = await repository.get_campaign(campaign_id)
            candidates = await repository.list_candidates(campaign_id)
            snapshot_id = uuid4()
            snapshot_repository = RankingSnapshotRepository(session)
            version = await snapshot_repository.next_version(campaign_id)
            await snapshot_repository.add(
                RankingSnapshotDraft(
                    id=snapshot_id,
                    campaign_id=campaign_id,
                    version=version,
                    formula_version="effective-votes-v1",
                    campaign_rule_version=4,
                    source_digest="a" * 64,
                    result_digest="b" * 64,
                    candidate_count=2,
                    total_valid_votes=2,
                    created_at=NOW,
                    items=(
                        RankingSnapshotItemDraft(
                            work_id=approved_with_votes,
                            category_id=category_a,
                            rank=1,
                            category_rank=1,
                            display_order=1,
                            score=2,
                            effective_vote_count=2,
                        ),
                    ),
                )
            )
            await snapshot_repository.commit()
            next_version = await snapshot_repository.next_version(campaign_id)
            stored_snapshot = await session.get(RankingSnapshot, snapshot_id)
            stored_item = await session.get(
                RankingSnapshotItem,
                (snapshot_id, approved_with_votes),
            )

        assert campaign is not None
        assert campaign.status is CampaignStatus.ENDED
        assert campaign.rule_version == 4
        assert {(item.work_id, item.effective_vote_count) for item in candidates} == {
            (approved_with_votes, 2),
            (approved_without_votes, 0),
        }
        assert {item.work_id: item.category_id for item in candidates} == {
            approved_with_votes: category_a,
            approved_without_votes: category_b,
        }
        assert version == 1
        assert next_version == 2
        assert stored_snapshot is not None
        assert stored_snapshot.result_digest == "b" * 64
        assert stored_item is not None
        assert stored_item.rank == 1
        assert stored_item.category_id == category_a
        assert stored_item.category_rank == 1
        await engine.dispose()

    asyncio.run(exercise())
