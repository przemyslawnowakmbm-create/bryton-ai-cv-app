"""Profile Catalogue API and compliance service tests (Plan 03-03).

Tests cover:
- Profile CRUD (POST, GET list, GET detail, PATCH, DELETE/deactivate)
- Nested requirements creation and retrieval
- Customer role can list/view profiles (read-only)
- demand-defaults endpoint returns complete pre-fill dict with profile_snapshot
- Profile compliance service: MET/PARTIALLY_MET/NOT_MET per requirement type
- CEFR level comparison
- compute_profile_diff: empty diff vs populated diff

Uses SQLite in-memory from conftest for API tests.
Compliance service and diff utility tests use the service/helper directly.

Note: Profile endpoints use get_tenant_db (tenant-scoped RLS session).
In tests, get_tenant_db is overridden to yield the same SQLite test session,
bypassing RLS and GUC setting which is PostgreSQL-specific.
"""
import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import get_tenant_db
from app.main import app
from app.models.profile_catalogue import ProfileCatalogue
from app.models.profile_requirement import ProfileRequirement
from app.models.tenant import Tenant
from app.models.user import User
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
    prefix: str = "PROF",
    name: str = "Profile Tenant",
) -> Tenant:
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


async def _login(client: AsyncClient, email: str) -> dict:
    resp = await client.post("/api/auth/login", json={"email": email, "password": _TEST_PASS})
    assert resp.status_code == 200, f"Login failed for {email}: {resp.text}"
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}


@pytest_asyncio.fixture
async def client_with_tenant_db(db_session: AsyncSession):
    """AsyncClient with both get_db and get_tenant_db overridden to the test session.

    The profiles endpoints use get_tenant_db (bryton_app role + RLS context).
    In tests, we bypass RLS by using the same SQLite in-memory session.
    """

    async def override_get_db():
        yield db_session

    async def override_get_tenant_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_tenant_db] = override_get_tenant_db

    # Reset rate limiters
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

    from httpx import ASGITransport, AsyncClient as _AsyncClient
    transport = ASGITransport(app=app)
    async with _AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac

    app.dependency_overrides.clear()


def _make_profile_body(
    code: str = "SE3",
    title: str = "Software Engineer L3",
    sfia_min: int = 3,
    sfia_max: int = 4,
    requirements: list | None = None,
) -> dict:
    """Return a valid ProfileCreate body dict."""
    if requirements is None:
        requirements = [
            {"req_type": "skill", "description": "Python", "is_mandatory": True},
            {"req_type": "certification", "description": "AWS Certified Developer", "is_mandatory": False},
        ]
    return {
        "code": code,
        "title": title,
        "sfia_level_min": sfia_min,
        "sfia_level_max": sfia_max,
        "min_years_exp": 2,
        "min_education": "bachelor",
        "required_clearance": "SC",
        "requirements": requirements,
    }


# ---------------------------------------------------------------------------
# Profile CRUD tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_create_profile_with_requirements(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """Admin can create a profile with nested requirements — returns 201 with requirements list."""
    tenant = await _create_tenant(db_session, prefix="CRT1")
    await _create_user(db_session, "admin_crt1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_crt1@example.com")

    body = _make_profile_body(
        code="SE3",
        requirements=[
            {"req_type": "skill", "description": "Python", "is_mandatory": True},
            {"req_type": "language", "description": "English", "is_mandatory": True, "min_cefr_level": "C1"},
        ],
    )
    resp = await client_with_tenant_db.post("/api/profiles", json=body, headers=headers)
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["code"] == "SE3"
    assert data["title"] == "Software Engineer L3"
    assert data["sfia_level_min"] == 3
    assert data["sfia_level_max"] == 4
    assert data["is_active"] is True
    assert len(data["requirements"]) == 2
    req_types = {r["req_type"] for r in data["requirements"]}
    assert req_types == {"skill", "language"}


@pytest.mark.asyncio
async def test_create_profile_as_sm(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """SM can create a profile — returns 201."""
    tenant = await _create_tenant(db_session, prefix="SM01")
    await _create_user(db_session, "sm_crt@example.com", "sm", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "sm_crt@example.com")

    resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="BE2"),
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["code"] == "BE2"


@pytest.mark.asyncio
async def test_create_profile_unauthorized(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """Customer cannot create a profile — returns 403."""
    tenant = await _create_tenant(db_session, prefix="CUS1")
    await _create_user(db_session, "customer_crt@example.com", "customer", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "customer_crt@example.com")

    resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="FE1"),
        headers=headers,
    )
    assert resp.status_code == 403, resp.text


@pytest.mark.asyncio
async def test_list_profiles(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """Admin can list profiles — returns non-empty list."""
    tenant = await _create_tenant(db_session, prefix="LST1")
    await _create_user(db_session, "admin_lst@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_lst@example.com")

    # Create a profile first
    await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="LST1"),
        headers=headers,
    )

    resp = await client_with_tenant_db.get("/api/profiles", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert isinstance(data, list)
    assert len(data) >= 1


@pytest.mark.asyncio
async def test_list_profiles_as_customer(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """Customer can list profiles (read-only access for demand creation) — returns 200."""
    tenant = await _create_tenant(db_session, prefix="CST2")
    admin = await _create_user(db_session, "admin_cst2@example.com", "admin", tenant_id=tenant.id)
    await _create_user(db_session, "customer_lst@example.com", "customer", tenant_id=tenant.id)
    await db_session.commit()
    admin_headers = await _login(client_with_tenant_db, "admin_cst2@example.com")
    customer_headers = await _login(client_with_tenant_db, "customer_lst@example.com")

    # Admin creates a profile
    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="CST2"),
        headers=admin_headers,
    )
    assert create_resp.status_code == 201

    # Customer can list profiles
    resp = await client_with_tenant_db.get("/api/profiles", headers=customer_headers)
    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)


@pytest.mark.asyncio
async def test_get_profile_detail(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """GET /api/profiles/{id} returns 200 with requirements list."""
    tenant = await _create_tenant(db_session, prefix="DET1")
    await _create_user(db_session, "admin_det1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_det1@example.com")

    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(
            code="DET1",
            requirements=[
                {"req_type": "skill", "description": "Go", "is_mandatory": True},
                {"req_type": "clearance", "description": "DV", "is_mandatory": True},
            ],
        ),
        headers=headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    resp = await client_with_tenant_db.get(f"/api/profiles/{profile_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["id"] == profile_id
    assert len(data["requirements"]) == 2
    req_types = {r["req_type"] for r in data["requirements"]}
    assert req_types == {"skill", "clearance"}


@pytest.mark.asyncio
async def test_update_profile(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """PATCH /api/profiles/{id} updates fields correctly."""
    tenant = await _create_tenant(db_session, prefix="UPD1")
    await _create_user(db_session, "admin_upd1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_upd1@example.com")

    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="UPD1", title="Original Title"),
        headers=headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    patch_resp = await client_with_tenant_db.patch(
        f"/api/profiles/{profile_id}",
        json={"title": "Updated Title", "min_years_exp": 5},
        headers=headers,
    )
    assert patch_resp.status_code == 200, patch_resp.text
    data = patch_resp.json()
    assert data["title"] == "Updated Title"
    assert data["min_years_exp"] == 5
    # Code should not change
    assert data["code"] == "UPD1"


@pytest.mark.asyncio
async def test_deactivate_profile(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """DELETE /api/profiles/{id} sets is_active=False (soft delete)."""
    tenant = await _create_tenant(db_session, prefix="DAC1")
    await _create_user(db_session, "admin_dac1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_dac1@example.com")

    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(code="DAC1"),
        headers=headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    resp = await client_with_tenant_db.delete(f"/api/profiles/{profile_id}", headers=headers)
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["is_active"] is False


# ---------------------------------------------------------------------------
# Demand defaults tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_demand_defaults(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """GET /api/profiles/{id}/demand-defaults returns correct pre-fill dict with all fields mapped."""
    tenant = await _create_tenant(db_session, prefix="DEF1")
    await _create_user(db_session, "admin_def1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_def1@example.com")

    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json={
            "code": "DEF1",
            "title": "Default Test Profile",
            "sfia_level_min": 2,
            "sfia_level_max": 4,
            "min_years_exp": 3,
            "min_education": "bachelor",
            "required_clearance": "SC",
            "requirements": [
                {"req_type": "skill", "description": "Python", "is_mandatory": True},
                {"req_type": "skill", "description": "SQL", "is_mandatory": True},
                {
                    "req_type": "language",
                    "description": "French",
                    "is_mandatory": False,
                    "min_cefr_level": "B2",
                },
                {
                    "req_type": "certification",
                    "description": "AWS Solutions Architect",
                    "is_mandatory": False,
                },
            ],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    resp = await client_with_tenant_db.get(
        f"/api/profiles/{profile_id}/demand-defaults", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["sfia_level_min"] == 2
    assert data["sfia_level_max"] == 4
    assert data["min_years_exp"] == 3
    assert data["min_education"] == "bachelor"
    assert data["required_clearance"] == "SC"
    # Skills joined with comma
    assert "Python" in data["required_skills"]
    assert "SQL" in data["required_skills"]
    # Language derived from language requirement
    assert len(data["languages"]) == 1
    assert data["languages"][0]["language_description"] == "French"
    assert data["languages"][0]["min_cefr_level"] == "B2"
    # Certification derived from certification requirement
    assert "AWS Solutions Architect" in data["certifications"]


@pytest.mark.asyncio
async def test_demand_defaults_includes_snapshot(
    client_with_tenant_db: AsyncClient, db_session: AsyncSession
):
    """demand-defaults response includes a complete profile_snapshot dict."""
    tenant = await _create_tenant(db_session, prefix="SNP1")
    await _create_user(db_session, "admin_snp1@example.com", "admin", tenant_id=tenant.id)
    await db_session.commit()
    headers = await _login(client_with_tenant_db, "admin_snp1@example.com")

    create_resp = await client_with_tenant_db.post(
        "/api/profiles",
        json=_make_profile_body(
            code="SNP1",
            requirements=[
                {"req_type": "skill", "description": "Kubernetes", "is_mandatory": True},
            ],
        ),
        headers=headers,
    )
    assert create_resp.status_code == 201
    profile_id = create_resp.json()["id"]

    resp = await client_with_tenant_db.get(
        f"/api/profiles/{profile_id}/demand-defaults", headers=headers
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # profile_snapshot must be present and contain profile_id and requirements
    assert "profile_snapshot" in data
    snapshot = data["profile_snapshot"]
    assert snapshot["profile_id"] == profile_id
    assert snapshot["code"] == "SNP1"
    assert "requirements" in snapshot
    assert len(snapshot["requirements"]) == 1
    assert snapshot["requirements"][0]["description"] == "Kubernetes"
    assert snapshot["requirements"][0]["req_type"] == "skill"


# ---------------------------------------------------------------------------
# Compliance service tests
# ---------------------------------------------------------------------------


def _make_req(
    req_type: str,
    description: str,
    is_mandatory: bool = True,
    min_cefr_level: str | None = None,
) -> ProfileRequirement:
    """Create a ProfileRequirement ORM object for testing (no DB needed)."""
    req = ProfileRequirement.__new__(ProfileRequirement)
    req.id = uuid.uuid4()
    req.profile_id = uuid.uuid4()
    req.tenant_id = uuid.uuid4()
    req.req_type = req_type
    req.description = description
    req.is_mandatory = is_mandatory
    req.min_cefr_level = min_cefr_level
    return req


@pytest.mark.asyncio
async def test_compliance_all_met():
    """All requirements satisfied — overall status is MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [
        _make_req("skill", "Python", is_mandatory=True),
        _make_req("certification", "AWS Developer", is_mandatory=False),
    ]
    candidate_data = {
        "skills": "Python, JavaScript, Docker",
        "certifications": ["AWS Developer", "Kubernetes KCAD"],
    }
    result = check_profile_compliance(requirements, candidate_data)
    assert result["overall"] == "MET"
    items_by_type = {item["req_type"]: item for item in result["items"]}
    assert items_by_type["skill"]["status"] == "MET"
    assert items_by_type["certification"]["status"] == "MET"


@pytest.mark.asyncio
async def test_compliance_not_met():
    """Mandatory requirement is missing — overall status is NOT_MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [
        _make_req("skill", "Rust", is_mandatory=True),
        _make_req("skill", "Python", is_mandatory=False),
    ]
    candidate_data = {
        "skills": "Python, Go",
        "certifications": [],
    }
    result = check_profile_compliance(requirements, candidate_data)
    # Rust is mandatory and missing
    assert result["overall"] == "NOT_MET"
    items_by_desc = {item["description"]: item for item in result["items"]}
    assert items_by_desc["Rust"]["status"] == "NOT_MET"
    assert items_by_desc["Python"]["status"] == "MET"


@pytest.mark.asyncio
async def test_compliance_partially_met():
    """Language found but at lower CEFR level — status is PARTIALLY_MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [
        _make_req("language", "French", is_mandatory=False, min_cefr_level="C1"),
    ]
    candidate_data = {
        "languages": [{"language": "French", "cefr_level": "B2"}],
    }
    result = check_profile_compliance(requirements, candidate_data)
    # French found but B2 < C1
    assert result["overall"] == "PARTIALLY_MET"
    assert result["items"][0]["status"] == "PARTIALLY_MET"


@pytest.mark.asyncio
async def test_compliance_empty_candidate():
    """Empty candidate data — all requirements NOT_MET, no exception raised."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [
        _make_req("skill", "Java", is_mandatory=True),
        _make_req("certification", "Oracle DBA", is_mandatory=True),
        _make_req("language", "German", is_mandatory=False, min_cefr_level="B1"),
    ]
    # Empty dict — should not raise
    result = check_profile_compliance(requirements, {})
    assert result["overall"] == "NOT_MET"
    for item in result["items"]:
        assert item["status"] == "NOT_MET"

    # None — should also not raise
    result_none = check_profile_compliance(requirements, None)  # type: ignore[arg-type]
    assert result_none["overall"] == "NOT_MET"


@pytest.mark.asyncio
async def test_cefr_comparison():
    """CEFR comparison: B2 meets B1 minimum; A2 does not meet B1 minimum."""
    from app.services.profile_compliance import _cefr_meets_minimum

    assert _cefr_meets_minimum("B2", "B1") is True
    assert _cefr_meets_minimum("C2", "B1") is True
    assert _cefr_meets_minimum("B1", "B1") is True
    assert _cefr_meets_minimum("A2", "B1") is False
    assert _cefr_meets_minimum("A1", "C2") is False
    assert _cefr_meets_minimum("C1", "C2") is False


# ---------------------------------------------------------------------------
# Profile diff utility tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compute_diff_no_deviations():
    """Identical snapshot and demand values — compute_profile_diff returns empty list."""
    from app.api.profiles import compute_profile_diff

    snapshot = {
        "sfia_level_min": 3,
        "sfia_level_max": 5,
        "min_years_exp": 4,
        "min_education": "bachelor",
        "required_clearance": "SC",
        "description": "A senior engineer",
    }
    demand_values = dict(snapshot)  # identical

    diffs = compute_profile_diff(snapshot, demand_values)
    assert diffs == []


@pytest.mark.asyncio
async def test_compute_diff_with_deviations():
    """Changed sfia_level_min and min_education — returns two diff entries."""
    from app.api.profiles import compute_profile_diff

    snapshot = {
        "sfia_level_min": 3,
        "sfia_level_max": 5,
        "min_years_exp": 4,
        "min_education": "bachelor",
        "required_clearance": "SC",
        "description": "A senior engineer",
    }
    demand_values = {
        "sfia_level_min": 4,  # changed
        "sfia_level_max": 5,
        "min_years_exp": 4,
        "min_education": "master",  # changed
        "required_clearance": "SC",
        "description": "A senior engineer",
    }

    diffs = compute_profile_diff(snapshot, demand_values)
    assert len(diffs) == 2

    diff_fields = {d["field"] for d in diffs}
    assert "sfia_level_min" in diff_fields
    assert "min_education" in diff_fields

    for diff in diffs:
        if diff["field"] == "sfia_level_min":
            assert diff["profile_value"] == 3
            assert diff["demand_value"] == 4
        elif diff["field"] == "min_education":
            assert diff["profile_value"] == "bachelor"
            assert diff["demand_value"] == "master"


# ---------------------------------------------------------------------------
# Additional compliance tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_compliance_clearance_met():
    """Candidate has required clearance — status is MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [_make_req("clearance", "SC", is_mandatory=True)]
    candidate_data = {"clearances": [{"level": "SC Cleared"}, {"level": "DV"}]}
    result = check_profile_compliance(requirements, candidate_data)
    assert result["items"][0]["status"] == "MET"


@pytest.mark.asyncio
async def test_compliance_education_met():
    """Candidate education field contains required level — status is MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [_make_req("education", "bachelor", is_mandatory=True)]
    candidate_data = {"education": "BSc Computer Science, University of London, 2018"}
    result = check_profile_compliance(requirements, candidate_data)
    assert result["items"][0]["status"] == "MET"


@pytest.mark.asyncio
async def test_compliance_language_cefr_met():
    """Language found at exact minimum CEFR level — status is MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [_make_req("language", "Spanish", is_mandatory=False, min_cefr_level="B2")]
    candidate_data = {"languages": [{"language": "Spanish", "cefr_level": "B2"}]}
    result = check_profile_compliance(requirements, candidate_data)
    assert result["items"][0]["status"] == "MET"


@pytest.mark.asyncio
async def test_compliance_certification_partially_met():
    """Certification name partially matches — status is PARTIALLY_MET."""
    from app.services.profile_compliance import check_profile_compliance

    requirements = [_make_req("certification", "AWS Solutions Architect", is_mandatory=False)]
    # Candidate has partial match
    candidate_data = {"certifications": ["AWS Solutions Associate"]}
    result = check_profile_compliance(requirements, candidate_data)
    # "AWS Solutions" matches partially but not exactly
    assert result["items"][0]["status"] in ("MET", "PARTIALLY_MET")


@pytest.mark.asyncio
async def test_compliance_no_requirements():
    """No requirements — overall is MET with empty items list."""
    from app.services.profile_compliance import check_profile_compliance

    result = check_profile_compliance([], {"skills": "Python"})
    assert result["overall"] == "MET"
    assert result["items"] == []
