import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.modules.dossiers.models import Category as Category
from app.modules.public.models import PublicWork as PublicWork
from app.modules.ranking.trending_repository import TrendingRepository
from app.modules.ranking.trending_types import TrendingWindow

WINDOW_END = datetime(2026, 8, 3, 8, tzinfo=UTC)


def test_repository_applies_public_visibility_and_velocity_weights(
    tmp_path: Path,
) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'trending.sqlite3').as_posix()}"
        )
        category_id = uuid4()
        hot_work, warm_work, cold_work, private_work = (uuid4() for _ in range(4))
        async with engine.begin() as connection:
            await connection.execute(
                text(
                    "CREATE TABLE public_works ("
                    "id CHAR(32) PRIMARY KEY, category_id CHAR(32) NOT NULL, "
                    "publication_status VARCHAR(32) NOT NULL, "
                    "visibility VARCHAR(32) NOT NULL, deleted_at DATETIME)"
                )
            )
            await connection.execute(
                text(
                    "CREATE TABLE votes ("
                    "id CHAR(32) PRIMARY KEY, work_id CHAR(32) NOT NULL, "
                    "status VARCHAR(32) NOT NULL, created_at DATETIME NOT NULL)"
                )
            )
            for work_id, visibility in (
                (hot_work, "PUBLIC"),
                (warm_work, "PUBLIC"),
                (cold_work, "PUBLIC"),
                (private_work, "PRIVATE"),
            ):
                await connection.execute(
                    text(
                        "INSERT INTO public_works VALUES "
                        "(:id, :category, 'PUBLISHED', :visibility, NULL)"
                    ),
                    {
                        "id": work_id.hex,
                        "category": category_id.hex,
                        "visibility": visibility,
                    },
                )
            vote_times = (
                (hot_work, WINDOW_END - timedelta(hours=2), "VALID"),
                (hot_work, WINDOW_END - timedelta(hours=30), "VALID"),
                (hot_work, WINDOW_END - timedelta(hours=24), "VALID"),
                (hot_work, WINDOW_END - timedelta(hours=48), "VALID"),
                (hot_work, WINDOW_END - timedelta(hours=3), "REVOKED_BY_USER"),
                (warm_work, WINDOW_END - timedelta(days=3), "VALID"),
                (warm_work, WINDOW_END - timedelta(days=8), "VALID"),
                (private_work, WINDOW_END - timedelta(hours=1), "VALID"),
            )
            for work_id, created_at, status in vote_times:
                await connection.execute(
                    text("INSERT INTO votes VALUES (:id, :work, :status, :created_at)"),
                    {
                        "id": uuid4().hex,
                        "work": work_id.hex,
                        "status": status,
                        "created_at": created_at,
                    },
                )

        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            candidates = await TrendingRepository(session).list_candidates(
                window=TrendingWindow(
                    WINDOW_END - timedelta(days=7),
                    WINDOW_END,
                )
            )

        assert {candidate.work_id: candidate.score for candidate in candidates} == {
            hot_work: 9,
            warm_work: 1,
            cold_work: 0,
        }
        await engine.dispose()

    asyncio.run(exercise())
