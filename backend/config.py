# backend/config.py - Part 1 of 2
#!/usr/bin/env python3
"""
Central Application Configuration
Loads non-secret settings from app.config.json with environment variable overrides.
Sensitive credentials (GEMINI_API_KEY, JIRA_API_TOKEN, etc.) are injected natively 
using the official Google Cloud Secret Manager SDK client.
"""
import os
import json
import sys
from typing import Any, Dict, Optional
from google.cloud import secretmanager

# Optional dotenv loading fallback for local testing loops
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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
            print(f"[Config] Notice: could not read app.config.json: {e}", file=sys.stderr)

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
    return get_secret_ids().get(env_var)

_SECRET_CLIENT = None
_SECRET_CLIENT_ATTEMPTED = False
_SECRET_CLIENT_AVAILABLE = False

def get_secret_client() -> Optional[secretmanager.SecretManagerServiceClient]:
    global _SECRET_CLIENT, _SECRET_CLIENT_ATTEMPTED, _SECRET_CLIENT_AVAILABLE
    if _SECRET_CLIENT is not None:
        return _SECRET_CLIENT
    if _SECRET_CLIENT_ATTEMPTED and not _SECRET_CLIENT_AVAILABLE:
        return None

    _SECRET_CLIENT_ATTEMPTED = True
    try:
        import google.auth
        credentials, _ = google.auth.default()
        _SECRET_CLIENT = secretmanager.SecretManagerServiceClient(credentials=credentials)
        _SECRET_CLIENT_AVAILABLE = True
        return _SECRET_CLIENT
    except Exception as e:
        _SECRET_CLIENT_AVAILABLE = False
        print(f"[Config] Secret Manager credentials notice: {e}", file=sys.stderr)
        return None

def get_secret(env_var: str, default: Optional[str] = None) -> Optional[str]:
    """
    Retrieves secret value:
    1. First checks os.environ (mounted via Cloud Run --set-secrets or container environment).
    2. If not present, natively uses Secret Manager SDK Client to fetch payload.
    3. Returns default if not found.
    """
    val = os.environ.get(env_var)
    if val and val.strip():
        return val.strip()

    secret_id = get_secret_id(env_var)
    if not secret_id:
        return default

    client = get_secret_client()
    if not client:
        return default

    project_id = get_config_val("GCP_PROJECT_ID", "patchamomma-505416")
    try:
        name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"
        response = client.access_secret_version(request={"name": name})
        secret_val = response.payload.data.decode("utf-8")
        
        if secret_val:
            # Cache directly in environment to prevent redundant cross-network calls
            os.environ[env_var] = secret_val
            return secret_val
    except Exception as e:
        # Suppress exception for local testing loops without throwing process breaks
        print(f"[Config] Secret Manager SDK notice for '{secret_id}': {e}", file=sys.stderr)

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
        
        masked = "missing"
        if resolved_val:
            masked = (resolved_val[:4] + "..." + resolved_val[-4:]) if len(resolved_val) > 8 else "configured"
            
        status_report[env_var] = {
            "secret_id": secret_id,
            "is_set": bool(resolved_val),
            "source": "environment" if in_env else ("secret_manager" if resolved_val else "not_configured"),
            "masked_preview": masked
        }
    return status_report
