"""
Code Mentor and Engineering Standards Agent Tools.
Enforces Patchamomma corporate structured logging guardrails and semantic vector repo search.
"""

import os
import re
import json
import logging
from typing import Optional, Dict, Any

from app.core import context

logger = logging.getLogger("patchamomma.agents.tools.code")

SEMANTIC_CODE_VECTOR_INDEX: Dict[str, Dict[str, Any]] = {
    "backend/database/connection.py": {
        "description": "Database connection pool initialization using Cloud SQL Proxy",
        "symbols": ["connect_database", "get_connection_pool", "close_pool"],
        "snippet": (
            "def connect_database():\n"
            "    print('Initializing Cloud SQL staging connection pool...')\n"
            "    db_conn = 'postgresql://app:secret@127.0.0.1:5432/patchamomma_prod'\n"
            "    print('Database connection established successfully')\n"
            "    return db_conn"
        ),
    },
    "services/auth/jwt_validator.py": {
        "description": "Enterprise JWT token signature verification and IAM roles extraction",
        "symbols": ["verify_token", "extract_claims", "enforce_scope"],
        "snippet": (
            "def verify_token(token: str):\n"
            "    print('Verifying incoming bearer token against Google KMS JWKS')\n"
            "    return {'valid': True, 'scope': 'developer'}"
        ),
    },
    "pipeline/telemetry/friction_stream.py": {
        "description": "BigQuery streaming inserter client for real-time manager telemetry",
        "symbols": ["stream_friction_event", "build_telemetry_payload"],
        "snippet": (
            "def stream_friction_event(payload: dict):\n"
            "    print('Submitting streaming insert to BigQuery friction log...')\n"
            "    return {'status': 'INSERTED'}"
        ),
    },
}


def apply_code_guardrails(raw_code: str) -> str:
    """
    Enforces Patchamomma Enterprise Coding Standards:
    1. Replaces basic print(...) calls with structured JSON logger.info() blocks.
    2. Injects standard corporate structured logger imports if missing.
    """
    transformed = raw_code

    print_pattern = re.compile(r"print\s*\((.*?)\)", re.DOTALL)

    def print_replacer(match):
        arg = match.group(1).strip()
        return (
            f'logger.info(json.dumps({{'
            f'"event": "application_log", '
            f'"message": str({arg}), '
            f'"standard": "PATCHAMOMMA-2026-JSON-V1"'
            f'}}))'
        )

    if print_pattern.search(transformed):
        transformed = print_pattern.sub(print_replacer, transformed)

    preamble = (
        "# --- [PATCHAMOMMA BEST PRACTICES GUARDRAIL APPLIED] ---\n"
        "import json\n"
        "import logging\n"
        "logger = logging.getLogger('patchamomma.enterprise')\n"
        "# ------------------------------------------------------\n"
    )

    if "logger = logging.getLogger" not in transformed:
        transformed = preamble + transformed

    return transformed


def fetch_repository_context(repo_name: str, query: Optional[str] = None, file_path: Optional[str] = None) -> str:
    """
    Fetches codebase context and target file blocks for code explanation or refactoring.
    Applies the corporate Best Practices Guardrail engine to all output code snippets.
    Args:
        repo_name: Target repository name (e.g. 'patchamomma-core')
        query: Function symbol or keyword to look up (e.g. 'connect_database')
        file_path: Specific file path (e.g. 'backend/database/connection.py')
    """
    actor = context.get_current_employee()
    logger.info(f"fetch_repository_context called by {actor.employee_id} for repo={repo_name}, file={file_path}")

    retrieved_code = ""
    source_method = ""

    if file_path and file_path in SEMANTIC_CODE_VECTOR_INDEX:
        source_method = f"Live Code Repository [Exact Match: {file_path}]"
        retrieved_code = SEMANTIC_CODE_VECTOR_INDEX[file_path]["snippet"]
    else:
        source_method = "Semantic Code Index (0 GitHub API calls consumed)"
        search_term = (query or file_path or "").lower()
        matched = []
        for path, data in SEMANTIC_CODE_VECTOR_INDEX.items():
            if search_term in path.lower() or search_term in data["description"].lower() or any(search_term in s.lower() for s in data["symbols"]):
                matched.append((path, data))

        if matched:
            parts = []
            for path, data in matched:
                parts.append(
                    f"### File: {path}\n"
                    f"Description: {data['description']}\n"
                    f"Symbols: {', '.join(data['symbols'])}\n"
                    f"Code:\n```python\n{data['snippet']}\n```"
                )
            retrieved_code = "\n\n".join(parts)
        else:
            retrieved_code = f"# No indexed code found matching '{query}' in {repo_name}."

    guardrailed_code = apply_code_guardrails(retrieved_code)

    return (
        f"--- REPOSITORY CONTEXT RESULT ---\n"
        f"Source: {source_method}\n"
        f"Repository: {repo_name}\n"
        f"Guardrails Status: ENFORCED (JSON Structured Logger Standard Applied)\n\n"
        f"{guardrailed_code}"
    )
