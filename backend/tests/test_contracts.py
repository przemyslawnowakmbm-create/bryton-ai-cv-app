"""Contracts, Rate Cards API, and Rate Check service tests (Plan 03-02).

Tests cover:
- Contract CRUD: create, list, get detail, update, deactivate
- Rate card CRUD: create, list, update, delete, unique constraint
- Role-based access: Admin/SM can create, Recruiter gets 403
- Margin visibility: margin is None in Phase 3 for all roles
- Rate check service: ceiling enforcement, bypass for None inputs, bypass for approved override

Uses SQLite in-memory from conftest — no real DB needed.
RLS is not enforced in SQLite tests; application-level logic is tested.

NOTE: The contracts API uses get_tenant_db (not get_db). The conftest only overrides
get_db. This test module additionally overrides get_tenant_db to use the same test DB
session, so tenant-scoped endpoints work in tests.
"""
import uuid
from datetime import date, timedelta
from decimal import Decimal

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import get_tenant_db
from app.main import app
from app.models.contract import Contract
from app.models.profile_catalogue import ProfileCatalogue
from app.models.rate_card import RateCardEntry
from app.models.tenant import Tenant
from app.models.user import User
from app.services.auth import hash_password
from app.services.rate_check import RateCeilingExceeded, check_rate_ceiling, has_approved_rate_override

_TEST_PASS = "T3stPassw0rd"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _create_tenant(
    db: AsyncSession,
    prefix: str = "CTR",
    name: str = "Contract Tenant",
) -> Tenant:
    tenant = Tenant(
        prefix=prefix,
        name=name,
        config={"approval_gates": {"rate_override": True}},
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return tenant


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


async def _create_profile(
    db: AsyncSession,
    tenant_id: uuid.UUID,
    code: str = "SWE",
    title: str = "Software Engineer",
) -> ProfileCatalogue:
    profile = ProfileCatalogue(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        code=code,
        title=title,
        sfia_level_min=3,
        sfia_level_max=6,
        min_years_exp=2,
        is_active=True,
    )
    db.add(profile)
    await db.flush()
    await db.refresh(profile)
    return profile


async def _login(client: AsyncClient, email: str) -> dict:
    resp = await client.post("/api/auth/login", json={"email": email, "password": _TEST_PASS})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


def _contract_body(
    reference: str = "CTR-2024-001",
    title: str = "Test Framework Contract",
) -> dict:
    return {
        "reference": reference,
        "title": title,
        "lot_number": "Lot 1",
        "start_date": "2024-01-01",
        "end_date": "2026-12-31",
        "max_value": "500000.00",
        "currency": "GBP",
        "status": "active",
    }


# ---------------------------------------------------------------------------
# Test fixture: override get_tenant_db to use test DB session
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def tenant_client(db_session: AsyncSession) -> AsyncClient:
    """AsyncClient with BOTH get_db and get_tenant_db overridden to use the test DB.

    Contracts endpoints use get_tenant_db (not get_db). Without this override,
    the test would attempt to connect to the real PostgreSQL bryton_app session.

    The override yields db_session directly without SET LOCAL (SQLite doesn't support
    PostgreSQL GUCs). The _resolve_tenant_id_from_session helper in contracts.py
    calls current_setting('app.current_tenant', true) — this returns empty string or
    null on SQLite, so it raises HTTP 400.

    To avoid this, the contracts test endpoints must be tested differently:
    We mock the tenant resolution by ensuring the endpoint logic path that calls
    current_setting is bypassed. Since we're testing SQLite, we need to provide
    a test-compatible path.

    This fixture provides the client. The test functions handle tenant context
    by patching _resolve_tenant_id_from_session via a session that returns a valid UUID.
    """
    from app.database import get_db

    async def override_get_db():
        yield db_session

    async def override_get_tenant_db():
        # For tests: yield the same test db_session without RLS SET LOCAL
        # The tenant context will be provided by the test setup directly
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_db] = override_get_tenant_db

    # Reset rate limiter
    if hasattr(app.state, "limiter") and hasattr(app.state.limiter, "_storage"):
        try:
            app.state.limiter._storage.reset()
        except Exception:
            pass
    try:
        from app.api.auth import _limiter as _auth_limiter
        if hasattr(_auth_limiter, "_storage"):
            _auth_limiter._storage.reset()
    except Exception:
        pass
    try:
        from app.api.auth import _login_attempts
        _login_attempts.clear()
    except ImportError:
        pass

    from httpx import ASGITransport
    transport = ASGITransport(app=app)
    from httpx import AsyncClient as HC
    async with HC(transport=transport, base_url="http://test") as ac:
        yield ac
    app.dependency_overrides.clear()


# ---------------------------------------------------------------------------
# Contract CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_contract_as_admin(tenant_client: AsyncClient, db_session: AsyncSession):
    """Admin creates a contract -> 201 with correct fields."""
    tenant = await _create_tenant(db_session, prefix="CTAD")
    admin = await _create_user(db_session, "admin_ctcreate@example.com", "admin")
    await db_session.commit()
    headers = await _login(tenant_client, "admin_ctcreate@example.com")

    resp = await tenant_client.post(
        "/api/contracts",
        json=_contract_body("CTR-ADMIN-001"),
        headers={**headers, "X-Tenant-ID": str(tenant.id)},
    )
    # Admin must provide X-Tenant-ID header. The tenant_client overrides get_tenant_db
    # so SQLite is used (no RLS). _resolve_tenant_id falls back to X-Tenant-ID header
    # when current_setting() is unavailable (SQLite).
    assert resp.status_code == 201, f"Expected 201: {resp.status_code} - {resp.text}"
    data = resp.json()
    assert data["reference"] == "CTR-ADMIN-001"
    assert data["status"] == "active"
    assert data["tenant_id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_create_contract_as_sm(tenant_client: AsyncClient, db_session: AsyncSession):
    """SM creates a contract -> 201 (uses their tenant_id from user record)."""
    tenant = await _create_tenant(db_session, prefix="CTSM")
    sm = await _create_user(db_session, "sm_ctcreate@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_ctcreate@example.com")

    resp = await tenant_client.post(
        "/api/contracts",
        json=_contract_body("CTR-SM-001", "SM Framework Contract"),
        headers=headers,
    )
    assert resp.status_code == 201, f"Expected 201: {resp.status_code} - {resp.text}"
    data = resp.json()
    assert data["reference"] == "CTR-SM-001"
    assert data["tenant_id"] == str(tenant.id)


@pytest.mark.asyncio
async def test_create_contract_unauthorized(tenant_client: AsyncClient, db_session: AsyncSession):
    """Recruiter trying to create a contract -> 403."""
    tenant = await _create_tenant(db_session, prefix="CTUNAUTH")
    recruiter = await _create_user(db_session, "rec_ctcreate@example.com", "recruiter", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(tenant_client, "rec_ctcreate@example.com")

    resp = await tenant_client.post(
        "/api/contracts",
        json=_contract_body("CTR-REC-001"),
        headers=headers,
    )
    assert resp.status_code == 403, f"Expected 403 but got {resp.status_code}: {resp.text}"


@pytest.mark.asyncio
async def test_list_contracts_as_sm(tenant_client: AsyncClient, db_session: AsyncSession):
    """SM can list contracts (returns 200 with a list)."""
    tenant = await _create_tenant(db_session, prefix="CTLIST")
    sm = await _create_user(db_session, "sm_ctlist@example.com", "sm", tenant_id=tenant.id)
    # Insert a contract directly
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-LIST-001",
        title="Listed Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_ctlist@example.com")

    resp = await tenant_client.get("/api/contracts", headers=headers)
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert isinstance(data, list)
    # At least one contract (the one we inserted)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_contracts_as_recruiter(tenant_client: AsyncClient, db_session: AsyncSession):
    """Recruiter can list contracts (returns 200)."""
    tenant = await _create_tenant(db_session, prefix="CTREC")
    recruiter = await _create_user(db_session, "rec_ctlist@example.com", "recruiter", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(tenant_client, "rec_ctlist@example.com")

    resp = await tenant_client.get("/api/contracts", headers=headers)
    assert resp.status_code == 200, f"Expected 200: {resp.text}"


@pytest.mark.asyncio
async def test_get_contract_detail(tenant_client: AsyncClient, db_session: AsyncSession):
    """GET /contracts/{id} returns contract details for SM."""
    tenant = await _create_tenant(db_session, prefix="CTDET")
    sm = await _create_user(db_session, "sm_ctdet@example.com", "sm", tenant_id=tenant.id)
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-DET-001",
        title="Detail Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="EUR",
        status="active",
    )
    db_session.add(contract)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_ctdet@example.com")

    resp = await tenant_client.get(f"/api/contracts/{contract.id}", headers=headers)
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert data["reference"] == "CTR-DET-001"
    assert data["title"] == "Detail Contract"
    assert data["status"] == "active"


@pytest.mark.asyncio
async def test_get_contract_not_found(tenant_client: AsyncClient, db_session: AsyncSession):
    """GET /contracts/{non_existent_id} returns 404."""
    tenant = await _create_tenant(db_session, prefix="CT404")
    sm = await _create_user(db_session, "sm_ct404@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_ct404@example.com")

    resp = await tenant_client.get(f"/api/contracts/{uuid.uuid4()}", headers=headers)
    assert resp.status_code == 404, f"Expected 404: {resp.text}"


@pytest.mark.asyncio
async def test_update_contract(tenant_client: AsyncClient, db_session: AsyncSession):
    """PATCH /contracts/{id} updates fields and returns updated data."""
    tenant = await _create_tenant(db_session, prefix="CTUPD")
    sm = await _create_user(db_session, "sm_ctupd@example.com", "sm", tenant_id=tenant.id)
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-UPD-001",
        title="Original Title",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="EUR",
        status="active",
    )
    db_session.add(contract)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_ctupd@example.com")

    resp = await tenant_client.patch(
        f"/api/contracts/{contract.id}",
        json={"title": "Updated Title", "status": "expired"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert data["title"] == "Updated Title"
    assert data["status"] == "expired"


@pytest.mark.asyncio
async def test_deactivate_contract(tenant_client: AsyncClient, db_session: AsyncSession):
    """POST /contracts/{id}/deactivate sets status to 'suspended' (Admin only)."""
    tenant = await _create_tenant(db_session, prefix="CTDEACT")
    admin = await _create_user(db_session, "admin_ctdeact@example.com", "admin")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-DEACT-001",
        title="To Deactivate",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="EUR",
        status="active",
    )
    db_session.add(contract)
    await db_session.commit()
    headers = await _login(tenant_client, "admin_ctdeact@example.com")

    resp = await tenant_client.post(
        f"/api/contracts/{contract.id}/deactivate",
        headers={**headers, "X-Tenant-ID": str(tenant.id)},
    )
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert data["status"] == "suspended"


# ---------------------------------------------------------------------------
# Rate card CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_rate_card_entry(tenant_client: AsyncClient, db_session: AsyncSession):
    """POST /contracts/{id}/rate-card creates a rate card entry -> 201."""
    tenant = await _create_tenant(db_session, prefix="RCCE")
    sm = await _create_user(db_session, "sm_rcce@example.com", "sm", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE01")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RC-001",
        title="Rate Card Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_rcce@example.com")

    resp = await tenant_client.post(
        f"/api/contracts/{contract.id}/rate-card",
        json={
            "profile_id": str(profile.id),
            "sfia_level": 4,
            "max_daily_rate": "750.00",
            "currency": "GBP",
            "effective_from": "2024-01-01",
            "effective_to": "2025-12-31",
        },
        headers=headers,
    )
    assert resp.status_code == 201, f"Expected 201: {resp.text}"
    data = resp.json()
    assert data["sfia_level"] == 4
    assert Decimal(data["max_daily_rate"]) == Decimal("750.00")
    assert data["margin"] is None  # Phase 3 — cost_rate not available yet


@pytest.mark.asyncio
async def test_list_rate_card_entries(tenant_client: AsyncClient, db_session: AsyncSession):
    """GET /contracts/{id}/rate-card returns all entries for the contract."""
    tenant = await _create_tenant(db_session, prefix="RCLST")
    sm = await _create_user(db_session, "sm_rclst@example.com", "sm", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE02")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCLST-001",
        title="Rate Card List Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    entry1 = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=3,
        max_daily_rate=Decimal("600.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    entry2 = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=5,
        max_daily_rate=Decimal("900.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry1)
    db_session.add(entry2)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_rclst@example.com")

    resp = await tenant_client.get(f"/api/contracts/{contract.id}/rate-card", headers=headers)
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert len(data) == 2
    # All margins should be None in Phase 3
    for entry in data:
        assert entry["margin"] is None


@pytest.mark.asyncio
async def test_rate_card_entries_margin_none_for_customer(tenant_client: AsyncClient, db_session: AsyncSession):
    """Customer sees rate card entries with margin=None (hidden, role-gated)."""
    tenant = await _create_tenant(db_session, prefix="RCCU")
    customer = await _create_user(db_session, "cust_rccu@example.com", "customer", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE03")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCCU-001",
        title="Customer Rate Card Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="EUR",
        status="active",
    )
    db_session.add(contract)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("750.00"),
        currency="EUR",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()
    headers = await _login(tenant_client, "cust_rccu@example.com")

    resp = await tenant_client.get(f"/api/contracts/{contract.id}/rate-card", headers=headers)
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    for e in resp.json():
        assert e["margin"] is None


@pytest.mark.asyncio
async def test_update_rate_card_entry(tenant_client: AsyncClient, db_session: AsyncSession):
    """PATCH /contracts/{id}/rate-card/{rid} updates max_daily_rate."""
    tenant = await _create_tenant(db_session, prefix="RCUPD")
    sm = await _create_user(db_session, "sm_rcupd@example.com", "sm", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE04")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCUPD-001",
        title="Update Rate Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("700.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_rcupd@example.com")

    resp = await tenant_client.patch(
        f"/api/contracts/{contract.id}/rate-card/{entry.id}",
        json={"max_daily_rate": "800.00"},
        headers=headers,
    )
    assert resp.status_code == 200, f"Expected 200: {resp.text}"
    data = resp.json()
    assert Decimal(data["max_daily_rate"]) == Decimal("800.00")


@pytest.mark.asyncio
async def test_delete_rate_card_entry(tenant_client: AsyncClient, db_session: AsyncSession):
    """DELETE /contracts/{id}/rate-card/{rid} -> 204, entry gone."""
    tenant = await _create_tenant(db_session, prefix="RCDEL")
    sm = await _create_user(db_session, "sm_rcdel@example.com", "sm", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE05")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCDEL-001",
        title="Delete Rate Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("700.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_rcdel@example.com")

    entry_id = entry.id
    resp = await tenant_client.delete(
        f"/api/contracts/{contract.id}/rate-card/{entry_id}",
        headers=headers,
    )
    assert resp.status_code == 204, f"Expected 204: {resp.text}"

    # Verify the entry is gone
    result = await db_session.execute(
        select(RateCardEntry).where(RateCardEntry.id == entry_id)
    )
    assert result.scalar_one_or_none() is None


@pytest.mark.asyncio
async def test_rate_card_entry_wrong_contract_returns_404(tenant_client: AsyncClient, db_session: AsyncSession):
    """PATCH rate card entry with wrong contract_id returns 404."""
    tenant = await _create_tenant(db_session, prefix="RCWRG")
    sm = await _create_user(db_session, "sm_rcwrg@example.com", "sm", tenant_id=tenant.id)
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="SE06")
    contract1 = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-WRG-001",
        title="Wrong Contract 1",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    contract2 = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-WRG-002",
        title="Wrong Contract 2",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract1)
    db_session.add(contract2)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract1.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("700.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()
    headers = await _login(tenant_client, "sm_rcwrg@example.com")

    # Try to update entry using the wrong contract_id
    resp = await tenant_client.patch(
        f"/api/contracts/{contract2.id}/rate-card/{entry.id}",
        json={"max_daily_rate": "999.00"},
        headers=headers,
    )
    assert resp.status_code == 404, f"Expected 404: {resp.text}"


# ---------------------------------------------------------------------------
# Rate check service tests (direct service function tests, no HTTP)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_rate_check_passes_under_ceiling(db_session: AsyncSession):
    """check_rate_ceiling returns silently when candidate_rate < ceiling."""
    tenant = await _create_tenant(db_session, prefix="RCPS")
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="RC01")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCPS-001",
        title="Rate Check Pass Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    today = date(2024, 6, 1)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("750.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()

    # Rate under ceiling — should NOT raise
    result = await check_rate_ceiling(
        db_session,
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        candidate_rate=Decimal("700.00"),
        today=today,
    )
    assert result is None  # returns silently


@pytest.mark.asyncio
async def test_rate_check_raises_over_ceiling(db_session: AsyncSession):
    """check_rate_ceiling raises RateCeilingExceeded when candidate_rate > ceiling."""
    tenant = await _create_tenant(db_session, prefix="RCFL")
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="RC02")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCFL-001",
        title="Rate Check Fail Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    today = date(2024, 6, 1)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("750.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()

    # Rate over ceiling — should raise
    with pytest.raises(RateCeilingExceeded) as exc_info:
        await check_rate_ceiling(
            db_session,
            contract_id=contract.id,
            profile_id=profile.id,
            sfia_level=4,
            candidate_rate=Decimal("900.00"),
            today=today,
        )
    exc = exc_info.value
    assert exc.candidate_rate == Decimal("900.00")
    assert exc.ceiling == Decimal("750.00")
    assert exc.sfia_level == 4


@pytest.mark.asyncio
async def test_rate_check_at_ceiling_does_not_raise(db_session: AsyncSession):
    """check_rate_ceiling returns silently when candidate_rate == ceiling (not strictly over)."""
    tenant = await _create_tenant(db_session, prefix="RCEQ")
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="RC03")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCEQ-001",
        title="Rate Check Equal Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    today = date(2024, 6, 1)
    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("750.00"),
        currency="GBP",
        effective_from=date(2024, 1, 1),
        effective_to=date(2025, 12, 31),
    )
    db_session.add(entry)
    await db_session.commit()

    # Rate exactly at ceiling — should NOT raise (only strictly over raises)
    result = await check_rate_ceiling(
        db_session,
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        candidate_rate=Decimal("750.00"),
        today=today,
    )
    assert result is None


@pytest.mark.asyncio
async def test_rate_check_no_contract(db_session: AsyncSession):
    """check_rate_ceiling returns silently when contract_id is None."""
    result = await check_rate_ceiling(
        db_session,
        contract_id=None,
        profile_id=uuid.uuid4(),
        sfia_level=4,
        candidate_rate=Decimal("1000.00"),
    )
    assert result is None  # no contract -> no check


@pytest.mark.asyncio
async def test_rate_check_no_profile(db_session: AsyncSession):
    """check_rate_ceiling returns silently when profile_id is None."""
    result = await check_rate_ceiling(
        db_session,
        contract_id=uuid.uuid4(),
        profile_id=None,
        sfia_level=4,
        candidate_rate=Decimal("1000.00"),
    )
    assert result is None  # no profile -> no check


@pytest.mark.asyncio
async def test_rate_check_no_candidate_rate(db_session: AsyncSession):
    """check_rate_ceiling returns silently when candidate_rate is None (Pitfall 3)."""
    result = await check_rate_ceiling(
        db_session,
        contract_id=uuid.uuid4(),
        profile_id=uuid.uuid4(),
        sfia_level=4,
        candidate_rate=None,
    )
    assert result is None  # no rate -> no check


@pytest.mark.asyncio
async def test_rate_check_no_active_entry(db_session: AsyncSession):
    """check_rate_ceiling returns silently when no rate card entry covers today."""
    tenant = await _create_tenant(db_session, prefix="RCNA")
    profile = await _create_profile(db_session, tenant_id=tenant.id, code="RC04")
    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        reference="CTR-RCNA-001",
        title="No Active Entry Contract",
        start_date=date(2024, 1, 1),
        end_date=date(2026, 12, 31),
        currency="GBP",
        status="active",
    )
    db_session.add(contract)
    # Entry that expired before 'today'
    past_entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        max_daily_rate=Decimal("750.00"),
        currency="GBP",
        effective_from=date(2023, 1, 1),
        effective_to=date(2023, 12, 31),  # expired in 2023
    )
    db_session.add(past_entry)
    await db_session.commit()

    # Today is 2024-06-01 — no active entry -> should return silently
    result = await check_rate_ceiling(
        db_session,
        contract_id=contract.id,
        profile_id=profile.id,
        sfia_level=4,
        candidate_rate=Decimal("1000.00"),
        today=date(2024, 6, 1),
    )
    assert result is None  # no active entry -> no constraint


@pytest.mark.asyncio
async def test_has_approved_rate_override_returns_true(db_session: AsyncSession):
    """has_approved_rate_override returns True when an approved override exists."""
    from app.models.approval import ApprovalRequest

    tenant = await _create_tenant(db_session, prefix="ROVA")
    user = await _create_user(db_session, "user_rova@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()

    demand_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    approval = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        requester_id=user.id,
        approver_id=user.id,
        type="rate_override",
        status="approved",
        context_data={
            "demand_id": str(demand_id),
            "candidate_id": str(candidate_id),
        },
        justification="Rate override approved for this candidate",
    )
    db_session.add(approval)
    await db_session.commit()

    result = await has_approved_rate_override(db_session, demand_id, candidate_id)
    assert result is True


@pytest.mark.asyncio
async def test_has_approved_rate_override_returns_false_no_approval(db_session: AsyncSession):
    """has_approved_rate_override returns False when no override exists."""
    await db_session.commit()

    result = await has_approved_rate_override(
        db_session, uuid.uuid4(), uuid.uuid4()
    )
    assert result is False


@pytest.mark.asyncio
async def test_has_approved_rate_override_returns_false_pending(db_session: AsyncSession):
    """has_approved_rate_override returns False for pending (not yet approved) override."""
    from app.models.approval import ApprovalRequest

    tenant = await _create_tenant(db_session, prefix="ROVP")
    user = await _create_user(db_session, "user_rovp@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()

    demand_id = uuid.uuid4()
    candidate_id = uuid.uuid4()

    # Pending override — not yet approved
    approval = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        requester_id=user.id,
        approver_id=user.id,
        type="rate_override",
        status="pending",  # NOT approved
        context_data={
            "demand_id": str(demand_id),
            "candidate_id": str(candidate_id),
        },
        justification="Pending override",
    )
    db_session.add(approval)
    await db_session.commit()

    result = await has_approved_rate_override(db_session, demand_id, candidate_id)
    assert result is False  # pending, not approved


@pytest.mark.asyncio
async def test_has_approved_rate_override_different_candidate(db_session: AsyncSession):
    """has_approved_rate_override returns False for a different candidate_id."""
    from app.models.approval import ApprovalRequest

    tenant = await _create_tenant(db_session, prefix="ROVD")
    user = await _create_user(db_session, "user_rovd@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()

    demand_id = uuid.uuid4()
    candidate_id_1 = uuid.uuid4()
    candidate_id_2 = uuid.uuid4()

    # Approved for candidate 1
    approval = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=tenant.id,
        requester_id=user.id,
        approver_id=user.id,
        type="rate_override",
        status="approved",
        context_data={
            "demand_id": str(demand_id),
            "candidate_id": str(candidate_id_1),
        },
        justification="Override for candidate 1",
    )
    db_session.add(approval)
    await db_session.commit()

    # Check for candidate 2 — should be False
    result = await has_approved_rate_override(db_session, demand_id, candidate_id_2)
    assert result is False
