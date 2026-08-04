import asyncio
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.ranking.public_repository import PublicRankingRepository

NOW = datetime(2026, 8, 3, 8, tzinfo=UTC)


def test_public_repository_returns_only_published_public_items_and_latest_snapshot(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'public-ranking.sqlite3').as_posix()}"
        )
        campaign_id = uuid4()
        snapshot_id = uuid4()
        hidden_snapshot_id = uuid4()
        visible_work_id = uuid4()
        hidden_work_id = uuid4()
        category_id = uuid4()
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE voting_campaigns ("
                    "id CHAR(32) PRIMARY KEY, slug VARCHAR(180) NOT NULL, "
                    "status VARCHAR(32) NOT NULL, "
                    "published_snapshot_id CHAR(32), "
                    "results_published_at DATETIME)"
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
                    "total_valid_votes BIGINT NOT NULL, "
                    "created_at DATETIME NOT NULL)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE categories (id CHAR(32) PRIMARY KEY, "
                    "name VARCHAR(255) NOT NULL, slug VARCHAR(160))"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE public_works ("
                    "id CHAR(32) PRIMARY KEY, slug VARCHAR(180) NOT NULL, "
                    "title VARCHAR(255) NOT NULL, "
                    "short_description VARCHAR(500) NOT NULL, "
                    "author_display_name VARCHAR(255), category_id CHAR(32) NOT NULL, "
                    "publication_status VARCHAR(32) NOT NULL, "
                    "visibility VARCHAR(32) NOT NULL, "
                    "deleted_at DATETIME)"
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
                text(
                    "INSERT INTO voting_campaigns VALUES "
                    "(:id, :slug, 'PUBLISHED', :snapshot_id, :published_at)"
                ),
                {
                    "id": campaign_id.hex,
                    "slug": "heritage-campaign",
                    "snapshot_id": snapshot_id.hex,
                    "published_at": NOW,
                },
            )
            for snapshot, version in ((hidden_snapshot_id, 1), (snapshot_id, 2)):
                await connection.execute(
                    text(
                        "INSERT INTO ranking_snapshots VALUES "
                        "(:id, :campaign_id, :version, 'effective-votes-v1', 4, "
                        ":source_digest, :result_digest, 2, 3, :created_at)"
                    ),
                    {
                        "id": snapshot.hex,
                        "campaign_id": campaign_id.hex,
                        "version": version,
                        "source_digest": "a" * 64,
                        "result_digest": "b" * 64,
                        "created_at": NOW,
                    },
                )
            await connection.execute(
                text("INSERT INTO categories VALUES (:id, 'Heritage', 'heritage')"),
                {"id": category_id.hex},
            )
            for work_id, status, visibility in (
                (visible_work_id, "PUBLISHED", "PUBLIC"),
                (hidden_work_id, "HIDDEN", "PUBLIC"),
            ):
                await connection.execute(
                    text(
                        "INSERT INTO public_works VALUES "
                        "(:id, :slug, :title, :description, :author, :category_id, "
                        ":status, :visibility, NULL)"
                    ),
                    {
                        "id": work_id.hex,
                        "slug": f"work-{work_id.hex[:8]}",
                        "title": (
                            "Public work"
                            if work_id == visible_work_id
                            else "Hidden work"
                        ),
                        "description": "Safe description",
                        "author": "Public author",
                        "category_id": category_id.hex,
                        "status": status,
                        "visibility": visibility,
                    },
                )
                await connection.execute(
                    text(
                        "INSERT INTO ranking_snapshot_items VALUES "
                        "(:snapshot_id, :work_id, :category_id, :rank, :category_rank, "
                        ":display_order, :score, :votes)"
                    ),
                    {
                        "snapshot_id": snapshot_id.hex,
                        "work_id": work_id.hex,
                        "category_id": category_id.hex,
                        "rank": 1,
                        "category_rank": 1,
                        "display_order": 1 if work_id == visible_work_id else 2,
                        "score": 3,
                        "votes": 3,
                    },
                )

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            repository = PublicRankingRepository(session)
            latest_snapshot = await repository.get_snapshot(
                campaign_slug="heritage-campaign", version=None
            )
            assert latest_snapshot is not None
            assert latest_snapshot.version == 2
            items, total = await repository.list_items(
                snapshot_id=latest_snapshot.id,
                category_id=category_id,
                offset=0,
                limit=20,
            )
            assert total == 1
            assert [item.slug for item in items] == [f"work-{visible_work_id.hex[:8]}"]
            version_one = await repository.get_snapshot(
                campaign_slug="heritage-campaign", version=1
            )
            assert version_one is not None
            assert version_one.version == 1

        await engine.dispose()

    asyncio.run(exercise())
