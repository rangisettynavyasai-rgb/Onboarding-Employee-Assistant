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
        "FIREBASE_PROJECT_ID": cfg.get("gcpProjectId"),
        "FIRESTORE_DATABASE_ID": cfg.get("firestoreDatabaseId"),
        "GOOGLE_OAUTH_CLIENT_ID": cfg.get("googleOAuthClientId"),
        "JIRA_HOST": jira.get("host"),
        "JIRA_PROJECT_KEY": jira.get("projectKey"),
        "SALESFORCE_INSTANCE_URL": sf.get("instanceUrl"),
    }

    val = key_map.get(key)
    if val is not None and val != "":
        return val

    return default
