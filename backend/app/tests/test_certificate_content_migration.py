import importlib.util
from pathlib import Path
from uuid import uuid4

import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


def test_existing_unissued_dossiers_get_review_drafts() -> None:
    migration_path = (
        Path(__file__).resolve().parents[2]
        / "alembic"
        / "versions"
        / "0098_certificate_content_drafts.py"
    )
    spec = importlib.util.spec_from_file_location(
        "certificate_content_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)

    metadata = sa.MetaData()
    dossiers = sa.Table(
        "dossiers",
        metadata,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_version_no", sa.Integer(), nullable=False),
    )
    versions = sa.Table(
        "dossier_versions",
        metadata,
        sa.Column("dossier_id", sa.Uuid(), nullable=False),
        sa.Column("version_no", sa.Integer(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
    )
    certificates = sa.Table(
        "certificates", metadata, sa.Column("dossier_id", sa.Uuid())
    )
    sa.Table("users", metadata, sa.Column("id", sa.Uuid(), primary_key=True))
    engine = sa.create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        metadata.create_all(connection)
        pending_id, issued_id = uuid4(), uuid4()
        connection.execute(
            sa.insert(dossiers),
            [
                {
                    "id": pending_id,
                    "status": "PAYMENT_PENDING",
                    "current_version_no": 1,
                },
                {"id": issued_id, "status": "PAID", "current_version_no": 1},
            ],
        )
        connection.execute(
            sa.insert(versions),
            [
                {
                    "dossier_id": dossier_id,
                    "version_no": 1,
                    "snapshot_json": {
                        "dossier": {
                            "title": "Đồng diễn múa Saravan",
                            "summary": "Mô tả được duyệt",
                            "category": {"name": "Tài sản trí tuệ số"},
                        }
                    },
                }
                for dossier_id in (pending_id, issued_id)
            ],
        )
        connection.execute(sa.insert(certificates).values(dossier_id=issued_id))
        migration.op = Operations(MigrationContext.configure(connection))
        migration.upgrade()
        drafts = sa.Table(
            "certificate_content_drafts", sa.MetaData(), autoload_with=connection
        )
        rows = connection.execute(
            sa.select(drafts.c.dossier_id, drafts.c.content_json)
        ).all()

    assert rows == [
        (
            pending_id.hex,
            {
                "title": "Đồng diễn múa Saravan",
                "summary": "Mô tả được duyệt",
                "subject": "",
                "category": "Tài sản trí tuệ số",
            },
        )
    ]
