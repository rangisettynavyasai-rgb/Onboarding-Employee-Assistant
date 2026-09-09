# Payments Architecture Blueprint: Event Ledger & Idempotency

## Overview
The Payments Core service handles credit, debit, and settlement transactions across global payment gateways. All accounting operations follow an immutable double-entry bookkeeping model.

## 1. Idempotency Key Specification
- Every mutative endpoint (`POST /v1/charges`, `POST /v1/transfers`) requires an `Idempotency-Key: <UUID-v4>` header.
- Redis KV cluster caches request payloads and status codes for a **24-hour TTL** window.
- In the event of network retries, duplicate requests return the cached response without re-executing funds movement.

## 2. Cloud SQL Persistence & BigQuery Streaming
- Primary datastore: Cloud SQL PostgreSQL instance running with automated failover.
- Change Data Capture (CDC): Events are streamed in real time to BigQuery `payments_events_ledger` table for audit reconciliation.