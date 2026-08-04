from collections.abc import AsyncIterator
from functools import lru_cache

from pydantic import SecretStr
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings, get_settings


class DatabaseConfigurationError(RuntimeError):
    """Raised when a required database connection URL is not configured."""


def _required_url(value: SecretStr | None, variable_name: str) -> str:
    if value is None or not value.get_secret_value():
        raise DatabaseConfigurationError(f"{variable_name} is not configured.")
    return value.get_secret_value()


def get_direct_database_url(settings: Settings) -> str:
    return _required_url(settings.database_direct_url, "DATABASE_DIRECT_URL")


def create_runtime_engine(settings: Settings) -> AsyncEngine:
    # Source: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html#sqlalchemy.ext.asyncio.create_async_engine
    return create_async_engine(
        _required_url(settings.database_url, "DATABASE_URL"),
        pool_pre_ping=True,
        pool_recycle=300,
    )


def create_session_factory(
    engine: AsyncEngine,
) -> async_sessionmaker[AsyncSession]:
    return async_sessionmaker(engine, expire_on_commit=False)


@lru_cache
def get_runtime_engine() -> AsyncEngine:
    return create_runtime_engine(get_settings())


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    return create_session_factory(get_runtime_engine())


async def get_session() -> AsyncIterator[AsyncSession]:
    async with get_session_factory()() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
