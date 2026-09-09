#!/usr/bin/env python3
"""
Company AI Assistant: Google Cloud Storage (GCS) Document Service
Direct integration with Google Cloud Storage for retrieving official enterprise runbooks,
markdown policies, blueprints, and architecture documents.
Supports Cloud Run IAM service account authentication via Instance Metadata Service.
"""

import os
import sys
import json
import urllib.request
import urllib.parse
import urllib.error
from typing import Dict, Any, Optional
from backend.config import get_config_val

class GCSService:
    """
    Manages document retrieval directly from Google Cloud Storage (gs://<bucket>/<object_path>).
    Authenticates using Google Cloud Run Application Default Credentials / Metadata server.
    """

    _cached_token: Optional[str] = None
    _token_expiry: float = 0.0

    @classmethod
    def get_configured_bucket(cls) -> str:
        return get_config_val("GCS_BUCKET", "patchamomma-505416-employee-ai-knowledge")

    @classmethod
    def get_gcp_access_token(cls) -> Optional[str]:
        """
        Retrieves GCP OAuth2 access token for Cloud Storage API calls.
        Precedence:
        1. Explicit environment variable GCP_ACCESS_TOKEN
        2. GCP Instance Metadata Server (Cloud Run / Compute Engine native)
        """
        if os.environ.get("GCP_ACCESS_TOKEN"):
            return os.environ.get("GCP_ACCESS_TOKEN")

        import time
        now = time.time()
        if cls._cached_token and now < cls._token_expiry:
            return cls._cached_token

        # Query metadata server in Cloud Run
        try:
            req = urllib.request.Request(
                "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
                headers={"Metadata-Flavor": "Google"}
            )
            with urllib.request.urlopen(req, timeout=2) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                token = data.get("access_token")
                expires_in = data.get("expires_in", 3600)
                cls._cached_token = token
                cls._token_expiry = now + expires_in - 60
                return token
        except Exception:
            return None

    @classmethod
    def parse_gcs_uri(cls, uri: str) -> tuple[str, str]:
        """
        Parses gs://bucket-name/path/to/object into (bucket, object_name).
        """
        if uri.startswith("gs://"):
            parts = uri[5:].split("/", 1)
            bucket = parts[0]
            obj = parts[1] if len(parts) > 1 else ""
            return bucket, obj
        return cls.get_configured_bucket(), uri.lstrip("/")

    @classmethod
    def read_document_from_gcs(cls, gcs_uri: str) -> Dict[str, Any]:
        """
        Fetches document content directly from Google Cloud Storage via REST API.
        Returns a dictionary containing content, size, and source metadata.
        """
        bucket, object_path = cls.parse_gcs_uri(gcs_uri)
        if not object_path:
            return {"error": "Invalid GCS URI: missing object path.", "content": ""}

        project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
        token = cls.get_gcp_access_token()
        encoded_object = urllib.parse.quote(object_path, safe="")

        # GCS Media Download endpoint
        url = f"https://storage.googleapis.com/storage/v1/b/{bucket}/o/{encoded_object}?alt=media"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if project_id:
            headers["x-goog-user-project"] = project_id

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=6) as resp:
                raw_bytes = resp.read()
                try:
                    content_text = raw_bytes.decode("utf-8")
                except UnicodeDecodeError:
                    content_text = raw_bytes.decode("latin-1", errors="replace")

                return {
                    "source": "GCS",
                    "bucket": bucket,
                    "object_path": object_path,
                    "gcs_uri": f"gs://{bucket}/{object_path}",
                    "content": content_text,
                    "bytes_length": len(raw_bytes),
                    "status": "LOADED_FROM_GCS",
                }
        except urllib.error.HTTPError as he:
            err_body = ""
            try:
                err_body = he.read().decode("utf-8")
            except Exception:
                pass
            print(f"[GCSService] HTTP {he.code} fetching gs://{bucket}/{object_path}: {he.reason} - {err_body[:100]}", file=sys.stderr)
            return {
                "source": "GCS",
                "bucket": bucket,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket}/{object_path}",
                "error": f"HTTP {he.code}: {he.reason}",
                "status": "GCS_ACCESS_DENIED" if he.code == 403 else "GCS_OBJECT_NOT_FOUND" if he.code == 404 else "GCS_ERROR",
                "content": "",
            }
        except Exception as e:
            print(f"[GCSService] Error fetching gs://{bucket}/{object_path}: {e}", file=sys.stderr)
            return {
                "source": "GCS",
                "bucket": bucket,
                "object_path": object_path,
                "gcs_uri": f"gs://{bucket}/{object_path}",
                "error": str(e),
                "status": "GCS_CONNECTION_FAILED",
                "content": "",
            }

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """
        Tests connection to Google Cloud Storage and checks configured bucket status.
        """
        bucket = cls.get_configured_bucket()
        project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
        token = cls.get_gcp_access_token()

        result = {
            "bucket": bucket,
            "project_id": project_id,
            "connected": False,
            "authenticated": token is not None,
            "status": "Checking...",
            "iam_role_required": "roles/storage.objectViewer (or roles/storage.admin)",
            "details": {}
        }

        url = f"https://storage.googleapis.com/storage/v1/b/{bucket}"
        headers = {}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        if project_id:
            headers["x-goog-user-project"] = project_id

        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                result["connected"] = True
                result["status"] = f"Connected successfully to GCS bucket: {bucket}"
                result["details"] = {
                    "location": data.get("location"),
                    "storageClass": data.get("storageClass"),
                    "timeCreated": data.get("timeCreated")
                }
        except urllib.error.HTTPError as he:
            body = ""
            try:
                body = he.read().decode("utf-8")
            except Exception:
                pass

            if he.code == 403:
                result["status"] = "GCS API reachable; IAM permission 'storage.buckets.get' or 'roles/storage.objectViewer' required."
                result["error_code"] = 403
            elif he.code == 404:
                result["status"] = f"GCS API reachable; bucket '{bucket}' does not exist or requires creation."
                result["error_code"] = 404
            else:
                result["status"] = f"GCS HTTP {he.code}: {he.reason}"
        except Exception as e:
            result["status"] = f"Connection failed: {str(e)}"

        return result
