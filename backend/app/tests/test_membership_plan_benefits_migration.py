import json
import sqlite3
from pathlib import Path

import pytest
from alembic.config import Config

from alembic import command
from app.core.config import get_settings

BACKEND_ROOT = Path(__file__).resolve().parents[2]
REVISION = "0132_membership_catalog_content"


def test_plan_benefits_are_seeded_and_downgrade_preserves_catalog_copy(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    database = tmp_path / "membership-plan-benefits.sqlite3"
    monkeypatch.setenv(
        "DATABASE_DIRECT_URL", f"sqlite+aiosqlite:///{database.as_posix()}"
    )
    get_settings.cache_clear()
    config = Config(BACKEND_ROOT / "alembic.ini")
    try:
        command.upgrade(config, "0131_membership_plan_benefits")
        with sqlite3.connect(database) as connection:
            connection.execute(
                "UPDATE membership_plans SET description = ? WHERE tier = ?",
                ("Mô tả do quản trị viên cập nhật.", "SILVER"),
            )

        command.upgrade(config, REVISION)
        with sqlite3.connect(database) as connection:
            rows = connection.execute(
                "SELECT tier, name, amount_minor, duration_days, description, "
                "benefits, conditions FROM membership_plans WHERE active = 1"
            ).fetchall()
            catalog = {
                tier: (
                    name,
                    amount,
                    duration,
                    description,
                    json.loads(benefits),
                    conditions,
                )
                for (
                    tier,
                    name,
                    amount,
                    duration,
                    description,
                    benefits,
                    conditions,
                ) in rows
            }
            assert set(catalog) == {"SILVER", "COMPANION", "PRESTIGE"}
            assert catalog["SILVER"][3] == "Mô tả do quản trị viên cập nhật."
            assert (catalog["SILVER"][0], catalog["SILVER"][1:3]) == (
                "Kết nối",
                (490_000, 365),
            )
            assert (catalog["COMPANION"][0], catalog["COMPANION"][1:3]) == (
                "Đồng hành",
                (1_490_000, 365),
            )
            assert (catalog["PRESTIGE"][0], catalog["PRESTIGE"][1:3]) == (
                "Tinh hoa",
                (3_990_000, 365),
            )
            assert any(
                "thư viện nội dung" in benefit for benefit in catalog["SILVER"][4]
            )
            assert any(
                "Tinh Hoa Connect" in benefit for benefit in catalog["COMPANION"][4]
            )
            assert any(
                "30 phút" in benefit and "tư vấn" in benefit.lower()
                for benefit in catalog["PRESTIGE"][4]
            )
            assert "xét duyệt trước khi thanh toán" in catalog["PRESTIGE"][5]

        with pytest.raises(
            RuntimeError, match="Cannot drop configured membership benefits"
        ):
            command.downgrade(config, "0130_community_events")
    finally:
        get_settings.cache_clear()
