"""Approval chain and audit log endpoint tests (Plan 02-04).

Tests cover:
- Approval request creation (POST /approvals)
- Approval decisions: approve, reject, changes_requested
- Authorization: only assigned approver or Admin can decide
- Audit log: every decision creates an audit_log entry
- Audit log query: Admin-only, filterable
- Visibility scoping: SM sees only their approvals, Recruiter sees own requests

Uses SQLite in-memory from conftest — no real DB needed.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenantAssignment
from app.services.auth import hash_password

_TEST_PASS = "T3stPassw0rd"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_user(
    db: AsyncSession,
    email: str,
    role: str,
    tenant_id: uuid.UUID | None = None,
    email_verified: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(_TEST_PASS),
        role=role,
        email_verified=email_verified,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_tenant(
    db: AsyncSession,
    prefix: str = "APPT",
    name: str = "Approval Tenant",
    config: dict | None = None,
) -> Tenant:
    tenant = Tenant(
        prefix=prefix,
        name=name,
        config=config or {"approval_gates": {"shortlist_submission": True, "rate_override": True}},
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def _login(client: AsyncClient, email: str) -> dict:
    resp = await client.post("/api/auth/login", json={"email": email, "password": _TEST_PASS})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


# ---------------------------------------------------------------------------
# Create approval request
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_approval_request(client: AsyncClient, db_session: AsyncSession):
    """Recruiter creates an approval request — returns 201 with status=pending."""
    tenant = await _create_tenant(db_session, prefix="CAPPR")
    sm = await _create_user(db_session, "sm_approver@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_create@example.com", "recruiter", tenant_id=tenant.id)
    # Assign SM to tenant so route_approval can find them
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "rec_create@example.com")

    resp = await client.post(
        "/api/approvals",
        json={
            "type": "shortlist_submission",
            "justification": "Candidate meets all requirements",
            "context_data": {"candidate_id": str(uuid.uuid4()), "demand_id": str(uuid.uuid4())},
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "pending"
    assert data["type"] == "shortlist_submission"
    assert data["requester_id"] == str(recruiter.id)
    assert data["justification"] == "Candidate meets all requirements"


@pytest.mark.asyncio
async def test_create_approval_request_invalid_type(client: AsyncClient, db_session: AsyncSession):
    """Creating approval request with invalid type returns 422."""
    tenant = await _create_tenant(db_session, prefix="BADT")
    recruiter = await _create_user(db_session, "rec_bad_type@example.com", "recruiter", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "rec_bad_type@example.com")

    resp = await client.post(
        "/api/approvals",
        json={
            "type": "invalid_type",
            "justification": "Some reason",
        },
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


# ---------------------------------------------------------------------------
# Approval decisions
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approve_request(client: AsyncClient, db_session: AsyncSession):
    """SM decides to approve — status changes to 'approved' and decided_at is set."""
    tenant = await _create_tenant(db_session, prefix="APPR")
    sm = await _create_user(db_session, "sm_decide@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_decide@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_decide@example.com")
    sm_headers = await _login(client, "sm_decide@example.com")

    # Create approval request
    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Qualified candidate"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201, create_resp.text
    approval_id = create_resp.json()["id"]

    # SM decides to approve
    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Looks good"},
        headers=sm_headers,
    )
    assert decide_resp.status_code == 200, decide_resp.text
    data = decide_resp.json()
    assert data["status"] == "approved"
    assert data["decision_reason"] == "Looks good"
    assert data["decided_at"] is not None


@pytest.mark.asyncio
async def test_reject_request(client: AsyncClient, db_session: AsyncSession):
    """SM rejects approval request — status changes to 'rejected'."""
    tenant = await _create_tenant(db_session, prefix="REJT")
    sm = await _create_user(db_session, "sm_reject@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_reject@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_reject@example.com")
    sm_headers = await _login(client, "sm_reject@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "rejected", "decision_reason": "Does not meet requirements"},
        headers=sm_headers,
    )
    assert decide_resp.status_code == 200, decide_resp.text
    assert decide_resp.json()["status"] == "rejected"


@pytest.mark.asyncio
async def test_request_changes(client: AsyncClient, db_session: AsyncSession):
    """SM requests changes — status changes to 'changes_requested'."""
    tenant = await _create_tenant(db_session, prefix="CHNG")
    sm = await _create_user(db_session, "sm_changes@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_changes@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_changes@example.com")
    sm_headers = await _login(client, "sm_changes@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "changes_requested", "decision_reason": "Please update the rate"},
        headers=sm_headers,
    )
    assert decide_resp.status_code == 200, decide_resp.text
    assert decide_resp.json()["status"] == "changes_requested"


# ---------------------------------------------------------------------------
# Authorization tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_non_approver_cannot_decide(client: AsyncClient, db_session: AsyncSession):
    """Recruiter tries to decide on their own request — returns 403."""
    tenant = await _create_tenant(db_session, prefix="FRBD")
    sm = await _create_user(db_session, "sm_forbid@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_forbid@example.com", "recruiter", tenant_id=tenant.id)
    other_recruiter = await _create_user(db_session, "rec_other@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_forbid@example.com")
    other_headers = await _login(client, "rec_other@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    # Recruiter (requester) tries to decide — forbidden
    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Self-approve attempt"},
        headers=rec_headers,
    )
    assert decide_resp.status_code == 403, decide_resp.text


@pytest.mark.asyncio
async def test_admin_can_decide_any_approval(client: AsyncClient, db_session: AsyncSession):
    """Admin can decide on any approval regardless of approver_id."""
    tenant = await _create_tenant(db_session, prefix="ADMD")
    admin = await _create_user(db_session, "admin_decide@example.com", "admin")
    sm = await _create_user(db_session, "sm_admd@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_admd@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_admd@example.com")
    admin_headers = await _login(client, "admin_decide@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    # Admin decides
    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Admin override"},
        headers=admin_headers,
    )
    assert decide_resp.status_code == 200, decide_resp.text
    assert decide_resp.json()["status"] == "approved"


# ---------------------------------------------------------------------------
# Audit log tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approval_decision_creates_audit_log(client: AsyncClient, db_session: AsyncSession):
    """After approval decision, an audit_log entry exists with correct action and payload."""
    tenant = await _create_tenant(db_session, prefix="AUDT")
    admin = await _create_user(db_session, "admin_audit@example.com", "admin")
    sm = await _create_user(db_session, "sm_audit@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_audit@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_audit@example.com")
    sm_headers = await _login(client, "sm_audit@example.com")
    admin_headers = await _login(client, "admin_audit@example.com")

    # Create and approve
    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Audit test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    decide_resp = await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "approved", "decision_reason": "Audit test decision"},
        headers=sm_headers,
    )
    assert decide_resp.status_code == 200

    # Query audit log as Admin
    audit_resp = await client.get("/api/audit-log", headers=admin_headers)
    assert audit_resp.status_code == 200, audit_resp.text
    entries = audit_resp.json()

    # Find the approval.approved entry
    approved_entries = [e for e in entries if e["action"] == "approval.approved"]
    assert len(approved_entries) >= 1
    entry = approved_entries[0]
    assert entry["entity_type"] == "approval_request"
    assert entry["entity_id"] == approval_id
    assert "decision_reason" in entry["payload"]
    assert entry["payload"]["decision_reason"] == "Audit test decision"


@pytest.mark.asyncio
async def test_audit_log_admin_query(client: AsyncClient, db_session: AsyncSession):
    """Admin GET /audit-log returns entries; filter by action works."""
    tenant = await _create_tenant(db_session, prefix="AUDQ")
    admin = await _create_user(db_session, "admin_audq@example.com", "admin")
    sm = await _create_user(db_session, "sm_audq@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_audq@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_audq@example.com")
    sm_headers = await _login(client, "sm_audq@example.com")
    admin_headers = await _login(client, "admin_audq@example.com")

    # Create an approval to generate audit entries
    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Query test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    await client.post(
        f"/api/approvals/{approval_id}/decide",
        json={"status": "rejected", "decision_reason": "Not suitable"},
        headers=sm_headers,
    )

    # Query with action filter
    resp = await client.get("/api/audit-log?action=approval.rejected", headers=admin_headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert len(data) >= 1
    assert all(e["action"] == "approval.rejected" for e in data)


@pytest.mark.asyncio
async def test_non_admin_cannot_query_audit_log(client: AsyncClient, db_session: AsyncSession):
    """Recruiter GET /audit-log returns 403."""
    await _create_user(db_session, "rec_nolog@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "rec_nolog@example.com")

    resp = await client.get("/api/audit-log", headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_sm_cannot_query_audit_log(client: AsyncClient, db_session: AsyncSession):
    """SM GET /audit-log returns 403 (Admin only)."""
    tenant = await _create_tenant(db_session, prefix="SMLOG")
    sm = await _create_user(db_session, "sm_nolog@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "sm_nolog@example.com")

    resp = await client.get("/api/audit-log", headers=headers)
    assert resp.status_code == 403, resp.text


# ---------------------------------------------------------------------------
# Visibility scoping tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_list_approvals_as_sm_sees_only_own(client: AsyncClient, db_session: AsyncSession):
    """SM sees only approvals where they are the approver."""
    tenant = await _create_tenant(db_session, prefix="SMVS")
    sm1 = await _create_user(db_session, "sm_vis1@example.com", "sm", tenant_id=tenant.id)
    sm2 = await _create_user(db_session, "sm_vis2@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_vis@example.com", "recruiter", tenant_id=tenant.id)
    assignment1 = UserTenantAssignment(user_id=sm1.id, tenant_id=tenant.id)
    assignment2 = UserTenantAssignment(user_id=sm2.id, tenant_id=tenant.id)
    db_session.add(assignment1)
    db_session.add(assignment2)
    await db_session.commit()
    rec_headers = await _login(client, "rec_vis@example.com")
    sm1_headers = await _login(client, "sm_vis1@example.com")

    # Create approval — routed to SM1 (first SM in tenant)
    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Visibility test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_data = create_resp.json()

    # SM1 lists approvals — sees the approval where they are approver
    list_resp = await client.get("/api/approvals", headers=sm1_headers)
    assert list_resp.status_code == 200, list_resp.text
    sm1_approvals = list_resp.json()
    # All returned approvals should have approver_id = sm1.id
    for a in sm1_approvals:
        assert a["approver_id"] == str(sm1.id)


@pytest.mark.asyncio
async def test_list_approvals_as_recruiter_sees_only_own_requests(
    client: AsyncClient, db_session: AsyncSession
):
    """Recruiter sees only their own approval requests."""
    tenant = await _create_tenant(db_session, prefix="RVST")
    sm = await _create_user(db_session, "sm_rvis@example.com", "sm", tenant_id=tenant.id)
    recruiter1 = await _create_user(db_session, "rec_rvis1@example.com", "recruiter", tenant_id=tenant.id)
    recruiter2 = await _create_user(db_session, "rec_rvis2@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec1_headers = await _login(client, "rec_rvis1@example.com")
    rec2_headers = await _login(client, "rec_rvis2@example.com")

    # Recruiter1 creates an approval
    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Recruiter visibility test"},
        headers=rec1_headers,
    )
    assert create_resp.status_code == 201
    rec1_approval_id = create_resp.json()["id"]

    # Recruiter1 lists — sees only own requests
    list_resp = await client.get("/api/approvals", headers=rec1_headers)
    assert list_resp.status_code == 200, list_resp.text
    ids = [a["id"] for a in list_resp.json()]
    assert rec1_approval_id in ids
    for a in list_resp.json():
        assert a["requester_id"] == str(recruiter1.id)

    # Recruiter2 lists — sees zero (they made no requests)
    list_resp2 = await client.get("/api/approvals", headers=rec2_headers)
    assert list_resp2.status_code == 200, list_resp2.text
    assert len(list_resp2.json()) == 0


@pytest.mark.asyncio
async def test_get_approval_by_requester(client: AsyncClient, db_session: AsyncSession):
    """Requester can view their own approval request by ID."""
    tenant = await _create_tenant(db_session, prefix="GTAR")
    sm = await _create_user(db_session, "sm_gtar@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_gtar@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_gtar@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Get test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/approvals/{approval_id}", headers=rec_headers)
    assert get_resp.status_code == 200, get_resp.text
    assert get_resp.json()["id"] == approval_id


@pytest.mark.asyncio
async def test_unauthorized_user_cannot_view_approval(client: AsyncClient, db_session: AsyncSession):
    """User who is neither requester, approver, nor Admin gets 403."""
    tenant = await _create_tenant(db_session, prefix="UNAR")
    sm = await _create_user(db_session, "sm_unar@example.com", "sm", tenant_id=tenant.id)
    recruiter = await _create_user(db_session, "rec_unar@example.com", "recruiter", tenant_id=tenant.id)
    other_recruiter = await _create_user(db_session, "rec_other2@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    rec_headers = await _login(client, "rec_unar@example.com")
    other_headers = await _login(client, "rec_other2@example.com")

    create_resp = await client.post(
        "/api/approvals",
        json={"type": "shortlist_submission", "justification": "Unauthorized test"},
        headers=rec_headers,
    )
    assert create_resp.status_code == 201
    approval_id = create_resp.json()["id"]

    # Other recruiter (not requester or approver) tries to view
    get_resp = await client.get(f"/api/approvals/{approval_id}", headers=other_headers)
    assert get_resp.status_code == 403, get_resp.text
