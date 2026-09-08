#!/usr/bin/env python3
"""
Company AI Assistant: Role-Based Access Policy & Pre-Retrieval ACL Filters
Implements BigQuery-grounded security policies across employees, teams, and documents.
"""
from typing import List, Optional, Any
from backend.models import EmployeeRecord, AuthorizationRole, KnowledgeAsset, KnowledgeChunk

class AuthPolicy:
    """
    Evaluates Pre-Retrieval Document ACLs and Operational Permissions.
    Rules:
      1. Role Hierarchy:
         - HR and IT have full administrative view for their operations.
         - MANAGER role can access 'manager' and 'employee' tagged documents.
         - EMPLOYEE role can ONLY access 'employee' tagged documents.
      2. Domain/Team Boundary:
         - An employee can access documents tagged with their own team (e.g. 'Payments') OR company-wide 'ALL'.
         - Manager/HR can view their team + cross-team reports.
    """

    @staticmethod
    def can_access_chunk(employee: EmployeeRecord, chunk_team: str, chunk_access_level: str) -> bool:
        # 1. Role clearance check
        emp_role = (
            employee.authorization_role.value 
            if isinstance(employee.authorization_role, AuthorizationRole) 
            else str(employee.authorization_role).lower()
        )
        chunk_level = chunk_access_level.lower()

        # Manager or HR access
        if chunk_level in ["manager", "hr"]:
            if emp_role not in ["manager", "hr"]:
                return False

        if chunk_level == "it" and emp_role not in ["it", "manager"]:
            return False

        # 2. Team domain check
        c_team = chunk_team.upper()
        if c_team != "ALL":
            emp_team = employee.team.upper()
            if emp_team != c_team and emp_role not in ["manager", "hr"]:
                return False

        return True

    @staticmethod
    def filter_knowledge_chunks(employee: EmployeeRecord, chunks: List[KnowledgeChunk]) -> List[KnowledgeChunk]:
        return [
            c for c in chunks 
            if AuthPolicy.can_access_chunk(employee, c.team, c.access_level)
        ]

    @staticmethod
    def filter_knowledge_assets(employee: EmployeeRecord, assets: List[KnowledgeAsset]) -> List[KnowledgeAsset]:
        filtered = []
        for a in assets:
            if AuthPolicy.can_access_chunk(employee, a.team, a.access_level):
                # Filter internal chunks as well
                allowed_chunks = [
                    c for c in a.chunks 
                    if AuthPolicy.can_access_chunk(employee, c.team, c.access_level)
                ]
                asset_copy = KnowledgeAsset(
                    document_id=a.document_id,
                    title=a.title,
                    source=a.source,
                    gcs_uri=a.gcs_uri,
                    team=a.team,
                    access_level=a.access_level,
                    document_type=a.document_type,
                    owner=a.owner,
                    description=a.description,
                    chunks=allowed_chunks,
                )
                filtered.append(asset_copy)
        return filtered

def can_access_chunk(employee: EmployeeRecord, chunk_team: str, chunk_access_level: str) -> bool:
    return AuthPolicy.can_access_chunk(employee, chunk_team, chunk_access_level)

def is_manager_or_hr(role: Any) -> bool:
    role_str = role.value if isinstance(role, AuthorizationRole) else str(role).lower()
    return role_str in ["manager", "hr"]

