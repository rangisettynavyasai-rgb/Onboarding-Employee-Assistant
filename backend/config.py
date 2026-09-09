#!/usr/bin/env python3
"""
Central Application Configuration
Loads non-secret settings from app.config.json with environment variable overrides.
Sensitive credentials (GEMINI_API_KEY, JIRA_API_TOKEN, etc.) are injected via Secret Manager into os.environ.
"""
import os
import json
from typing import Any, Dict, Optional

_CONFIG_CACHE: Optional[Dict[str, Any]] = None

def load_app_config() -> Dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE

    cfg_path = os.path.join(os.getcwd(), "app.config.json")
    config: Dict[str, Any] = {}
    if os.path.exists(cfg_path):
        try:
            with open(cfg_path, "r", encoding="utf-8") as f:
                config = json.load(f)
        except Exception as e:
            print(f"[Config] Notice: could not read app.config.json: {e}")

    _CONFIG_CACHE = config
    return config

def get_config_val(key: str, default: Any = None) -> Any:
    """
    Resolves configuration value following precedence:
    1. Environment Variable (Cloud Run / Secret Manager / .env)
    2. app.config.json (safe for Git)
    3. Default value
    """
    env_val = os.environ.get(key)
    if env_val is not None and env_val.strip() != "":
        return env_val.strip()

    cfg = load_app_config()
    jira = cfg.get("jira", {})
    sf = cfg.get("salesforce", {})

    key_map = {
        "ENVIRONMENT": cfg.get("environment"),
        "ALLOWED_CORPORATE_DOMAIN": cfg.get("allowedCorporateDomain"),
        "GCP_PROJECT_ID": cfg.get("gcpProjectId"),
        "GCP_REGION": cfg.get("gcpRegion", "us-central1"),
        "FIREBASE_PROJECT_ID": cfg.get("firebaseProjectId") or cfg.get("gcpProjectId"),
        "FIRESTORE_DATABASE_ID": cfg.get("firestoreDatabaseId"),
        "BIGQUERY_DATASET": cfg.get("bigqueryDataset", "employee_ai"),
        "GCS_BUCKET": cfg.get("gcsBucket", "patchamomma-505416-employee-ai-knowledge"),
        "GOOGLE_OAUTH_CLIENT_ID": cfg.get("googleOAuthClientId"),
        "JIRA_HOST": jira.get("host"),
        "JIRA_PROJECT_KEY": jira.get("projectKey"),
        "JIRA_EMAIL": jira.get("email"),
        "SALESFORCE_INSTANCE_URL": sf.get("instanceUrl"),
    }

    val = key_map.get(key)
    if val is not None and val != "":
        return val

    return default

def get_secret_ids() -> Dict[str, str]:
    """
    Returns the mapping of Environment Variable names to Google Cloud Secret Manager Secret IDs.
    """
    cfg = load_app_config()
    secret_ids = cfg.get("secretIds", {})
    if not secret_ids and "secrets" in cfg:
        secret_ids = {
            item["envVar"]: item["secretId"]
            for item in cfg["secrets"].values()
            if isinstance(item, dict) and "envVar" in item and "secretId" in item
        }
    return secret_ids

def get_secret_id(env_var: str) -> Optional[str]:
    """
    Returns the Secret Manager secret ID for a given environment variable name.
    """
    return get_secret_ids().get(env_var)

def get_secret(env_var: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieves secret value:
    1. First checks os.environ (mounted via Cloud Run --set-secrets or container environment).
    2. If not present and GCP credentials exist, attempts to fetch from Secret Manager.
    3. Returns default if not found.
    """
    val = os.environ.get(env_var)
    if val and val.strip():
        return val.strip()

    secret_id = get_secret_id(env_var)
    if not secret_id:
        return default

    project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
    try:
        import urllib.request
        import base64
        # Attempt to get access token from GCP metadata server
        meta_req = urllib.request.Request(
            "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token",
            headers={"Metadata-Flavor": "Google"}
        )
        token = None
        with urllib.request.urlopen(meta_req, timeout=2) as resp:
            token = json.loads(resp.read().decode())["access_token"]

        if token:
            url = f"https://secretmanager.googleapis.com/v1/projects/{project_id}/secrets/{secret_id}/versions/latest:access"
            sec_req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
            with urllib.request.urlopen(sec_req, timeout=3) as resp:
                data = json.loads(resp.read().decode())
                payload_b64 = data.get("payload", {}).get("data", "")
                if payload_b64:
                    secret_val = base64.b64decode(payload_b64).decode("utf-8")
                    os.environ[env_var] = secret_val  # cache in environment
                    return secret_val
    except Exception:
        pass

    return default

def check_secrets_status() -> Dict[str, Any]:
    """
    Validates the status of all secrets declared in app.config.json.
    """
    secret_map = get_secret_ids()
    status_report = {}
    for env_var, secret_id in secret_map.items():
        in_env = bool(os.environ.get(env_var))
        resolved_val = get_secret(env_var)
        status_report[env_var] = {
            "secret_id": secret_id,
            "is_set": bool(resolved_val),
            "source": "environment" if in_env else ("secret_manager" if resolved_val else "not_configured"),
            "masked_preview": (resolved_val[:4] + "..." + resolved_val[-4:]) if resolved_val and len(resolved_val) > 8 else ("configured" if resolved_val else "missing")
        }
    return status_report
