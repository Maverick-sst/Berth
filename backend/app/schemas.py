from datetime import datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

TaskStatus = Literal["TODO", "IN_PROGRESS", "DONE"]
Priority = Literal["LOW", "MEDIUM", "HIGH"]
ProjectStatus = Literal["ACTIVE", "ARCHIVED"]
ReleaseStatus = Literal["PLANNED", "READY", "DEPLOYING", "DEPLOYED", "FAILED"]
DeploymentStatus = Literal["IN_PROGRESS", "SUCCEEDED", "FAILED"]
Environment = Literal["dev", "staging", "prod"]


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


class ReleaseCreate(BaseModel):
    project_id: int = Field(ge=1)
    name: str = Field(min_length=1, max_length=120)
    description: str = ""
    status: ReleaseStatus = "PLANNED"


class ReleaseUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=120)
    description: str | None = None
    status: ReleaseStatus | None = None


class TaskBrief(BaseModel):
    id: int
    title: str
    status: TaskStatus
    model_config = ConfigDict(from_attributes=True)


class ReadinessOut(BaseModel):
    ready: bool
    total_tasks: int
    done_tasks: int
    blockers: list[str]
    unfinished_tasks: list[TaskBrief]


class ReleaseOut(BaseModel):
    id: int
    project_id: int
    name: str
    description: str
    status: ReleaseStatus
    created_at: datetime
    model_config = ConfigDict(from_attributes=True)


class ReleaseDetailOut(ReleaseOut):
    readiness: ReadinessOut
    tasks: list[TaskBrief]


class DeploymentCreate(BaseModel):
    environment: Environment = "dev"
    commit_sha: str | None = Field(default=None, max_length=40)
    image_ref: str | None = Field(default=None, max_length=300)
    source: Literal["manual", "ci"] = "manual"
    status: DeploymentStatus = "IN_PROGRESS"


class DeploymentOut(BaseModel):
    id: int
    release_id: int
    environment: str
    commit_sha: str | None
    image_ref: str | None
    status: DeploymentStatus
    source: str
    started_at: datetime
    finished_at: datetime | None
    failure_reason: str | None
    model_config = ConfigDict(from_attributes=True)


class DeploymentFinish(BaseModel):
    status: Literal["SUCCEEDED", "FAILED"]
    failure_reason: str | None = Field(default=None, max_length=2000)


class StatsOut(BaseModel):
    total: int
    todo: int
    inProgress: int
    done: int
