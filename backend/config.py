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
