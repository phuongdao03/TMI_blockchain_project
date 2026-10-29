import importlib.util
from pathlib import Path

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from app.db.base import Base, NAMING_CONVENTION
from app.modules.auth.models import User, Permission


def test_promotion_upgrade_chain_preserves_draft_seed_and_round_trips():
    engine = sa.create_engine("sqlite://")
    metadata = sa.MetaData(naming_convention=NAMING_CONVENTION)
    sa.Table("wallet_journals", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    sa.Table(
        "payment_orders",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="amount_minor_positive"),
    )
    sa.Table(
        "membership_purchases",
        metadata,
        sa.Column(
            "id",
            sa.Uuid(),
            sa.ForeignKey("wallet_journals.id", ondelete="RESTRICT"),
            primary_key=True,
        ),
        sa.Column("amount_minor", sa.BigInteger(), nullable=False),
        sa.CheckConstraint("amount_minor > 0", name="positive_amount"),
    )
    with engine.begin() as connection:
        User.__table__.create(connection)
        Permission.__table__.create(connection)
        metadata.create_all(connection)
        modules = []
        with Operations.context(
            MigrationContext.configure(
                connection, opts={"target_metadata": Base.metadata}
            )
        ):
            for filename in (
                "0145_login_vouchers.py",
                "0146_promotion_management.py",
                "0147_promotion_checkout.py",
                "0148_promotion_distribution_media.py",
            ):
                path = (
                    Path(__file__).resolve().parents[2] / "alembic/versions" / filename
                )
                spec = importlib.util.spec_from_file_location(
                    filename.removesuffix(".py"), path
                )
                assert spec is not None and spec.loader is not None
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                module.upgrade()
                modules.append(module)
            seed = connection.execute(
                sa.text(
                    "SELECT status,active,program_type FROM voucher_campaigns WHERE code='EARLY_MEMBER_2026'"
                )
            ).one()
            assert (
                seed.status == "DRAFT"
                and not seed.active
                and seed.program_type == "AUTO"
            )
            assert (
                connection.scalar(
                    sa.text(
                        "SELECT count(*) FROM permissions WHERE code LIKE 'promotions.%'"
                    )
                )
                == 2
            )
            assert "issuance_slot" in {
                column["name"]
                for column in sa.inspect(connection).get_columns("voucher_claims")
            }
            for module in reversed(modules):
                module.downgrade()
            assert "voucher_campaigns" not in sa.inspect(connection).get_table_names()
    engine.dispose()
