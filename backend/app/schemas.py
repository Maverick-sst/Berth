from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]
ProjectStatus = Literal["ACTIVE", "ARCHIVED"]


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str = ""
    status: ProjectStatus = "ACTIVE"


class ProjectUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    status: ProjectStatus | None = None


class TaskOut(BaseModel):
    id: int
    title: str
    description: str
    priority: Priority
    status: TaskStatus
    assignee: str
    project_id: int | None = None
    due_date: datetime | None = None
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ProjectOut(ProjectCreate):
    id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = ""
    priority: Priority = "MEDIUM"
    status: TaskStatus = "TODO"
    assignee: str = "Unassigned"
    project_id: int | None = None
    due_date: datetime | None = None


class TaskUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    priority: Priority | None = None
    status: TaskStatus | None = None
    assignee: str | None = None
    project_id: int | None = Field(default=None, ge=1)
    due_date: datetime | None = None


class CommentCreate(BaseModel):
    author: str = Field(min_length=1, max_length=120, default="Unassigned")
    content: str = Field(min_length=1, max_length=2000)


class CommentOut(CommentCreate):
    id: int
    task_id: int
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ActivityEventOut(BaseModel):
    id: int
    entity_type: str
    entity_id: int | None
    action: str
    summary: str
    actor: str
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class StatsOut(BaseModel):
    total: int
    todo: int
    inProgress: int
    done: int
