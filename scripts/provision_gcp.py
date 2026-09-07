"""
GCP BigQuery & Cloud Storage Provisioning and Seed Script.
Connects to project patchamomma-505416 and initializes BigQuery schemas, seed data, and GCS assets.
"""

import os
import sys
import logging
from google.cloud import bigquery, storage

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from app.config import settings

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("patchamomma.provision")

PROJECT_ID = settings.GCP_PROJECT_ID
DATASET_ID = settings.BIGQUERY_DATASET
BUCKET_NAME = settings.GCS_KNOWLEDGE_BUCKET


def provision_bigquery_tables(bq_client: bigquery.Client):
    """Executes DDL statements to create all required tables in employee_ai."""
    logger.info(f"Provisioning BigQuery dataset '{PROJECT_ID}.{DATASET_ID}' tables...")

    # Ensure dataset exists
    dataset_ref = bigquery.DatasetReference(PROJECT_ID, DATASET_ID)
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = "us-central1"
    dataset = bq_client.create_dataset(dataset, exists_ok=True)
    logger.info(f"Dataset '{DATASET_ID}' verified.")

    # Read and execute tables.sql
    with open("bigquery/tables.sql", "r", encoding="utf-8") as f:
        ddl_sql = f.read()

    # Split on CREATE OR REPLACE TABLE / CREATE SCHEMA statements
    job = bq_client.query(ddl_sql)
    job.result()
    logger.info("Successfully created all BigQuery tables.")


def seed_bigquery_data(bq_client: bigquery.Client):
    """Populates BigQuery tables with synthetic seed datasets."""
    logger.info(f"Seeding synthetic data into BigQuery '{DATASET_ID}'...")
    with open("bigquery/seed_data.sql", "r", encoding="utf-8") as f:
        seed_sql = f.read()

    job = bq_client.query(seed_sql)
    job.result()
    logger.info("Successfully seeded BigQuery tables.")


def upload_gcs_knowledge_docs(gcs_client: storage.Client):
    """Generates and uploads structured knowledge mesh documents to GCS bucket."""
    logger.info(f"Uploading Knowledge Mesh documents to 'gs://{BUCKET_NAME}'...")

    try:
        bucket = gcs_client.get_bucket(BUCKET_NAME)
    except Exception:
        logger.info(f"Creating bucket '{BUCKET_NAME}' in us-central1...")
        bucket = gcs_client.create_bucket(BUCKET_NAME, location="us-central1")

    docs = {
        "company/code_of_conduct_2026.md": (
            "# Patchamomma 2026 Code of Conduct & Values\n\n"
            "We prioritize psychological safety, radical candor with empathy, and customer obsession.\n"
            "Working hours are core-flexible (10am - 4pm local). Timesheets must be finalized by Friday 5pm.\n"
        ),
        "engineering/logging_standards_2026.md": (
            "# Corporate Coding Standards 2026\n\n"
            "1. Never use raw print(...) statements in production services. Always use logger.info(json.dumps(...)).\n"
            "2. All microservices communicate via Cloud Pub/Sub and Cloud SQL Postgres proxy with IAM auth.\n"
            "3. Functions must be fully type-hinted and pass ruff/mypy checks.\n"
        ),
        "engineering/payments/architecture_blueprint.pdf": (
            "# Payments Architecture Blueprint\n\n"
            "The Payments Gateway utilizes an event-sourced ledger on Cloud SQL PostgreSQL with read-replicas.\n"
            "Transactions require an Idempotency-Key header. Staging database URL is managed via Cloud SQL Proxy at 127.0.0.1:5432.\n"
            "Video walkthrough: `gs://patchamomma-505416-employee-ai-knowledge/videos/onboarding/payments_deepdive.mp4` (Key timestamp: 18:45 for Cloud SQL Proxy setup).\n"
        ),
        "runbooks/kubernetes_cluster_triage.md": (
            "# GKE Cluster Triage Runbook\n\n"
            "For Pod CrashLoopBackOff events, execute `kubectl logs --tail=100 -n production`.\n"
            "If nodes are non-responsive, verify Cloud NAT and VPC firewall rules before restarting node pools.\n"
        ),
        "management/manager_playbook_2026.md": (
            "# Engineering Manager Playbook (Manager Eyes Only)\n\n"
            "Hold weekly 30-minute 1:1s with all new joiners throughout their first 90 days.\n"
            "Review timesheet submissions every Friday afternoon in the Manager Portal.\n"
        ),
        "hr/compensation_bands_2026.pdf": (
            "# HR Restricted Salary & Equity Matrix\n\n"
            "Level L3 (SWE I): Base range $130,000 - $160,000.\n"
            "Level L4 (SWE II): Base range $160,000 - $195,000.\n"
            "Level L6 (Staff): Base range $230,000 - $280,000.\n"
        ),
        "it/iam_firewall_admin.md": (
            "# IT Master Administration & KMS Key Vault\n\n"
            "VPN certificates must be issued using Cloud KMS HSM keys.\n"
            "Revoke compromised service account keys immediately via `gcloud iam service-accounts keys delete`.\n"
        ),
    }

    for path, content in docs.items():
        blob = bucket.blob(path)
        blob.upload_from_string(content, content_type="text/markdown" if path.endswith(".md") else "application/pdf")
        logger.info(f"Uploaded gs://{BUCKET_NAME}/{path}")

    logger.info("Knowledge Mesh document upload completed.")


def main():
    logger.info(f"Starting GCP Provisioning for project '{PROJECT_ID}'...")
    bq_client = bigquery.Client(project=PROJECT_ID)
    gcs_client = storage.Client(project=PROJECT_ID)

    provision_bigquery_tables(bq_client)
    seed_bigquery_data(bq_client)
    upload_gcs_knowledge_docs(gcs_client)
    logger.info("🎉 All GCP BigQuery tables, seed records, and GCS assets provisioned successfully!")


if __name__ == "__main__":
    main()
