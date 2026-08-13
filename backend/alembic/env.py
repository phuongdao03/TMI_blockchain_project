import asyncio
from collections.abc import Callable

from sqlalchemy import Connection, pool
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from alembic import context
from app.core.config import get_settings
from app.db import outbox as outbox_models  # noqa: F401
from app.db.base import Base
from app.db.session import get_direct_database_url
from app.modules.auth import models as auth_models  # noqa: F401
from app.modules.blockchain import models as blockchain_models  # noqa: F401
from app.modules.council import models as council_models  # noqa: F401
from app.modules.dossiers import models as dossier_models  # noqa: F401
from app.modules.engagement import models as engagement_models  # noqa: F401
from app.modules.media import models as media_models  # noqa: F401
from app.modules.operations import job_models as operations_job_models  # noqa: F401
from app.modules.organizations import models as organization_models  # noqa: F401
from app.modules.payments import models as payment_models  # noqa: F401
from app.modules.public import models as public_models  # noqa: F401
from app.modules.ranking import models as ranking_models  # noqa: F401
from app.modules.ranking import trending_models as trending_models  # noqa: F401
from app.modules.reviews import models as review_models  # noqa: F401
from app.modules.search import discovery_models as search_discovery_models  # noqa: F401
from app.modules.search import history_models as search_history_models  # noqa: F401
from app.modules.users import models as user_models  # noqa: F401
from app.modules.voting import models as voting_models  # noqa: F401

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    context.configure(
        url=get_direct_database_url(get_settings()),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations(
    engine_factory: Callable[[str], AsyncEngine] | None = None,
) -> None:
    direct_url = get_direct_database_url(get_settings())
    connectable = (
        engine_factory(direct_url)
        if engine_factory is not None
        else create_async_engine(direct_url, poolclass=pool.NullPool)
    )

    try:
        async with connectable.connect() as connection:
            await connection.run_sync(do_run_migrations)
    finally:
        await connectable.dispose()


def run_migrations_online() -> None:
    # Source: https://alembic.sqlalchemy.org/en/latest/cookbook.html#using-asyncio-with-alembic
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
