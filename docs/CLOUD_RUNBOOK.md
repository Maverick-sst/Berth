# Cloud runbook — Berth on AWS EKS

> **Read this first.** Every step marked **[COSTS MONEY]** creates billable
> AWS resources. Nothing in this repository applies Terraform automatically.
> You run these commands; you approve the plan; you destroy when done.

## Stage A — Choose and prepare the target

- Target: AWS EKS in `ap-south-1` (matches `terraform/` defaults).
- Confirm before starting: AWS account/role with EKS+VPC permissions, budget
  you accept, whether the environment is temporary (demo) or persistent.
- Expected cost drivers while the stack is up (verify current pricing):

| Resource | Rough monthly cost |
|---|---|
| EKS control plane | ~$73 |
| 2× t3.medium nodes | ~$60 |
| NAT gateway (+ data) | ~$65+ |
| Network Load Balancer (ingress/Service) | ~$16+ |
| EBS volumes (nodes + PVC) | ~$5–10 |

Total ≈ **$150–220/month** while up. Billing alerts are recommended but do
not prevent charges.

- Configure credentials locally (`aws configure` / SSO) or via GitHub OIDC.
  **Never paste secrets into chat, logs, or the repository.**

## Stage B — Validate infrastructure without applying

```bash
cd terraform
terraform init          # downloads providers (network only, no cost)
terraform fmt -check -recursive
terraform validate
cp terraform.tfvars.example terraform.tfvars   # edit if needed; tfvars is gitignored
terraform plan          # queries AWS; shows the exact billable list — READ IT
```

`terraform plan` shows what will be created. **Do not run `terraform apply`
until you have reviewed the plan and explicitly decided to pay.**

## Stage C — Build and publish images (no cost)

CI does this on every push to `main` after tests + Trivy gate:

- Images: `ghcr.io/<owner>/<repo>/berth-backend:<sha>` and
  `ghcr.io/<owner>/<repo>/berth-frontend:<sha>` — for this repository
  (lowercased, nested under the repo name):
  `ghcr.io/maverick-sst/berth/berth-backend:<sha>` and
  `ghcr.io/maverick-sst/berth/berth-frontend:<sha>`.
- After the first run, open the GHCR package pages and set visibility /
  access for the cluster (private packages need a pull secret):

```bash
kubectl create secret docker-registry ghcr-pull \
  --namespace berth \
  --docker-server=ghcr.io \
  --docker-username=<github-user> \
  --docker-password=<PAT-with-read:packages> \
  # then: helm ... --set imagePullSecrets[0].name=ghcr-pull
```

## Stage D — Provision and deploy  **[COSTS MONEY]**

```bash
cd terraform
terraform apply            # review the plan summary one last time; type yes

# configure kubectl for the new cluster (output `configure_kubectl` shows this):
aws eks update-kubeconfig --region ap-south-1 --name berth-eks
kubectl config current-context   # confirm you are on berth-eks, not another cluster

# confirm the EBS CSI driver is active — without it the Postgres PVC stays
# Pending (EKS 1.31 has no in-tree EBS provisioner). Terraform installs the
# add-on; verify before deploying:
kubectl get deployment ebs-csi-controller -n kube-system
kubectl get storageclass   # expect a gp2/gp3 class named after the CSI driver

# observability stack (kube-prometheus-stack, ~free besides storage):
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  --namespace monitoring --create-namespace \
  -f monitoring/prometheus-values.yaml

# application:
helm upgrade --install berth ./helm/taskboard \
  --namespace berth --create-namespace \
  --set backend.image=ghcr.io/maverick-sst/berth/berth-backend \
  --set backend.tag=<COMMIT_SHA> \
  --set frontend.image=ghcr.io/maverick-sst/berth/berth-frontend \
  --set frontend.tag=<COMMIT_SHA> \
  --set postgres.password=<generate-one>

# watch rollout:
kubectl -n berth get pods -w
kubectl -n berth wait --for=condition=available deployment/berth-berth-backend --timeout=300s

# smoke test:
kubectl -n berth port-forward svc/berth-berth-backend 8001:8000 &
curl -s localhost:8001/health && curl -s localhost:8001/ready
```

- **Ingress controller (required before enabling ingress):** the chart's
  Ingress resource does nothing by itself — install ingress-nginx first
  (creates a billable load balancer), then enable the chart ingress:

  ```bash
  helm upgrade --install ingress-nginx ingress-nginx \
    --repo https://kubernetes.github.io/ingress-nginx \
    --namespace ingress-nginx --create-namespace
  kubectl -n ingress-nginx get svc ingress-nginx-controller   # wait for EXTERNAL-IP
  helm upgrade berth ./helm/taskboard -n berth --reuse-values \
    --set ingress.enabled=true --set ingress.host=<nlb-dns-or-host>
  ```
- **Prometheus verification:** `kubectl -n monitoring port-forward
  svc/monitoring-kube-prometheus-prometheus 9090:9090` → check the
  `berth-berth-backend` target is **UP** at `/targets`.
- **CI deployment reporting (optional):** set `DEPLOY_REPORT_TOKEN` on the
  backend (`--set` a secret or use External Secrets) and the same value as a
  GitHub Actions secret (`DEPLOY_REPORT_TOKEN`, name only — never the value
  in logs); CI can then `POST /api/deployments/report` after publishing.

## Stage E — DNS / HTTPS (optional, only if exposing publicly)

- Berth has **no authentication** — do not expose it publicly without adding
  auth at the edge (e.g., ingress basic-auth/OAuth2 proxy) or accepting the risk.
- DNS record + cert-manager + Let's Encrypt are manual, user-owned steps.
  Do not modify DNS or issue certificates without explicit approval.

## Stage F — Rollback and teardown

Rollback the app (safe, keeps data):

```bash
helm -n berth list                                  # revisions
helm -n berth rollback berth <REVISION>             # chart revision
helm -n berth upgrade berth ./helm/taskboard ... \
  --set backend.tag=<PREVIOUS_SHA>                  # or pin a previous image SHA
kubectl -n berth rollout status deployment/berth-berth-backend
```

Debug unhealthy pods:

```bash
kubectl -n berth get events --sort-by=.lastTimestamp
kubectl -n berth describe pod <pod>
kubectl -n berth logs deploy/berth-berth-backend --tail=100
```

**Teardown  [COSTS MONEY / DESTRUCTIVE]:**

```bash
helm -n berth uninstall berth          # removes app + in-cluster postgres PVC? check:
kubectl -n berth get pvc               # PVC may persist after uninstall; delete explicitly if intended
helm -n monitoring uninstall monitoring
cd terraform && terraform destroy      # removes VPC/EKS/NAT — reads back every deletion
```

- `terraform destroy` permanently removes the cluster and everything on it.
  Anything you want to keep must be exported first.
- Some resources can outlive destroy (unreferenced EBS volumes, load balancer
  leftovers if orphaned) — check the AWS console for stragglers after destroy.
- **Never delete persistent data as an incidental part of a rollback.**

## GitHub repository settings needed (names only, no values)

- Actions enabled with `contents: read`, `packages: write` (workflow declares it).
- Optional secret `DEPLOY_REPORT_TOKEN` for CI deployment reporting.
- No AWS/kubeconfig secrets belong in this repository by design.
