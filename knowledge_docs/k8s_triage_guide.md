# Platform Runbook: Kubernetes Staging Cluster Triage

## Common Alert: 5xx Spike on Ingress
1. **Check Gateway Logs**:
   `kubectl logs -l app=payment-gateway -c istio-proxy -n staging --tail=100`
2. **Verify Cloud SQL Proxy Sidecar**:
   Check pod sidecar status: `kubectl get pods -n staging -o wide`
   Inspect proxy logs: `kubectl logs <pod-name> -c cloud-sql-proxy -n staging`
3. **Restarting Unhealthy Pods**:
   `kubectl rollout restart deployment/payment-gateway -n staging`
4. **Escalation**:
   If latency exceeds 500ms or error rate > 1%, page the on-call engineer via `#platform-incidents`.