"""
Knowledge & RAG Detective Sub-Agent.
Grounds responses in authorized company documents, architecture runbooks, and video assets.
"""

import logging
from app.core import context
from app.agents.tools.knowledge_tools import search_company_knowledge

logger = logging.getLogger("patchamomma.agents.knowledge")


class KnowledgeAgent:
    name = "knowledge-detective-agent"
    description = "Searches company knowledge mesh, GCS runbooks, and video guides with pre-retrieval ACL security."

    def execute(self, user_message: str) -> str:
        # Extract search query from user prompt
        cleaned_query = user_message.replace("search", "").replace("find", "").replace("tell me about", "").strip()
        if not cleaned_query:
            cleaned_query = user_message

        return search_company_knowledge(cleaned_query)


knowledge_agent = KnowledgeAgent()
