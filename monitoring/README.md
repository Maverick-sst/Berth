# Berth monitoring

## What exists

- `prometheus-values.yaml` - kube-prometheus-stack values. Prometheus is
  configured to discover ServiceMonitors in any namespace
  (`serviceMonitorSelectorNilUsesHelmValues: false`).
- The backend chart ships a `ServiceMonitor` (release label
  `kube-prometheus-stack`) scraping the backend service on `/metrics`
  every 15s. The backend exposes request rate/latency metrics via
  prometheus-fastapi-instrumentator.
- `grafana-dashboard.json` - importable Grafana dashboard with four
  panels: request rate, p95 latency, error rate, and requests by
  status code.

## Verify (on a cluster with kube-prometheus-stack installed)

```bash
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace -f monitoring/prometheus-values.yaml

# deploy the app first (see cloud runbook), then check targets:
kubectl port-forward -n monitoring svc/monitoring-kube-prometheus-prometheus 9090:9090
# open http://localhost:9090/targets - the berth backend target should be UP

# Grafana:
kubectl port-forward -n monitoring svc/monitoring-grafana 3001:80
# import monitoring/grafana-dashboard.json, panels should populate
# after you generate some API traffic
```

## Dashboard note

The dashboard queries no longer filter on a per-app label — the default
metrics from `prometheus-fastapi-instrumentator` only carry
`handler`/`status`/`method` labels, so filtering on a label like
`app="berth-backend"` would leave every panel empty. If you add custom
labels to the instrumentator later, you can re-introduce selectors; if
panels are still empty, check the actual metric labels in Prometheus
(`up`, `http_requests_total`) and adjust the queries in
`grafana-dashboard.json` accordingly. Do not trust a green dashboard
without confirming the Prometheus target is UP.
