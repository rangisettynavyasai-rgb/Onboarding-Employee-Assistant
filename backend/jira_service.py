# backend/jira_service.py
"""
Company AI Assistant: Jira Cloud Production Integration

Handles Jira Cloud connectivity and incident creation.

Configuration:
- JIRA_HOST          -> backend.config.get_config_val()
- JIRA_PROJECT_KEY  -> backend.config.get_config_val()
- JIRA_EMAIL        -> backend.config.get_config_val()
- JIRA_API_TOKEN    -> backend.config.get_secret()

The calling service does NOT need to provide Jira connection
configuration. It only provides incident/business data.
"""

import base64
import json
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional

from backend.config import get_config_val, get_secret


class JiraService:

    @classmethod
    def _get_host(cls) -> str:
        return str(
            get_config_val("JIRA_HOST", "")
        ).strip().rstrip("/")

    @classmethod
    def _get_project_key(cls) -> str:
        return str(
            get_config_val("JIRA_PROJECT_KEY", "OPS")
        ).strip()

    @classmethod
    def _get_email(cls) -> str:
        return str(
            get_config_val("JIRA_EMAIL", "")
        ).strip()

    @classmethod
    def _get_api_token(cls) -> str:
        return str(
            get_secret("JIRA_API_TOKEN", "")
        ).strip()

    @classmethod
    def is_configured(cls) -> bool:
        """
        Returns True only when all Jira connection settings
        required for live Jira access are available.
        """
        host = cls._get_host()
        email = cls._get_email()
        token = cls._get_api_token()
        project_key = cls._get_project_key()

        return bool(
            host
            and email
            and token
            and project_key
        )

    @classmethod
    def get_site_url(cls) -> str:
        """
        Returns the configured Jira Cloud site URL.
        """
        return cls._get_host() or "Not configured"

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Returns Jira configuration/connection status.

        Never exposes the actual API token.
        """
        host = cls._get_host()
        email = cls._get_email()
        token = cls._get_api_token()
        project_key = cls._get_project_key()

        configured = bool(
            host
            and email
            and token
            and project_key
        )

        return {
            "configured": configured,
            "host": host or "Not configured",
            "project_key": project_key or "Not configured",
            "email": email or "Not configured",
            "has_token": bool(token),
            "mode": (
                "PRODUCTION_LIVE"
                if configured
                else "NOT_CONFIGURED"
            )
        }

    @classmethod
    def _get_auth_headers(cls) -> Dict[str, str]:
        """
        Creates Jira Cloud Basic Authentication headers.

        Jira Cloud uses:
            email + API token
        """
        email = cls._get_email()
        api_token = cls._get_api_token()

        auth_string = f"{email}:{api_token}"
        encoded_auth = base64.b64encode(
            auth_string.encode("utf-8")
        ).decode("utf-8")

        return {
            "Authorization": f"Basic {encoded_auth}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Enterprise-Onboarding-Assistant/1.0"
        }

    @classmethod
    def _request(
        cls,
        method: str,
        path: str,
        payload: Optional[Dict[str, Any]] = None,
        timeout: int = 10
    ) -> Dict[str, Any]:

        host = cls._get_host()

        if not host:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_HOST is not configured."
            }

        url = f"{host}{path}"

        headers = cls._get_auth_headers()

        data = None

        if payload is not None:
            data = json.dumps(payload).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=data,
            headers=headers,
            method=method
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=timeout
            ) as response:

                raw = response.read().decode(
                    "utf-8",
                    errors="ignore"
                )

                response_data: Any = {}

                if raw:
                    try:
                        response_data = json.loads(raw)
                    except json.JSONDecodeError:
                        response_data = {
                            "raw": raw
                        }

                return {
                    "success": True,
                    "http_status": response.status,
                    "data": response_data
                }

        except urllib.error.HTTPError as error:

            error_body = error.read().decode(
                "utf-8",
                errors="ignore"
            )

            try:
                error_data = json.loads(error_body)
            except Exception:
                error_data = {
                    "raw": error_body
                }

            return {
                "success": False,
                "http_status": error.code,
                "error": error_data
            }

        except urllib.error.URLError as error:

            return {
                "success": False,
                "http_status": None,
                "error": str(error.reason)
            }

        except Exception as error:

            return {
                "success": False,
                "http_status": None,
                "error": str(error)
            }

    @classmethod
    def test_connection(cls) -> Dict[str, Any]:
        """
        Tests authenticated access to Jira Cloud.

        GET /rest/api/3/myself verifies that the supplied
        Jira email + API token can authenticate.
        """

        host = cls._get_host()
        email = cls._get_email()
        token = cls._get_api_token()

        if not host:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_HOST is not configured."
            }

        if not email:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_EMAIL is not configured."
            }

        if not token:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_API_TOKEN is not available."
            }

        result = cls._request(
            "GET",
            "/rest/api/3/myself"
        )

        if result.get("success"):
            data = result.get("data") or {}

            return {
                "success": True,
                "status": "CONNECTED",
                "message": "Successfully authenticated with Jira Cloud.",
                "account_id": data.get("accountId"),
                "display_name": data.get("displayName"),
                "email": data.get("emailAddress") or email
            }

        http_status = result.get("http_status")

        if http_status == 401:
            return {
                "success": False,
                "status": "AUTHENTICATION_FAILED",
                "message": (
                    "Jira rejected the email/API token combination."
                )
            }

        return {
            "success": False,
            "status": "CONNECTION_FAILED",
            "http_status": http_status,
            "message": "Unable to authenticate with Jira Cloud.",
            "error": result.get("error")
        }

    @classmethod
    def test_project_access(cls) -> Dict[str, Any]:
        """
        Verifies that the configured Jira project exists and
        is accessible using the configured credentials.
        """

        project_key = cls._get_project_key()

        if not project_key:
            return {
                "success": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_PROJECT_KEY is not configured."
            }

        result = cls._request(
            "GET",
            f"/rest/api/3/project/{project_key}"
        )

        if result.get("success"):
            data = result.get("data") or {}

            return {
                "success": True,
                "status": "PROJECT_ACCESSIBLE",
                "project_key": data.get(
                    "key",
                    project_key
                ),
                "project_name": data.get(
                    "name"
                )
            }

        http_status = result.get("http_status")

        if http_status == 401:
            status = "AUTHENTICATION_FAILED"
        elif http_status == 403:
            status = "PROJECT_ACCESS_DENIED"
        elif http_status == 404:
            status = "PROJECT_NOT_FOUND"
        else:
            status = "PROJECT_CHECK_FAILED"

        return {
            "success": False,
            "status": status,
            "http_status": http_status,
            "project_key": project_key,
            "message": "Unable to access Jira project.",
            "error": result.get("error")
        }

    @classmethod
    def create_incident_issue(
        cls,
        summary: str,
        category: str,
        severity: str,
        employee_id: str,
        reporter_email: str
    ) -> Dict[str, Any]:
        """
        Creates an incident directly in Jira Cloud.

        IMPORTANT:
        Jira connection configuration is loaded internally from
        backend.config. The caller only supplies incident data.
        """

        host = cls._get_host()
        project_key = cls._get_project_key()
        email = cls._get_email()
        api_token = cls._get_api_token()

        if not host:
            return {
                "success": False,
                "live_sync": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_HOST is not configured."
            }

        if not project_key:
            return {
                "success": False,
                "live_sync": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_PROJECT_KEY is not configured."
            }

        if not email:
            return {
                "success": False,
                "live_sync": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_EMAIL is not configured."
            }

        if not api_token:
            return {
                "success": False,
                "live_sync": False,
                "status": "NOT_CONFIGURED",
                "message": "JIRA_API_TOKEN is not available."
            }

        payload = {
            "fields": {
                "project": {
                    "key": project_key
                },
                "summary": (
                    f"[{severity}] "
                    f"{category}: "
                    f"{summary[:120]}"
                ),
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        "Reported via "
                                        "Employee AI Assistant."
                                    )
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Reporter: "
                                        f"{reporter_email} "
                                        f"(ID: {employee_id})"
                                    )
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Severity: {severity}"
                                    )
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Category: {category}"
                                    )
                                }
                            ]
                        },
                        {
                            "type": "paragraph",
                            "content": [
                                {
                                    "type": "text",
                                    "text": (
                                        f"Details: {summary}"
                                    )
                                }
                            ]
                        }
                    ]
                },
                "issuetype": {
                    "name": "Task"
                }
            }
        }

        result = cls._request(
            "POST",
            "/rest/api/3/issue",
            payload=payload,
            timeout=10
        )

        if result.get("success"):

            response_data = result.get("data") or {}

            jira_key = response_data.get("key")
            jira_id = response_data.get("id")

            if jira_key:

                return {
                    "success": True,
                    "live_sync": True,
                    "jira_key": jira_key,
                    "jira_url": (
                        f"{host}/browse/{jira_key}"
                    ),
                    "jira_id": jira_id,
                    "status": "CREATED_IN_JIRA_CLOUD",
                    "message": (
                        f"Successfully created Jira ticket "
                        f"{jira_key}"
                    )
                }

            return {
                "success": False,
                "live_sync": False,
                "status": "INVALID_JIRA_RESPONSE",
                "message": (
                    "Jira accepted the request but did not "
                    "return an issue key."
                )
            }

        http_status = result.get("http_status")

        if http_status == 400:
            status = "JIRA_REQUEST_REJECTED"
        elif http_status == 401:
            status = "JIRA_AUTHENTICATION_FAILED"
        elif http_status == 403:
            status = "JIRA_PERMISSION_DENIED"
        elif http_status == 404:
            status = "JIRA_PROJECT_NOT_FOUND"
        else:
            status = "JIRA_SYNC_FAILED"

        return {
            "success": False,
            "live_sync": False,
            "status": status,
            "http_status": http_status,
            "message": (
                "Jira incident creation failed."
            ),
            "error": result.get("error")
        }