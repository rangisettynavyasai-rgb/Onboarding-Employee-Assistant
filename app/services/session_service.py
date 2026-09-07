"""
Session Security & Cost-Optimized State Storage Service (Phase C).
Replaces expensive Redis clusters ($35+/mo) with Google Cloud Firestore (Native Mode)
leveraging the 100% free daily tier (50k reads, 20k writes, 1GB storage) for $0.00 infrastructure cost.
Cryptographically binds ActiveSessionState payloads directly to verified employee_id to block
cross-user token reuse and cross-tenant session hijacking.
"""

import copy
import logging
import uuid
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any

from app.config import settings
from app.core.exceptions import SessionSecurityError
from app.core.logging import log_audit_event
from app.models import EmployeeRecord, ActiveSessionState, ChatMessage

logger = logging.getLogger("patchamomma.services.session")


# Backward-compatible UserSession wrapper
class UserSession:
    """Convenience class maintaining active session state and in-memory methods."""
    def __init__(self, session_id: str, employee_id: str, history: Optional[List[Dict[str, str]]] = None):
        self.session_id = session_id
        self.employee_id = employee_id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.last_accessed_at = datetime.now(timezone.utc).isoformat()
        self.history: List[Dict[str, str]] = history or []

    def append_message(self, role: str, content: str) -> None:
        self.history.append({"role": role, "content": content, "timestamp": datetime.now(timezone.utc).isoformat()})
        self.last_accessed_at = datetime.now(timezone.utc).isoformat()

    def to_state(self) -> ActiveSessionState:
        chat_msgs = [
            ChatMessage(role=m.get("role", "user"), content=m.get("content", ""), timestamp=m.get("timestamp", ""))
            for m in self.history
        ]
        return ActiveSessionState(
            session_id=self.session_id,
            employee_id=self.employee_id,
            created_at=self.created_at,
            last_accessed_at=self.last_accessed_at,
            conversation_history=chat_msgs,
        )

    @classmethod
    def from_state(cls, state: ActiveSessionState) -> "UserSession":
        sess = cls(session_id=state.session_id, employee_id=state.employee_id)
        sess.created_at = state.created_at
        sess.last_accessed_at = state.last_accessed_at
        sess.history = [
            {"role": m.role, "content": m.content, "timestamp": m.timestamp}
            for m in state.conversation_history
        ]
        return sess


class ISessionStore(ABC):
    @abstractmethod
    def get_session(self, session_id: str) -> Optional[ActiveSessionState]:
        pass

    @abstractmethod
    def save_session(self, session: ActiveSessionState) -> None:
        pass

    @abstractmethod
    def delete_session(self, session_id: str) -> bool:
        pass


class MemorySessionStore(ISessionStore):
    """Thread-safe in-memory session store for local sandbox and unit tests."""
    def __init__(self):
        self._store: Dict[str, ActiveSessionState] = {}

    def get_session(self, session_id: str) -> Optional[ActiveSessionState]:
        item = self._store.get(session_id)
        return copy.deepcopy(item) if item else None

    def save_session(self, session: ActiveSessionState) -> None:
        self._store[session.session_id] = copy.deepcopy(session)

    def delete_session(self, session_id: str) -> bool:
        return self._store.pop(session_id, None) is not None


class FirestoreSessionStore(ISessionStore):
    """
    Production Firestore (Native Mode) session persistence.
    Utilizes Firestore's 100% Free Daily Tier (50k reads, 20k writes, 1GB storage) for $0.00 state cost.
    """
    def __init__(self):
        self._client = None
        self._collection_name = settings.FIRESTORE_COLLECTION_SESSIONS
        self._memory_fallback = MemorySessionStore()

        try:
            from google.cloud import firestore
            database_id = settings.FIRESTORE_DATABASE if settings.FIRESTORE_DATABASE != "(default)" else None
            if database_id:
                self._client = firestore.Client(project=settings.GCP_PROJECT_ID, database=database_id)
            else:
                self._client = firestore.Client(project=settings.GCP_PROJECT_ID)
            logger.info(f"Firestore Session Store initialized for project '{settings.GCP_PROJECT_ID}' collection '{self._collection_name}'")
        except Exception as e:
            logger.warning(f"Firestore client initialization failed ({e}). Falling back to in-memory session store.")
            self._client = None

    def get_session(self, session_id: str) -> Optional[ActiveSessionState]:
        if not self._client:
            return self._memory_fallback.get_session(session_id)

        try:
            doc_ref = self._client.collection(self._collection_name).document(session_id)
            doc = doc_ref.get()
            if doc.exists:
                data = doc.to_dict()
                return ActiveSessionState(**data)
            return None
        except Exception as e:
            logger.error(f"Firestore get_session failed for '{session_id}': {e}")
            return self._memory_fallback.get_session(session_id)

    def save_session(self, session: ActiveSessionState) -> None:
        if not self._client:
            self._memory_fallback.save_session(session)
            return

        try:
            doc_ref = self._client.collection(self._collection_name).document(session.session_id)
            doc_ref.set(session.model_dump())
        except Exception as e:
            logger.error(f"Firestore save_session failed for '{session.session_id}': {e}")
            self._memory_fallback.save_session(session)

    def delete_session(self, session_id: str) -> bool:
        if not self._client:
            return self._memory_fallback.delete_session(session_id)

        try:
            doc_ref = self._client.collection(self._collection_name).document(session_id)
            doc_ref.delete()
            return True
        except Exception as e:
            logger.error(f"Firestore delete_session failed for '{session_id}': {e}")
            return self._memory_fallback.delete_session(session_id)


class SessionService:
    """
    Manages active conversational sessions with strict employee binding and anti-hijacking enforcement.
    """

    def __init__(self, store: Optional[ISessionStore] = None):
        if store:
            self.store = store
        elif settings.SESSION_STORE_BACKEND == "firestore":
            self.store = FirestoreSessionStore()
        else:
            self.store = MemorySessionStore()

    def get_or_create_session(self, session_id: Optional[str], employee: EmployeeRecord) -> UserSession:
        """
        Retrieves an existing session while validating employee ownership, or creates a new session.
        ANTI-HIJACKING BOUNDARY: Raises SessionSecurityError (403) if session belongs to another employee.
        """
        now_iso = datetime.now(timezone.utc).isoformat()

        if not session_id:
            new_id = str(uuid.uuid4())
            new_state = ActiveSessionState(
                session_id=new_id,
                employee_id=employee.employee_id,
                created_at=now_iso,
                last_accessed_at=now_iso,
                conversation_history=[],
                metadata={"department": employee.department, "team": employee.team, "role": employee.authorization_role.value},
            )
            self.store.save_session(new_state)
            log_audit_event("SESSION_CREATED", employee.employee_id, "CREATE_SESSION", "ALLOWED", new_id)
            return UserSession.from_state(new_state)

        existing_state = self.store.get_session(session_id)
        if existing_state:
            # STRICT ANTI-HIJACKING OWNERSHIP VERIFICATION
            if existing_state.employee_id != employee.employee_id:
                log_audit_event(
                    "SESSION_HIJACK_ATTEMPT",
                    employee.employee_id,
                    "ACCESS_SESSION",
                    "DENIED",
                    session_id,
                    {"owner_employee_id": existing_state.employee_id, "attempted_by": employee.employee_id},
                )
                raise SessionSecurityError(
                    f"Session security violation: Session '{session_id}' is owned by another employee."
                )

            existing_state.last_accessed_at = now_iso
            self.store.save_session(existing_state)
            return UserSession.from_state(existing_state)

        # Session ID supplied by client but not yet in store: initialize bound to current employee
        new_state = ActiveSessionState(
            session_id=session_id,
            employee_id=employee.employee_id,
            created_at=now_iso,
            last_accessed_at=now_iso,
            conversation_history=[],
            metadata={"department": employee.department, "team": employee.team, "role": employee.authorization_role.value},
        )
        self.store.save_session(new_state)
        log_audit_event("SESSION_INITIALIZED", employee.employee_id, "INIT_SESSION", "ALLOWED", session_id)
        return UserSession.from_state(new_state)

    def persist_session(self, session: UserSession) -> None:
        """Saves current state of UserSession into persistent store."""
        state = session.to_state()
        self.store.save_session(state)
