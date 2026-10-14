# Berth — Cloud deployment & recording runbook

> **Full flow, step by step.** This is the operator guide: choose the instance,
> deploy with Terraform → AWS, set guardrails, prevent crashes at every gate,
> then record the video in the official submission order.
>
> Commit this doc was written against: `4ce05a7d3d7b5e8e619744597e8a8b5321545e05`.
>
> **Labels:** **[SAFE]** = read-only or no billable effect · **[COSTS MONEY]** =
> creates billable AWS resources · **[DESTRUCTIVE]** = irreversible.
>
> **Deadline: Sun 19 Oct 2026, 11:59 PM IST.** Late = −5 pts/24 h.

---

## 0. The full flow at a glance

```text
 ┌─ YOU ───────────────────────────────────────────────────────────────────┐
 │ 1. push to main ─▶ GitHub Actions: test(53) → build → Trivy gate → GHCR │
 │      └▶ immutable images: ghcr.io/maverick-sst/berth/berth-{fe,be}:SHA  │
 │ 2. terraform init/fmt/validate/plan  (SAFE — nothing applied)           │
 │ 3. terraform apply [COSTS] ─▶ VPC + NAT + EKS berth-eks 1.31 + 2×t3.med │
 │      └▶ aws-ebs-csi-driver add-on installed by Terraform (PVC support)  │
 │ 4. update-kubeconfig → verify context → verify nodes + CSI + StorageCl  │
 │ 5. helm upgrade --install berth (pinned SHA images + real DB password)  │
 │      └▶ backend runs: alembic upgrade head 0001→0004, then uvicorn      │
 │ 6. ingress-nginx install [COSTS: NLB] → enable chart ingress            │
 │ 7. kube-prometheus-stack → ServiceMonitor → /targets UP → Grafana       │
 │ 8. ArgoCD install → parameterized Application → show Synced (demo only) │
 │ 9. RECORD in SUBMISSION.md order → 10. teardown [DESTRUCTIVE]           │
 └─────────────────────────────────────────────────────────────────────────┘
```

CI never touches AWS. Real-cluster deployment is **manual by design** — no
cloud credentials live in this repository.

---

## 1. Pre-flight (all [SAFE])

```bash
cd ~/Devops_Capstone/devsecops-python
git status --short --branch          # expect: ## main, nothing to commit
git rev-parse HEAD                   # SAVE — this 40-char SHA is your image tag

# tool versions (Terraform >= 1.7 per terraform/versions.tf; kubectl ±1 of 1.31)
aws --version && terraform version && kubectl version --client && helm version

aws sts get-caller-identity          # right account? right role?
aws configure get region             # expect ap-south-1 (or always pass --region)
```

**Pre-flight checklist:**

- [ ] On `main`, clean tree, at the commit whose images you will deploy
- [ ] AWS permissions: EKS create/update, VPC/IAM full, EBS, ELB
- [ ] AWS Budgets alarm set (see §3 guardrails) **before** applying
- [ ] Confirm nothing already exists in `ap-south-1`
      (`aws eks list-clusters --region ap-south-1`,
      `aws ec2 describe-vpcs --region ap-south-1 --filters Name=tag:Name,Values=berth-vpc`)
- [ ] Free time-box: 2–3 h for up → record → destroy in one session

## 2. Choosing the instance type (why t3.medium)

| Option | vCPU/RAM | ~$/mo each (ap-south-1, on-demand) | Verdict |
|---|---|---|---|
| **t3.small** | 2/2 GiB | ~$30 | ❌ OOM risk: kube-prometheus-stack (~1.5–2 GiB) + ArgoCD (~0.4 GiB) + app (~640 Mi requests) exceeds 2 nodes × 2 GiB |
| **t3.medium** (repo default) | 2/4 GiB | ~$60 | ✅ fits app + monitoring + ArgoCD across 2 nodes with modest headroom; burstable CPU absorbs load-test spikes |
| **t3.large** | 2/8 GiB | ~$120 | Only if recording under sustained load or karpenter-style scaling demos; +$120/mo for little demo value |

**Instance choice = `terraform/main.tf` → `eks_managed_node_groups.main.instance_types = ["t3.medium"]`, min 2 / max 4 / desired 2.** Keep desired = 2 (rubric M8 wants ≥2 replicas; HPA min is 2). Don't raise max_size "to be safe" — autoscaling will happily bill you to 4 under load tests. The app requests `100m/256Mi` (backend) and `50m/64Mi` (frontend) per pod (`helm/taskboard/values.yaml`), so the workload is modest; it's the monitoring stack that dominates memory.

**Full stack cost while up (repo estimates — verify current pricing):**
EKS control plane ~$73 + 2× t3.medium ~$60 + NAT ~$65 + NLB (ingress) ~$16 + EBS ~$5–10 ≈ **$150–220/mo pro-rated by the hours it's up**. Up for one 8-hour day ≈ **$0.5–0.7 of a month's run-rate + control-plane $0.10/h** — cheap *if you destroy the same day*.

## 3. Guardrails — set these BEFORE any apply

1. **Billing alarm** (console: Billing → Budgets; or CLI, [SAFE] to set up):
   ```bash
   # Budget 1: alert at $40 actual (approaching stack cost)
   # Budget 2: alert at $80 (something is wrong)
   # Console: Billing → Budgets → Create budget → Cost budget → ap-south-1 linked account
   ```
   Budgets don't stop spend — they tell you while it's still small.
2. **Never `terraform apply -auto-approve`. Never `terraform destroy -auto-approve`.** The interactive `yes` prompt is your last gate.
3. **Plan-review checklist** (every apply, every destroy):
   - Plan summary says `Plan: N to add, 0 to change, 0 to destroy` on first apply (N ≈ 70–90 incl. security groups, routes, IAM).
   - Any line starting with `-` (destroy) or `-/+` (replace) on an apply you didn't intend = **stop and investigate**.
   - Confirm region in the header and `cluster_name = "berth-eks"`.
4. **Region pinning:** all commands carry `--region ap-south-1` or `AWS_REGION=ap-south-1` exported once. A wrong region creates *two* half-stacks.
5. **State safety:** Terraform state stays local (`terraform/*.tfstate`, gitignored). Losing it with a live cluster = orphaned billable resources. After apply: `cp terraform/terraform.tfstate ~/backup-berth-$(date +%F).tfstate` and **only ever run plan/apply/destroy from this one machine**.
6. **Time-box + destroy discipline:** decide the destroy date *before* apply. The destroy screenshot is a rubric item (M7) anyway.
7. **Secret hygiene:** DB password and any PAT never enter commands that get committed, screenshotted, or filmed. Use `read -s` variables (§5).

## 4. CI & GHCR (all [SAFE] to inspect)

Pipeline = `.github/workflows/ci-cd.yml`: **test** (pytest 53 + frontend build)
→ **build-scan-push** (both images, Trivy `HIGH,CRITICAL`, `exit-code: '1'`,
`ignore-unfixed` → fails on findings, then push with SHA tag) → **smoke-kind**
(pushes only: kind cluster, chart at 1 replica, curls health/ready/create).

```bash
# trigger a fresh run for the video: harmless docs commit, then push (user-run)
git commit --allow-empty -m "chore: trigger CI pipeline run" && git push
# watch: https://github.com/Maverick-sst/Berth/actions

# confirm images exist for the SHA you will deploy:
#   https://github.com/Maverick-sst?tab=packages  → berth/berth-backend, berth/berth-frontend
export SHA=$(git rev-parse HEAD)
# anonymous pull check (public packages — SAFE):
curl -s -o /dev/null -w '%{http_code}\n' \
  "https://ghcr.io/v2/maverick-sst/berth/berth-backend/manifests/$SHA"   # 200 = good
```

⚠️ **Image path rule:** paths are nested under the repo name (lowercased):
`ghcr.io/maverick-sst/berth/berth-backend` — NOT `ghcr.io/maverick-sst/berth-backend`.

Private-package fallback (only if you ever flip visibility, [SAFE to prepare]):

```bash
read -rs GHCR_PAT        # PAT with read:packages — paste, Enter; not echoed, not in history
kubectl create secret docker-registry ghcr-pull --namespace berth \
  --docker-server=ghcr.io --docker-username=<github-user> --docker-password="$GHCR_PAT"
# add to install: --set imagePullSecrets[0].name=ghcr-pull
```

## 5. Terraform — review then apply

```bash
cd terraform
terraform init                  # [SAFE] downloads providers
terraform fmt -check -recursive # [SAFE] expect silence (clean)
terraform validate              # [SAFE] expect: Success!
cp terraform.tfvars.example terraform.tfvars   # if not present; gitignored; never commit/show
terraform plan                  # [SAFE] queries AWS; READ ALL OF IT
```

**Plan must show:** VPC `berth-vpc` (10.20.0.0/16, 2 pub + 2 priv), IGW, 1 NAT,
routes/SGs, EKS `berth-eks` (1.31, public endpoint), node group `main`
2× t3.medium, IAM roles, **the EBS CSI IRSA role (`berth-eks-ebs-csi`) +
add-on**, OIDC provider. **No RDS, no ingress controller, nothing else.**

```bash
terraform apply                 # [COSTS MONEY] re-read summary → type yes
```

Apply takes ~15–20 min (control plane + nodes). When done:

```bash
terraform output configure_kubectl   # copy the exact command it prints
```

## 6. Kubeconfig & context safety

```bash
aws eks update-kubeconfig --region ap-south-1 --name berth-eks
kubectl config current-context      # MUST contain "berth-eks" — if not: STOP
kubectl config get-contexts         # never mutate an unrelated context (kind, other clusters)
kubectl get nodes                   # expect 2× Ready t3.medium
kubectl get ns                      # default/kube-system only; no berth yet
```

Kubeconfig setup deploys **nothing** — it's a key, not a workload.

## 7. Crash-prevention gates (run in this exact order)

```bash
# GATE 1 — CSI driver (without it, PVC Pending → postgres → backend crash loop)
kubectl get deployment ebs-csi-controller -n kube-system       # READY 2/2 or 1/1
kubectl get storageclass                                        # gp2/gp3 class present

# GATE 2 — Helm render before install (catches value typos)
cd ~/Devops_Capstone/devsecops-python
helm lint helm/taskboard
helm template berth helm/taskboard --namespace berth \
  --set backend.image=ghcr.io/maverick-sst/berth/berth-backend --set backend.tag=$SHA \
  --set frontend.image=ghcr.io/maverick-sst/berth/berth-frontend --set frontend.tag=$SHA \
  | less                                                        # eyeball, then q

# GATE 3 — install with pinned images + real password
read -rs PGPASSWORD      # generate first: openssl rand -hex 16 (never echo, never commit, never film)
helm upgrade --install berth ./helm/taskboard --namespace berth --create-namespace \
  --set backend.image=ghcr.io/maverick-sst/berth/berth-backend \
  --set backend.tag="$SHA" \
  --set frontend.image=ghcr.io/maverick-sst/berth/berth-frontend \
  --set frontend.tag="$SHA" \
  --set postgres.password="$PGPASSWORD"

# GATE 4 — wait with timeouts (don't eyeball-loop; let kubectl gate you)
kubectl -n berth get pods -w     # postgres first Running/Bound, then backend/frontend
kubectl -n berth wait --for=jsonpath='{.status.phase}'=Bound pvc/berth-postgres-data --timeout=120s
kubectl -n berth wait --for=condition=available deployment/berth-berth-backend --timeout=300s
kubectl -n berth wait --for=condition=available deployment/berth-berth-frontend --timeout=300s

# GATE 5 — functional smoke
kubectl -n berth port-forward svc/berth-berth-backend 8001:8000 &
curl -sf localhost:8001/health && curl -sf localhost:8001/ready   # UP + READY
curl -s localhost:8001/metrics | head -5                          # http_requests_total present
```

**Why the order matters:** PVC Bound *before* backend wait (backend can't be
Ready if the DB never came up); health ≠ ready (`/ready` actually queries the
DB); migrations run inside the backend container at start — verify with
`kubectl -n berth logs deploy/berth-berth-backend | grep -i alembic` (expect
`Running upgrade … -> 0004_releases_deployments`).

## 8. Ingress (public endpoint) — optional but recommended for M8

```bash
helm upgrade --install ingress-nginx ingress-nginx \
  --repo https://kubernetes.github.io/ingress-nginx \
  --namespace ingress-nginx --create-namespace        # [COSTS MONEY: NLB ~$16+/mo]
kubectl -n ingress-nginx wait --for=condition=available deploy/ingress-nginx-controller --timeout=300s
kubectl -n ingress-nginx get svc ingress-nginx-controller     # EXTERNAL-IP = NLB DNS name

helm upgrade berth ./helm/taskboard -n berth --reuse-values \
  --set ingress.enabled=true --set ingress.host=<nlb-dns-or-host>
kubectl -n berth get ingress berth-berth                      # ADDRESS fills in ~1–2 min
curl -sf http://<nlb-dns-or-host>/api/health                   # {"status":"UP"} via the real LB
```

⚠️ **No app auth + CORS `*`.** Anyone with the hostname can create/delete data.
For the demo: keep the hostname unlisted, take it down after recording. Edge
auth (ingress basic-auth / OAuth2-proxy) and DNS + cert-manager are optional,
user-owned, and cost-approving steps — skip unless you want public HTTPS.

## 9. Monitoring — Prometheus & Grafana

```bash
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
read -rs GRAFANA_PW    # openssl rand -hex 8 — overrides the chart's demo 'changeme'
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml --set grafana.adminPassword="$GRAFANA_PW"
kubectl -n monitoring get pods    # operator/prometheus/grafana/alertmanager → Running

# target check:
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090 &
#   http://localhost:9090/targets → endpoint :8443/:80 with ns=berth must be UP (scrape 15s)

# Grafana:
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80 &
#   http://localhost:3001 → admin / $GRAFANA_PW → import monitoring/grafana-dashboard.json
```

Generate traffic so panels populate:
`URL=http://localhost:8001/health scripts/load-test.sh` (500 requests) plus
clicking in the UI through port-forward `svc/berth-berth-frontend 8081:8080`.

> The committed dashboard was fixed to drop the `app="berth-backend"` label
> filter — the instrumentator's default metrics carry only
> `handler`/`status`/`method`. If panels are still empty: check `/targets` is
> UP first, then the query labels in Prometheus itself.

Port-forwarding = temporary local access, **not** a public endpoint.

## 10. ArgoCD — demo-only segment

⚠️ Ownership: Helm installs and owns `berth`; the ArgoCD Application below
pins the **same values**, so selfHeal has nothing to change. After recording,
delete the Application — the app keeps running under Helm. Not wired into CI
(say so plainly in the narration; it's a GitOps-mechanics demo).

```bash
kubectl create namespace argocd
kubectl apply -n argocd -f https://raw.githubusercontent.com/argoproj/argo-cd/stable/manifests/install.yaml
kubectl -n argocd rollout status deployment/argocd-server

cat <<'YAML' | kubectl apply -f -
apiVersion: argoproj.io/v1alpha1
kind: Application
metadata: {name: berth, namespace: argocd}
spec:
  project: default
  source:
    repoURL: https://github.com/Maverick-sst/Berth.git
    targetRevision: main
    path: helm/taskboard
    helm:
      parameters:
      - {forceString: true, name: backend.image,  value: ghcr.io/maverick-sst/berth/berth-backend}
      - {forceString: true, name: backend.tag,    value: <PASTE_SHA>}
      - {forceString: true, name: frontend.image, value: ghcr.io/maverick-sst/berth/berth-frontend}
      - {forceString: true, name: frontend.tag,   value: <PASTE_SHA>}
      - {forceString: true, name: postgres.password, value: <SAME_GENERATED_PASSWORD>}
  destination: {server: https://kubernetes.default.svc, namespace: berth}
  syncPolicy: {automated: {prune: false, selfHeal: true}}
YAML

kubectl -n argocd get application berth      # expect SYNCED + Healthy
kubectl -n argocd port-forward svc/argocd-server 8090:443 &
#   https://localhost:8090 → admin / (argocd-initial-admin-secret) → show Synced app

# after recording:
kubectl -n argocd delete application berth
```

## 11. Application demo script (for the video, woven into the K8s segment)

1. Port-forward the frontend (`kubectl -n berth port-forward svc/berth-berth-frontend 8081:8080`) → open `http://localhost:8081`.
2. Create project → add tasks → comment → watch the activity timeline update.
3. Attach 2 tasks to a release → readiness shows blockers ("2 of 2 tasks not DONE") → advance both to DONE → release READY.
4. Start a deployment attempt → finish as **FAILED with a reason** → then retry and finish **SUCCEEDED** → release DEPLOYED.
5. Refresh the page → everything persisted (proves Postgres + migrations).

Seed via UI (preferred on camera) or the same flow via the local runbook's curl examples pointed at `localhost:8001`.

## 12. Recording plan — official order (SUBMISSION.md)

| # | Segment | ~min | Show | Narration core |
|---|---|---|---|---|
| 1 | Slides | 2–3 | deck (≥8 slides, committed under demo/) | what/why of Berth |
| 2 | Codebase | 1–2 | main.py, models, migrations 0001–0004, App.jsx, ci-cd.yml | migrations are schema authority; readiness computed not faked |
| 3 | CI/CD | 2–3 | fresh push → green run → Trivy step → GHCR SHA tags | immutable SHA tags; Trivy gate fails builds |
| 4 | Terraform | 2 | `terraform plan` output; AWS Console VPC + EKS (ap-south-1) | plan-then-apply; destroy discipline |
| 5 | ArgoCD | 1–2 | Application SYNCED + Healthy in UI | GitOps mechanics; Helm remains owner |
| 6 | Kubernetes | 1–2 | `kubectl get pods/svc/ingress -n berth`, `helm list`; **app demo here** | probes, HPA, non-root |
| 7 | Prometheus | 1 | /targets → berth target UP | ServiceMonitor discovery |
| 8 | Grafana | 1 | imported dashboard with live panels | real rate/p95/errors |
| 9 | Evidence close | 1 | checklist on screen | destroy reminder |

**Never on camera:** `terraform.tfvars`, passwords/tokens, kubeconfig,
argocd admin secret, GHCR PAT. Big terminal font. Output = `demo/video.mp4` +
`demo/slides.pdf`, committed before submitting the form.

## 13. Evidence checklist (mapped to GRADING.md)

- M1: compose screenshot + app screenshots
- M2: `pytest -v` (53 passing) terminal capture
- M3: commit history (≥10 meaningful commits)
- M4: `docker compose up --build` + non-root uid check
- M5: green Actions run URL + GHCR package page (SHA tags)
- M6: Trivy table from the run (clean counts are fine — explain what was scanned)
- M7: `terraform plan` output + Console VPC/EKS screenshots + **`terraform destroy` completion screenshot**
- M8: pods/svc/`helm list`/ingress-accessible screenshots
- M9: `/metrics` output + Targets UP + populated Grafana panel
- M10: `demo/video.mp4` + `demo/slides.pdf` committed

## 14. Rollback, teardown & cost containment

**App-level rollback (safe, keeps data):**

```bash
helm -n berth list                      # find revision
helm -n berth rollback berth <REVISION> # chart-level rollback
# or redeploy a previous immutable image:
helm upgrade berth ./helm/taskboard -n berth --reuse-values --set backend.tag=<PREVIOUS_SHA>
kubectl -n berth rollout status deployment/berth-berth-backend
```

**Full teardown [DESTRUCTIVE] — in this order:**

```bash
kubectl -n argocd delete application berth          # if still present
helm -n berth uninstall berth                       # ⚠ PVC berth-postgres-data SURVIVES on purpose
kubectl -n berth get pvc                            # delete ONLY with explicit approval (data gone forever)
helm -n monitoring uninstall monitoring
helm -n ingress-nginx uninstall ingress-nginx       # removes the NLB — verify in console
cd terraform && terraform destroy                   # removes VPC/EKS/NAT/CSI role/add-on; re-reads every deletion
```

**Post-destroy sweep (console, ~5 min):** orphaned EBS volumes, leftover
load balancers/target groups/security groups (side-effect resources Terraform
doesn't track), and confirm billing alarms stop climbing. Destroy screenshot =
M7 evidence.

## 15. Troubleshooting quick table

| Symptom | Likely cause | First command |
|---|---|---|
| Pod `Pending` | no CSI / no StorageClass | §7 Gate 1; `kubectl get sc` |
| PVC `Pending` | CSI not running | `kubectl -n kube-system get pod -l app.kubernetes.io/name=aws-ebs-csi-driver` |
| `ImagePullBackOff` | wrong image path / tag / private pkg | `kubectl describe pod` → image string vs `ghcr.io/maverick-sst/berth/…:<SHA>` |
| `CrashLoopBackOff` backend | DB unreachable / wrong password | `kubectl -n berth logs deploy/berth-berth-backend --tail=50` |
| Backend not Ready | postgres not ready → readiness fails | postgres pod logs; secret `berth-postgres` vs your `--set` value |
| Ingress no ADDRESS | controller missing | §8 step 1 |
| Grafana panels empty | target down or label mismatch | `/targets` UP? then query labels |
| `terraform apply` hangs on nodes | IAM propagation | wait 5 min, re-run `terraform apply` |

---

*Related docs: `docs/CLOUD_RUNBOOK.md` (condensed original), `docs/DEMO_PLAN.md`
(ArgoCD + recording details), `docs/LOCAL_RUNBOOK.md` (local Compose path),
`monitoring/README.md` (observability verification).*
