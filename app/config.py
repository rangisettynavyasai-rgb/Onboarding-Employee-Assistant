"""
Configuration and Environment Management Module
Handles Google Secret Manager resolution and application configuration.
"""

import os
import logging
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("patchamomma.config")


class Settings:
    """Application configuration and GCP parameters."""

    ENVIRONMENT: str = os.getenv("ENVIRONMENT", "development")
    GCP_PROJECT_ID: str = os.getenv("GCP_PROJECT_ID", "patchamomma-505416")
    GCS_KNOWLEDGE_BUCKET: str = os.getenv("GCS_KNOWLEDGE_BUCKET", "patchamomma-505416-employee-ai-knowledge")
    BIGQUERY_DATASET: str = os.getenv("BIGQUERY_DATASET", "employee_ai")

    # Perimeter Security & Identity configuration
    ALLOWED_CORPORATE_DOMAIN: str = os.getenv("ALLOWED_CORPORATE_DOMAIN", "company.com")
    AUTH_PROVIDER: str = os.getenv("AUTH_PROVIDER", "mock_google")  # 'mock_google' | 'google_oauth' | 'iap'
    GOOGLE_OAUTH_CLIENT_ID: Optional[str] = os.getenv("GOOGLE_OAUTH_CLIENT_ID", "patchamomma-client-id.apps.googleusercontent.com")
    IAP_AUDIENCE: Optional[str] = os.getenv("IAP_AUDIENCE", None)

    # AI Model & Pay-Per-Token Invocation
    GEMINI_MODEL: str = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    USE_VERTEX_AI: bool = os.getenv("USE_VERTEX_AI", "false").lower() in ("true", "1")
    TEMPERATURE: float = float(os.getenv("TEMPERATURE", "0.2"))
    MAX_OUTPUT_TOKENS: int = int(os.getenv("MAX_OUTPUT_TOKENS", "2048"))

    # Storage & Persistence Backends
    REPOSITORY_BACKEND: str = os.getenv("REPOSITORY_BACKEND", "memory")  # 'memory' | 'bigquery'
    SESSION_STORE_BACKEND: str = os.getenv("SESSION_STORE_BACKEND", "memory")  # 'memory' | 'firestore'
    FIRESTORE_COLLECTION_SESSIONS: str = os.getenv("FIRESTORE_COLLECTION_SESSIONS", "employee_sessions")
    FIRESTORE_DATABASE: str = os.getenv("FIRESTORE_DATABASE", "(default)")

    @classmethod
    def get_secret(cls, secret_id: str, default: Optional[str] = None) -> Optional[str]:
        """
        Securely retrieves a secret from Google Secret Manager with local env fallback.
        """
        env_var_name = secret_id.upper().replace("-", "_")
        env_val = os.getenv(env_var_name)
        if env_val:
            return env_val

        # Attempt Google Secret Manager resolution if running on GCP
        if cls.ENVIRONMENT in ("staging", "production"):
            try:
                from google.cloud import secretmanager
                client = secretmanager.SecretManagerServiceClient()
                secret_name = f"projects/{cls.GCP_PROJECT_ID}/secrets/{secret_id}/versions/latest"
                response = client.access_secret_version(request={"name": secret_name})
                return response.payload.data.decode("UTF-8").strip()
            except Exception as e:
                logger.warning(f"Secret Manager resolution for '{secret_id}' failed: {e}")

        return default


settings = Settings()
