import asyncio
import base64
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.db.base import Base
from app.modules.audit.service import AuditService
from app.modules.auth.security import OutboxPayloadCipher
from app.modules.auth.session_service import AuthPrincipal
from app.modules.dossiers.models import Category
from app.modules.public.errors import (
    ContentReportDuplicateError,
    PublicWorkForbiddenError,
)
from app.modules.public.models import (
    ContentReportReason,
    ContentReportStatus,
    PublicationStatus,
    PublicWork,
    PublicWorkVisibility,
)
from app.modules.public.report_service import ContentReportInput, ContentReportService
from app.modules.users.security import SensitiveFieldCipher

NOW = datetime(2026, 8, 1, tzinfo=UTC)


def test_anonymous_user_dedup_permission_and_resolution(tmp_path: Path) -> None:
    async def exercise() -> None:
        engine = create_async_engine(
            f"sqlite+aiosqlite:///{(tmp_path / 'reports.sqlite3').as_posix()}"
        )
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)
        factory = async_sessionmaker(engine, expire_on_commit=False)
        category_id = uuid4()
        work_id = uuid4()
        async with factory() as session:
            async with session.begin():
                session.add(
                    Category(
                        id=category_id,
                        code="REPORT",
                        name="Report",
                        slug="report",
                    )
                )
                session.add(
                    PublicWork(
                        id=work_id,
                        dossier_id=uuid4(),
                        owner_user_id=uuid4(),
                        slug="reportable",
                        title="Reportable",
                        short_description="Public work",
                        category_id=category_id,
                        publication_status=PublicationStatus.PUBLISHED,
                        visibility=PublicWorkVisibility.PUBLIC,
                        published_at=NOW,
                    )
                )
            service = _service(session)
            payload = ContentReportInput(
                reason=ContentReportReason.COPYRIGHT,
                description="  Nội dung <script> được lưu như plain text.  ",
                reporter_email="Contact@Example.Test",
                captcha_token=None,
            )
            anonymous = await service.submit(
                work_id,
                payload,
                principal=None,
                client_ip="203.0.113.10",
                request_id="report-anonymous",
            )
            assert anonymous.reporter_user_id is None
            assert anonymous.reporter_email_encrypted is not None
            assert b"Contact@Example.Test" not in anonymous.reporter_email_encrypted
            assert anonymous.description == (
                "Nội dung <script> được lưu như plain text."
            )
            anonymous_id = anonymous.id
            with pytest.raises(ContentReportDuplicateError):
                await service.submit(
                    work_id,
                    payload,
                    principal=None,
                    client_ip="203.0.113.10",
                    request_id="report-duplicate",
                )

            user = _principal(("USER",))
            user_report = await service.submit(
                work_id,
                ContentReportInput(
                    reason=ContentReportReason.INCORRECT_INFORMATION,
                    description="Thông tin chưa chính xác.",
                    reporter_email=None,
                    captcha_token=None,
                ),
                principal=user,
                client_ip="203.0.113.11",
                request_id="report-user",
            )
            assert user_report.reporter_user_id == user.user_id
            with pytest.raises(PublicWorkForbiddenError):
                await service.list_admin(user, status=None, page=1, page_size=20)

            admin = _principal(("CONTENT_ADMIN",))
            reviewing = await service.transition(
                admin,
                anonymous_id,
                status=ContentReportStatus.UNDER_REVIEW,
                resolution_note=None,
                request_id="report-review",
            )
            assert reviewing.report.status is ContentReportStatus.UNDER_REVIEW
            resolved = await service.transition(
                admin,
                anonymous_id,
                status=ContentReportStatus.RESOLVED,
                resolution_note="Đã liên hệ và xử lý.",
                request_id="report-resolve",
            )
            assert resolved.report.resolved_at is not None
        await engine.dispose()

    asyncio.run(exercise())


def _service(session: object) -> ContentReportService:
    key = b"r" * 32
    return ContentReportService(
        session,  # type: ignore[arg-type]
        audit=AuditService(session),  # type: ignore[arg-type]
        pii_cipher=SensitiveFieldCipher(key=key),
        outbox_cipher=OutboxPayloadCipher.from_base64(
            encoded_key=base64.b64encode(key).decode(),
            key_id="content-report-v1",
        ),
    )


def _principal(roles: tuple[str, ...]) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="user@example.test",
        roles=roles,
    )
