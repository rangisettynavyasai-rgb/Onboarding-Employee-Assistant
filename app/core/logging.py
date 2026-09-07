"""
Structured Corporate JSON Logger and Security Audit Module.
Complies with GCP Cloud Logging standards and corporate compliance.
"""

import json
import logging
import time
import sys
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class JSONFormatter(logging.Formatter):
    """Formats log records as structured JSON for GCP Cloud Logging."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry: Dict[str, Any] = {
            "severity": record.levelname,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Include custom extra fields if present
        if hasattr(record, "audit_event"):
            log_entry["audit"] = record.audit_event
        if hasattr(record, "correlation_id"):
            log_entry["correlation_id"] = record.correlation_id
        if hasattr(record, "employee_id"):
            log_entry["employee_id"] = record.employee_id

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def setup_logger(name: str = "patchamomma") -> logging.Logger:
    """Configures and returns a structured logger."""
    logger = logging.getLogger(name)
    if not logger.handlers:
        logger.setLevel(logging.INFO)
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(JSONFormatter())
        logger.addHandler(handler)
        logger.propagate = False
    return logger


logger = setup_logger("patchamomma.enterprise")


def log_audit_event(
    event_type: str,
    actor_id: str,
    action: str,
    decision: str,  # 'ALLOWED' | 'DENIED' | 'EXECUTED' | 'FAILED'
    resource: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """
    Logs an immutable security audit event for compliance and forensics.
    Never logs raw secrets, tokens, or private document payloads.
    """
    audit_data = {
        "event_type": event_type,
        "actor_id": actor_id,
        "action": action,
        "decision": decision,
        "resource": resource,
        "timestamp": time.time(),
        "details": details or {},
    }
    logger.info(
        f"AUDIT: [{decision}] {actor_id} -> {action} on {resource}",
        extra={"audit_event": audit_data, "employee_id": actor_id},
    )
