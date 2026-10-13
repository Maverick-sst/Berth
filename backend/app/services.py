from sqlalchemy.orm import Session

from .models import ActivityEvent, ACTIVITY_TARGETS

_entity_labels = {
    "project": "Project",
    "task": "Task",
    "release": "Release",
    "deployment": "Deployment",
}


def record_activity(
    db: Session,
    entity_type: str,
    entity_id: int | None,
    action: str,
    summary: str,
    actor: str = "Berth Crew",
) -> ActivityEvent:
    if entity_type not in ACTIVITY_TARGETS:
        raise ValueError(f"Unknown activity target: {entity_type}")
    event = ActivityEvent(
        entity_type=entity_type,
        entity_id=entity_id,
        action=action,
        summary=f"{_entity_labels[entity_type]}: {summary}",
        actor=actor,
    )
    db.add(event)
    db.flush()
    return event
