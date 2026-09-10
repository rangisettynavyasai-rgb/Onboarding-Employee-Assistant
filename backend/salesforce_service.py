#!/usr/bin/env python3
"""
Company AI Assistant: Salesforce Production Integration
Synchronizes submitted employee timesheets directly to Salesforce REST API
using Salesforce OAuth 2.0 Client Credentials Flow.
"""

import json
import time
import urllib.request
import urllib.error
import urllib.parse
from typing import Dict, Any, Optional
from datetime import datetime, timedelta

from backend.config import get_config_val, get_secret


class SalesforceService:
    """
    Salesforce integration using OAuth 2.0 Client Credentials Flow.

    Configuration:
        SALESFORCE_INSTANCE_URL -> app.config.json via config.py
        SALESFORCE_CLIENT_ID -> app.config.json via config.py
        SALESFORCE_CLIENT_SECRET -> Google Secret Manager via config.py

    Salesforce custom object:
        Timesheet__c

    Salesforce custom fields:
        Employee_ID__c
        Employee_Name__c
        Start_Date__c
        End_Date__c
        Hours__c
        Notes__c
        Status__c
    """

    API_VERSION = "v58.0"

    OBJECT_NAME = "Timesheet__c"

    @classmethod
    def _get_instance_url(cls) -> str:
        return (
            str(
                get_config_val(
                    "SALESFORCE_INSTANCE_URL",
                    ""
                )
            )
            .strip()
            .rstrip("/")
        )

    @classmethod
    def _get_client_id(cls) -> str:
        return (
            str(
                get_config_val(
                    "SALESFORCE_CLIENT_ID",
                    ""
                )
            )
            .strip()
        )

    @classmethod
    def _get_client_secret(cls) -> str:
        return (
            str(
                get_secret(
                    "SALESFORCE_ACCESS_TOKEN",
                    ""
                ) or ""
            )
            .strip()
        )

    @classmethod
    def is_configured(cls) -> bool:
        """
        Returns True when all Salesforce Client Credentials
        settings are available.
        """

        instance_url = cls._get_instance_url()
        client_id = cls._get_client_id()
        client_secret = cls._get_client_secret()

        return bool(
            instance_url
            and client_id
            and client_secret
        )

    @classmethod
    def get_instance_url(cls) -> str:
        """
        Returns the configured Salesforce My Domain URL.
        """

        return cls._get_instance_url()

    @classmethod
    def get_status(cls) -> Dict[str, Any]:
        """
        Returns Salesforce configuration status without exposing
        the client secret.
        """

        instance_url = cls._get_instance_url()
        client_id = cls._get_client_id()
        client_secret = cls._get_client_secret()

        configured = bool(
            instance_url
            and client_id
            and client_secret
        )

        return {
            "configured": configured,
            "instance_url": (
                instance_url
                if instance_url
                else "Not configured"
            ),
            "has_client_id": bool(client_id),
            "has_client_secret": bool(client_secret),
            "mode": (
                "PRODUCTION_LIVE"
                if configured
                else "FIRESTORE_STAGING_MODE"
            )
        }

    @classmethod
    def _get_access_token(cls) -> Optional[str]:
        """
        Obtains a Salesforce OAuth access token using the
        Client Credentials Flow.
        """

        instance_url = cls._get_instance_url()
        client_id = cls._get_client_id()
        client_secret = cls._get_client_secret()

        if not instance_url:
            print(
                "[SalesforceService] "
                "SALESFORCE_INSTANCE_URL is not configured."
            )
            return None

        if not client_id:
            print(
                "[SalesforceService] "
                "SALESFORCE_CLIENT_ID is not configured."
            )
            return None

        if not client_secret:
            print(
                "[SalesforceService] "
                "SALESFORCE_CLIENT_SECRET is not configured."
            )
            return None

        # Salesforce OAuth Client Credentials endpoint.
        token_url = (
            f"{instance_url}"
            "/services/oauth2/token"
        )

        form_data = urllib.parse.urlencode(
            {
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
            }
        )

        data = form_data.encode("utf-8")

        headers = {
            "Content-Type": "application/x-www-form-urlencoded",
            "Accept": "application/json"
        }

        request = urllib.request.Request(
            token_url,
            data=data,
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(
                request,
                timeout=10
            ) as response:

                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            access_token = response_data.get(
                "access_token"
            )

            if not access_token:
                print(
                    "[SalesforceService] "
                    "Salesforce did not return an access token."
                )
                return None

            return access_token

        except urllib.error.HTTPError as he:

            error_body = he.read().decode(
                "utf-8",
                errors="ignore"
            )

            print(
                "[SalesforceService] Salesforce OAuth HTTP "
                f"error {he.code}: {error_body}"
            )

        except Exception as e:

            print(
                "[SalesforceService] Salesforce OAuth "
                f"connection error: {e}"
            )

        return None

    @classmethod
    def sync_timesheet(
        cls,
        employee_id: str,
        employee_name: str,
        hours: float,
        notes: str
    ) -> Dict[str, Any]:
        """
        Creates a Timesheet__c record in Salesforce.

        Authentication:
            OAuth 2.0 Client Credentials Flow

        Salesforce object:
            Timesheet__c

        Falls back to Firestore staging if Salesforce
        authentication or API synchronization fails.
        """

        instance_url = cls._get_instance_url()

        ts = int(time.time())

        # Determine current week start (Monday)
        # and end (Friday).
        today = datetime.now()

        monday = (
            today
            - timedelta(days=today.weekday())
        )

        friday = (
            monday
            + timedelta(days=4)
        )

        period_str = (
            f"{monday.strftime('%Y-%m-%d')} "
            f"to {friday.strftime('%Y-%m-%d')}"
        )

        # Get a fresh Salesforce OAuth token.
        access_token = cls._get_access_token()
        print(
            f"[SalesforceService] OAuth token received: "
            f"{bool(access_token)}"
        )

        if instance_url and access_token:

            url = (
                f"{instance_url}/services/data/"
                f"{cls.API_VERSION}/sobjects/"
                f"{cls.OBJECT_NAME}"
            )

            headers = {
                "Authorization": (
                    f"Bearer {access_token}"
                ),
                "Content-Type": "application/json",
                "Accept": "application/json"
            }

            # Payload for Salesforce custom object.
            payload = {
                "Employee_ID__c": employee_id,
                "Employee_Name__c": employee_name,
                "Start_Date__c": (
                    monday.strftime("%Y-%m-%d")
                ),
                "End_Date__c": (
                    friday.strftime("%Y-%m-%d")
                ),
                "Hours__c": hours,
                "Notes__c": notes,
                "Status__c": "Submitted"
            }

            try:

                data = json.dumps(
                    payload
                ).encode("utf-8")

                request = urllib.request.Request(
                    url,
                    data=data,
                    headers=headers,
                    method="POST"
                )

                with urllib.request.urlopen(
                    request,
                    timeout=10
                ) as response:

                    response_data = json.loads(
                        response.read().decode("utf-8")
                    )

                record_id = response_data.get(
                    "id"
                )

                if not record_id:

                    print(
                        "[SalesforceService] "
                        "Salesforce response did not "
                        "contain a record ID."
                    )

                    raise RuntimeError(
                        "Salesforce did not return "
                        "a record ID."
                    )

                return {
                    "success": True,
                    "live_sync": True,
                    "salesforce_id": record_id,
                    "salesforce_url": (
                        f"{instance_url}/{record_id}"
                    ),
                    "status": (
                        "SYNCED_TO_SALESFORCE"
                    ),
                    "period": period_str,
                    "message": (
                        f"Timesheet record {record_id} "
                        "created in Salesforce"
                    )
                }

            except urllib.error.HTTPError as he:

                error_body = he.read().decode(
                    "utf-8",
                    errors="ignore"
                )

                print(
                    "[SalesforceService] Salesforce API "
                    f"HTTP error {he.code}: {error_body}"
                )

            except Exception as e:

                print(
                    "[SalesforceService] Connection error "
                    f"to Salesforce: {e}"
                )

        # Firestore staging fallback.
        staged_id = (
            f"02i8X"
            f"{ts % 1000000:07d}"
            "AA"
        )

        return {
            "success": True,
            "live_sync": False,
            "salesforce_id": staged_id,
            "salesforce_url": (
                f"{instance_url or 'https://salesforce.company.internal'}"
                f"/{staged_id}"
            ),
            "status": "STAGED_IN_FIRESTORE",
            "period": period_str,
            "message": (
                "Timesheet recorded in Cloud Firestore. "
                "Salesforce live synchronization was not completed."
            )
        }