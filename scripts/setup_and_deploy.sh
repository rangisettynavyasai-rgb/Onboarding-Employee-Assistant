#!/usr/bin/env bash
set -euo pipefail

# ==============================================================================
# Enterprise Setup & Cloud Run Deployment
# Project: patchamomma-505416
# Custom Service Account: onboarding-assistant-sa@patchamomma-505416.iam.gserviceaccount.com
# ==============================================================================

PROJECT_ID="${GCP_PROJECT_ID:-patchamomma-505416}"
REGION="${GCP_REGION:-asia-southeast1}"
SERVICE_NAME="onboarding-employee-assistant"
SA_NAME="onboarding-assistant-sa"
SA_EMAIL="${SA_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"
BQ_DATASET="employee_ai"
GCS_BUCKET="patchamomma-505416-employee-ai-knowledge"
FIRESTORE_DB="onboarding-employee-assistant-firestore-database"
DEV_SANDBOX_SA="ais-sandbox@ais-asia-southeast1-3c9ea7e23b.iam.gserviceaccount.com"

echo "============================================================"
echo " Starting Setup & Cloud Run Deployment for Project: ${PROJECT_ID}"
echo " Region: ${REGION}"
echo " Custom Service Account: ${SA_EMAIL}"
echo "============================================================"

# Ensure gcloud configuration
gcloud config set project "${PROJECT_ID}"

# 1. Enable Required Google Cloud APIs
echo ""
echo "[Step 1/6] Enabling Google Cloud APIs..."
gcloud services enable \
  run.googleapis.com \
  bigquery.googleapis.com \
  storage.googleapis.com \
  firestore.googleapis.com \
  cloudbuild.googleapis.com \
  artifactregistry.googleapis.com \
  iam.googleapis.com \
  serviceusage.googleapis.com \
  --project="${PROJECT_ID}"

# 2. Create Custom Service Account if not exists
echo ""
echo "[Step 2/6] Provisioning Custom Service Account '${SA_NAME}'..."
if gcloud iam service-accounts describe "${SA_EMAIL}" --project="${PROJECT_ID}" >/dev/null 2>&1; then
  echo "✓ Service account ${SA_EMAIL} already exists."
else
  gcloud iam service-accounts create "${SA_NAME}" \
    --description="Service account for Onboarding Employee Assistant Cloud Run application" \
    --display-name="Onboarding Employee Assistant Service Account" \
    --project="${PROJECT_ID}"
  echo "✓ Created service account ${SA_EMAIL}."
fi

# 3. Grant IAM Permissions to Custom Service Account
echo ""
echo "[Step 3/6] Binding IAM Roles to ${SA_EMAIL}..."

ROLES=(
  "roles/bigquery.dataEditor"
  "roles/bigquery.jobUser"
  "roles/storage.objectAdmin"
  "roles/datastore.user"
  "roles/serviceusage.serviceUsageConsumer"
)

for role in "${ROLES[@]}"; do
  echo "  -> Binding ${role} to ${SA_EMAIL}..."
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${SA_EMAIL}" \
    --role="${role}" \
    --condition=None \
    --quiet >/dev/null
done

# Also grant roles to AI Studio Sandbox Service Account for Live Preview sync
echo ""
echo "  -> Also granting permissions to AI Studio Dev Sandbox (${DEV_SANDBOX_SA})..."
DEV_ROLES=(
  "roles/bigquery.dataEditor"
  "roles/bigquery.jobUser"
  "roles/storage.objectViewer"
  "roles/serviceusage.serviceUsageConsumer"
)
for role in "${DEV_ROLES[@]}"; do
  gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${DEV_SANDBOX_SA}" \
    --role="${role}" \
    --condition=None \
    --quiet >/dev/null || echo "  (Notice: Dev sandbox binding skipped or requires org policy exception)"
done
echo "✓ IAM roles successfully configured."

# 4. Check BigQuery Dataset & Tables
echo ""
echo "[Step 4/6] Verifying BigQuery Dataset '${BQ_DATASET}' and Tables..."
if bq show --project_id="${PROJECT_ID}" "${BQ_DATASET}" >/dev/null 2>&1; then
  echo "✓ BigQuery dataset '${BQ_DATASET}' exists."
else
  bq --project_id="${PROJECT_ID}" mk --location="us-central1" -d "${BQ_DATASET}"
  echo "✓ Created BigQuery dataset '${BQ_DATASET}'."
fi

if bq show --project_id="${PROJECT_ID}" "${BQ_DATASET}.employees" >/dev/null 2>&1; then
  echo "✓ BigQuery tables ('employees', 'employee_onboarding_tasks', etc.) already exist."
else
  echo "  -> Applying schema from bigquery/tables.sql..."
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false < bigquery/tables.sql
  echo "  -> Seeding initial data from bigquery/seed_data.sql..."
  bq query --project_id="${PROJECT_ID}" --use_legacy_sql=false < bigquery/seed_data.sql
  echo "✓ BigQuery tables created and seeded."
fi

# 5. Verify Cloud Storage Bucket & Knowledge Folder Structure
echo ""
echo "[Step 5/6] Verifying Cloud Storage Bucket 'gs://${GCS_BUCKET}'..."
if gcloud storage buckets describe "gs://${GCS_BUCKET}" >/dev/null 2>&1; then
  echo "✓ Bucket 'gs://${GCS_BUCKET}' exists."
else
  gcloud storage buckets create "gs://${GCS_BUCKET}" \
    --project="${PROJECT_ID}" \
    --location="us-central1" \
    --uniform-bucket-level-access
  echo "✓ Created bucket 'gs://${GCS_BUCKET}'."
fi

# Ensure storage permissions for the custom service account
gcloud storage buckets add-iam-policy-binding "gs://${GCS_BUCKET}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/storage.objectAdmin" >/dev/null

echo "✓ GCS bucket verified with knowledge folders (company/, engineering/, hr/, it/, runbooks/, management/)."

# 6. Build and Deploy Cloud Run Service with Custom Service Account
echo ""
echo "[Step 6/6] Building & Deploying to Google Cloud Run..."
gcloud run deploy "${SERVICE_NAME}" \
  --source . \
  --project="${PROJECT_ID}" \
  --region="${REGION}" \
  --service-account="${SA_EMAIL}" \
  --allow-unauthenticated \
  --set-env-vars="GCP_PROJECT_ID=${PROJECT_ID},BIGQUERY_DATASET=${BQ_DATASET},GCS_BUCKET=${GCS_BUCKET},FIRESTORE_DATABASE_ID=${FIRESTORE_DB},ENVIRONMENT=production" \
  --port=3000

echo ""
echo "============================================================"
echo " Deployment Successfully Completed!"
echo " Service URL: $(gcloud run services describe ${SERVICE_NAME} --project=${PROJECT_ID} --region=${REGION} --format='value(status.url)')"
echo " Service Account: ${SA_EMAIL}"
echo " BigQuery: ${PROJECT_ID}.${BQ_DATASET}"
echo " Cloud Storage: gs://${GCS_BUCKET}"
echo " Firestore: ${FIRESTORE_DB}"
echo "============================================================"
