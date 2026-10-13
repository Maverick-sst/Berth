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
