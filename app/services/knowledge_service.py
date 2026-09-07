"""
Knowledge Mesh & Secure RAG Service (Phase E: Pre-Retrieval RAG Hardening).
Applies pre-retrieval ACL filtering before chunks are exposed to the AI context.
Cryptographically/deterministically stamps department and clearance security perimeters
into the retrieval context before LLM reasoning.
"""

import hashlib
import logging
from typing import List, Dict, Any, Optional

from app.core.logging import log_audit_event
from app.models import EmployeeRecord, KnowledgeChunk, AuthAction
from app.repositories.base import IKnowledgeRepository
from app.services.authorization_service import AuthorizationService

logger = logging.getLogger("patchamomma.services.knowledge")


class KnowledgeService:
    """Manages secure knowledge retrieval and pre-retrieval ACL boundaries."""

    def __init__(self, knowledge_repo: IKnowledgeRepository, authz_service: AuthorizationService):
        self.knowledge_repo = knowledge_repo
        self.authz_service = authz_service

    def search_authorized_knowledge(self, actor: EmployeeRecord, query: str) -> List[KnowledgeChunk]:
        """
        Executes pre-retrieval ACL filtered search against the Knowledge Mesh.
        Only chunks matching caller's team domain and authorization role are retrieved.
        Unauthorized chunks are filtered at the repository/storage boundary.
        """
        # 1. Authorize general document search action
        self.authz_service.authorize(
            actor=actor,
            action=AuthAction.VIEW_DOCUMENT,
            resource="KNOWLEDGE_CATALOG",
        )

        # 2. PRE-RETRIEVAL ACL: Filtered at the repository/storage boundary
        chunks = self.knowledge_repo.search_authorized(
            query=query,
            user_team=actor.team,
            user_role=actor.authorization_role,
        )

        log_audit_event(
            "KNOWLEDGE_SEARCH",
            actor.employee_id,
            "RETRIEVE_CHUNKS",
            "ALLOWED",
            "KNOWLEDGE_MESH",
            {
                "query": query,
                "retrieved_chunk_count": len(chunks),
                "user_team": actor.team,
                "user_department": actor.department,
                "user_role": actor.authorization_role.value,
            },
        )

        return chunks

    def format_chunks_for_context(self, actor: EmployeeRecord, chunks: List[KnowledgeChunk], query: Optional[str] = None) -> str:
        """
        Formats authorized chunks into clean context for LLM reasoning.
        Enforces Phase E Pre-Retrieval RAG Hardening:
        Stamps the user's verified department, team, and clearance level into the security perimeter header.
        """
        perimeter_stamp = (
            f"[ENFORCED_SECURITY_PERIMETER: employee_id={actor.employee_id} | "
            f"department={actor.department} | team={actor.team} | clearance={actor.authorization_role.value}]"
        )

        if not chunks:
            return f"{perimeter_stamp}\nNo authorized company knowledge assets matched your query."

        formatted_parts = [perimeter_stamp]
        if query:
            formatted_parts.append(f"Search Query: {query}")

        for i, chunk in enumerate(chunks, start=1):
            formatted_parts.append(
                f"--- [AUTHORIZED ASSET {i} | ID: {chunk.document_id}] ---\n"
                f"Team Domain: {chunk.team} | Clearance Level: {chunk.access_level.value}\n"
                f"{chunk.content}\n"
            )
        return "\n".join(formatted_parts)
