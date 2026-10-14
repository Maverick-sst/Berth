# Berth — engineering work, releases, and deployment history

Berth is where engineering work docks: organize work into **projects**, track
**tasks** with comments and a real activity timeline, prepare **releases** with
server-computed readiness, and keep an auditable **deployment history** —
shipped through a complete DevSecOps pipeline (tests → container build →
vulnerability scanning → immutable GHCR images → Helm on Kubernetes →
monitoring).

> Evolved from the TaskBoard capstone baseline. The domain, release-readiness
> workflow, and deployment-history model are Berth's own.

## Architecture

```text
Browser ──▶ nginx (frontend, non-root, :8080)
                 │  /api proxy
                 ▼
           FastAPI backend (:8000)
                 │  SQLAlchemy + Alembic
                 ▼
           PostgreSQL 16
                 ▲
        Prometheus ◀── ServiceMonitor ──▶ Grafana dashboard
```

- **Frontend:** React 18 + Vite (JavaScript, no TypeScript), Tailwind CSS v4
  with shadcn-style components (Radix primitives). Responsive at mobile and
  desktop sizes.
- **Backend:** FastAPI, SQLAlchemy 2, Pydantic v2, prometheus-fastapi-instrumentator.
- **Database:** PostgreSQL; schema lifecycle owned by **Alembic migrations
  0001–0004**. The app never runs `create_all` in production.
- **CI/CD:** one authoritative GitHub Actions workflow (`.github/workflows/ci-cd.yml`).
- **Infra:** Terraform (VPC + EKS), Helm chart (`helm/taskboard`, chart name
  `berth`), kind smoke tests in CI.

### Data model

| Entity | Key fields |
|---|---|
| Project | name, description, status (ACTIVE/ARCHIVED) |
| Task | project FK, title, description, status TODO/IN_PROGRESS/DONE, priority LOW/MEDIUM/HIGH, assignee, due date, release FK |
| Comment | task FK, author, content |
| ActivityEvent | entity type/id, action, summary, actor, timestamp |
| Release | project FK, name, status PLANNED→READY→DEPLOYING→DEPLOYED/FAILED (FAILED→PLANNED retry) |
| DeploymentAttempt | release FK, environment, commit SHA, image ref, status, source (manual/ci), started/finished, failure reason |

**Release readiness** is computed server-side from real task states: a release
is ready only when it has tasks attached and every attached task is DONE.
Blockers are explicit and shown in the UI. Illegal release transitions are
rejected with HTTP 409.

**Deployment records are never fabricated.** Attempts start as IN_PROGRESS;
finishing requires an explicit result, and FAILED requires a failure reason.
CI can report outcomes through a token-protected endpoint
(`POST /api/deployments/report`, bearer `DEPLOY_REPORT_TOKEN`); UI-created
records are marked `source=manual`, CI ones `source=ci`.

## API overview

Interactive docs at `/docs` when the backend runs.

```text
GET    /                 service info
GET    /health           liveness (no DB)
GET    /ready            readiness (checks DB)
GET    /metrics          Prometheus metrics

GET    /api/projects                       list projects
POST   /api/projects                       create (201)
GET    /api/projects/{id}                  detail
PUT    /api/projects/{id}                  update
DELETE /api/projects/{id}                  delete (409 if tasks exist)
GET    /api/projects/{id}/tasks            project-scoped task list

GET    /api/tasks                          list (filters: project_id, status,
                                           priority, search; page, page_size ≤ 100)
POST   /api/tasks                          create (validates project_id)
GET    /api/tasks/{id}                     detail (404 handling)
PUT    /api/tasks/{id}                     partial update
DELETE /api/tasks/{id}                     delete (204)
GET    /api/tasks/stats                    counts by status
GET    /api/tasks/{id}/comments            list comments
POST   /api/tasks/{id}/comments            add comment
GET    /api/activity                       recent events (limit ≤ 100)

GET    /api/releases                       list (filter: project_id)
POST   /api/releases                       create (PLANNED)
GET    /api/releases/{id}                  detail incl. computed readiness
PUT    /api/releases/{id}                  update / validated transition
POST   /api/releases/{id}/tasks/{task_id}  attach task (409 guards)
DELETE /api/releases/{id}/tasks/{task_id}  detach task
DELETE /api/releases/{id}                  delete (409 if tasks attached)
GET    /api/releases/{id}/deployments      attempt history (newest first)
POST   /api/releases/{id}/deployments      start attempt (IN_PROGRESS only)
POST   /api/deployments/{id}/finish        record SUCCEEDED/FAILED
GET    /api/deployments                    global history
POST   /api/deployments/report             CI-reported outcome (bearer token)
```

## Quick start (Docker Compose)

Requirements: Docker Engine/Desktop with Compose v2. No other setup needed.

```bash
docker compose up --build
```

Open:

- Frontend: <http://localhost:3000>
- API docs: <http://localhost:8000/docs>
- Health / readiness: <http://localhost:8000/health>, <http://localhost:8000/ready>
- Metrics: <http://localhost:8000/metrics>

Stop: `docker compose down` (add `-v` to also erase the database volume —
destructive, choose deliberately).

The backend container runs `alembic upgrade head` before starting Uvicorn, so
a fresh volume gets the full schema automatically. See
[`docs/LOCAL_RUNBOOK.md`](docs/LOCAL_RUNBOOK.md) for host-native setup,
seeding demo data, and troubleshooting.

## Tests

53 pytest cases covering CRUD, validation, 404s, stats, comments, activity
ordering, release state machine, readiness, deployment history, and the
CI-report auth path — against an isolated in-memory database:

```bash
cd backend && python -m pytest -v
```

Frontend production build (the CI gate):

```bash
cd frontend && npm ci && npm run build
```

## CI/CD pipeline

`.github/workflows/ci-cd.yml` runs on pushes/PRs to `main`:

1. **test** — pytest (fails the pipeline on test failure) + frontend build.
2. **build-scan-push** — buildx builds both images, **Trivy scans with a
   HIGH/CRITICAL gate (`exit-code: 1`, unfixed-only)**, images are published
   to GHCR tagged with the immutable commit SHA.
3. **smoke-kind** (pushes only) — spins up a kind cluster, deploys the Helm
   chart with real PostgreSQL, waits for readiness, and curls
   health/ready/create-project.

Real-cluster deployments are intentionally **not** automated in CI; see the
cloud runbook. No cloud credentials live in this repository.

## Kubernetes / Helm

```bash
helm upgrade --install berth ./helm/taskboard \
  --namespace berth --create-namespace \
  --set backend.image=ghcr.io/<OWNER>/<REPO>/berth-backend \
  --set backend.tag=<COMMIT_SHA> \
  --set frontend.image=ghcr.io/<OWNER>/<REPO>/berth-frontend \
  --set frontend.tag=<COMMIT_SHA>
```

> Image paths are **nested under the repo name** because the CI lowercases
> `owner/repo`: for this repository that is
> `ghcr.io/maverick-sst/berth/berth-backend` and
> `ghcr.io/maverick-sst/berth/berth-frontend`, tagged with the full commit SHA
> (immutable; never `latest` for a real deploy).

- Backend: Deployment + Service (`:8000`), readiness `/ready`, liveness `/health`,
  HPA (CPU 60%, 2–6 replicas), ServiceMonitor for the Prometheus Operator.
- Frontend: Deployment + Service (`:8080`, unprivileged nginx).
- PostgreSQL in-cluster with a 5Gi PVC (classroom/demo; use RDS for real prod).
- Ingress (off by default; enable with `values-dev.yaml` / `values-prod.yaml`):
  `/api` → backend, `/` → frontend. Enabling it also requires an ingress
  controller — e.g. `helm upgrade --install ingress-nginx ingress-nginx
  --repo https://kubernetes.github.io/ingress-nginx -n ingress-nginx
  --create-namespace` (the resulting cloud load balancer is billable).
- Both deployments run non-root (`runAsNonRoot`, uid 10001, caps dropped).

Validate without a cluster: `helm lint helm/taskboard && helm template berth ./helm/taskboard`.

## Observability

- Backend exposes Prometheus metrics at `/metrics`.
- `monitoring/prometheus-values.yaml` — kube-prometheus-stack values that let
  ServiceMonitors in any namespace be discovered.
- `monitoring/grafana-dashboard.json` — importable dashboard: request rate,
  p95 latency, error rate, status-code breakdown.
- `monitoring/README.md` — exact steps to verify the scrape target is UP and
  the dashboard is populated (never trust an unverified dashboard).

## Infrastructure (Terraform, AWS)

`terraform/` provisions VPC (2 public + 2 private subnets, single NAT) and an
EKS 1.31 cluster (t3.medium managed nodes, 2–4), and installs the
**aws-ebs-csi-driver add-on** with an IRSA role so the chart's PVC binds
(EKS 1.31 has no in-tree EBS provisioner). Validated with
`terraform fmt -check -recursive` and `terraform validate`; `terraform.tfvars.example`
holds placeholders only.

> **Cost warning:** running this cluster costs real money (EKS control plane
> ~$73/mo, 2× t3.medium ~$60/mo, NAT gateway ~$65/mo + data — roughly $150–200/mo
> total while up, plus LB/disks). **Run `terraform destroy` when done.**
> Exact sequence, cost drivers, and teardown steps: [`docs/CLOUD_RUNBOOK.md`](docs/CLOUD_RUNBOOK.md).

## Repository layout

```text
backend/            FastAPI app, Alembic migrations, 53 pytest tests
frontend/           React/Vite UI (Tailwind v4, shadcn-style components)
helm/taskboard/     Berth Helm chart (chart name: berth)
k8s/                lab manifests (SQLite-backed, demo-only — see note)
monitoring/         Prometheus values, Grafana dashboard, verification runbook
terraform/          AWS VPC + EKS (validated, never applied by CI)
troubleshooting/    deliberately broken manifests for the debugging lab
scripts/            load-test helper
docs/               local + cloud runbooks, demo plan
```

> `k8s/deployment.yaml` points DATABASE_URL at SQLite on purpose (lab/demo
> manifests kept for kubectl practice). For real data use Compose or the Helm
> chart (PostgreSQL + PVC).

## Known limitations

- **No authentication.** This is a single-tenant demo; do not expose it to the
  public internet. Auth/RBAC is a prerequisite for real multi-user use.
- CORS defaults to `*` for local development — set `CORS_ORIGINS` in shared
  environments.
- CI deployment reporting is protected by a shared bearer token, not per-user
  identity.
- PostgreSQL runs in-cluster with a PVC for the classroom demo (RDS tradeoff
  documented in the runbook).

## Rubric traceability

| Requirement | Implementation | Evidence |
|---|---|---|
| Full-stack + DB (M1) | FastAPI + React + PostgreSQL/Alembic | Compose stack, migrations 0001–0004 |
| ≥4 REST endpoints (M1) | 25+ endpoints across 6 entities | `/docs`, tests |
| Pytest ≥5 tests, ≥3 endpoints, isolated DB (M2) | 53 tests, 8+ endpoints, in-memory DB | `pytest -v` output |
| Git hygiene (M3) | meaningful messages, `.gitignore` incl. `.venv`/`.env` | commit history |
| Docker non-root both images (M4) | backend uid 10001, nginx-unprivileged uid 101 | `docker compose exec frontend id` |
| CI on push, tests+build gate (M5) | `.github/workflows/ci-cd.yml` | Actions run URL |
| GHCR + SHA tags (M5) | `docker/build-push-action`, tag `github.sha` | GHCR package page |
| Trivy HIGH/CRITICAL gate (M6) | `exit-code: '1'`, both images | pipeline logs |
| Terraform VPC+EKS, tfvars.example (M7) | `terraform/`, validated statically | fmt/validate output; apply+destroy screenshots (user-run) |
| K8s+Helm, probes, HPA, ingress (M8) | `helm/taskboard` validated with lint/template | cluster screenshots (user-run) |
| Prometheus/Grafana real (M9) | ServiceMonitor + dashboard JSON + runbook | Targets page + dashboard screenshots (user-run) |
| Docs/video/slides (M10) | this README, `docs/`, `demo/` plan | `docs/DEMO_PLAN.md` |

## Submission artifacts

- Video walkthrough + slide deck are user-owned deliverables — the recording
  script, shot list, and slide outline live in [`docs/DEMO_PLAN.md`](docs/DEMO_PLAN.md).
- After recording, place `demo/video.mp4` (or link) and `demo/slides.pdf` in
  the `demo/` folder per the submission guide.
