"""
Knowledge Mesh & RAG Agent Tools.
Enforces pre-retrieval ACL boundaries before chunks are passed to the agent.
"""

import logging
from typing import Optional

from app.core import context
from app.dependencies import knowledge_service

logger = logging.getLogger("patchamomma.agents.tools.knowledge")


def search_company_knowledge(query: str) -> str:
    """
    Searches company knowledge mesh, GCS runbooks, architecture specs, and video guides.
    CRITICAL SECURITY: Pre-retrieval ACL filtering is executed server-side.
    Unauthorized documents (other team's confidential docs, manager/HR only files) are completely omitted.
    Args:
        query: Keywords or concept to search for (e.g. 'Cloud SQL Proxy', 'Logging standards', '1:1 guidelines')
    """
    actor = context.get_current_employee()
    try:
        chunks = knowledge_service.search_authorized_knowledge(actor, query)
        if not chunks:
            return f"No authorized company knowledge assets found matching '{query}' for team '{actor.team}' and role '{actor.authorization_role.value}'."

        formatted_chunks = knowledge_service.format_chunks_for_context(actor, chunks, query)
        return (
            f"=== AUTHORIZED KNOWLEDGE MESH RESULTS (Caller: {actor.name}, Team: {actor.team}) ===\n"
            f"Query: {query}\n"
            f"Retrieved Chunks: {len(chunks)}\n\n"
            f"{formatted_chunks}"
        )
    except Exception as e:
        logger.error(f"search_company_knowledge failed: {e}")
        return f"Knowledge search error: {str(e)}"
