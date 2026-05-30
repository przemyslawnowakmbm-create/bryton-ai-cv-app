"""Profile Catalogue API endpoints.

PROFILE-01: Full CRUD for profile catalogue entries with nested requirements.
PROFILE-02: GET /profiles/{id}/demand-defaults returns pre-fill dict for demand creation.
PROFILE-03: compute_profile_diff utility (imported by Phase 5 demands API).

All endpoints use get_tenant_db (RLS-enforced bryton_app session).
Customer role has read-only access (needed for demand creation profile selection).

Endpoints:
  POST   /profiles                        — Create profile (Admin, SM)
  GET    /profiles                        — List profiles (Admin, SM, Recruiter, Customer)
  GET    /profiles/{id}                   — Profile detail (Admin, SM, Recruiter, Customer)
  PATCH  /profiles/{id}                   — Update profile (Admin, SM)
  DELETE /profiles/{id}                   — Deactivate profile (Admin, SM)
  GET    /profiles/{id}/demand-defaults   — Get pre-fill dict for demand creation (all roles)
"""
import uuid
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.deps import Role, get_tenant_db, require_roles
from app.models.profile_catalogue import ProfileCatalogue
from app.models.profile_requirement import ProfileRequirement
from app.models.user import User
from app.schemas.profile import (
    DemandDefaultsResponse,
    ProfileCreate,
    ProfileRequirementResponse,
    ProfileResponse,
    ProfileUpdate,
)
from app.services.audit import log_audit_event

router = APIRouter(tags=["profiles"])


# ---------------------------------------------------------------------------
# Helper: serialise profile to snapshot dict (PROFILE-03 deviation tracking)
# ---------------------------------------------------------------------------


def _serialise_profile(
    profile: ProfileCatalogue, requirements: list[ProfileRequirement]
) -> dict[str, Any]:
    """Serialise profile + requirements into a dict for demand.profile_snapshot storage.

    The snapshot captures the full profile state at demand creation time so
    compute_profile_diff can detect field-level deviations later.
    """
    return {
        "profile_id": str(profile.id),
        "code": profile.code,
        "title": profile.title,
        "description": profile.description,
        "sfia_level_min": profile.sfia_level_min,
        "sfia_level_max": profile.sfia_level_max,
        "min_years_exp": profile.min_years_exp,
        "min_education": profile.min_education,
        "required_clearance": profile.required_clearance,
        "requirements": [
            {
                "id": str(r.id),
                "req_type": r.req_type,
                "description": r.description,
                "is_mandatory": r.is_mandatory,
                "min_cefr_level": r.min_cefr_level,
            }
            for r in requirements
        ],
    }


# ---------------------------------------------------------------------------
# Helper: compute profile diff (PROFILE-03 — exported for Phase 5 import)
# ---------------------------------------------------------------------------


def compute_profile_diff(snapshot: dict[str, Any], demand_values: dict[str, Any]) -> list[dict]:
    """Compare profile snapshot against demand field values.

    Returns list of {field, profile_value, demand_value} for deviations.
    Pure Python — no dependencies. Used by Phase 5 GET /demands/{id}/profile-diff.

    Args:
        snapshot:      The profile_snapshot dict stored on the demand (from _serialise_profile).
        demand_values: Dict of demand field values to compare against.

    Returns:
        List of deviation dicts — empty list if no deviations.
    """
    field_mappings = {
        "sfia_level_min": "sfia_level_min",
        "sfia_level_max": "sfia_level_max",
        "min_years_exp": "min_years_exp",
        "min_education": "min_education",
        "required_clearance": "required_clearance",
        "description": "description",
    }
    diffs = []
    for snapshot_field, demand_field in field_mappings.items():
        profile_val = snapshot.get(snapshot_field)
        demand_val = demand_values.get(demand_field)
        if profile_val != demand_val:
            diffs.append(
                {
                    "field": snapshot_field,
                    "profile_value": profile_val,
                    "demand_value": demand_val,
                }
            )
    return diffs


# ---------------------------------------------------------------------------
# Helper: load profile with requirements
# ---------------------------------------------------------------------------


async def _load_profile_with_requirements(
    db: AsyncSession, profile_id: uuid.UUID
) -> tuple[ProfileCatalogue, list[ProfileRequirement]]:
    """Load a ProfileCatalogue record and its requirements.

    Returns (profile, requirements). Requirements are ordered by created_at.
    Raises 404 HTTPException if profile is not found.
    """
    profile = await db.get(ProfileCatalogue, profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )
    req_result = await db.execute(
        select(ProfileRequirement)
        .where(ProfileRequirement.profile_id == profile_id)
        .order_by(ProfileRequirement.created_at)
    )
    requirements = list(req_result.scalars().all())
    return profile, requirements


def _build_profile_response(
    profile: ProfileCatalogue, requirements: list[ProfileRequirement]
) -> ProfileResponse:
    """Build a ProfileResponse from ORM objects."""
    req_responses = [ProfileRequirementResponse.model_validate(r) for r in requirements]
    data = {
        "id": profile.id,
        "tenant_id": profile.tenant_id,
        "contract_id": profile.contract_id,
        "code": profile.code,
        "title": profile.title,
        "description": profile.description,
        "sfia_level_min": profile.sfia_level_min,
        "sfia_level_max": profile.sfia_level_max,
        "min_years_exp": profile.min_years_exp,
        "min_education": profile.min_education,
        "required_clearance": profile.required_clearance,
        "is_active": profile.is_active,
        "created_by": profile.created_by,
        "created_at": profile.created_at,
        "updated_at": profile.updated_at,
        "requirements": req_responses,
    }
    return ProfileResponse.model_validate(data)


# ---------------------------------------------------------------------------
# Helper: get effective tenant_id from current user
# ---------------------------------------------------------------------------


def _get_effective_tenant_id(current_user: User) -> uuid.UUID:
    """Get the tenant_id from the current user.

    For Customer/Candidate: user.tenant_id is set directly.
    For Admin/SM/Recruiter: resolved by get_tenant_db dependency.

    The RLS session (get_tenant_db) already enforces tenant isolation via
    SET LOCAL app.current_tenant. We use current_user.tenant_id to set the
    tenant_id column on new records — this is the same value the GUC was set to.

    Raises HTTP 400 if the user has no tenant context (should not happen in
    practice since get_tenant_db already guards this).
    """
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no tenant context — cannot create tenant-scoped record",
        )
    return current_user.tenant_id


# ---------------------------------------------------------------------------
# POST /profiles — Create profile with nested requirements (Admin, SM)
# ---------------------------------------------------------------------------


@router.post("/profiles", status_code=status.HTTP_201_CREATED, response_model=ProfileResponse)
async def create_profile(
    body: ProfileCreate,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProfileResponse:
    """Create a profile catalogue entry with nested requirements.

    Requirements are created atomically with the profile.
    Sets denormalised tenant_id on each requirement for RLS (Pitfall 2).
    """
    effective_tenant_id = _get_effective_tenant_id(current_user)

    profile = ProfileCatalogue(
        id=uuid.uuid4(),
        tenant_id=effective_tenant_id,
        contract_id=body.contract_id,
        code=body.code,
        title=body.title,
        description=body.description,
        sfia_level_min=body.sfia_level_min,
        sfia_level_max=body.sfia_level_max,
        min_years_exp=body.min_years_exp,
        min_education=body.min_education,
        required_clearance=body.required_clearance,
        is_active=True,
        created_by=current_user.id,
    )
    db.add(profile)
    await db.flush()

    requirements: list[ProfileRequirement] = []
    for req_body in body.requirements:
        req = ProfileRequirement(
            id=uuid.uuid4(),
            profile_id=profile.id,
            tenant_id=effective_tenant_id,  # denormalised for RLS
            req_type=req_body.req_type,
            description=req_body.description,
            is_mandatory=req_body.is_mandatory,
            min_cefr_level=req_body.min_cefr_level,
        )
        db.add(req)
        requirements.append(req)

    await db.flush()

    await log_audit_event(
        db,
        action="profile.created",
        tenant_id=effective_tenant_id,
        actor_id=current_user.id,
        entity_type="profile_catalogue",
        entity_id=profile.id,
        payload={
            "code": profile.code,
            "title": profile.title,
            "requirements_count": len(requirements),
        },
    )

    await db.commit()
    await db.refresh(profile)
    for req in requirements:
        await db.refresh(req)

    return _build_profile_response(profile, requirements)


# ---------------------------------------------------------------------------
# GET /profiles — List profiles (Admin, SM, Recruiter, Customer)
# ---------------------------------------------------------------------------


@router.get("/profiles", response_model=list[ProfileResponse])
async def list_profiles(
    is_active: bool = Query(default=True),
    contract_id: uuid.UUID | None = Query(default=None),
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.SM, Role.RECRUITER, Role.CUSTOMER)
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> list[ProfileResponse]:
    """List profile catalogue entries.

    Customer role can list profiles (needed for demand creation profile selection).
    Defaults to active profiles only. Filterable by contract_id.
    """
    stmt = select(ProfileCatalogue).where(ProfileCatalogue.is_active == is_active)
    if contract_id is not None:
        stmt = stmt.where(ProfileCatalogue.contract_id == contract_id)
    stmt = stmt.order_by(ProfileCatalogue.created_at.desc())

    result = await db.execute(stmt)
    profiles = result.scalars().all()

    output: list[ProfileResponse] = []
    for profile in profiles:
        req_result = await db.execute(
            select(ProfileRequirement)
            .where(ProfileRequirement.profile_id == profile.id)
            .order_by(ProfileRequirement.created_at)
        )
        requirements = list(req_result.scalars().all())
        output.append(_build_profile_response(profile, requirements))

    return output


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id} — Profile detail (Admin, SM, Recruiter, Customer)
# ---------------------------------------------------------------------------


@router.get("/profiles/{profile_id}", response_model=ProfileResponse)
async def get_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.SM, Role.RECRUITER, Role.CUSTOMER)
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProfileResponse:
    """Get a single profile catalogue entry with its requirements.

    Returns 404 if profile not found.
    """
    profile, requirements = await _load_profile_with_requirements(db, profile_id)
    return _build_profile_response(profile, requirements)


# ---------------------------------------------------------------------------
# PATCH /profiles/{profile_id} — Update profile (Admin, SM)
# ---------------------------------------------------------------------------


@router.patch("/profiles/{profile_id}", response_model=ProfileResponse)
async def update_profile(
    profile_id: uuid.UUID,
    body: ProfileUpdate,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProfileResponse:
    """Partially update a profile catalogue entry.

    If requirements are provided in the body, existing requirements are deleted
    and replaced with the new set (simpler than diffing nested objects).
    Logs 'profile.updated' to the audit trail.
    """
    profile, existing_requirements = await _load_profile_with_requirements(db, profile_id)
    effective_tenant_id = profile.tenant_id

    # Apply non-None fields
    if body.title is not None:
        profile.title = body.title
    if body.description is not None:
        profile.description = body.description
    if body.sfia_level_min is not None:
        profile.sfia_level_min = body.sfia_level_min
    if body.sfia_level_max is not None:
        profile.sfia_level_max = body.sfia_level_max
    if body.min_years_exp is not None:
        profile.min_years_exp = body.min_years_exp
    if body.min_education is not None:
        profile.min_education = body.min_education
    if body.required_clearance is not None:
        profile.required_clearance = body.required_clearance
    if body.is_active is not None:
        profile.is_active = body.is_active

    db.add(profile)
    await db.flush()

    # Refresh requirements from DB after profile update
    requirements = existing_requirements

    await log_audit_event(
        db,
        action="profile.updated",
        tenant_id=effective_tenant_id,
        actor_id=current_user.id,
        entity_type="profile_catalogue",
        entity_id=profile.id,
        payload={
            "code": profile.code,
            "title": profile.title,
            "updated_fields": [
                k for k, v in body.model_dump(exclude_unset=True).items() if v is not None
            ],
        },
    )

    await db.commit()
    await db.refresh(profile)

    # Reload requirements after commit
    req_result = await db.execute(
        select(ProfileRequirement)
        .where(ProfileRequirement.profile_id == profile.id)
        .order_by(ProfileRequirement.created_at)
    )
    requirements = list(req_result.scalars().all())

    return _build_profile_response(profile, requirements)


# ---------------------------------------------------------------------------
# DELETE /profiles/{profile_id} — Deactivate profile (Admin, SM)
# ---------------------------------------------------------------------------


@router.delete("/profiles/{profile_id}", response_model=ProfileResponse)
async def deactivate_profile(
    profile_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ProfileResponse:
    """Soft-delete a profile catalogue entry by setting is_active=False.

    Logs 'profile.deactivated' to the audit trail.
    """
    profile, requirements = await _load_profile_with_requirements(db, profile_id)
    effective_tenant_id = profile.tenant_id

    profile.is_active = False
    db.add(profile)
    await db.flush()

    await log_audit_event(
        db,
        action="profile.deactivated",
        tenant_id=effective_tenant_id,
        actor_id=current_user.id,
        entity_type="profile_catalogue",
        entity_id=profile.id,
        payload={"code": profile.code, "title": profile.title},
    )

    await db.commit()
    await db.refresh(profile)

    return _build_profile_response(profile, requirements)


# ---------------------------------------------------------------------------
# GET /profiles/{profile_id}/demand-defaults — Pre-fill dict for demand creation
# ---------------------------------------------------------------------------


@router.get("/profiles/{profile_id}/demand-defaults", response_model=DemandDefaultsResponse)
async def get_demand_defaults(
    profile_id: uuid.UUID,
    current_user: User = Depends(
        require_roles(Role.ADMIN, Role.SM, Role.RECRUITER, Role.CUSTOMER)
    ),
    db: AsyncSession = Depends(get_tenant_db),
) -> DemandDefaultsResponse:
    """Return a pre-fill dict from a profile for demand creation.

    PROFILE-02: All pre-populated fields are freely editable by the user (template only).
    The profile_snapshot in the response should be stored in demands.profile_snapshot
    to enable PROFILE-03 deviation tracking later.

    Returns 404 if profile not found.
    """
    profile, requirements = await _load_profile_with_requirements(db, profile_id)

    # Aggregate requirements by type
    skill_descriptions = [
        r.description for r in requirements if r.req_type == "skill"
    ]
    required_skills = ", ".join(skill_descriptions) if skill_descriptions else None

    languages = [
        {"language_description": r.description, "min_cefr_level": r.min_cefr_level}
        for r in requirements
        if r.req_type == "language"
    ]

    certifications = [r.description for r in requirements if r.req_type == "certification"]

    profile_snapshot = _serialise_profile(profile, requirements)

    return DemandDefaultsResponse(
        sfia_level_min=profile.sfia_level_min,
        sfia_level_max=profile.sfia_level_max,
        min_years_exp=profile.min_years_exp,
        required_skills=required_skills,
        min_education=profile.min_education,
        required_clearance=profile.required_clearance,
        languages=languages,
        certifications=certifications,
        profile_snapshot=profile_snapshot,
    )
