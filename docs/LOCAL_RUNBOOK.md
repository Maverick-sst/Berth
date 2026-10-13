# Local runbook — Berth

## 1. Prerequisites

| Tool | Check | Version |
|---|---|---|
| Docker Engine/Desktop | `docker --version` | 24+ with Compose v2 (`docker compose version`) |
| (host-native backend only) Python | `python3 --version` | 3.12+ |
| (host-native frontend only) Node | `node --version` | 22+ |

Ports used: **3000** (frontend), **8000** (backend), **5432** (Postgres).
Ensure nothing else occupies them (`ss -tlnp | grep -E '3000|8000|5432'`).

## 2. Start the stack (recommended)

```bash
docker compose up --build -d
docker compose ps                  # all three services, postgres "(healthy)"
docker compose logs -f backend     # watch migrations + startup (Ctrl+C to stop watching)
```

On a **fresh volume** the backend runs migrations 0001→0004 automatically
before serving. First launch takes a few minutes (image builds).

## 3. Verify

```bash
curl http://localhost:8000/health        # {"status":"UP"}
curl http://localhost:8000/ready         # {"status":"READY"}
curl http://localhost:8000/api/projects  # [] or existing projects
```

Open <http://localhost:3000> — create a project, add tasks, advance them to
DONE, create a release, mark READY, start a deployment, finish it.
Everything you do persists (refresh the page to confirm).

## 4. Seed demo data (optional, safe)

```bash
curl -s -X POST http://localhost:3000/api/projects -H 'Content-Type: application/json' \
  -d '{"name":"Berth Demo","description":"Sample project for the walkthrough"}'

curl -s -X POST http://localhost:3000/api/tasks -H 'Content-Type: application/json' \
  -d '{"title":"Write runbook","project_id":1,"priority":"HIGH","assignee":"Rehan"}'
curl -s -X POST http://localhost:3000/api/tasks -H 'Content-Type: application/json' \
  -d '{"title":"Configure ingress","project_id":1,"priority":"MEDIUM"}'
curl -s -X PUT  http://localhost:3000/api/tasks/1 -H 'Content-Type: application/json' \
  -d '{"status":"DONE"}'
curl -s -X POST http://localhost:3000/api/releases -H 'Content-Type: application/json' \
  -d '{"name":"v1.0.0","project_id":1,"description":"First docked release"}'
```

## 5. Run tests

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python -m pytest -v          # 53 tests, in-memory DB — never touches your data
```

## 6. Host-native development (instead of Compose)

```bash
# Postgres (from compose or your own instance):
export DATABASE_URL='postgresql+psycopg://taskboard:taskboard@localhost:5432/taskboard'

cd backend
source .venv/bin/activate
alembic upgrade head
uvicorn app.main:app --reload --port 8000

cd ../frontend
npm ci
npm run dev          # http://localhost:5173, proxies /api -> :8000
```

## 7. Environment variables

Copy `.env.example` (root or `backend/`) for placeholder values. Relevant vars:

| Var | Default | Purpose |
|---|---|---|
| `DATABASE_URL` | compose-injected | Postgres connection |
| `CORS_ORIGINS` | `*` | comma-separated allowed origins (tighten off-local) |
| `DEPLOY_REPORT_TOKEN` | empty | bearer token for `POST /api/deployments/report` (unset → endpoint returns 503) |

Generate a report token with `openssl rand -hex 32`. **Never commit real values.**

## 8. Stop / reset

```bash
docker compose down        # stop, keep data
docker compose down -v     # stop AND erase the database volume (destructive!)
```

## 9. Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Backend restart-loop, logs show `connection refused` on 5432 | Postgres not healthy yet | Compose gates on `service_healthy`; check `docker compose logs postgres`. Retry `docker compose restart backend` |
| `port is already allocated` | something else on 3000/8000/5432 | stop the other process or change the compose mapping |
| Frontend shows error banner "is the backend running?" | API unreachable | `docker compose ps`; check `logs backend`; confirm `curl localhost:8000/health` |
| `alembic` says table already exists | volume created before migrations were authoritative | `docker compose down -v && docker compose up --build` (erases local demo data) |
| Migrations fail with FK/index errors | partial upgrade history | fresh volume rebuild above; never hand-edit applied migrations |
| `npm ci` fails | lockfile out of sync | run inside `frontend/`: `npm install` and commit the updated lockfile |
