import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
PROXY_URL = "/api/v1/public/works/work/media/video"


def test_video_rendition_migration_requeues_only_published_proxy_videos(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database_path = tmp_path / "public-video-renditions.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0079_backfill_category_slugs")
        with sqlite3.connect(database_path) as connection:
            connection.executemany(
                """
                INSERT INTO public_works (
                    id, dossier_id, owner_user_id, slug, title, short_description,
                    publication_status, visibility, category_id
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    (
                        "published",
                        "dossier-1",
                        "owner-1",
                        "published",
                        "Published",
                        "",
                        "PUBLISHED",
                        "PUBLIC",
                        "category-1",
                    ),
                    (
                        "draft",
                        "dossier-2",
                        "owner-2",
                        "draft",
                        "Draft",
                        "",
                        "DRAFT",
                        "PRIVATE",
                        "category-2",
                    ),
                ),
            )
            connection.executemany(
                """
                INSERT INTO public_work_media (
                    id, public_work_id, media_asset_id, media_kind, sort_order,
                    derivative_status, derivative_url, derivative_public_id,
                    derivative_mime_type, derivative_width, derivative_height,
                    duration_ms, failure_code
                ) VALUES (?, ?, ?, ?, 0, 'READY', ?, 'old-rendition',
                          'video/mp4', 1920, 1080, 12000, 'OLD_FAILURE')
                """,
                (
                    ("published-video", "published", "asset-1", "VIDEO", PROXY_URL),
                    ("draft-video", "draft", "asset-2", "VIDEO", PROXY_URL),
                    ("published-image", "published", "asset-3", "IMAGE", PROXY_URL),
                    (
                        "published-rendition",
                        "published",
                        "asset-4",
                        "VIDEO",
                        "https://res.cloudinary.com/demo/video/upload/rendition.mp4",
                    ),
                ),
            )

        command.upgrade(config, "0080_video_renditions")
        with sqlite3.connect(database_path) as connection:
            migrated = connection.execute(
                """
                SELECT derivative_status, derivative_url, derivative_public_id,
                       derivative_mime_type, derivative_width, derivative_height,
                       duration_ms, failure_code
                FROM public_work_media WHERE id = 'published-video'
                """
            ).fetchone()
            untouched = connection.execute(
                """
                SELECT id, derivative_status, derivative_url
                FROM public_work_media WHERE id != 'published-video' ORDER BY id
                """
            ).fetchall()
        assert migrated == ("PENDING", None, None, None, None, None, None, None)
        assert untouched == [
            ("draft-video", "READY", PROXY_URL),
            ("published-image", "READY", PROXY_URL),
            (
                "published-rendition",
                "READY",
                "https://res.cloudinary.com/demo/video/upload/rendition.mp4",
            ),
        ]
    finally:
        get_settings.cache_clear()
