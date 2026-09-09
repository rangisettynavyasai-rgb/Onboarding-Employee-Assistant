### Cloud SQL Auth Proxy Sidecar Configuration & Triage

**Scope**: All GKE workloads connecting to Cloud SQL PostgreSQL.

**Guidelines**:
1. **Local Address**: Pods must route database queries to `127.0.0.1:5432`.
2. **Workload Identity**: Authenticates pod service account with Google Cloud IAM without hardcoded passwords.
3. **Triage Command**:
   `kubectl logs <pod-name> -c cloud-sql-proxy -n staging`
4. **Emergency Escalation**: Page on-call infrastructure engineers on `#help-infrastructure`.