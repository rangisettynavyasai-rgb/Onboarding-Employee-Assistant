"""
Knowledge Mesh Pre-Retrieval ACL & Document Isolation Tests (Phase E: Pre-Retrieval RAG Hardening).
Verifies that unauthorized chunks are filtered out at the storage layer before entering AI context,
and that security perimeters are stamped into context payloads.
"""

import pytest
from app.data.synthetic_employees import SYNTHETIC_EMPLOYEES
from app.dependencies import knowledge_service


def test_team_isolation_payments_vs_platform():
    """
    Payments engineer (Rahul) should retrieve Payments docs and Company-wide docs,
    but NEVER Platform-only docs.
    """
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]  # Payments
    maya = SYNTHETIC_EMPLOYEES["EMP-2026-002"]   # Platform

    # Rahul searches for database / architecture
    rahul_chunks = knowledge_service.search_authorized_knowledge(rahul, "architecture")
    doc_ids_rahul = {c.document_id for c in rahul_chunks}

    assert "DOC-PAY-001" in doc_ids_rahul
    assert "DOC-PLT-001" not in doc_ids_rahul  # Platform doc must be blocked!

    # Maya searches for architecture / cluster
    maya_chunks = knowledge_service.search_authorized_knowledge(maya, "runbook cluster")
    doc_ids_maya = {c.document_id for c in maya_chunks}

    assert "DOC-PLT-001" in doc_ids_maya
    assert "DOC-PAY-001" not in doc_ids_maya  # Payments doc must be blocked!


def test_role_level_clearance_manager_doc():
    """
    Manager (Sarah) can access Manager 1:1 playbook.
    Regular employee (Rahul) CANNOT access Manager playbook.
    """
    sarah = SYNTHETIC_EMPLOYEES["EMP-2026-010"]  # Manager
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]  # Employee

    sarah_chunks = knowledge_service.search_authorized_knowledge(sarah, "manager playbook 1:1")
    sarah_docs = {c.document_id for c in sarah_chunks}
    assert "DOC-MGR-001" in sarah_docs

    rahul_chunks = knowledge_service.search_authorized_knowledge(rahul, "manager playbook 1:1")
    rahul_docs = {c.document_id for c in rahul_chunks}
    assert "DOC-MGR-001" not in rahul_docs  # Manager doc must be omitted!


def test_role_level_clearance_hr_salary_doc():
    """
    HR Specialist (Amanda) can access HR salary bands.
    Regular employee (Rahul) CANNOT access HR salary bands.
    """
    amanda = SYNTHETIC_EMPLOYEES["EMP-2026-009"]  # HR
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]   # Employee

    amanda_chunks = knowledge_service.search_authorized_knowledge(amanda, "salary compensation bands")
    amanda_docs = {c.document_id for c in amanda_chunks}
    assert "DOC-HR-001" in amanda_docs

    rahul_chunks = knowledge_service.search_authorized_knowledge(rahul, "salary compensation bands")
    rahul_docs = {c.document_id for c in rahul_chunks}
    assert "DOC-HR-001" not in rahul_docs  # HR doc must be omitted!


def test_company_wide_docs_accessible_to_all():
    """Company-wide policies are accessible to all employees regardless of team."""
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    maya = SYNTHETIC_EMPLOYEES["EMP-2026-002"]

    chunks_rahul = knowledge_service.search_authorized_knowledge(rahul, "code of conduct")
    chunks_maya = knowledge_service.search_authorized_knowledge(maya, "code of conduct")

    assert any(c.document_id == "DOC-ALL-001" for c in chunks_rahul)
    assert any(c.document_id == "DOC-ALL-001" for c in chunks_maya)


def test_pre_retrieval_security_perimeter_stamping():
    """Verifies that formatted RAG context contains the mandatory security perimeter tag."""
    rahul = SYNTHETIC_EMPLOYEES["EMP-2026-001"]
    chunks = knowledge_service.search_authorized_knowledge(rahul, "payments")
    formatted = knowledge_service.format_chunks_for_context(rahul, chunks, "payments")

    assert "[ENFORCED_SECURITY_PERIMETER:" in formatted
    assert "employee_id=EMP-2026-001" in formatted
    assert "department=Engineering" in formatted
    assert "team=Payments" in formatted
    assert "clearance=employee" in formatted
