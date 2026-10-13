#!/usr/bin/env python3
"""Generate demo/slides.pdf - Berth capstone presentation deck.

Design: clean zinc/near-black on white, generous whitespace, one message
per slide. Run: python3 tools/build_slides.py
"""
from reportlab.lib.pagesizes import landscape
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor
from reportlab.pdfgen import canvas

W, H = landscape((1280, 720))
INK = HexColor("#18181b")        # zinc-900
MUTED = HexColor("#71717a")      # zinc-500
FAINT = HexColor("#e4e4e7")      # zinc-200
BG = HexColor("#ffffff")
ACCENT = HexColor("#2563eb")     # restrained blue for emphasis only
CARD = HexColor("#fafafa")

import os
OUT = os.path.join(os.path.dirname(__file__), "..", "demo", "slides.pdf")


def header(c, title, kicker=None, page=None):
    c.setFillColor(BG)
    c.rect(0, 0, W, H, stroke=0, fill=1)
    if kicker:
        c.setFont("Helvetica-Bold", 11)
        c.setFillColor(MUTED)
        c.drawString(18 * mm, H - 24 * mm, kicker.upper())
    c.setFont("Helvetica-Bold", 34)
    c.setFillColor(INK)
    c.drawString(18 * mm, H - 40 * mm, title)
    c.setStrokeColor(FAINT)
    c.setLineWidth(1)
    c.line(18 * mm, H - 48 * mm, W - 18 * mm, H - 48 * mm)
    if page:
        c.setFont("Helvetica", 10)
        c.setFillColor(MUTED)
        c.drawRightString(W - 18 * mm, 12 * mm, f"Berth - DevSecOps Capstone   ·   {page}")


def bullets(c, items, x=18 * mm, y=None, size=15, gap=10 * mm, maxw=None):
    y = y if y is not None else H - 62 * mm
    c.setFont("Helvetica", size)
    for item in items:
        if isinstance(item, tuple):
            bold, rest = item
            c.setFillColor(INK)
            c.setFont("Helvetica-Bold", size)
            c.drawString(x, y, bold)
            bw = c.stringWidth(bold, "Helvetica-Bold", size)
            c.setFont("Helvetica", size)
            c.setFillColor(HexColor("#3f3f46"))
            c.drawString(x + bw + 3 * mm, y, rest)
        else:
            c.setFillColor(HexColor("#3f3f46"))
            c.drawString(x, y, item)
        c.setFillColor(MUTED)
        c.circle(x - 4 * mm, y + 3.5, 2, stroke=0, fill=1)
        y -= gap
    return y


def boxes(c, rows, y_top, col_w=None, x0=18 * mm, gap=6 * mm, h=26 * mm, size=12):
    col_w = col_w or (W - 36 * mm - gap * (len(rows) - 1)) / len(rows)
    x = x0
    for title, sub in rows:
        c.setFillColor(CARD)
        c.setStrokeColor(FAINT)
        c.roundRect(x, y_top - h, col_w, h, 3 * mm, stroke=1, fill=1)
        c.setFillColor(INK)
        c.setFont("Helvetica-Bold", size)
        c.drawCentredString(x + col_w / 2, y_top - h / 2 + 4, title)
        c.setFont("Helvetica", 9.5)
        c.setFillColor(MUTED)
        c.drawCentredString(x + col_w / 2, y_top - h / 2 - 10, sub)
        x += col_w + gap


def arrow(c, x, y, w=10 * mm):
    c.setStrokeColor(MUTED)
    c.setLineWidth(1.4)
    c.line(x, y, x + w, y)
    c.setFillColor(MUTED)
    p = c.beginPath()
    p.moveTo(x + w, y + 1.6)
    p.lineTo(x + w, y - 1.6)
    p.lineTo(x + w + 2.4, y)
    p.close()
    c.drawPath(p, stroke=0, fill=1)


c = canvas.Canvas(OUT, pagesize=(W, H))
P = 0

# ---- Slide 1: Title -------------------------------------------------------
c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
c.setFillColor(INK)
c.setFont("Helvetica-Bold", 76)
c.drawCentredString(W / 2, H * 0.60, "Berth")
c.setFont("Helvetica", 22)
c.setFillColor(HexColor("#3f3f46"))
c.drawCentredString(W / 2, H * 0.50, "Engineering work, releases, and deployment history - docked.")
c.setFont("Helvetica", 14)
c.setFillColor(MUTED)
c.drawCentredString(W / 2, H * 0.38, "DevSecOps Final Capstone  ·  Session 21")
c.drawCentredString(W / 2, H * 0.32, "Maverick-sst/Berth  ·  github.com/Maverick-sst/Berth")
c.setFillColor(ACCENT)
c.rect(W / 2 - 14 * mm, H * 0.66, 28 * mm, 1.2 * mm, stroke=0, fill=1)
c.showPage(); P += 1

# ---- Slide 2: Problem & domain --------------------------------------------
header(c, "A TaskBoard clone is not a product", "Problem & domain", P + 1)
bullets(c, [
    ("Generic clones:  ", "rename labels, ship a to-do list, add zero domain depth."),
    ("Berth's answer:  ", "release readiness and deployment history are first-class product features."),
    ("Readiness is computed  ", "from real task states - never hard-coded or fabricated."),
    ("Deployments are auditable:  ", "every attempt recorded with outcome and failure reason."),
    ("Nothing pretends success  ", "- the UI can't fabricate a passing deployment."),
], size=15, gap=13 * mm)
c.showPage(); P += 1

# ---- Slide 3: Tech stack ---------------------------------------------------
header(c, "Tech stack", "What Berth is built with", P + 1)
boxes(c, [
    ("FastAPI", "Python 3.12 - REST API"),
    ("PostgreSQL 16", "Alembic migrations"),
    ("React 18 + Vite", "Tailwind v4 / shadcn-style"),
    ("SQLAlchemy 2", "Pydantic v2 validation"),
], H - 66 * mm, size=13)
boxes(c, [
    ("Docker Compose", "local full stack"),
    ("GitHub Actions", "CI/CD pipeline"),
    ("Trivy", "HIGH/CRITICAL gate"),
    ("GHCR", "immutable SHA tags"),
], H - 66 * mm - 34 * mm, size=13)
boxes(c, [
    ("Terraform", "AWS VPC + EKS"),
    ("Kubernetes", "probes, HPA, ingress"),
    ("Helm", "berth chart"),
    ("Prometheus + Grafana", "observability"),
], H - 66 * mm - 68 * mm, size=13)
c.showPage(); P += 1

# ---- Slide 4: Architecture -------------------------------------------------
header(c, "Architecture", "Request & data flow", P + 1)
y = H - 78 * mm
c.setFont("Helvetica-Bold", 13)
boxes(c, [
    ("Browser", "React UI on :3000"),
], y, col_w=42 * mm, size=12)
arrow(c, 60 * mm, y - 13 * mm)
boxes(c, [
    ("nginx", "non-root :8080, /api proxy"),
], y, col_w=52 * mm, x0=74 * mm, size=12)
arrow(c, 126 * mm, y - 13 * mm)
boxes(c, [
    ("FastAPI :8000", "25+ endpoints"),
], y, col_w=48 * mm, x0=140 * mm, size=12)
arrow(c, 188 * mm, y - 13 * mm)
boxes(c, [
    ("PostgreSQL 16", "Alembic schema"),
], y, col_w=46 * mm, x0=202 * mm, size=12)
c.setFont("Helvetica", 12)
c.setFillColor(HexColor("#3f3f46"))
c.drawString(18 * mm, y - 46 * mm, "Prometheus scrapes /metrics via ServiceMonitor  ->  Grafana dashboards (rate, latency, errors)")
c.showPage(); P += 1

# ---- Slide 5: Product features ---------------------------------------------
header(c, "What Berth actually does", "Product walkthrough", P + 1)
bullets(c, [
    ("Projects  ", "group tasks; deleting a project with tasks is refused (409)."),
    ("Tasks  ", "status TODO -> IN_PROGRESS -> DONE, priorities, assignee, due dates, search, pagination."),
    ("Comments & activity  ", "persisted discussion per task; every action writes a real ActivityEvent."),
    ("Releases  ", "PLANNED -> READY -> DEPLOYING -> DEPLOYED / FAILED, illegal jumps rejected (409)."),
    ("Deployment history  ", "environment, commit SHA, outcome, timestamps, failure reason - failures are first-class."),
], size=14.5, gap=12 * mm)
c.showPage(); P += 1

# ---- Slide 6: CI/CD ----------------------------------------------------------
header(c, "CI/CD - one authoritative pipeline", "GitHub Actions", P + 1)
stages = [
    ("test", "pytest 53 tests + frontend build"),
    ("build-scan-push", "Trivy HIGH/CRIT gate -> GHCR SHA tags"),
    ("smoke-kind", "Helm on kind + curl health/ready"),
]
y = H - 70 * mm
x = 18 * mm
for name, sub in stages:
    c.setFillColor(CARD); c.setStrokeColor(FAINT)
    c.roundRect(x, y - 30 * mm, 112 * mm, 30 * mm, 3 * mm, stroke=1, fill=1)
    c.setFillColor(INK); c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 6 * mm, y - 11 * mm, name)
    c.setFont("Helvetica", 11); c.setFillColor(MUTED)
    c.drawString(x + 6 * mm, y - 20 * mm, sub)
    x += 116 * mm
    if name != "smoke-kind":
        arrow(c, x - 8 * mm, y - 15 * mm, 4 * mm)
bullets(c, [
    ("Security gate is real:  ", "exit-code 1 - findings fail the build before any push."),
    ("Both images scanned clean  ", "- 0 HIGH/CRITICAL on the published run."),
    ("Immutable traceability  ", "- ghcr.io/maverick-sst/berth/berth-{backend,frontend}:<commit-sha>."),
    ("No cloud credentials in CI  ", "- real deploys stay manual via the runbook."),
], y=H - 112 * mm, size=13.5, gap=11 * mm)
c.showPage(); P += 1

# ---- Slide 7: Infrastructure -------------------------------------------------
header(c, "Infrastructure as Code", "Terraform - AWS", P + 1)
y = H - 74 * mm
c.setFillColor(CARD); c.setStrokeColor(FAINT)
c.roundRect(18 * mm, y - 56 * mm, 60 * mm, 56 * mm, 3 * mm, stroke=1, fill=1)
c.setFillColor(INK); c.setFont("Helvetica-Bold", 13)
c.drawString(24 * mm, y - 12 * mm, "terraform/ provisions")
c.setFont("Helvetica", 11.5); c.setFillColor(HexColor("#3f3f46"))
for i, line in enumerate([
    "VPC 10.20.0.0/16",
    "2 public + 2 private subnets",
    "Single NAT gateway",
    "EKS 1.31, t3.medium 2-4 nodes",
]):
    c.drawString(26 * mm, y - 24 * mm - i * 8 * mm, "·  " + line)
c.setFillColor(CARD); c.setStrokeColor(FAINT)
c.roundRect(84 * mm, y - 56 * mm, 108 * mm, 56 * mm, 3 * mm, stroke=1, fill=1)
c.setFillColor(INK); c.setFont("Helvetica-Bold", 13)
c.drawString(90 * mm, y - 12 * mm, "Cost discipline")
c.setFont("Helvetica", 11.5); c.setFillColor(HexColor("#3f3f46"))
for i, line in enumerate([
    "Validated statically: fmt -check + validate pass",
    "tfvars.example only - no real values committed",
    "~$150-220/month while running - documented",
    "Runbook: plan -> apply (user-approved) -> destroy",
]):
    c.drawString(92 * mm, y - 24 * mm - i * 8 * mm, "·  " + line)
c.showPage(); P += 1

# ---- Slide 8: Kubernetes ------------------------------------------------------
header(c, "Kubernetes + Helm", "How Berth runs in a cluster", P + 1)
bullets(c, [
    ("Chart:  ", "helm/taskboard (chart name: berth) - validated with helm lint + helm template."),
    ("Probes  ", "readiness /ready (checks DB), liveness /health - cheap and meaningful."),
    ("Scaling  ", "HPA on CPU 60%, 2-6 replicas, resource requests set."),
    ("Hardening  ", "runAsNonRoot uid 10001/101, capabilities dropped, no privilege escalation."),
    ("Ingress  ", "/api -> backend :8000, / -> frontend :8080 (nginx class)."),
    ("Smoke-tested in CI  ", "- kind + Helm + real Postgres + curl health/ready/create."),
], size=14, gap=11 * mm)
c.showPage(); P += 1

# ---- Slide 9: Observability ----------------------------------------------------
header(c, "Observability", "Prometheus + Grafana", P + 1)
bullets(c, [
    ("Instrumentation  ", "prometheus-fastapi-instrumentator exposes /metrics on the backend."),
    ("Discovery  ", "ServiceMonitor finds the app in any namespace (kube-prometheus-stack values)."),
    ("Dashboard  ", "importable JSON - request rate, p95 latency, error rate, status-code breakdown."),
    ("Verified, not assumed  ", "- runbook steps to confirm the target is UP and panels are populated."),
    ("Load demo  ", "scripts/load-test.sh generates traffic so panels come alive on screen."),
], size=14, gap=12 * mm)
c.showPage(); P += 1

# ---- Slide 10: Quality gates ---------------------------------------------------
header(c, "Quality gates", "What keeps Berth honest", P + 1)
boxes(c, [
    ("53 pytest tests", "8+ endpoints, isolated in-memory DB"),
    ("Alembic authoritative", "4 migrations, no create_all in prod"),
    ("Non-root containers", "uid 10001 backend / 101 nginx"),
    ("State machines", "release transitions validated 409"),
], H - 70 * mm, size=12)
boxes(c, [
    ("409-protected deletes", "no orphaned or cascaded data"),
    ("Token-gated CI reports", "hmac.compare_digest bearer"),
    ("Real activity only", "no fabricated feed or metrics"),
    ("Zero secrets in git", "placeholders + runtime injection"),
], H - 70 * mm - 34 * mm, size=12)
c.showPage(); P += 1

# ---- Slide 11: Learnings --------------------------------------------------------
header(c, "Key learnings", "What building Berth taught me", P + 1)
bullets(c, [
    ("Migrations own the schema.  ", "create_all at startup hides drift; Alembic up/down/up on every change."),
    ("Security gates must fail builds.  ", "Trivy caught 3 HIGH starlette CVEs - fixed by upgrading, not ignoring."),
    ("Base images go stale.  ", "41 frontend CVEs traced to frozen packages - apk/apt upgrade at build time."),
    ("Fabricated data is a smell.  ", "if a dashboard can't be trusted, it isn't a dashboard."),
    ("Least privilege everywhere.  ", "no cloud creds in CI; GITHUB_TOKEN with packages:write is enough."),
], size=14.5, gap=12 * mm)
c.showPage(); P += 1

# ---- Slide 12: Wrap ------------------------------------------------------------
c.setFillColor(BG); c.rect(0, 0, W, H, stroke=0, fill=1)
c.setFillColor(INK); c.setFont("Helvetica-Bold", 54)
c.drawCentredString(W / 2, H * 0.58, "Thank you")
c.setFont("Helvetica", 16); c.setFillColor(MUTED)
c.drawCentredString(W / 2, H * 0.46, "Berth - engineering work, docked.")
c.drawCentredString(W / 2, H * 0.38, "github.com/Maverick-sst/Berth  ·  52 commits  ·  53 tests  ·  2 clean images on GHCR")
c.setFillColor(ACCENT)
c.rect(W / 2 - 14 * mm, H * 0.66, 28 * mm, 1.2 * mm, stroke=0, fill=1)
c.showPage(); P += 1

c.save()
print(f"OK: wrote {os.path.normpath(OUT)} ({P} slides)")
