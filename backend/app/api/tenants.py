"""Tenant CRUD, deactivation, and user-tenant assignment endpoints.

All endpoints are Admin-only unless explicitly noted.
Admin endpoints use the superuser engine (get_db) to bypass RLS — they need
cross-tenant visibility by design. SM listing endpoint uses require_roles check.
"""
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import Role, require_roles
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenantAssignment
from app.schemas.tenant import (
    TenantCreate,
    TenantResponse,
    TenantUpdate,
    UserBrief,
    UserTenantAssignRequest,
    UserTenantAssignResponse,
)

router = APIRouter(prefix="/tenants", tags=["tenants"])

# Roles allowed to be assigned to multiple tenants (via user_tenant_assignments)
_MULTI_TENANT_ROLES = (Role.SM, Role.RECRUITER)


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------


@router.post("", status_code=status.HTTP_201_CREATED, response_model=TenantResponse)
async def create_tenant(
    body: TenantCreate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Create a new tenant (Admin only).

    prefix must be 2-6 uppercase alphanumeric characters and must be unique.
    Default config initialises approval gates.
    """
    # Check prefix uniqueness
    existing = await db.execute(
        select(Tenant).where(Tenant.prefix == body.prefix)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Tenant with prefix '{body.prefix}' already exists",
        )

    default_config = {"approval_gates": {"shortlist_submission": True, "rate_override": True}}
    tenant_config = body.config if body.config is not None else default_config

    tenant = Tenant(
        prefix=body.prefix,
        name=body.name,
        config=tenant_config,
        is_active=True,
    )
    db.add(tenant)
    await db.flush()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.get("", response_model=List[TenantResponse])
async def list_tenants(
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[TenantResponse]:
    """List all tenants — active and inactive (Admin only)."""
    result = await db.execute(select(Tenant).order_by(Tenant.created_at))
    tenants = result.scalars().all()
    return [TenantResponse.model_validate(t) for t in tenants]


@router.get("/{tenant_id}", response_model=TenantResponse)
async def get_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Get a single tenant by ID (Admin only)."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
async def update_tenant(
    tenant_id: uuid.UUID,
    body: TenantUpdate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Partially update a tenant's name or config (Admin only).

    Prefix is immutable — not allowed in TenantUpdate body.
    """
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    if body.name is not None:
        tenant.name = body.name
    if body.config is not None:
        tenant.config = body.config

    await db.flush()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/deactivate", response_model=TenantResponse)
async def deactivate_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Deactivate a tenant (Admin only).

    Sets is_active=False. This makes the tenant's data effectively read-only —
    future write endpoints should check tenant.is_active before allowing mutations.
    """
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.is_active = False
    await db.flush()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


@router.post("/{tenant_id}/activate", response_model=TenantResponse)
async def activate_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> TenantResponse:
    """Re-activate a deactivated tenant (Admin only)."""
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    tenant.is_active = True
    await db.flush()
    await db.refresh(tenant)
    return TenantResponse.model_validate(tenant)


# ---------------------------------------------------------------------------
# User-tenant assignment endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{tenant_id}/assign-user",
    status_code=status.HTTP_201_CREATED,
    response_model=UserTenantAssignResponse,
)
async def assign_user_to_tenant(
    tenant_id: uuid.UUID,
    body: UserTenantAssignRequest,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserTenantAssignResponse:
    """Assign a user to a tenant (Admin only).

    Only SM and Recruiter users can be assigned via the junction table.
    Customer and Candidate users belong to exactly one tenant via user.tenant_id.
    Returns 409 if the assignment already exists.
    """
    # Verify tenant exists
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # Verify user exists
    user = await db.get(User, body.user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Only SM/Recruiter can be assigned via multi-tenant junction table
    try:
        user_role = Role(user.role)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User has unknown role: {user.role}",
        )
    if user_role not in _MULTI_TENANT_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                f"Only SM and Recruiter users can be assigned to multiple tenants via this endpoint. "
                f"User role is '{user.role}'."
            ),
        )

    # Check for duplicate assignment
    existing = await db.execute(
        select(UserTenantAssignment).where(
            UserTenantAssignment.user_id == body.user_id,
            UserTenantAssignment.tenant_id == tenant_id,
        )
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already assigned to this tenant",
        )

    assignment = UserTenantAssignment(user_id=body.user_id, tenant_id=tenant_id)
    db.add(assignment)
    await db.flush()
    await db.refresh(assignment)
    return UserTenantAssignResponse.model_validate(assignment)


@router.delete(
    "/{tenant_id}/assign-user/{user_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_user_from_tenant(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Remove a user's assignment from a tenant (Admin only)."""
    assignment = await db.get(UserTenantAssignment, (user_id, tenant_id))
    if assignment is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Assignment not found",
        )
    await db.delete(assignment)
    await db.flush()


@router.get("/{tenant_id}/users", response_model=List[UserBrief])
async def list_tenant_users(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_db),
) -> List[UserBrief]:
    """List users belonging to a tenant (Admin or assigned SM).

    Admin sees all users in the tenant.
    SM must be assigned to the tenant to view its users.
    """
    # Verify tenant exists
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # SM must be assigned to the tenant
    if current_user.role == Role.SM:
        sm_assignment = await db.execute(
            select(UserTenantAssignment).where(
                UserTenantAssignment.user_id == current_user.id,
                UserTenantAssignment.tenant_id == tenant_id,
            )
        )
        if sm_assignment.scalar_one_or_none() is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="SM is not assigned to this tenant",
            )

    # Query users belonging to this tenant
    result = await db.execute(
        select(User).where(User.tenant_id == tenant_id).order_by(User.email)
    )
    users = result.scalars().all()
    return [UserBrief.model_validate(u) for u in users]
