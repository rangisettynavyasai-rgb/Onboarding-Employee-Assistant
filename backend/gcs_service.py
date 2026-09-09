#!/usr/bin/env python3
"""
Company AI Assistant: Google Cloud Storage (GCS) Document Service
Direct integration with Google Cloud Storage for retrieving official enterprise runbooks,
markdown policies, blueprints, and architecture documents.
Supports Cloud Run IAM service account authentication and local application default credentials.
"""

import os
import sys
from typing import Dict, Any, Optional
from backend.config import get_config_val
from google.cloud import storage
from google.cloud.exceptions import NotFound, Forbidden

class GCSService:
    """
    Manages document retrieval directly from Google Cloud Storage (gs://<bucket>/<object_path>).
    Authenticates natively using the Google Cloud Storage SDK client.
    """

    OBJECT_ALIASES = {
        "runbooks/dev_environment_setup.md": "runbooks/kubernetes_cluster_triage.md",
        "platform/kubernetes_cluster_triage.md": "runbooks/kubernetes_cluster_triage.md",
        "platform/k8s_triage_guide.md": "runbooks/kubernetes_cluster_triage.md",
        "payments/architecture_overview_2026.md": "engineering/payments/architecture_blueprint.pdf",
        "hr/compensation_guidelines_2026.pdf": "hr/compensation_bands_2026.pdf",
    }

    @classmethod
    def get_configured_bucket(cls) -> str:
        # Check environment variable first, stripping out container injection quotes
        bucket_env = os.environ.get("GCS_BUCKET")
        if bucket_env and bucket_env.strip():
            clean_bucket = bucket_env.strip().replace('"', '').replace("'", "")
            if clean_bucket not in ("company-knowledge-mesh", "company-internal-knowledge", ""):
                return clean_bucket

        config_val = get_config_val("GCS_BUCKET")
        if config_val and "company-" not in str(config_val):
            return str(config_val).strip()

        return "patchamomma-505416-employee-ai-knowledge"

    @classmethod
    def parse_gcs_uri(cls, uri: str) -> tuple[str, str]:
        """
        Parses gs://bucket-name/path/to/object into (bucket, object_name).
        Maps generic or placeholder bucket names to configured GCS bucket.
        """
        configured_bucket = cls.get_configured_bucket()
        if uri.startswith("gs://"):
            parts = uri[5:].split("/", 1)
            bucket = parts[0]
            obj = parts[1] if len(parts) > 1 else ""
            if bucket in ("company-knowledge-mesh", "company-internal-knowledge", ""):
                bucket = configured_bucket
            # Apply object path aliasing if needed
            resolved_obj = cls.OBJECT_ALIASES.get(obj, obj)
            return bucket, resolved_obj
        clean_path = uri.lstrip("/")
        return configured_bucket, cls.OBJECT_ALIASES.get(clean_path, clean_path)

    @classmethod
    def read_document_from_gcs(cls, gcs_uri: str) -> Dict[str, Any]:
        """
        Fetches document content directly from Google Cloud Storage via the Native SDK client.
        Returns a dictionary containing content, size, and source metadata.
        """
        bucket_name, object_path = cls.parse_gcs_uri(gcs_uri)
        if not object_path:
            return {"error": "Invalid GCS URI: missing object path.", "content": ""}

        project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")

        try:
            # Initialize native client using ambient project and container credentials
            client = storage.Client(project=project_id)
            bucket = client.bucket(bucket_name)
            blob = bucket.blob(object_path)

            # Download content directly as bytes stream
            raw_bytes = blob.download_as_bytes()
            
            try:
                content_text = raw_bytes.decode("utf-8")
            except UnicodeDecodeError:
                content_text = raw_bytes.decode("latin-1", errors="replace")

            return {
                "source": "Google Cloud Storage (GCS Client)",
                "bucket": bucket_name,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket_name}/{object_path}",
                "content": content_text,
                "bytes_length": len(raw_bytes),
                "status": "LOADED_FROM_GCS",
            }

        except NotFound:
            print(f"[GCSService] 404 Object/Bucket Not Found: gs://{bucket_name}/{object_path}", file=sys.stderr)
            return {
                "source": "GCS",
                "bucket": bucket_name,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket_name}/{object_path}",
                "error": "The specified bucket or knowledge artifact was not found.",
                "status": "GCS_OBJECT_NOT_FOUND",
                "content": "",
            }
        except Forbidden as fe:
            print(f"[GCSService] 403 Access Denied fetching gs://{bucket_name}/{object_path}: {str(fe)}", file=sys.stderr)
            return {
                "source": "GCS",
                "bucket": bucket_name,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket_name}/{object_path}",
                "error": "Access Denied: Enforced service account IAM policies blocked read operations.",
                "status": "GCS_ACCESS_DENIED",
                "content": "",
            }
        except Exception as e:
            print(f"[GCSService] Client Error fetching gs://{bucket_name}/{object_path}: {str(e)}", file=sys.stderr)
            return {
                "source": "GCS",
                "bucket": bucket_name,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket_name}/{object_path}",
                "error": str(e),
                "status": "GCS_CONNECTION_FAILED",
                "content": "",
            }

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """
        Tests connection to Google Cloud Storage using the native storage client SDK.
        """
        bucket_name = cls.get_configured_bucket()
        project_id = os.environ.get("GCP_PROJECT_ID", get_config_val("GCP_PROJECT_ID", "patchamomma-505416"))

        result = {
            "bucket": bucket_name,
            "project_id": project_id,
            "connected": False,
            "status": "Checking...",
            "details": {}
        }

        try:
            # Native SDK automatically inherits system identity environment fields
            client = storage.Client(project=project_id)
            bucket = client.get_bucket(bucket_name)
            
            result["connected"] = True
            result["status"] = f"Connected successfully to GCS bucket: {bucket_name}"
            result["details"] = {
                "location": bucket.location,
                "storage_class": bucket.storage_class,
                "exists": True
            }
        except Exception as e:
            result["connected"] = False
            result["status"] = f"GCS SDK Resolution Failure: {str(e)}"

        return result
