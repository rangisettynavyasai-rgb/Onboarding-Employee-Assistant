"""
Domain and HTTP Exception Hierarchy.
Ensures strict status code separation (401 Unauthorized vs 403 Forbidden).
"""

from typing import Optional, Dict, Any


class AppException(Exception):
    """Base exception for application errors."""

    def __init__(self, message: str, status_code: int = 500, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}


class AuthenticationError(AppException):
    """Raised when authentication fails (Missing/Invalid Token, Unknown Subject)."""

    def __init__(self, message: str = "Authentication failed. Valid Google credentials required.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=401, details=details)


class AuthorizationError(AppException):
    """Raised when authenticated user is not authorized for the requested action."""

    def __init__(self, message: str = "Access forbidden. Insufficient permissions.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=403, details=details)


class SessionSecurityError(AppException):
    """Raised when a user attempts to access or hijack a session owned by another employee."""

    def __init__(self, message: str = "Session ownership mismatch. Access denied.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=403, details=details)


class NotFoundError(AppException):
    """Raised when a requested resource is not found."""

    def __init__(self, message: str = "Resource not found.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=404, details=details)


class ValidationError(AppException):
    """Raised when request payload or parameters fail validation."""

    def __init__(self, message: str = "Invalid request payload.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=400, details=details)


class IntegrationError(AppException):
    """Raised when an external enterprise integration fails."""

    def __init__(self, message: str = "External service integration failure.", details: Optional[Dict[str, Any]] = None):
        super().__init__(message=message, status_code=502, details=details)
