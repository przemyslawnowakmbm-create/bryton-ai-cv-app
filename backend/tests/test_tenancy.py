"""Tenant CRUD and RBAC enforcement tests.

Tests use the SQLite-based test setup from conftest.py (in-memory, fast).
RLS is PostgreSQL-specific and cannot be tested here — these tests verify
the APPLICATION-LEVEL behavior: role checks, CRUD operations, prefix validation,
and multi-tenant user assignment.

KNOWN GAP — RLS enforcement (TENANT-02, TENANT-04):
RLS isolation is enforced by PostgreSQL policies in migration 003. The SQLite
test suite cannot verify that `SET LOCAL app.current_tenant` actually filters
rows or that bryton_app is restricted by RLS policies.

Manual RLS verification steps (after `docker compose up -d && alembic upgrade head`):
    1. Connect as bryton_app: psql -U bryton_app -d bryton_ai
    2. SET LOCAL app.current_tenant = '<tenant-uuid>';
    3. SELECT * FROM users;  -- should only return users for that tenant
    4. Without SET LOCAL: SELECT * FROM users;  -- should return no rows (NULL tenant + FORCE RLS)
    5. As superuser: SELECT * FROM users;  -- returns all rows (superuser bypasses RLS)

Future improvement: Add docker-based integration tests using testcontainers-python.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenantAssignment
from app.services.auth import hash_password

# Test credentials — not real passwords
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
    """Create and persist a user with the given role."""
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
    prefix: str = "ECTL",
    name: str = "Eccleston Co.",
) -> Tenant:
    """Create and persist a tenant."""
    tenant = Tenant(
        prefix=prefix,
        name=name,
        config={"approval_gates": {"shortlist_submission": True, "rate_override": True}},
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


async def _login(client: AsyncClient, email: str, password: str = _TEST_PASS) -> dict:
    """Login and return auth headers dict."""
    resp = await client.post(
        "/api/auth/login",
        json={"email": email, "password": password},
    )
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    token = resp.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Tenant CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_tenant_as_admin(client: AsyncClient, db_session: AsyncSession):
    """Admin can create a tenant with a valid 2-6 char prefix."""
    await _create_user(db_session, "admin@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "ECTL", "name": "Eccleston Co."},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["prefix"] == "ECTL"
    assert data["name"] == "Eccleston Co."
    assert data["is_active"] is True
    assert "id" in data
    assert "config" in data
    # Default config should include approval_gates
    assert data["config"]["approval_gates"]["shortlist_submission"] is True


@pytest.mark.asyncio
async def test_create_tenant_as_non_admin_returns_403(client: AsyncClient, db_session: AsyncSession):
    """Non-admin (recruiter) cannot create a tenant — returns 403."""
    await _create_user(db_session, "recruiter@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "recruiter@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "ECTL", "name": "Eccleston Co."},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_create_tenant_duplicate_prefix_returns_409(client: AsyncClient, db_session: AsyncSession):
    """Creating a second tenant with the same prefix returns 409."""
    await _create_user(db_session, "admin2@example.com", "admin")
    await _create_tenant(db_session, prefix="DUPL")
    await db_session.commit()
    headers = await _login(client, "admin2@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "DUPL", "name": "Duplicate Co."},
        headers=headers,
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_create_tenant_invalid_prefix_too_short(client: AsyncClient, db_session: AsyncSession):
    """Prefix 'X' (1 char) is too short — returns 422."""
    await _create_user(db_session, "admin3@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin3@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "X", "name": "Short Prefix"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_tenant_invalid_prefix_too_long(client: AsyncClient, db_session: AsyncSession):
    """Prefix 'TOOLONG' (7 chars) is too long — returns 422."""
    await _create_user(db_session, "admin4@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin4@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "TOOLONG", "name": "Long Prefix"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_tenant_invalid_prefix_lowercase(client: AsyncClient, db_session: AsyncSession):
    """Prefix with lowercase 'ec1' is invalid — returns 422."""
    await _create_user(db_session, "admin5@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin5@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "ec1", "name": "Lowercase Prefix"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_create_tenant_invalid_prefix_special_chars(client: AsyncClient, db_session: AsyncSession):
    """Prefix with special chars 'EC-1' is invalid — returns 422."""
    await _create_user(db_session, "admin6@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin6@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "EC-1", "name": "Special Prefix"},
        headers=headers,
    )
    assert resp.status_code == 422, resp.text


@pytest.mark.asyncio
async def test_list_tenants_as_admin(client: AsyncClient, db_session: AsyncSession):
    """Admin can list all tenants."""
    await _create_user(db_session, "admin7@example.com", "admin")
    await _create_tenant(db_session, prefix="LIST", name="Listable Co.")
    await db_session.commit()
    headers = await _login(client, "admin7@example.com")

    resp = await client.get("/api/tenants", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1
    prefixes = [t["prefix"] for t in data]
    assert "LIST" in prefixes


@pytest.mark.asyncio
async def test_get_single_tenant(client: AsyncClient, db_session: AsyncSession):
    """Admin can get a single tenant by ID."""
    await _create_user(db_session, "admin8@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="SING", name="Single Co.")
    await db_session.commit()
    headers = await _login(client, "admin8@example.com")

    resp = await client.get(f"/api/tenants/{tenant.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["prefix"] == "SING"


@pytest.mark.asyncio
async def test_get_nonexistent_tenant_returns_404(client: AsyncClient, db_session: AsyncSession):
    """Fetching a nonexistent tenant ID returns 404."""
    await _create_user(db_session, "admin9@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin9@example.com")

    fake_id = uuid.uuid4()
    resp = await client.get(f"/api/tenants/{fake_id}", headers=headers)
    assert resp.status_code == 404, resp.text


@pytest.mark.asyncio
async def test_deactivate_tenant(client: AsyncClient, db_session: AsyncSession):
    """Admin can deactivate a tenant — is_active becomes False."""
    await _create_user(db_session, "admin10@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="DACT", name="Deactivate Co.")
    await db_session.commit()
    headers = await _login(client, "admin10@example.com")

    resp = await client.post(f"/api/tenants/{tenant.id}/deactivate", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False


@pytest.mark.asyncio
async def test_activate_tenant(client: AsyncClient, db_session: AsyncSession):
    """Admin can re-activate a deactivated tenant — is_active becomes True."""
    await _create_user(db_session, "admin11@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="ACTV", name="Activate Co.")
    tenant.is_active = False  # start deactivated
    await db_session.flush()
    await db_session.commit()
    headers = await _login(client, "admin11@example.com")

    resp = await client.post(f"/api/tenants/{tenant.id}/activate", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is True


# ---------------------------------------------------------------------------
# User-tenant assignment tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_assign_user_to_tenant(client: AsyncClient, db_session: AsyncSession):
    """Admin can assign an SM user to a tenant; GET /users shows the SM."""
    admin = await _create_user(db_session, "admin12@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="ASGN", name="Assign Co.")
    sm_user = await _create_user(db_session, "sm@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "admin12@example.com")

    # Assign SM to tenant
    resp = await client.post(
        f"/api/tenants/{tenant.id}/assign-user",
        json={"user_id": str(sm_user.id)},
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["user_id"] == str(sm_user.id)
    assert data["tenant_id"] == str(tenant.id)

    # List tenant users — SM should appear
    list_resp = await client.get(f"/api/tenants/{tenant.id}/users", headers=headers)
    assert list_resp.status_code == 200, list_resp.text
    user_emails = [u["email"] for u in list_resp.json()]
    assert "sm@example.com" in user_emails


@pytest.mark.asyncio
async def test_assign_duplicate_returns_409(client: AsyncClient, db_session: AsyncSession):
    """Assigning the same SM to a tenant twice returns 409."""
    admin = await _create_user(db_session, "admin13@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="DUPM", name="Dup Map Co.")
    sm_user = await _create_user(db_session, "sm2@example.com", "sm", tenant_id=tenant.id)
    # Pre-create the assignment
    assignment = UserTenantAssignment(user_id=sm_user.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "admin13@example.com")

    resp = await client.post(
        f"/api/tenants/{tenant.id}/assign-user",
        json={"user_id": str(sm_user.id)},
        headers=headers,
    )
    assert resp.status_code == 409, resp.text


@pytest.mark.asyncio
async def test_assign_non_sm_recruiter_returns_400(client: AsyncClient, db_session: AsyncSession):
    """Assigning a Customer user via junction table returns 400."""
    admin = await _create_user(db_session, "admin14@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="CUST", name="Customer Co.")
    customer = await _create_user(db_session, "customer@example.com", "customer", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "admin14@example.com")

    resp = await client.post(
        f"/api/tenants/{tenant.id}/assign-user",
        json={"user_id": str(customer.id)},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text


@pytest.mark.asyncio
async def test_remove_user_from_tenant(client: AsyncClient, db_session: AsyncSession):
    """Admin can remove a user's tenant assignment — returns 204."""
    admin = await _create_user(db_session, "admin15@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="RMV1", name="Remove Co.")
    recruiter = await _create_user(db_session, "recruiter2@example.com", "recruiter", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=recruiter.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "admin15@example.com")

    resp = await client.delete(
        f"/api/tenants/{tenant.id}/assign-user/{recruiter.id}",
        headers=headers,
    )
    assert resp.status_code == 204, resp.text


# ---------------------------------------------------------------------------
# RBAC enforcement tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_require_roles_returns_403_for_recruiter(client: AsyncClient, db_session: AsyncSession):
    """Recruiter cannot access admin-only POST /tenants — returns 403."""
    await _create_user(db_session, "rbac_recruiter@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "rbac_recruiter@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "RBAC", "name": "RBAC Test"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_candidate_cannot_access_tenant_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Candidate attempting GET /api/tenants returns 403."""
    await _create_user(db_session, "candidate@example.com", "candidate")
    await db_session.commit()
    headers = await _login(client, "candidate@example.com")

    resp = await client.get("/api/tenants", headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_customer_cannot_access_tenant_endpoints(client: AsyncClient, db_session: AsyncSession):
    """Customer attempting GET /api/tenants returns 403."""
    await _create_user(db_session, "customer2@example.com", "customer")
    await db_session.commit()
    headers = await _login(client, "customer2@example.com")

    resp = await client.get("/api/tenants", headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_sm_cannot_create_tenant(client: AsyncClient, db_session: AsyncSession):
    """SM attempting POST /api/tenants returns 403."""
    await _create_user(db_session, "sm3@example.com", "sm")
    await db_session.commit()
    headers = await _login(client, "sm3@example.com")

    resp = await client.post(
        "/api/tenants",
        json={"prefix": "SMNO", "name": "SM No"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_unauthenticated_access_returns_401(client: AsyncClient):
    """Unauthenticated request to /api/tenants returns 401 or 403."""
    resp = await client.get("/api/tenants")
    # FastAPI HTTPBearer returns 403 when no token is provided with auto_error=False
    assert resp.status_code in (401, 403), resp.text


@pytest.mark.asyncio
async def test_update_tenant_as_admin(client: AsyncClient, db_session: AsyncSession):
    """Admin can update tenant name via PATCH."""
    await _create_user(db_session, "admin16@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="UPDT", name="Original Name")
    await db_session.commit()
    headers = await _login(client, "admin16@example.com")

    resp = await client.patch(
        f"/api/tenants/{tenant.id}",
        json={"name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Updated Name"
    # Prefix must remain unchanged
    assert resp.json()["prefix"] == "UPDT"
