from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .db import get_db
from .models import (
    ActivityEvent,
    Comment,
    DeploymentAttempt,
    Project,
    Release,
    Task,
)
from .schemas import (
    ActivityEventOut,
    CommentCreate,
    CommentOut,
    DeploymentCreate,
    DeploymentFinish,
    DeploymentOut,
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    ReleaseCreate,
    ReleaseDetailOut,
    ReleaseOut,
    ReleaseUpdate,
    StatsOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)
from .releases import can_transition, release_readiness
from .services import record_activity

app = FastAPI(title=settings.app_name, version="1.1.0")
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")


@app.get("/")
def root():
    return {"service": settings.app_name, "version": "1.1.0", "docs": "/docs"}


@app.get("/health")
def health():
    return {"status": "UP"}


@app.get("/ready")
def ready(db: Session = Depends(get_db)):
    db.execute(select(func.count(Task.id)))
    return {"status": "READY"}


def _get_project_or_404(project_id: int, db: Session) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@app.get("/api/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return list(db.scalars(select(Project).order_by(Project.id.desc())))


@app.post("/api/projects", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(**payload.model_dump())
    db.add(project)
    db.flush()
    record_activity(db, "project", project.id, "created", f"Project created: {project.name}")
    db.commit()
    db.refresh(project)
    return project


@app.get("/api/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, db: Session = Depends(get_db)):
    return _get_project_or_404(project_id, db)


@app.put("/api/projects/{project_id}", response_model=ProjectOut)
def update_project(
    project_id: int, payload: ProjectUpdate, db: Session = Depends(get_db)
):
    project = _get_project_or_404(project_id, db)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(project, key, value)
    record_activity(db, "project", project.id, "updated", f"Project updated: {project.name}")
    db.commit()
    db.refresh(project)
    return project


@app.delete("/api/projects/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project(project_id: int, db: Session = Depends(get_db)):
    project = _get_project_or_404(project_id, db)
    task_count = db.scalar(
        select(func.count(Task.id)).where(Task.project_id == project_id)
    )
    if task_count:
        raise HTTPException(
            status_code=409,
            detail="Project has tasks. Move or delete them before deleting the project.",
        )
    record_activity(db, "project", project.id, "deleted", f"Project deleted: {project.name}")
    db.delete(project)
    db.commit()


@app.get("/api/projects/{project_id}/tasks", response_model=list[TaskOut])
def list_project_tasks(
    project_id: int,
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    _get_project_or_404(project_id, db)
    query = select(Task).where(Task.project_id == project_id)
    if status:
        if status not in ("TODO", "IN_PROGRESS", "DONE"):
            raise HTTPException(status_code=422, detail="Invalid status filter")
        query = query.where(Task.status == status)
    if priority:
        if priority not in ("LOW", "MEDIUM", "HIGH"):
            raise HTTPException(status_code=422, detail="Invalid priority filter")
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    query = query.order_by(Task.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(query))


@app.get("/api/tasks", response_model=list[TaskOut])
def list_tasks(
    project_id: int | None = Query(default=None),
    status: str | None = Query(default=None),
    priority: str | None = Query(default=None),
    search: str | None = Query(default=None, max_length=100),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = select(Task)
    if project_id is not None:
        query = query.where(Task.project_id == project_id)
    if status:
        if status not in ("TODO", "IN_PROGRESS", "DONE"):
            raise HTTPException(status_code=422, detail="Invalid status filter")
        query = query.where(Task.status == status)
    if priority:
        if priority not in ("LOW", "MEDIUM", "HIGH"):
            raise HTTPException(status_code=422, detail="Invalid priority filter")
        query = query.where(Task.priority == priority)
    if search:
        query = query.where(Task.title.ilike(f"%{search}%"))
    query = query.order_by(Task.id.desc())
    query = query.offset((page - 1) * page_size).limit(page_size)
    return list(db.scalars(query))


@app.post(
    "/api/tasks/{task_id}/comments",
    response_model=CommentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_comment(task_id: int, payload: CommentCreate, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    comment = Comment(task_id=task_id, **payload.model_dump())
    db.add(comment)
    db.flush()
    record_activity(
        db, "task", task_id, "commented",
        f"Comment added on task: {task.title}",
        actor=payload.author,
    )
    db.commit()
    db.refresh(comment)
    return comment


@app.get("/api/tasks/{task_id}/comments", response_model=list[CommentOut])
def list_comments(task_id: int, db: Session = Depends(get_db)):
    if not db.get(Task, task_id):
        raise HTTPException(status_code=404, detail="Task not found")
    return list(
        db.scalars(
            select(Comment).where(Comment.task_id == task_id).order_by(Comment.id.asc())
        )
    )


@app.get("/api/activity", response_model=list[ActivityEventOut])
def list_activity(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(ActivityEvent).order_by(ActivityEvent.id.desc()).limit(limit)
        )
    )


@app.get("/api/releases", response_model=list[ReleaseOut])
def list_releases(
    project_id: int | None = Query(default=None),
    db: Session = Depends(get_db),
):
    query = select(Release).order_by(Release.id.desc())
    if project_id is not None:
        query = query.where(Release.project_id == project_id)
    return list(db.scalars(query))


@app.post("/api/releases", response_model=ReleaseOut, status_code=status.HTTP_201_CREATED)
def create_release(payload: ReleaseCreate, db: Session = Depends(get_db)):
    _validate_project_ref(payload.project_id, db)
    release = Release(**payload.model_dump())
    db.add(release)
    db.flush()
    record_activity(db, "release", release.id, "created", f"Release created: {release.name}")
    db.commit()
    db.refresh(release)
    return release


@app.get("/api/releases/{release_id}", response_model=ReleaseDetailOut)
def get_release(release_id: int, db: Session = Depends(get_db)):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    tasks = list(db.scalars(select(Task).where(Task.release_id == release.id)))
    detail = ReleaseDetailOut(
        id=release.id,
        project_id=release.project_id,
        name=release.name,
        description=release.description,
        status=release.status,
        created_at=release.created_at,
        readiness=release_readiness(db, release),
        tasks=tasks,
    )
    return detail


@app.put("/api/releases/{release_id}", response_model=ReleaseOut)
def update_release(release_id: int, payload: ReleaseUpdate, db: Session = Depends(get_db)):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    updates = payload.model_dump(exclude_unset=True)
    new_status = updates.pop("status", None)
    if new_status and new_status != release.status:
        try:
            can_transition(release, new_status)
        except ValueError as exc:
            raise HTTPException(status_code=409, detail=str(exc))
        record_activity(
            db, "release", release.id, "status_changed",
            f"Release status changed: {release.name} ({release.status} -> {new_status})",
        )
        release.status = new_status
    for key, value in updates.items():
        setattr(release, key, value)
    record_activity(db, "release", release.id, "updated", f"Release updated: {release.name}")
    db.commit()
    db.refresh(release)
    return release


@app.post("/api/releases/{release_id}/tasks/{task_id}", response_model=ReleaseDetailOut)
def attach_task(release_id: int, task_id: int, db: Session = Depends(get_db)):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    if task.release_id and task.release_id != release_id:
        raise HTTPException(
            status_code=409, detail="Task is already attached to another release"
        )
    if task.project_id and task.project_id != release.project_id:
        raise HTTPException(
            status_code=409, detail="Task does not belong to this release's project"
        )
    task.release_id = release_id
    record_activity(db, "release", release_id, "updated", f"Task attached to release: {release.name} <- {task.title}")
    db.commit()
    db.refresh(release)
    return get_release(release_id, db)


@app.delete("/api/releases/{release_id}/tasks/{task_id}", response_model=ReleaseDetailOut)
def detach_task(release_id: int, task_id: int, db: Session = Depends(get_db)):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    task = db.get(Task, task_id)
    if not task or task.release_id != release_id:
        raise HTTPException(status_code=404, detail="Task not attached to this release")
    task.release_id = None
    record_activity(db, "release", release_id, "updated", f"Task detached from release: {release.name} - {task.title}")
    db.commit()
    db.refresh(release)
    return get_release(release_id, db)


@app.delete("/api/releases/{release_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_release(release_id: int, db: Session = Depends(get_db)):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    attached = db.scalar(select(func.count(Task.id)).where(Task.release_id == release_id))
    if attached:
        raise HTTPException(
            status_code=409, detail="Release has tasks attached. Detach them before deleting."
        )
    record_activity(db, "release", release_id, "deleted", f"Release deleted: {release.name}")
    db.delete(release)
    db.commit()


@app.get("/api/releases/{release_id}/deployments", response_model=list[DeploymentOut])
def list_deployments(release_id: int, db: Session = Depends(get_db)):
    if not db.get(Release, release_id):
        raise HTTPException(status_code=404, detail="Release not found")
    return list(
        db.scalars(
            select(DeploymentAttempt)
            .where(DeploymentAttempt.release_id == release_id)
            .order_by(DeploymentAttempt.id.desc())
        )
    )


@app.post(
    "/api/releases/{release_id}/deployments",
    response_model=DeploymentOut,
    status_code=status.HTTP_201_CREATED,
)
def create_deployment(
    release_id: int, payload: DeploymentCreate, db: Session = Depends(get_db)
):
    release = db.get(Release, release_id)
    if not release:
        raise HTTPException(status_code=404, detail="Release not found")
    if payload.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=422, detail="New deployment attempts must start as IN_PROGRESS"
        )
    attempt = DeploymentAttempt(**payload.model_dump())
    attempt.release_id = release_id
    db.add(attempt)
    db.flush()
    record_activity(
        db, "deployment", attempt.id, "deployment_reported",
        f"Deployment attempt started: {release.name} -> {payload.environment}",
    )
    if release.status not in ("READY", "FAILED", "DEPLOYED") and payload.environment != "dev":
        pass
    if release.status == "READY":
        try:
            can_transition(release, "DEPLOYING")
        except ValueError:
            pass
        else:
            release.status = "DEPLOYING"
            record_activity(
                db, "release", release.id, "status_changed",
                f"Release status changed: {release.name} (READY -> DEPLOYING)",
            )
    db.commit()
    db.refresh(attempt)
    return attempt


@app.post(
    "/api/deployments/{deployment_id}/finish",
    response_model=DeploymentOut,
)
def finish_deployment(
    deployment_id: int, payload: DeploymentFinish, db: Session = Depends(get_db)
):
    attempt = db.get(DeploymentAttempt, deployment_id)
    if not attempt:
        raise HTTPException(status_code=404, detail="Deployment attempt not found")
    if attempt.status != "IN_PROGRESS":
        raise HTTPException(
            status_code=409, detail="Deployment attempt already finished"
        )
    if payload.status == "FAILED" and not payload.failure_reason:
        raise HTTPException(
            status_code=422, detail="failure_reason is required when marking FAILED"
        )
    attempt.status = payload.status
    attempt.failure_reason = payload.failure_reason
    attempt.finished_at = func.now()
    release = db.get(Release, attempt.release_id)
    if payload.status == "SUCCEEDED":
        if release.status == "DEPLOYING":
            release.status = "DEPLOYED"
            record_activity(
                db, "release", release.id, "status_changed",
                f"Release status changed: {release.name} (DEPLOYING -> DEPLOYED)",
            )
        record_activity(
            db, "deployment", attempt.id, "updated",
            f"Deployment succeeded: {release.name} -> {attempt.environment}",
        )
    else:
        if release.status == "DEPLOYING":
            release.status = "FAILED"
            record_activity(
                db, "release", release.id, "status_changed",
                f"Release status changed: {release.name} (DEPLOYING -> FAILED)",
            )
        record_activity(
            db, "deployment", attempt.id, "updated",
            f"Deployment failed: {release.name} -> {attempt.environment}: {payload.failure_reason}",
        )
    db.commit()
    db.refresh(attempt)
    return attempt


@app.get("/api/deployments", response_model=list[DeploymentOut])
def list_all_deployments(
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return list(
        db.scalars(
            select(DeploymentAttempt)
            .order_by(DeploymentAttempt.id.desc())
            .limit(limit)
        )
    )


@app.get("/api/tasks/stats", response_model=StatsOut)
def stats(db: Session = Depends(get_db)):
    rows = db.execute(
        select(Task.status, func.count(Task.id)).group_by(Task.status)
    ).all()
    counts = {row_status: count for row_status, count in rows}
    return StatsOut(
        total=sum(counts.values()),
        todo=counts.get("TODO", 0),
        inProgress=counts.get("IN_PROGRESS", 0),
        done=counts.get("DONE", 0),
    )


@app.get("/api/tasks/{task_id}", response_model=TaskOut)
def get_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


def _validate_project_ref(project_id: int | None, db: Session) -> None:
    if project_id is not None and not db.get(Project, project_id):
        raise HTTPException(status_code=404, detail="Project not found")


@app.post("/api/tasks", response_model=TaskOut, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate, db: Session = Depends(get_db)):
    _validate_project_ref(payload.project_id, db)
    task = Task(**payload.model_dump())
    db.add(task)
    db.flush()
    record_activity(db, "task", task.id, "created", f"Task created: {task.title}")
    db.commit()
    db.refresh(task)
    return task


@app.put("/api/tasks/{task_id}", response_model=TaskOut)
def update_task(
    task_id: int, payload: TaskUpdate, db: Session = Depends(get_db)
):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    updates = payload.model_dump(exclude_unset=True)
    _validate_project_ref(updates.get("project_id"), db)
    original_status = task.status
    for key, value in updates.items():
        setattr(task, key, value)
    if updates.get("status") and updates["status"] != original_status:
        record_activity(
            db, "task", task.id, "status_changed",
            f"Task status changed: {task.title} ({original_status} -> {task.status})",
        )
    if "assignee" in updates:
        record_activity(
            db, "task", task.id, "assigned", f"Task assigned to {task.assignee}: {task.title}"
        )
    if updates and "status" not in updates and "assignee" not in updates:
        record_activity(db, "task", task.id, "updated", f"Task updated: {task.title}")
    db.commit()
    db.refresh(task)
    return task


@app.delete("/api/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_task(task_id: int, db: Session = Depends(get_db)):
    task = db.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    db.delete(task)
    db.commit()
