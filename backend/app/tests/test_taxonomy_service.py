import asyncio
import base64
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import User, UserStatus
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.public.errors import (
    PublicWorkForbiddenError,
    TaxonomyCycleError,
    TaxonomyInUseError,
    TaxonomySlugConflictError,
)
from app.modules.public.models import PublicWork, PublicWorkTag
from app.modules.public.taxonomy_service import (
    CategoryInput,
    TagInput,
    TaxonomyService,
)


class MemoryCache:
    def __init__(self) -> None:
        self.values: dict[str, str] = {}

    async def get(self, key: str) -> str | None:
        return self.values.get(key)

    async def set(self, key: str, value: str) -> None:
        self.values[key] = value


def _principal(*roles: str) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="taxonomy@example.test",
        roles=roles,
    )


def test_taxonomy_normalization_cycle_permissions_and_audit(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'taxonomy-service.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        async with factory() as session:
            admin = _principal("SUPER_ADMIN")
            async with session.begin():
                session.add(
                    User(
                        id=admin.user_id,
                        email=admin.email,
                        password_hash="hash",
                        status=UserStatus.ACTIVE,
                    )
                )
            cache = MemoryCache()
            service = TaxonomyService(
                session=session,
                audit=AuditService(session),
                payload_cipher=OutboxPayloadCipher.from_base64(
                    encoded_key=base64.b64encode(b"t" * 32).decode(),
                    key_id="taxonomy-test-v1",
                ),
                cache=cache,
            )
            data = CategoryInput("Mỹ thuật", "Mỹ thuật", None, None, 0, True)
            with pytest.raises(PublicWorkForbiddenError):
                await service.create_category(
                    _principal("USER"), data, request_id="forbidden"
                )

            parent = await service.create_category(admin, data, request_id="parent")
            assert parent.slug == "my-thuat"
            parent_id = parent.id
            parent_name = parent.name
            parent_slug = parent.slug
            child = await service.create_category(
                admin,
                CategoryInput("Điêu khắc", "dieu-khac", None, parent_id, 1, True),
                request_id="child",
            )
            child_id = child.id
            with pytest.raises(TaxonomySlugConflictError):
                await service.create_category(admin, data, request_id="duplicate")
            with pytest.raises(TaxonomyCycleError):
                await service.update_category(
                    admin,
                    parent_id,
                    CategoryInput(
                        parent_name,
                        parent_slug or "my-thuat",
                        None,
                        child_id,
                        0,
                        True,
                    ),
                    request_id="cycle",
                )

            active_tag = await service.create_tag(
                admin, TagInput("Đương đại", "Đương đại", True), request_id="tag"
            )
            active_tag_id = active_tag.id
            await service.create_tag(
                admin, TagInput("Ẩn", "an", False), request_id="inactive-tag"
            )
            work_id = uuid4()
            async with session.begin():
                session.add(
                    PublicWork(
                        id=work_id,
                        dossier_id=uuid4(),
                        owner_user_id=admin.user_id,
                        slug="taxonomy-work",
                        title="Taxonomy work",
                        short_description="Description",
                        category_id=parent_id,
                    )
                )
            await service.assign_tags(
                admin, work_id, (active_tag_id, active_tag_id), request_id="assign"
            )
            assignment_count = await session.scalar(
                select(func.count()).select_from(PublicWorkTag)
            )
            assert assignment_count == 1
            await session.rollback()
            with pytest.raises(TaxonomyInUseError):
                await service.update_category(
                    admin,
                    parent_id,
                    CategoryInput(
                        parent_name,
                        parent_slug or "my-thuat",
                        None,
                        None,
                        0,
                        False,
                    ),
                    request_id="deactivate-in-use",
                )
            public_tags = await service.list_tags(public_only=True)
            assert tuple(tag.id for tag in public_tags) == (active_tag_id,)
            cached_tags = await service.list_tags(public_only=True)
            assert tuple(tag.id for tag in cached_tags) == (active_tag_id,)
            assert len(cache.values) == 1
            await session.rollback()
            audit_count = await session.scalar(
                select(func.count()).select_from(AuditLog)
            )
            assert audit_count == 5
        await engine.dispose()

    asyncio.run(exercise())
