"""
Thread-safe Execution Context Provider.
Uses Python contextvars to bind authenticated identity to the current async request context.
This prevents LLM prompt-injection arguments from spoofing caller identity.
"""

from contextvars import ContextVar
from typing import Optional, Any

_current_principal: ContextVar[Optional[Any]] = ContextVar("current_principal", default=None)
_current_employee: ContextVar[Optional[Any]] = ContextVar("current_employee", default=None)
_current_correlation_id: ContextVar[Optional[str]] = ContextVar("current_correlation_id", default=None)


def set_current_principal(principal: Any) -> None:
    """Sets the authenticated principal for the current request context."""
    _current_principal.set(principal)


def get_current_principal() -> Optional[Any]:
    """Retrieves the authenticated principal for the current request context."""
    return _current_principal.get()


def set_current_employee(employee: Any) -> None:
    """Sets the trusted EmployeeRecord for the current request context."""
    _current_employee.set(employee)


def get_current_employee() -> Any:
    """
    Retrieves the trusted EmployeeRecord for the current request context.
    Raises RuntimeError if accessed outside an authenticated request.
    """
    emp = _current_employee.get()
    if emp is None:
        raise RuntimeError("No authenticated employee in current context. Zero-trust check failed.")
    return emp


def set_correlation_id(correlation_id: str) -> None:
    """Sets the tracing correlation ID for the current request."""
    _current_correlation_id.set(correlation_id)


def get_correlation_id() -> Optional[str]:
    """Retrieves the tracing correlation ID."""
    return _current_correlation_id.get()
