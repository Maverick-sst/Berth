from datetime import datetime, timezone
from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .db import Base

ACTIVITY_TARGETS = ("project", "task", "release", "deployment")

RELEASE_STATUSES = ("PLANNED", "READY", "DEPLOYING", "DEPLOYED", "FAILED")
RELEASE_TRANSITIONS = {
    "PLANNED": {"READY"},
    "READY": {"PLANNED", "DEPLOYING"},
    "DEPLOYING": {"DEPLOYED", "FAILED"},
    "DEPLOYED": set(),
    "FAILED": {"PLANNED"},
}
DEPLOYMENT_STATUSES = ("IN_PROGRESS", "SUCCEEDED", "FAILED")


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    tasks: Mapped[list["Task"]] = relationship(back_populates="project")
    releases: Mapped[list["Release"]] = relationship(back_populates="project")


class Task(Base):
    __tablename__ = "tasks"
    __table_args__ = (
        Index("ix_tasks_project_id", "project_id"),
        Index("ix_tasks_status", "status"),
        Index("ix_tasks_priority", "priority"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    priority: Mapped[str] = mapped_column(String(20), default="MEDIUM")
    status: Mapped[str] = mapped_column(String(30), default="TODO")
    assignee: Mapped[str] = mapped_column(String(120), default="Unassigned")
    project_id: Mapped[int | None] = mapped_column(
        ForeignKey("projects.id"), nullable=True
    )
    release_id: Mapped[int | None] = mapped_column(
        ForeignKey("releases.id"), nullable=True
    )
    due_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project | None"] = relationship(back_populates="tasks")
    release: Mapped["Release | None"] = relationship(back_populates="tasks")
    comments: Mapped[list["Comment"]] = relationship(
        back_populates="task", cascade="all, delete-orphan"
    )


class Comment(Base):
    __tablename__ = "comments"
    __table_args__ = (Index("ix_comments_task_id", "task_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    task_id: Mapped[int] = mapped_column(ForeignKey("tasks.id"), nullable=False)
    author: Mapped[str] = mapped_column(String(120), nullable=False, default="Unassigned")
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    task: Mapped["Task"] = relationship(back_populates="comments")


class ActivityEvent(Base):
    __tablename__ = "activity_events"
    __table_args__ = (
        Index("ix_activity_events_created_at", "created_at"),
        Index("ix_activity_events_entity", "entity_type", "entity_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    entity_type: Mapped[str] = mapped_column(String(30), nullable=False)
    entity_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    action: Mapped[str] = mapped_column(String(40), nullable=False)
    summary: Mapped[str] = mapped_column(String(300), nullable=False)
    actor: Mapped[str] = mapped_column(String(120), nullable=False, default="Berth Crew")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow
    )


class Release(Base):
    __tablename__ = "releases"
    __table_args__ = (Index("ix_releases_project_id", "project_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(ForeignKey("projects.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    project: Mapped["Project"] = relationship(back_populates="releases")
    tasks: Mapped[list["Task"]] = relationship(back_populates="release")
    deployments: Mapped[list["DeploymentAttempt"]] = relationship(
        back_populates="release", cascade="all, delete-orphan"
    )


class DeploymentAttempt(Base):
    __tablename__ = "deployment_attempts"
    __table_args__ = (
        Index("ix_deployments_release_id", "release_id"),
        Index("ix_deployments_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    release_id: Mapped[int] = mapped_column(ForeignKey("releases.id"), nullable=False)
    environment: Mapped[str] = mapped_column(String(50), nullable=False, default="dev")
    commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
    image_ref: Mapped[str | None] = mapped_column(String(300), nullable=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    source: Mapped[str] = mapped_column(String(30), nullable=False, default="manual")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    failure_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    release: Mapped["Release"] = relationship(back_populates="deployments")
