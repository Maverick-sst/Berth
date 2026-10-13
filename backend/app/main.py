from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from prometheus_fastapi_instrumentator import Instrumentator

from .config import settings
from .db import get_db
from .models import Project, Task
from .schemas import (
    ProjectCreate,
    ProjectOut,
    ProjectUpdate,
    StatsOut,
    TaskCreate,
    TaskOut,
    TaskUpdate,
)

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
    for key, value in updates.items():
        setattr(task, key, value)
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
