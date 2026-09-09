# Engineering Coding & Structured Logging Standards

## 1. Zero Raw Print Policy
Never commit raw `print(...)` in Python or `console.log(...)` in TypeScript to production microservices. Unstructured log lines break downstream ingestion into Google Cloud Logging and BigQuery telemetry pipelines.

## 2. Standard Structured JSON Logging Format (RFC-5424)
All application logs must be serialized as JSON objects with the following schema:
```python
import logging, json
logger = logging.getLogger('payments-service')
logger.info(json.dumps({
    'event': 'PAYMENT_TRANSACTION_INITIATED',
    'trace_id': trace_id,
    'user_id': user_id,
    'amount_cents': 2500,
    'status': 'SUCCESS'
}))
```

## 3. Database Security & Credentials
- **No hardcoded credentials**: Never store database passwords or service account keys in repositories.
- **Cloud SQL Auth Proxy**: Connect to Cloud SQL via `127.0.0.1:5432` using IAM database authentication and Google Cloud Secret Manager.

## 4. Git & Code Review Rules
- Conventional Commits required: `feat(scope): message`, `fix(scope): message`.
- Every PR requires at least 1 peer approval and passing automated CI checks.