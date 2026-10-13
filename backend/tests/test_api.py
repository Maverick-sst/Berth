import pytest

from app.main import app


def create_project(client, name="Web Platform", **overrides):
    payload = {"name": name, **overrides}
    return client.post("/api/projects", json=payload)


def create_task(client, title="A task", **overrides):
    payload = {"title": title, **overrides}
    return client.post("/api/tasks", json=payload)


def test_health(client):
    assert client.get("/health").json() == {"status": "UP"}


def test_root(client):
    response = client.get("/")
    assert response.status_code == 200
    assert response.json()["service"] == app.title
    assert response.json()["docs"] == "/docs"


def test_ready(client):
    assert client.get("/ready").json() == {"status": "READY"}


def test_create_task_returns_201_with_defaults(client):
    response = client.post("/api/tasks", json={"title": "Deploy application", "priority": "HIGH", "assignee": "Student"})
    assert response.status_code == 201
    body = response.json()
    assert body["title"] == "Deploy application"
    assert body["priority"] == "HIGH"
    assert body["assignee"] == "Student"
    assert body["status"] == "TODO"
    assert body["description"] == ""
    assert body["id"] > 0


def test_create_task_rejects_blank_title(client):
    response = client.post("/api/tasks", json={"title": ""})
    assert response.status_code == 422


def test_create_task_rejects_invalid_status(client):
    response = client.post("/api/tasks", json={"title": "Valid", "status": "INVALID"})
    assert response.status_code == 422


def test_create_task_rejects_missing_title(client):
    response = client.post("/api/tasks", json={"description": "no title"})
    assert response.status_code == 422


def test_list_tasks_returns_all_ordered_desc(client):
    client.post("/api/tasks", json={"title": "First"})
    client.post("/api/tasks", json={"title": "Second"})
    response = client.get("/api/tasks")
    assert response.status_code == 200
    tasks = response.json()
    assert [t["title"] for t in tasks] == ["Second", "First"]


def test_get_task_by_id(client):
    created = client.post("/api/tasks", json={"title": "Findable"}).json()
    response = client.get(f"/api/tasks/{created['id']}")
    assert response.status_code == 200
    assert response.json()["title"] == "Findable"


def test_get_task_not_found(client):
    response = client.get("/api/tasks/9999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Task not found"


def test_update_task_partial_fields(client):
    created = client.post("/api/tasks", json={"title": "Original", "priority": "LOW"}).json()
    response = client.put(f"/api/tasks/{created['id']}", json={"title": "Renamed", "status": "IN_PROGRESS"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Renamed"
    assert body["status"] == "IN_PROGRESS"
    assert body["priority"] == "LOW"
    assert body["description"] == ""


def test_update_task_not_found(client):
    response = client.put("/api/tasks/9999", json={"title": "Ghost"})
    assert response.status_code == 404


def test_delete_task_removes_task(client):
    created = client.post("/api/tasks", json={"title": "Doomed"}).json()
    response = client.delete(f"/api/tasks/{created['id']}")
    assert response.status_code == 204
    assert client.get(f"/api/tasks/{created['id']}").status_code == 404


def test_delete_task_not_found(client):
    response = client.delete("/api/tasks/9999")
    assert response.status_code == 404


def test_stats_counts_by_status(client):
    client.post("/api/tasks", json={"title": "A"})
    b = client.post("/api/tasks", json={"title": "B"}).json()
    c = client.post("/api/tasks", json={"title": "C"}).json()
    client.put(f"/api/tasks/{b['id']}", json={"status": "IN_PROGRESS"})
    client.put(f"/api/tasks/{c['id']}", json={"status": "DONE"})
    response = client.get("/api/tasks/stats")
    assert response.status_code == 200
    assert response.json() == {"total": 3, "todo": 1, "inProgress": 1, "done": 1}


def test_create_project_defaults(client):
    response = create_project(client)
    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Web Platform"
    assert body["status"] == "ACTIVE"
    assert body["description"] == ""


def test_project_name_required(client):
    response = client.post("/api/projects", json={"description": "no name"})
    assert response.status_code == 422


def test_project_crud_roundtrip(client):
    created = create_project(client, name="Temp", description="d").json()
    updated = client.put(
        f"/api/projects/{created['id']}", json={"name": "Renamed", "status": "ARCHIVED"}
    )
    assert updated.status_code == 200
    assert updated.json()["name"] == "Renamed"
    assert updated.json()["status"] == "ARCHIVED"
    assert updated.json()["description"] == "d"
    assert client.delete(f"/api/projects/{created['id']}").status_code == 204
    assert client.get(f"/api/projects/{created['id']}").status_code == 404


def test_project_not_found(client):
    assert client.get("/api/projects/999").status_code == 404
    assert client.put("/api/projects/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/projects/999").status_code == 404


def test_delete_project_with_tasks_conflict(client):
    project = create_project(client).json()
    create_task(client, title="Blocked", project_id=project["id"])
    response = client.delete(f"/api/projects/{project['id']}")
    assert response.status_code == 409
    assert "tasks" in response.json()["detail"]
    assert client.get(f"/api/projects/{project['id']}").status_code == 200


def test_create_task_in_project(client):
    project = create_project(client, name="Ship").json()
    response = create_task(client, title="Build hull", project_id=project["id"])
    assert response.status_code == 201
    assert response.json()["project_id"] == project["id"]


def test_create_task_unknown_project_404(client):
    response = create_task(client, title="Orphan", project_id=999)
    assert response.status_code == 404
    assert response.json()["detail"] == "Project not found"


def test_update_task_reassign_project(client):
    project_a = create_project(client, name="A").json()
    project_b = create_project(client, name="B").json()
    task = create_task(client, project_id=project_a["id"]).json()
    response = client.put(f"/api/tasks/{task['id']}", json={"project_id": project_b["id"]})
    assert response.status_code == 200
    assert response.json()["project_id"] == project_b["id"]
    response = client.put(f"/api/tasks/{task['id']}", json={"project_id": None})
    assert response.json()["project_id"] is None


def test_update_task_unknown_project_404(client):
    task = create_task(client).json()
    response = client.put(f"/api/tasks/{task['id']}", json={"project_id": 999})
    assert response.status_code == 404


def test_task_due_date(client):
    response = create_task(client, title="Timed", due_date="2026-11-01T12:00:00Z")
    assert response.status_code == 201
    assert response.json()["due_date"] is not None


def test_project_tasks_and_global_filter_by_project(client):
    project = create_project(client, name="Scoped").json()
    other = create_project(client, name="Other").json()
    create_task(client, title="Inside", project_id=project["id"])
    create_task(client, title="Outside", project_id=other["id"])
    create_task(client, title="Loose")
    scoped = client.get(f"/api/projects/{project['id']}/tasks").json()
    assert [t["title"] for t in scoped] == ["Inside"]
    filtered = client.get("/api/tasks", params={"project_id": project["id"]}).json()
    assert [t["title"] for t in filtered] == ["Inside"]


def test_filter_tasks_by_status_and_priority(client):
    create_task(client, title="Low TODO", priority="LOW")
    high = create_task(client, title="High progress", priority="HIGH").json()
    client.put(f"/api/tasks/{high['id']}", json={"status": "IN_PROGRESS"})
    result = client.get(
        "/api/tasks", params={"status": "IN_PROGRESS", "priority": "HIGH"}
    ).json()
    assert [t["title"] for t in result] == ["High progress"]
    assert client.get("/api/tasks", params={"status": "BOGUS"}).status_code == 422
    assert client.get("/api/tasks", params={"priority": "BOGUS"}).status_code == 422


def test_search_tasks(client):
    create_task(client, title="Deploy ingress controller")
    create_task(client, title="Write runbook")
    result = client.get("/api/tasks", params={"search": "ingress"}).json()
    assert [t["title"] for t in result] == ["Deploy ingress controller"]


def test_pagination_bounded(client):
    for i in range(5):
        create_task(client, title=f"Task {i}")
    page1 = client.get("/api/tasks", params={"page": 1, "page_size": 2}).json()
    page2 = client.get("/api/tasks", params={"page": 2, "page_size": 2}).json()
    assert len(page1) == 2 and len(page2) == 2
    assert {t["id"] for t in page1}.isdisjoint({t["id"] for t in page2})
    assert client.get("/api/tasks", params={"page_size": 1000}).status_code == 422
    assert client.get("/api/tasks", params={"page": 0}).status_code == 422


def test_comment_roundtrip_and_ordering(client):
    task = create_task(client, title="Commented task").json()
    client.post(f"/api/tasks/{task['id']}/comments", json={"author": "Ana", "content": "First"})
    client.post(f"/api/tasks/{task['id']}/comments", json={"author": "Bo", "content": "Second"})
    response = client.get(f"/api/tasks/{task['id']}/comments")
    assert response.status_code == 200
    comments = response.json()
    assert [c["content"] for c in comments] == ["First", "Second"]
    assert comments[0]["author"] == "Ana"


def test_comment_content_required(client):
    task = create_task(client).json()
    response = client.post(f"/api/tasks/{task['id']}/comments", json={"content": ""})
    assert response.status_code == 422


def test_comments_on_missing_task_404(client):
    assert client.post("/api/tasks/999/comments", json={"content": "hi"}).status_code == 404
    assert client.get("/api/tasks/999/comments").status_code == 404


def test_task_activity_events_created(client):
    task = create_task(client, title="Tracked task").json()
    client.put(f"/api/tasks/{task['id']}", json={"status": "IN_PROGRESS"})
    client.put(f"/api/tasks/{task['id']}", json={"assignee": "Ana"})
    client.post(f"/api/tasks/{task['id']}/comments", json={"author": "Ana", "content": "ok"})
    events = client.get("/api/activity").json()
    actions = [(e["entity_type"], e["action"]) for e in events]
    assert ("task", "commented") in actions
    assert ("task", "status_changed") in actions
    assert ("task", "assigned") in actions
    assert ("task", "created") in actions
    assert events[0]["entity_id"] == task["id"]


def test_project_activity_events_created(client):
    project = create_project(client, name="Tracked project").json()
    client.put(f"/api/projects/{project['id']}", json={"description": "now real"})
    client.delete(f"/api/projects/{project['id']}")
    events = client.get("/api/activity").json()
    actions = [(e["entity_type"], e["action"]) for e in events]
    assert ("project", "created") in actions
    assert ("project", "updated") in actions
    assert ("project", "deleted") in actions


def test_activity_limit_and_ordering(client):
    for i in range(7):
        create_task(client, title=f"T{i}")
    events = client.get("/api/activity", params={"limit": 5}).json()
    assert len(events) == 5
    ids = [e["id"] for e in events]
    assert ids == sorted(ids, reverse=True)


def create_release(client, project_id, name="v1.0", **overrides):
    payload = {"project_id": project_id, "name": name, **overrides}
    return client.post("/api/releases", json=payload)


def test_release_create_defaults_and_readiness_empty(client):
    project = create_project(client).json()
    response = create_release(client, project["id"])
    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "PLANNED"
    detail = client.get(f"/api/releases/{body['id']}").json()
    assert detail["readiness"]["ready"] is False
    assert "no tasks" in detail["readiness"]["blockers"][0]


def test_release_unknown_project_404(client):
    response = create_release(client, 999)
    assert response.status_code == 404


def test_release_not_found(client):
    assert client.get("/api/releases/999").status_code == 404
    assert client.put("/api/releases/999", json={"name": "x"}).status_code == 404
    assert client.delete("/api/releases/999").status_code == 404


def test_release_readiness_calculated_from_tasks(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    t1 = create_task(client, title="Done work", project_id=project["id"]).json()
    create_task(client, title="Pending work", project_id=project["id"])
    client.post(f"/api/releases/{release['id']}/tasks/{t1['id']}")
    ptask = client.get("/api/tasks", params={"project_id": project["id"]}).json()
    for t in ptask:
        if t["title"] == "Pending work":
            client.post(f"/api/releases/{release['id']}/tasks/{t['id']}")
    client.put(f"/api/tasks/{t1['id']}", json={"status": "DONE"})
    detail = client.get(f"/api/releases/{release['id']}").json()
    readiness = detail["readiness"]
    assert readiness["total_tasks"] == 2
    assert readiness["done_tasks"] == 1
    assert readiness["ready"] is False
    assert readiness["blockers"] == ["1 of 2 tasks not DONE"]
    unfinished_ids = {t["id"] for t in readiness["unfinished_tasks"]}
    assert t1["id"] not in unfinished_ids


def test_release_all_tasks_done_ready(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    t1 = create_task(client, project_id=project["id"]).json()
    client.post(f"/api/releases/{release['id']}/tasks/{t1['id']}")
    client.put(f"/api/tasks/{t1['id']}", json={"status": "DONE"})
    detail = client.get(f"/api/releases/{release['id']}").json()
    assert detail["readiness"]["ready"] is True
    assert detail["readiness"]["blockers"] == []


def test_release_legal_transition_chain(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    rid = release["id"]
    t1 = create_task(client, project_id=project["id"]).json()
    client.post(f"/api/releases/{rid}/tasks/{t1['id']}")
    client.put(f"/api/tasks/{t1['id']}", json={"status": "DONE"})
    assert client.put(f"/api/releases/{rid}", json={"status": "READY"}).status_code == 200
    assert client.put(f"/api/releases/{rid}", json={"status": "DEPLOYING"}).status_code == 200
    dep = client.post(
        f"/api/releases/{rid}/deployments", json={"environment": "staging", "commit_sha": "abc123"}
    ).json()
    finish = client.post(f"/api/deployments/{dep['id']}/finish", json={"status": "SUCCEEDED"})
    assert finish.status_code == 200
    assert client.get(f"/api/releases/{rid}").json()["status"] == "DEPLOYED"


def test_release_illegal_transitions_409(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    rid = release["id"]
    assert client.put(f"/api/releases/{rid}", json={"status": "DEPLOYING"}).status_code == 409
    assert client.put(f"/api/releases/{rid}", json={"status": "DEPLOYED"}).status_code == 409
    assert client.put(f"/api/releases/{rid}", json={"status": "FAILED"}).status_code == 409
    assert client.put(f"/api/releases/{rid}", json={"status": "BOGUS"}).status_code == 422


def test_release_transition_out_of_terminal_state(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    rid = release["id"]
    t1 = create_task(client, project_id=project["id"]).json()
    client.post(f"/api/releases/{rid}/tasks/{t1['id']}")
    client.put(f"/api/tasks/{t1['id']}", json={"status": "DONE"})
    client.put(f"/api/releases/{rid}", json={"status": "READY"})
    client.put(f"/api/releases/{rid}", json={"status": "DEPLOYING"})
    dep = client.post(f"/api/releases/{rid}/deployments", json={"environment": "prod"}).json()
    client.post(
        f"/api/deployments/{dep['id']}/finish",
        json={"status": "FAILED", "failure_reason": "ImagePullBackOff"},
    )
    assert client.get(f"/api/releases/{rid}").json()["status"] == "FAILED"
    back = client.put(f"/api/releases/{rid}", json={"status": "PLANNED"})
    assert back.status_code == 200


def test_deployment_start_must_be_in_progress(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    response = client.post(
        f"/api/releases/{release['id']}/deployments", json={"status": "SUCCEEDED"}
    )
    assert response.status_code == 422


def test_deployment_finish_requires_reason_on_failure(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    dep = client.post(
        f"/api/releases/{release['id']}/deployments", json={"environment": "dev"}
    ).json()
    response = client.post(f"/api/deployments/{dep['id']}/finish", json={"status": "FAILED"})
    assert response.status_code == 422


def test_deployment_finish_idempotency_guard(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    dep = client.post(
        f"/api/releases/{release['id']}/deployments", json={"environment": "dev"}
    ).json()
    client.post(f"/api/deployments/{dep['id']}/finish", json={"status": "SUCCEEDED"})
    again = client.post(f"/api/deployments/{dep['id']}/finish", json={"status": "SUCCEEDED"})
    assert again.status_code == 409


def test_deployment_history_ordering_and_fields(client):
    project = create_project(client).json()
    release = create_release(client, project["id"], name="hist").json()
    d1 = client.post(
        f"/api/releases/{release['id']}/deployments",
        json={"environment": "dev", "commit_sha": "aaaa", "image_ref": "ghcr.io/x/y:sha"},
    ).json()
    client.post(f"/api/deployments/{d1['id']}/finish", json={"status": "SUCCEEDED"})
    d2 = client.post(
        f"/api/releases/{release['id']}/deployments",
        json={"environment": "staging", "commit_sha": "bbbb"},
    ).json()
    client.post(
        f"/api/deployments/{d2['id']}/finish",
        json={"status": "FAILED", "failure_reason": "CrashLoopBackOff"},
    )
    history = client.get(f"/api/releases/{release['id']}/deployments").json()
    assert [d["id"] for d in history] == [d2["id"], d1["id"]]
    assert history[1]["status"] == "SUCCEEDED"
    assert history[0]["status"] == "FAILED"
    assert history[0]["failure_reason"] == "CrashLoopBackOff"
    assert history[0]["finished_at"] is not None
    all_deployments = client.get("/api/deployments").json()
    assert len(all_deployments) == 2


def test_attach_task_cross_project_and_duplicate_409(client):
    project = create_project(client, name="A").json()
    other = create_project(client, name="B").json()
    release = create_release(client, project["id"]).json()
    foreign = create_task(client, project_id=other["id"]).json()
    loose = create_task(client).json()
    dup_target = create_task(client, project_id=project["id"]).json()
    client.post(f"/api/releases/{release['id']}/tasks/{dup_target['id']}")
    assert client.post(f"/api/releases/{release['id']}/tasks/{foreign['id']}").status_code == 409
    assert client.post(f"/api/releases/{release['id']}/tasks/{loose['id']}").status_code == 200
    other_release = create_release(client, project["id"], name="v2").json()
    assert client.post(f"/api/releases/{other_release['id']}/tasks/{dup_target['id']}").status_code == 409
    detach = client.delete(f"/api/releases/{release['id']}/tasks/{dup_target['id']}")
    assert detach.status_code == 200


def test_delete_release_with_tasks_409(client):
    project = create_project(client).json()
    release = create_release(client, project["id"]).json()
    t1 = create_task(client, project_id=project["id"]).json()
    client.post(f"/api/releases/{release['id']}/tasks/{t1['id']}")
    assert client.delete(f"/api/releases/{release['id']}").status_code == 409
    client.delete(f"/api/releases/{release['id']}/tasks/{t1['id']}")
    assert client.delete(f"/api/releases/{release['id']}").status_code == 204
