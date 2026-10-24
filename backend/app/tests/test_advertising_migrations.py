from pathlib import Path
from runpy import run_path

from alembic.operations import Operations
from alembic.runtime.migration import MigrationContext
from sqlalchemy import (
    Column,
    MetaData,
    Table,
    Uuid,
    column,
    create_engine,
    select,
    table,
)


def test_advertising_migrations_upgrade_seed_and_downgrade_on_sqlite() -> None:
    backend_dir = Path(__file__).resolve().parents[2]
    inventory = run_path(
        str(backend_dir / "alembic" / "versions" / "0136_advertising_inventory.py")
    )
    checkout = run_path(
        str(backend_dir / "alembic" / "versions" / "0137_advertising_checkout.py")
    )
    delivery = run_path(
        str(backend_dir / "alembic" / "versions" / "0138_advertising_delivery.py")
    )
    engine = create_engine("sqlite://")
    try:
        with engine.begin() as connection:
            parent_metadata = MetaData()
            Table("users", parent_metadata, Column("id", Uuid(), primary_key=True))
            Table("dossiers", parent_metadata, Column("id", Uuid(), primary_key=True))
            Table(
                "wallet_journals",
                parent_metadata,
                Column("id", Uuid(), primary_key=True),
            )
            parent_metadata.create_all(connection)
            operations = Operations(MigrationContext.configure(connection))
            with Operations.context(operations.migration_context):
                inventory["upgrade"]()
                checkout["upgrade"]()
                delivery["upgrade"]()

            placements = (
                connection.execute(
                    select(table("advertising_placements", column("code")).c.code)
                )
                .scalars()
                .all()
            )
            policies = (
                connection.execute(
                    select(
                        table("advertising_discount_policies", column("tier")).c.tier
                    )
                )
                .scalars()
                .all()
            )
            assert set(placements) == {
                "FEATURED_DOSSIER",
                "HOMEPAGE_SPOTLIGHT",
                "COMMUNITY_BANNER",
                "HOMEPAGE_HERO",
            }
            assert set(policies) == {"MEMBER", "SILVER", "COMPANION", "PRESTIGE"}

            with Operations.context(operations.migration_context):
                delivery["downgrade"]()
                checkout["downgrade"]()
                inventory["downgrade"]()
    finally:
        engine.dispose()
