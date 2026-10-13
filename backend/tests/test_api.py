import pytest

from app.main import app


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
