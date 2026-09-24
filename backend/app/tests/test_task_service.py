import asyncio
from datetime import UTC, date, datetime
from uuid import uuid4

import pytest
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.core.errors import DomainError
from app.db.base import Base
from app.modules.audit.models import AuditLog
from app.modules.audit.service import AuditService
from app.modules.auth.models import User
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import Department, Employee, EmploymentStatus
from app.modules.media.models import MediaAsset, MediaConfidentiality, MediaStatus
from app.modules.media.provenance import (
    CURRENT_INSPECTION_POLICY_VERSION,
    HASH_ALGORITHM,
)
from app.modules.tasks.models import (
    Task,
    TaskActivity,
    TaskAttachment,
    TaskChecklistItem,
    TaskComment,
    TaskPriority,
    TaskStatus,
)
from app.modules.tasks.schemas import (
    AddTaskAttachmentRequest,
    CreateTaskChecklistItemRequest,
    CreateTaskCommentRequest,
    CreateTaskRequest,
    UpdateTaskChecklistItemRequest,
    UpdateTaskRequest,
)
from app.modules.tasks.service import TaskService


async def _create_task_tables(engine: object) -> None:
    async with engine.begin() as connection:  # type: ignore[union-attr]
        await connection.run_sync(
            lambda sync_connection: Base.metadata.create_all(
                sync_connection,
                tables=[
                    User.__table__,
                    Department.__table__,
                    Employee.__table__,
                    Task.__table__,
                    TaskChecklistItem.__table__,
                    TaskComment.__table__,
                    MediaAsset.__table__,
                    TaskAttachment.__table__,
                    TaskActivity.__table__,
                    AuditLog.__table__,
                ],
            )
        )


def _principal(
    *, roles: tuple[str, ...], permissions: tuple[str, ...] = ()
) -> AuthPrincipal:
    return AuthPrincipal(
        user_id=uuid4(),
        session_id=uuid4(),
        email="task-admin@example.com",
        roles=roles,
        permissions=permissions,
    )


def test_super_admin_can_create_list_get_and_update_task_with_redacted_audit() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_task_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))

        async with sessions() as session:
            service = TaskService(session)
            created = await service.create_task(
                admin,
                CreateTaskRequest(
                    title="  Prepare incident report  ",
                    description="Sensitive operational context",
                    due_at=datetime(2026, 9, 26, 9, tzinfo=UTC),
                ),
                audit=AuditService(session),
                request_id="task-test",
                user_agent="pytest",
            )
            assert created.title == "Prepare incident report"
            assert created.status == "TODO"
            assert created.due_at == datetime(2026, 9, 26, 9, tzinfo=UTC)

            rows, total = await service.list_tasks(
                admin, page=1, page_size=20, search="incident"
            )
            assert total == 1
            assert rows[0].id == created.id

            detail = await service.get_task(admin, created.id)
            assert detail.description == "Sensitive operational context"

            updated = await service.update_task(
                admin,
                created.id,
                UpdateTaskRequest(title="Publish incident summary", due_at=None),
                audit=AuditService(session),
                request_id="task-test",
                user_agent="pytest",
            )
            assert updated.title == "Publish incident summary"
            assert updated.due_at is None
            audits = (
                await session.scalars(
                    select(AuditLog).where(
                        AuditLog.action.in_(("work.task.created", "work.task.updated"))
                    )
                )
            ).all()
            assert len(audits) == 2
            for audit in audits:
                for snapshot in (audit.before_json, audit.after_json):
                    assert not {"title", "description"}.intersection(snapshot or {})
        await engine.dispose()

    asyncio.run(exercise())


def test_non_super_admin_cannot_read_or_create_tasks() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_task_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        async with sessions() as session:
            service = TaskService(session)
            for role in ("VIEWER", "USER", "MODERATOR"):
                principal = _principal(
                    roles=(role,),
                    permissions=("work.tasks.read", "work.tasks.manage"),
                )
                with pytest.raises(DomainError) as read_error:
                    await service.list_tasks(
                        principal,
                        page=1,
                        page_size=20,
                        search=None,
                    )
                assert read_error.value.code == "WORK_TASK_FORBIDDEN"
                with pytest.raises(DomainError) as create_error:
                    await service.create_task(
                        principal,
                        CreateTaskRequest(title="Unauthorized"),
                        audit=AuditService(session),
                        request_id="task-test",
                        user_agent="pytest",
                    )
                assert create_error.value.code == "WORK_TASK_FORBIDDEN"
        await engine.dispose()

    asyncio.run(exercise())


def test_task_update_rejects_removing_or_blank_title() -> None:
    with pytest.raises(ValidationError):
        UpdateTaskRequest(title=None)
    with pytest.raises(ValidationError):
        UpdateTaskRequest(title="   ")


def test_task_assignment_priority_and_status_transition_are_controlled() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_task_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            department = Department(code="OPS", name="Operations")
            session.add(department)
            await session.flush()
            employee = Employee(
                employee_code="OPS-001",
                full_name="Assigned operator",
                email="operator@example.com",
                department_id=department.id,
                position="Operator",
                join_date=date(2026, 9, 1),
            )
            session.add(employee)
            inactive_employee = Employee(
                employee_code="OPS-002",
                full_name="Inactive operator",
                email="inactive@example.com",
                department_id=department.id,
                position="Operator",
                employment_status=EmploymentStatus.INACTIVE,
                join_date=date(2026, 9, 1),
            )
            session.add(inactive_employee)
            await session.flush()
            employee_id = employee.id
            inactive_employee_id = inactive_employee.id

        async with sessions() as session:
            service = TaskService(session)
            task = await service.create_task(
                admin,
                CreateTaskRequest(title="Review incident"),
                audit=AuditService(session),
                request_id="task-transition-test",
                user_agent="pytest",
            )
            assigned = await service.update_task(
                admin,
                task.id,
                UpdateTaskRequest(
                    assignee_employee_id=employee_id,
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.IN_PROGRESS,
                ),
                audit=AuditService(session),
                request_id="task-transition-test",
                user_agent="pytest",
            )
            assert assigned.assignee_employee_id == employee_id
            assert assigned.priority == TaskPriority.HIGH
            assert assigned.status == TaskStatus.IN_PROGRESS

            completed = await service.update_task(
                admin,
                task.id,
                UpdateTaskRequest(status=TaskStatus.DONE),
                audit=AuditService(session),
                request_id="task-transition-test",
                user_agent="pytest",
            )
            assert completed.completed_at is not None
            assert completed.completed_at.utcoffset() is not None
            with pytest.raises(DomainError) as transition_error:
                await service.update_task(
                    admin,
                    task.id,
                    UpdateTaskRequest(
                        title="Must not persist",
                        status=TaskStatus.IN_PROGRESS,
                    ),
                    audit=AuditService(session),
                    request_id="task-transition-test",
                    user_agent="pytest",
                )
            assert transition_error.value.code == "WORK_TASK_STATUS_TRANSITION_INVALID"
            after_rejected_transition = await service.get_task(admin, task.id)
            assert after_rejected_transition.title == "Review incident"
            with pytest.raises(DomainError) as inactive_assignee_error:
                await service.update_task(
                    admin,
                    task.id,
                    UpdateTaskRequest(assignee_employee_id=inactive_employee_id),
                    audit=AuditService(session),
                    request_id="task-transition-test",
                    user_agent="pytest",
                )
            assert (
                inactive_assignee_error.value.code == "WORK_TASK_ASSIGNEE_UNAVAILABLE"
            )
        await engine.dispose()

    asyncio.run(exercise())


def test_task_activity_subresources_redact_content_and_require_private_media() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_task_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))
            media = MediaAsset(
                owner_user_id=admin.user_id,
                cloudinary_public_id="task-test-private-media",
                cloudinary_version=1,
                resource_type="raw",
                access_mode="authenticated",
                original_filename="sensitive-attachment.pdf",
                mime_type="application/pdf",
                bytes=20,
                status=MediaStatus.ACTIVE,
                confidentiality=MediaConfidentiality.PRIVATE,
                sha256="a" * 64,
                hash_algorithm=HASH_ALGORITHM,
                hash_byte_length=20,
                inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
                hash_storage_version=1,
                hash_computed_at=datetime(2026, 9, 20, 10, tzinfo=UTC),
            )
            public_media = MediaAsset(
                owner_user_id=admin.user_id,
                cloudinary_public_id="task-test-public-media",
                cloudinary_version=1,
                resource_type="raw",
                access_mode="public",
                original_filename="public-attachment.pdf",
                mime_type="application/pdf",
                bytes=20,
                status=MediaStatus.ACTIVE,
                confidentiality=MediaConfidentiality.PUBLIC,
                sha256="b" * 64,
                hash_algorithm=HASH_ALGORITHM,
                hash_byte_length=20,
                inspection_policy_version=CURRENT_INSPECTION_POLICY_VERSION,
                hash_storage_version=1,
                hash_computed_at=datetime(2026, 9, 20, 10, tzinfo=UTC),
            )
            session.add_all([media, public_media])
            await session.flush()
            media_id = media.id
            public_media_id = public_media.id

        async with sessions() as session:
            service = TaskService(session)
            task = await service.create_task(
                admin,
                CreateTaskRequest(title="Collect release evidence"),
                audit=AuditService(session),
                request_id="task-activity-test",
                user_agent="pytest",
            )
            checklist = await service.create_checklist_item(
                admin,
                task.id,
                CreateTaskChecklistItemRequest(title="Verify approval", position=10),
                audit=AuditService(session),
                request_id="task-activity-test",
                user_agent="pytest",
            )
            completed = await service.update_checklist_item(
                admin,
                task.id,
                checklist.id,
                UpdateTaskChecklistItemRequest(is_complete=True),
                audit=AuditService(session),
                request_id="task-activity-test",
                user_agent="pytest",
            )
            assert completed.completed_by_user_id == admin.user_id
            assert completed.completed_at is not None
            assert completed.completed_at.utcoffset() is not None

            comment = await service.create_comment(
                admin,
                task.id,
                CreateTaskCommentRequest(body="Sensitive incident detail"),
                audit=AuditService(session),
                request_id="task-activity-test",
                user_agent="pytest",
            )
            assert comment.body == "Sensitive incident detail"
            attachment = await service.add_attachment(
                admin,
                task.id,
                AddTaskAttachmentRequest(media_asset_id=media_id),
                audit=AuditService(session),
                request_id="task-activity-test",
                user_agent="pytest",
            )
            assert attachment.media_asset_id == media_id

            activities, total = await service.list_activities(
                admin, task.id, page=1, page_size=20
            )
            assert total == 4
            assert {activity.event_type for activity in activities} == {
                "task.checklist.created",
                "task.checklist.completed",
                "task.comment.created",
                "task.attachment.added",
            }
            audit = await session.scalar(
                select(AuditLog).where(AuditLog.action == "work.task.comment.created")
            )
            assert audit is not None
            assert "body" not in audit.after_json
            with pytest.raises(DomainError) as public_media_error:
                await service.add_attachment(
                    admin,
                    task.id,
                    AddTaskAttachmentRequest(media_asset_id=public_media_id),
                    audit=AuditService(session),
                    request_id="task-activity-test",
                    user_agent="pytest",
                )
            assert public_media_error.value.code == "WORK_TASK_MEDIA_INVALID"
        await engine.dispose()

    asyncio.run(exercise())


def test_task_list_filters_and_sorts_by_due_time() -> None:
    async def exercise() -> None:
        engine = create_async_engine("sqlite+aiosqlite://")
        await _create_task_tables(engine)
        sessions = async_sessionmaker(engine, expire_on_commit=False)
        admin = _principal(roles=("SUPER_ADMIN",))
        async with sessions.begin() as session:
            session.add(User(id=admin.user_id, email=admin.email, password_hash=None))

        async with sessions() as session:
            service = TaskService(session)
            later = await service.create_task(
                admin,
                CreateTaskRequest(
                    title="Later task", due_at=datetime(2026, 9, 28, 9, tzinfo=UTC)
                ),
                audit=AuditService(session),
                request_id="task-list-test",
                user_agent="pytest",
            )
            earlier = await service.create_task(
                admin,
                CreateTaskRequest(
                    title="Earlier task", due_at=datetime(2026, 9, 25, 9, tzinfo=UTC)
                ),
                audit=AuditService(session),
                request_id="task-list-test",
                user_agent="pytest",
            )
            await service.update_task(
                admin,
                later.id,
                UpdateTaskRequest(
                    priority=TaskPriority.HIGH,
                    status=TaskStatus.IN_PROGRESS,
                ),
                audit=AuditService(session),
                request_id="task-list-test",
                user_agent="pytest",
            )
            rows, total = await service.list_tasks(
                admin,
                page=1,
                page_size=20,
                search="task",
                task_status=TaskStatus.TODO,
                priority=TaskPriority.MEDIUM,
                sort_by="dueAt",
                sort_direction="asc",
            )
            assert total == 1
            assert rows[0].id == earlier.id
        await engine.dispose()

    asyncio.run(exercise())
