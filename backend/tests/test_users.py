"""User management endpoint tests (Plan 02-04).

Tests cover:
- Admin CRUD: create, list (with filters), get, update, deactivate/activate
- SM tenant-scoped management: create customer, update customer, restrictions
- Role enforcement: non-admin cannot access admin endpoints

Uses SQLite in-memory from conftest — no real DB needed.
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
    is_active: bool = True,
) -> User:
    user = User(
        email=email,
        hashed_password=hash_password(_TEST_PASS),
        role=role,
        email_verified=email_verified,
        is_active=is_active,
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return user


async def _create_tenant(
    db: AsyncSession,
    prefix: str = "TSTT",
    name: str = "Test Tenant",
    is_active: bool = True,
) -> Tenant:
    tenant = Tenant(
        prefix=prefix,
        name=name,
        config={"approval_gates": {"shortlist_submission": True, "rate_override": True}},
        is_active=is_active,
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
# Admin CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_admin_create_user(client: AsyncClient, db_session: AsyncSession):
    """Admin POST /users creates a user with specified role and tenant.
    Admin-created user has email_verified=True."""
    admin = await _create_user(db_session, "admin_cu@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="ACRT")
    await db_session.commit()
    headers = await _login(client, "admin_cu@example.com")

    resp = await client.post(
        "/api/users",
        json={
            "email": "newuser@example.com",
            "password": "P@ssword123",
            "role": "sm",
            "display_name": "New SM",
            "tenant_id": str(tenant.id),
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "sm"
    assert data["email_verified"] is True
    assert data["is_active"] is True
    assert data["tenant_id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_admin_create_user_customer_requires_tenant(
    client: AsyncClient, db_session: AsyncSession
):
    """POST /users with role='customer' and no tenant_id returns 400."""
    await _create_user(db_session, "admin_cust@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin_cust@example.com")

    resp = await client.post(
        "/api/users",
        json={"email": "cust@example.com", "password": "P@ssword123", "role": "customer"},
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert "tenant_id" in resp.text


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, db_session: AsyncSession):
    """Admin GET /users returns all users."""
    admin = await _create_user(db_session, "admin_list@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="ALST")
    await _create_user(db_session, "user1@example.com", "sm", tenant_id=tenant.id)
    await _create_user(db_session, "user2@example.com", "recruiter", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "admin_list@example.com")

    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 200, resp.text
    emails = [u["email"] for u in resp.json()]
    assert "user1@example.com" in emails
    assert "user2@example.com" in emails
    assert "admin_list@example.com" in emails


@pytest.mark.asyncio
async def test_admin_list_users_filter_by_role(client: AsyncClient, db_session: AsyncSession):
    """GET /users?role=customer returns only customers."""
    admin = await _create_user(db_session, "admin_filt@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="AFLT")
    await _create_user(db_session, "cust1@example.com", "customer", tenant_id=tenant.id)
    await _create_user(db_session, "sm1@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "admin_filt@example.com")

    resp = await client.get("/api/users?role=customer", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert all(u["role"] == "customer" for u in data)
    emails = [u["email"] for u in data]
    assert "cust1@example.com" in emails
    assert "sm1@example.com" not in emails


@pytest.mark.asyncio
async def test_admin_deactivate_user(client: AsyncClient, db_session: AsyncSession):
    """POST /users/{id}/deactivate sets is_active=False."""
    admin = await _create_user(db_session, "admin_deact@example.com", "admin")
    target = await _create_user(db_session, "target@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "admin_deact@example.com")

    resp = await client.post(f"/api/users/{target.id}/deactivate", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is False


@pytest.mark.asyncio
async def test_admin_activate_user(client: AsyncClient, db_session: AsyncSession):
    """POST /users/{id}/activate sets is_active=True."""
    admin = await _create_user(db_session, "admin_act@example.com", "admin")
    target = await _create_user(db_session, "target_act@example.com", "recruiter", is_active=False)
    await db_session.commit()
    headers = await _login(client, "admin_act@example.com")

    resp = await client.post(f"/api/users/{target.id}/activate", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["is_active"] is True


@pytest.mark.asyncio
async def test_admin_update_user_role(client: AsyncClient, db_session: AsyncSession):
    """PATCH /users/{id} with new role succeeds."""
    admin = await _create_user(db_session, "admin_upd@example.com", "admin")
    tenant = await _create_tenant(db_session, prefix="AUPD")
    target = await _create_user(db_session, "target_upd@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "admin_upd@example.com")

    resp = await client.patch(
        f"/api/users/{target.id}",
        json={"role": "recruiter"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "recruiter"


@pytest.mark.asyncio
async def test_admin_get_user(client: AsyncClient, db_session: AsyncSession):
    """Admin GET /users/{id} returns the user."""
    admin = await _create_user(db_session, "admin_get@example.com", "admin")
    target = await _create_user(db_session, "target_get@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "admin_get@example.com")

    resp = await client.get(f"/api/users/{target.id}", headers=headers)
    assert resp.status_code == 200, resp.text
    assert resp.json()["email"] == "target_get@example.com"


@pytest.mark.asyncio
async def test_admin_get_nonexistent_user_returns_404(client: AsyncClient, db_session: AsyncSession):
    """Admin GET /users/{random_id} returns 404."""
    await _create_user(db_session, "admin_404@example.com", "admin")
    await db_session.commit()
    headers = await _login(client, "admin_404@example.com")

    resp = await client.get(f"/api/users/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404, resp.text


# ---------------------------------------------------------------------------
# SM tenant-scoped tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_sm_create_customer_in_own_tenant(client: AsyncClient, db_session: AsyncSession):
    """SM POST /tenants/{id}/users with role=customer succeeds for assigned tenant."""
    tenant = await _create_tenant(db_session, prefix="SMCT")
    sm = await _create_user(db_session, "sm_create@example.com", "sm", tenant_id=tenant.id)
    # Create junction table assignment
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "sm_create@example.com")

    resp = await client.post(
        f"/api/tenants/{tenant.id}/users",
        json={
            "email": "newcust@example.com",
            "password": "P@ssword123",
            "role": "customer",
            "display_name": "New Customer",
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["role"] == "customer"
    assert data["tenant_id"] == str(tenant.id)
    assert data["email_verified"] is True


@pytest.mark.asyncio
async def test_sm_cannot_create_admin(client: AsyncClient, db_session: AsyncSession):
    """SM POST /tenants/{id}/users with role=admin returns 400."""
    tenant = await _create_tenant(db_session, prefix="SMNO")
    sm = await _create_user(db_session, "sm_noadmin@example.com", "sm", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "sm_noadmin@example.com")

    resp = await client.post(
        f"/api/tenants/{tenant.id}/users",
        json={
            "email": "badadmin@example.com",
            "password": "P@ssword123",
            "role": "admin",
        },
        headers=headers,
    )
    assert resp.status_code == 400, resp.text
    assert "customer" in resp.text.lower()


@pytest.mark.asyncio
async def test_sm_cannot_create_in_unassigned_tenant(client: AsyncClient, db_session: AsyncSession):
    """SM POST /tenants/{other_id}/users returns 403 when SM is not assigned to that tenant."""
    tenant1 = await _create_tenant(db_session, prefix="SMAS")
    tenant2 = await _create_tenant(db_session, prefix="SMUN")
    sm = await _create_user(db_session, "sm_unassigned@example.com", "sm", tenant_id=tenant1.id)
    # Assign SM to tenant1 only
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant1.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "sm_unassigned@example.com")

    # Try to create in tenant2 (not assigned)
    resp = await client.post(
        f"/api/tenants/{tenant2.id}/users",
        json={
            "email": "wrongtenant@example.com",
            "password": "P@ssword123",
            "role": "customer",
        },
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_sm_update_customer_display_name(client: AsyncClient, db_session: AsyncSession):
    """SM PATCH /tenants/{id}/users/{user_id} updates display_name of customer."""
    tenant = await _create_tenant(db_session, prefix="SMUP")
    sm = await _create_user(db_session, "sm_update@example.com", "sm", tenant_id=tenant.id)
    customer = await _create_user(db_session, "cust_upd@example.com", "customer", tenant_id=tenant.id)
    assignment = UserTenantAssignment(user_id=sm.id, tenant_id=tenant.id)
    db_session.add(assignment)
    await db_session.commit()
    headers = await _login(client, "sm_update@example.com")

    resp = await client.patch(
        f"/api/tenants/{tenant.id}/users/{customer.id}",
        json={"display_name": "Updated Name"},
        headers=headers,
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["display_name"] == "Updated Name"


# ---------------------------------------------------------------------------
# Role restriction tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_recruiter_cannot_manage_users(client: AsyncClient, db_session: AsyncSession):
    """Recruiter POST /users returns 403."""
    await _create_user(db_session, "recruiter_block@example.com", "recruiter")
    await db_session.commit()
    headers = await _login(client, "recruiter_block@example.com")

    resp = await client.post(
        "/api/users",
        json={"email": "x@example.com", "password": "P@ssword123", "role": "candidate"},
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_candidate_cannot_manage_users(client: AsyncClient, db_session: AsyncSession):
    """Candidate GET /users returns 403."""
    await _create_user(db_session, "candidate_block@example.com", "candidate")
    await db_session.commit()
    headers = await _login(client, "candidate_block@example.com")

    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_sm_cannot_access_admin_list_users(client: AsyncClient, db_session: AsyncSession):
    """SM GET /users returns 403 (admin-only endpoint)."""
    tenant = await _create_tenant(db_session, prefix="SMLS")
    sm = await _create_user(db_session, "sm_list@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client, "sm_list@example.com")

    resp = await client.get("/api/users", headers=headers)
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_unauthenticated_user_management_returns_401(client: AsyncClient):
    """Unauthenticated GET /api/users returns 401 or 403."""
    resp = await client.get("/api/users")
    assert resp.status_code in (401, 403), resp.text
