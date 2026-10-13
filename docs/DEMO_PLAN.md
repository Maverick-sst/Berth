# Demo plan — Berth submission

Submission requirements (from `GRADING.md` M10 + `SUBMISSION.md`):
a **video** (mandatory — missing video = 0 for M10) presenting slides first,
then a live walkthrough in the order below; and a **slide deck** (≥8 slides)
committed to the repo under `demo/`.

## Recording checklist

- [ ] Record slides section first (2–3 min), then the live walkthrough
- [ ] Terminal font large enough to read on video
- [ ] Do **not** show real secrets, tokens, or `terraform.tfvars`
- [ ] Show `pytest` output and a green GitHub Actions run end-to-end
- [ ] Save as `demo/video.mp4`, slides as `demo/slides.pdf` (or `.pptx`)
- [ ] Commit both into the repository before submitting the form

## Suggested slide outline (8 slides minimum)

1. **Title** — Berth: engineering work, releases, deployment history; your name, repo link
2. **Problem & domain** — why TaskBoard-style clones are generic; Berth's release-readiness + deployment-history focus
3. **Tech stack** — FastAPI, SQLAlchemy/Alembic, PostgreSQL, React/Vite/Tailwind, Docker, GHCR, Trivy, Terraform, EKS, Helm, Prometheus/Grafana
4. **Architecture diagram** — browser → nginx → FastAPI → Postgres; CI → GHCR; Helm → cluster; monitoring
5. **CI/CD flow** — test → build → Trivy gate → GHCR (SHA tags) → kind smoke; deployment stays manual
6. **Infrastructure** — Terraform VPC+EKS diagram; cost controls & destroy discipline
7. **Kubernetes setup** — chart structure, probes, HPA, ingress, non-root securityContext
8. **Observability** — ServiceMonitor, /metrics, Grafana panels (rate/latency/errors)
9. **Key learnings** — migrations as authority, readiness computed not faked, auditable deployments, least-privilege registry

## Video walkthrough script (match SUBMISSION.md order)

1. **Codebase overview** (1–2 min) — `backend/app/main.py`, models, migrations
   0001–0004, `frontend/src/` pages, single CI workflow.
2. **CI/CD end-to-end** (2–3 min) — make a trivial commit (e.g. bump
   `app_version` or docs tweak), push to `main`, watch the Actions run:
   test → Trivy → GHCR publish → kind smoke. Open the GHCR package page and
   show the SHA tag.
3. **Terraform** (2 min) — show `terraform plan` output (user-run, cluster can
   be already up or the plan can be from a dry run), AWS Console screenshot of
   VPC + EKS in `ap-south-1`.
4. **ArgoCD** (1–2 min) — after installing ArgoCD on the cluster (see below),
   show the Application syncing the Berth Helm chart and the sync status in
   the UI.
5. **Kubernetes** (1 min) — `kubectl get pods -n berth`, `kubectl get svc`,
   ingress, `helm list -n berth`.
6. **Prometheus** (1 min) — Targets page showing `berth-berth-backend` UP.
7. **Grafana** (1 min) — imported dashboard with live panels after generating
   traffic (`scripts/load-test.sh` with `URL=http://localhost:8000/health` or
   port-forwarded service).
8. **App demo woven in** — create project → tasks → comments → release READY →
   deployment attempt → finish (show one FAILED with a reason, then SUCCEEDED)
   → activity timeline reflects everything (refresh to prove persistence).

## ArgoCD (GitOps segment)

Per the submission guide's video checklist, show a synced ArgoCD Application.
Minimal setup on the demo cluster (user-run, cluster already provisioned):

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deployment/argocd-server

# register the Berth chart as an Application:
cat <<'YAML' | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata:
  name: berth
  namespace: argocd
spec:
  project: default
  source:
    repoURL: https://github.com/<owner>/<repo>.git
    targetRevision: main
    path: helm/taskboard
  destination:
    server: https://kubernetes.default.svc
    namespace: berth
  syncPolicy:
    automated:
      prune: false
      selfHeal: true
YAML

kubectl -n argocd port-forward svc/argocd-server 8090:443
# open https://localhost:8090 — show the Application synced
```

Notes: ArgoCD syncs the chart from your repository; the initial `helm
upgrade --install` (Stage D) and the ArgoCD Application manage the same
release — pick one owner for ongoing changes (recommend: let ArgoCD own it
after the first install, or uninstall the ArgoCD Application after the demo
to avoid two controllers fighting).

## Evidence to capture while recording

- `pytest -v` terminal output (all 53 passing)
- Green Actions run URL + Trivy step output
- GHCR package page with SHA tags
- `terraform plan` output + Console VPC/EKS screenshots
- `terraform destroy` completion screenshot (after the demo — no runaway costs)
- `kubectl get pods`/`helm list` screenshots
- Prometheus Targets UP + Grafana populated panel
