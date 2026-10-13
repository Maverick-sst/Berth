from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .models import Release, RELEASE_STATUSES, RELEASE_TRANSITIONS, Task


def validate_transition(current: str, target: str) -> bool:
    return target in RELEASE_TRANSITIONS.get(current, set())


def allowed_next_statuses(current: str) -> list[str]:
    return sorted(RELEASE_TRANSITIONS.get(current, set()))


def can_transition(release: Release, target: str) -> None:
    if target not in RELEASE_STATUSES:
        raise ValueError(f"Unknown release status: {target}")
    if target == release.status:
        raise ValueError(f"Release is already {target}")
    if not validate_transition(release.status, target):
        legal = ", ".join(allowed_next_statuses(release.status)) or "none"
        raise ValueError(
            f"Illegal transition {release.status} -> {target}. Allowed: {legal}"
        )


def release_readiness(db: Session, release: Release) -> dict:
    tasks = list(db.scalars(select(Task).where(Task.release_id == release.id)))
    total = len(tasks)
    done = sum(1 for t in tasks if t.status == "DONE")
    unfinished = [
        {"id": t.id, "title": t.title, "status": t.status}
        for t in tasks
        if t.status != "DONE"
    ]
    blockers: list[str] = []
    if total == 0:
        blockers.append("Release has no tasks attached")
    if unfinished:
        blockers.append(
            f"{len(unfinished)} of {total} tasks not DONE"
        )
    ready = not blockers and release.status in ("PLANNED", "READY")
    return {
        "ready": ready,
        "total_tasks": total,
        "done_tasks": done,
        "blockers": blockers,
        "unfinished_tasks": unfinished,
    }
