from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql.elements import ColumnElement

from app.core.errors import DomainError
from app.modules.audit.service import AuditService
from app.modules.auth.authorization import AuthorizationPolicy, PolicyRequirement
from app.modules.auth.session_service import AuthPrincipal
from app.modules.hr.models import Employee, EmploymentStatus
from app.modules.media.models import MediaAsset, MediaConfidentiality
from app.modules.media.provenance import has_current_trusted_provenance
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
    TaskActivityData,
    TaskAttachmentData,
    TaskChecklistItemData,
    TaskCommentData,
    TaskData,
    UpdateTaskChecklistItemRequest,
    UpdateTaskRequest,
)


class TaskService:
    _STATUS_TRANSITIONS = {
        TaskStatus.TODO: frozenset({TaskStatus.IN_PROGRESS, TaskStatus.CANCELLED}),
        TaskStatus.IN_PROGRESS: frozenset({TaskStatus.DONE, TaskStatus.CANCELLED}),
        TaskStatus.DONE: frozenset(),
        TaskStatus.CANCELLED: frozenset(),
    }

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    @staticmethod
    def _now() -> datetime:
        return datetime.now(UTC)

    @staticmethod
    def _require(principal: AuthPrincipal, permission: str) -> None:
        AuthorizationPolicy.require_resource_scope(
            "SUPER_ADMIN" in principal.roles,
            lambda: DomainError(
                code="WORK_TASK_FORBIDDEN",
                message="You do not have permission to access tasks.",
                status_code=403,
            ),
        )
        AuthorizationPolicy.require_capability(
            principal,
            PolicyRequirement(
                permission=permission,
                compatible_roles=frozenset({"SUPER_ADMIN"}),
            ),
            lambda: DomainError(
                code="WORK_TASK_FORBIDDEN",
                message="You do not have permission to access tasks.",
                status_code=403,
            ),
        )

    @staticmethod
    def _task_data(task: Task) -> TaskData:
        data = TaskData.model_validate(task)
        return data.model_copy(
            update={
                field: TaskService._as_utc(getattr(data, field))
                for field in ("due_at", "completed_at", "created_at", "updated_at")
            }
        )

    @staticmethod
    def _as_utc(value: datetime | None) -> datetime | None:
        if value is None or value.utcoffset() is not None:
            return value
        return value.replace(tzinfo=UTC)

    @staticmethod
    def _audit_snapshot(task: Task) -> dict[str, object]:
        due_at = TaskService._as_utc(task.due_at)
        completed_at = TaskService._as_utc(task.completed_at)
        return {
            "status": task.status.value,
            "priority": task.priority.value,
            "assignee_employee_id": (
                str(task.assignee_employee_id) if task.assignee_employee_id else None
            ),
            "due_at": due_at.isoformat() if due_at else None,
            "completed_at": completed_at.isoformat() if completed_at else None,
        }

    async def _locked_task(self, task_id: UUID) -> Task:
        task = await self._session.scalar(
            select(Task).where(Task.id == task_id).with_for_update()
        )
        if task is None:
            raise DomainError(
                code="WORK_TASK_NOT_FOUND",
                message="Task not found.",
                status_code=404,
            )
        return task

    async def _existing_task(self, task_id: UUID) -> Task:
        task = await self._session.get(Task, task_id)
        if task is None:
            raise DomainError(
                code="WORK_TASK_NOT_FOUND",
                message="Task not found.",
                status_code=404,
            )
        return task

    def _record_activity(
        self,
        *,
        task_id: UUID,
        actor_user_id: UUID,
        event_type: str,
        payload: dict[str, object],
    ) -> None:
        self._session.add(
            TaskActivity(
                task_id=task_id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                payload=payload,
            )
        )

    @staticmethod
    def _checklist_data(item: TaskChecklistItem) -> TaskChecklistItemData:
        data = TaskChecklistItemData.model_validate(item)
        return data.model_copy(
            update={
                field: TaskService._as_utc(getattr(data, field))
                for field in ("completed_at", "created_at", "updated_at")
            }
        )

    @staticmethod
    def _comment_data(comment: TaskComment) -> TaskCommentData:
        data = TaskCommentData.model_validate(comment)
        return data.model_copy(
            update={
                field: TaskService._as_utc(getattr(data, field))
                for field in ("created_at", "updated_at")
            }
        )

    @staticmethod
    def _attachment_data(attachment: TaskAttachment) -> TaskAttachmentData:
        data = TaskAttachmentData.model_validate(attachment)
        return data.model_copy(
            update={
                field: TaskService._as_utc(getattr(data, field))
                for field in ("created_at", "updated_at")
            }
        )

    @staticmethod
    def _activity_data(activity: TaskActivity) -> TaskActivityData:
        data = TaskActivityData.model_validate(activity)
        return data.model_copy(
            update={"created_at": TaskService._as_utc(data.created_at)}
        )

    async def list_tasks(
        self,
        principal: AuthPrincipal,
        *,
        page: int,
        page_size: int,
        search: str | None,
        task_status: TaskStatus | None = None,
        priority: TaskPriority | None = None,
        sort_by: str = "createdAt",
        sort_direction: str = "desc",
    ) -> tuple[tuple[TaskData, ...], int]:
        self._require(principal, "work.tasks.read")
        criteria: list[ColumnElement[bool]] = []
        if search:
            criteria.append(Task.title.ilike(f"%{search.strip()}%"))
        if task_status is not None:
            criteria.append(Task.status == task_status)
        if priority is not None:
            criteria.append(Task.priority == priority)
        sort_column = Task.due_at if sort_by == "dueAt" else Task.created_at
        sort_order = (
            sort_column.asc().nulls_last()
            if sort_direction == "asc"
            else sort_column.desc().nulls_last()
        )
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(Task).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(Task)
                    .where(*criteria)
                    .order_by(sort_order, Task.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._task_data(task) for task in rows), total

    async def get_task(self, principal: AuthPrincipal, task_id: UUID) -> TaskData:
        self._require(principal, "work.tasks.read")
        task = await self._session.get(Task, task_id)
        if task is None:
            raise DomainError(
                code="WORK_TASK_NOT_FOUND",
                message="Task not found.",
                status_code=404,
            )
        return self._task_data(task)

    async def create_task(
        self,
        principal: AuthPrincipal,
        payload: CreateTaskRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskData:
        self._require(principal, "work.tasks.manage")
        task = Task(
            title=payload.title,
            description=payload.description,
            due_at=payload.due_at,
            created_by_user_id=principal.user_id,
        )
        self._session.add(task)
        await self._session.flush()
        await self._session.refresh(task)
        audit.record(
            actor_user_id=principal.user_id,
            action="work.task.created",
            resource_type="task",
            resource_id=str(task.id),
            after=self._audit_snapshot(task),
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._task_data(task)
        await self._session.commit()
        return data

    async def update_task(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        payload: UpdateTaskRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskData:
        self._require(principal, "work.tasks.manage")
        task = await self._session.scalar(
            select(Task).where(Task.id == task_id).with_for_update()
        )
        if task is None:
            raise DomainError(
                code="WORK_TASK_NOT_FOUND",
                message="Task not found.",
                status_code=404,
            )
        next_status = payload.status if "status" in payload.model_fields_set else None
        if (
            next_status is not None
            and next_status != task.status
            and next_status not in self._STATUS_TRANSITIONS[task.status]
        ):
            raise DomainError(
                code="WORK_TASK_STATUS_TRANSITION_INVALID",
                message="Task status transition is not allowed.",
                status_code=409,
            )
        if (
            "assignee_employee_id" in payload.model_fields_set
            and payload.assignee_employee_id is not None
        ):
            employee = await self._session.get(Employee, payload.assignee_employee_id)
            if employee is None:
                raise DomainError(
                    code="WORK_TASK_ASSIGNEE_NOT_FOUND",
                    message="Assigned employee not found.",
                    status_code=422,
                )
            if employee.employment_status != EmploymentStatus.ACTIVE:
                raise DomainError(
                    code="WORK_TASK_ASSIGNEE_UNAVAILABLE",
                    message="Assigned employee is not active.",
                    status_code=422,
                )
        before = self._audit_snapshot(task)
        if "title" in payload.model_fields_set:
            task.title = payload.title or task.title
        if "description" in payload.model_fields_set:
            task.description = payload.description
        if "due_at" in payload.model_fields_set:
            task.due_at = payload.due_at
        if "assignee_employee_id" in payload.model_fields_set:
            task.assignee_employee_id = payload.assignee_employee_id
        if "priority" in payload.model_fields_set and payload.priority is not None:
            task.priority = payload.priority
        if next_status is not None and next_status != task.status:
            task.status = next_status
            task.completed_at = self._now() if next_status == TaskStatus.DONE else None
        await self._session.flush()
        await self._session.refresh(task)
        audit.record(
            actor_user_id=principal.user_id,
            action="work.task.updated",
            resource_type="task",
            resource_id=str(task.id),
            before=before,
            after=self._audit_snapshot(task),
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._task_data(task)
        await self._session.commit()
        return data

    async def list_checklist_items(
        self, principal: AuthPrincipal, task_id: UUID
    ) -> tuple[TaskChecklistItemData, ...]:
        self._require(principal, "work.tasks.read")
        await self._existing_task(task_id)
        rows = tuple(
            (
                await self._session.scalars(
                    select(TaskChecklistItem)
                    .where(TaskChecklistItem.task_id == task_id)
                    .order_by(TaskChecklistItem.position, TaskChecklistItem.created_at)
                )
            ).all()
        )
        return tuple(self._checklist_data(item) for item in rows)

    async def create_checklist_item(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        payload: CreateTaskChecklistItemRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskChecklistItemData:
        self._require(principal, "work.tasks.manage")
        await self._locked_task(task_id)
        item = TaskChecklistItem(
            task_id=task_id,
            title=payload.title,
            position=payload.position,
        )
        self._session.add(item)
        await self._session.flush()
        await self._session.refresh(item)
        self._record_activity(
            task_id=task_id,
            actor_user_id=principal.user_id,
            event_type="task.checklist.created",
            payload={"checklistItemId": str(item.id), "position": item.position},
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="work.task.checklist.created",
            resource_type="task_checklist_item",
            resource_id=str(item.id),
            after={"task_id": str(task_id), "position": item.position},
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._checklist_data(item)
        await self._session.commit()
        return data

    async def update_checklist_item(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        checklist_item_id: UUID,
        payload: UpdateTaskChecklistItemRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskChecklistItemData:
        self._require(principal, "work.tasks.manage")
        await self._locked_task(task_id)
        item = await self._session.scalar(
            select(TaskChecklistItem)
            .where(
                TaskChecklistItem.id == checklist_item_id,
                TaskChecklistItem.task_id == task_id,
            )
            .with_for_update()
        )
        if item is None:
            raise DomainError(
                code="WORK_TASK_CHECKLIST_NOT_FOUND",
                message="Checklist item not found.",
                status_code=404,
            )
        before: dict[str, object] = {
            "position": item.position,
            "is_complete": item.is_complete,
        }
        if "title" in payload.model_fields_set and payload.title is not None:
            item.title = payload.title
        if "position" in payload.model_fields_set and payload.position is not None:
            item.position = payload.position
        if (
            "is_complete" in payload.model_fields_set
            and payload.is_complete is not None
        ):
            item.is_complete = payload.is_complete
            item.completed_at = self._now() if payload.is_complete else None
            item.completed_by_user_id = (
                principal.user_id if payload.is_complete else None
            )
        await self._session.flush()
        await self._session.refresh(item)
        event_type = (
            "task.checklist.completed"
            if "is_complete" in payload.model_fields_set and item.is_complete
            else "task.checklist.updated"
        )
        self._record_activity(
            task_id=task_id,
            actor_user_id=principal.user_id,
            event_type=event_type,
            payload={
                "checklistItemId": str(item.id),
                "isComplete": item.is_complete,
                "position": item.position,
            },
        )
        audit.record(
            actor_user_id=principal.user_id,
            action=f"work.{event_type}",
            resource_type="task_checklist_item",
            resource_id=str(item.id),
            before=before,
            after={"position": item.position, "is_complete": item.is_complete},
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._checklist_data(item)
        await self._session.commit()
        return data

    async def list_comments(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[TaskCommentData, ...], int]:
        self._require(principal, "work.tasks.read")
        await self._existing_task(task_id)
        criteria = (TaskComment.task_id == task_id,)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(TaskComment).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(TaskComment)
                    .where(*criteria)
                    .order_by(TaskComment.created_at.desc(), TaskComment.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._comment_data(comment) for comment in rows), total

    async def create_comment(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        payload: CreateTaskCommentRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskCommentData:
        self._require(principal, "work.tasks.manage")
        await self._locked_task(task_id)
        comment = TaskComment(
            task_id=task_id,
            author_user_id=principal.user_id,
            body=payload.body,
        )
        self._session.add(comment)
        await self._session.flush()
        await self._session.refresh(comment)
        self._record_activity(
            task_id=task_id,
            actor_user_id=principal.user_id,
            event_type="task.comment.created",
            payload={"commentId": str(comment.id)},
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="work.task.comment.created",
            resource_type="task_comment",
            resource_id=str(comment.id),
            after={"task_id": str(task_id)},
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._comment_data(comment)
        await self._session.commit()
        return data

    async def list_attachments(
        self, principal: AuthPrincipal, task_id: UUID
    ) -> tuple[TaskAttachmentData, ...]:
        self._require(principal, "work.tasks.read")
        await self._existing_task(task_id)
        rows = tuple(
            (
                await self._session.scalars(
                    select(TaskAttachment)
                    .where(TaskAttachment.task_id == task_id)
                    .order_by(TaskAttachment.created_at.desc(), TaskAttachment.id)
                )
            ).all()
        )
        return tuple(self._attachment_data(attachment) for attachment in rows)

    async def add_attachment(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        payload: AddTaskAttachmentRequest,
        *,
        audit: AuditService,
        request_id: str,
        user_agent: str | None,
    ) -> TaskAttachmentData:
        self._require(principal, "work.tasks.manage")
        await self._locked_task(task_id)
        media = await self._session.get(MediaAsset, payload.media_asset_id)
        if (
            media is None
            or media.owner_user_id != principal.user_id
            or media.confidentiality != MediaConfidentiality.PRIVATE
            or not has_current_trusted_provenance(media)
        ):
            raise DomainError(
                code="WORK_TASK_MEDIA_INVALID",
                message=(
                    "Task attachments must reference a private trusted media asset."
                ),
                status_code=422,
            )
        exists = await self._session.scalar(
            select(TaskAttachment.id).where(
                TaskAttachment.task_id == task_id,
                TaskAttachment.media_asset_id == payload.media_asset_id,
            )
        )
        if exists is not None:
            raise DomainError(
                code="WORK_TASK_ATTACHMENT_DUPLICATE",
                message="Media is already attached to this task.",
                status_code=409,
            )
        attachment = TaskAttachment(
            task_id=task_id,
            media_asset_id=payload.media_asset_id,
            attached_by_user_id=principal.user_id,
        )
        self._session.add(attachment)
        await self._session.flush()
        await self._session.refresh(attachment)
        self._record_activity(
            task_id=task_id,
            actor_user_id=principal.user_id,
            event_type="task.attachment.added",
            payload={
                "attachmentId": str(attachment.id),
                "mediaAssetId": str(attachment.media_asset_id),
            },
        )
        audit.record(
            actor_user_id=principal.user_id,
            action="work.task.attachment.added",
            resource_type="task_attachment",
            resource_id=str(attachment.id),
            after={
                "task_id": str(task_id),
                "media_asset_id": str(attachment.media_asset_id),
            },
            request_id=request_id,
            user_agent=user_agent,
        )
        data = self._attachment_data(attachment)
        await self._session.commit()
        return data

    async def list_activities(
        self,
        principal: AuthPrincipal,
        task_id: UUID,
        *,
        page: int,
        page_size: int,
    ) -> tuple[tuple[TaskActivityData, ...], int]:
        self._require(principal, "work.tasks.read")
        await self._existing_task(task_id)
        criteria = (TaskActivity.task_id == task_id,)
        total = int(
            await self._session.scalar(
                select(func.count()).select_from(TaskActivity).where(*criteria)
            )
            or 0
        )
        rows = tuple(
            (
                await self._session.scalars(
                    select(TaskActivity)
                    .where(*criteria)
                    .order_by(TaskActivity.created_at.desc(), TaskActivity.id)
                    .offset((page - 1) * page_size)
                    .limit(page_size)
                )
            ).all()
        )
        return tuple(self._activity_data(activity) for activity in rows), total
