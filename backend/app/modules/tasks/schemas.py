from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.modules.tasks.models import TaskPriority, TaskStatus


def _camel(name: str) -> str:
    first, *rest = name.split("_")
    return first + "".join(part.capitalize() for part in rest)


class TaskSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=_camel,
        populate_by_name=True,
        serialize_by_alias=True,
        from_attributes=True,
        extra="forbid",
    )


class CreateTaskRequest(TaskSchema):
    title: Annotated[str, Field(min_length=1, max_length=240)]
    description: Annotated[str | None, Field(max_length=10_000)] = None
    due_at: datetime | None = None

    @field_validator("title", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Task text must not be blank.")
        return normalized

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Due time must include a timezone offset.")
        return value


class UpdateTaskRequest(TaskSchema):
    title: Annotated[str | None, Field(min_length=1, max_length=240)] = None
    description: Annotated[str | None, Field(max_length=10_000)] = None
    due_at: datetime | None = None
    assignee_employee_id: UUID | None = None
    status: TaskStatus | None = None
    priority: TaskPriority | None = None

    @field_validator("title", "description")
    @classmethod
    def strip_text(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Task text must not be blank.")
        return normalized

    @field_validator("due_at")
    @classmethod
    def require_timezone(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.utcoffset() is None:
            raise ValueError("Due time must include a timezone offset.")
        return value

    @model_validator(mode="after")
    def require_change(self) -> "UpdateTaskRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one task field to update.")
        for field in ("title", "status", "priority"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Task {field} cannot be null.")
        return self


class TaskData(TaskSchema):
    id: UUID
    title: str
    description: str | None
    status: TaskStatus
    priority: TaskPriority
    assignee_employee_id: UUID | None
    created_by_user_id: UUID
    due_at: datetime | None
    completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class CreateTaskChecklistItemRequest(TaskSchema):
    title: Annotated[str, Field(min_length=1, max_length=240)]
    position: Annotated[int, Field(ge=0, le=100_000)] = 0

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Checklist title must not be blank.")
        return normalized


class UpdateTaskChecklistItemRequest(TaskSchema):
    title: Annotated[str | None, Field(min_length=1, max_length=240)] = None
    position: Annotated[int | None, Field(ge=0, le=100_000)] = None
    is_complete: bool | None = None

    @field_validator("title")
    @classmethod
    def strip_title(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = value.strip()
        if not normalized:
            raise ValueError("Checklist title must not be blank.")
        return normalized

    @model_validator(mode="after")
    def require_change(self) -> "UpdateTaskChecklistItemRequest":
        if not self.model_fields_set:
            raise ValueError("Provide at least one checklist field to update.")
        for field in ("title", "position", "is_complete"):
            if field in self.model_fields_set and getattr(self, field) is None:
                raise ValueError(f"Checklist {field} cannot be null.")
        return self


class TaskChecklistItemData(TaskSchema):
    id: UUID
    task_id: UUID
    title: str
    position: int
    is_complete: bool
    completed_at: datetime | None
    completed_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class CreateTaskCommentRequest(TaskSchema):
    body: Annotated[str, Field(min_length=1, max_length=10_000)]

    @field_validator("body")
    @classmethod
    def strip_body(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("Comment body must not be blank.")
        return normalized


class TaskCommentData(TaskSchema):
    id: UUID
    task_id: UUID
    author_user_id: UUID
    body: str
    created_at: datetime
    updated_at: datetime


class AddTaskAttachmentRequest(TaskSchema):
    media_asset_id: UUID


class TaskAttachmentData(TaskSchema):
    id: UUID
    task_id: UUID
    media_asset_id: UUID
    attached_by_user_id: UUID | None
    created_at: datetime
    updated_at: datetime


class TaskActivityData(TaskSchema):
    id: UUID
    task_id: UUID
    actor_user_id: UUID | None
    event_type: str
    payload: dict[str, object] | None
    created_at: datetime
