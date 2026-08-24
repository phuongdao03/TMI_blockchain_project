import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]


def test_default_dossier_type_catalog_is_seeded_and_reversible(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database_path = tmp_path / "dossier-type-catalog.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database_path.as_posix()}"
    )
    monkeypatch.chdir(tmp_path)
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")

    command.upgrade(config, "0055_seed_default_dossier_types")

    with sqlite3.connect(database_path) as connection:
        rows = connection.execute(
            "SELECT code, name FROM dossier_types ORDER BY code"
        ).fetchall()
        assert len(rows) == 12
        assert {code for code, _ in rows} == {
            "ARTWORK",
            "CERTIFICATE",
            "CULTURAL_HERITAGE",
            "CULTURAL_WORK",
            "DOCUMENT",
            "INITIATIVE",
            "INTELLECTUAL_ASSET",
            "ORGANIZATION",
            "OTHER",
            "PERSON",
            "PRODUCT",
            "TRADEMARK",
        }
        assert (
            connection.execute("SELECT COUNT(*) FROM dossier_type_versions").fetchone()[
                0
            ]
            == 12
        )

    command.downgrade(config, "0054_dynamic_dossier_types")

    with sqlite3.connect(database_path) as connection:
        assert (
            connection.execute("SELECT COUNT(*) FROM dossier_types").fetchone()[0] == 0
        )
        assert (
            connection.execute("SELECT COUNT(*) FROM dossier_type_versions").fetchone()[
                0
            ]
            == 0
        )
    get_settings.cache_clear()
