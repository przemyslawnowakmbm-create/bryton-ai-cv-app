"""User management API endpoints.

Admin endpoints (GET/POST/PATCH /users, POST /users/{id}/deactivate|activate):
  - Use get_db (superuser engine, bypasses RLS) — Admin needs cross-tenant visibility.
  - Require Role.ADMIN via require_roles dependency.

SM endpoints (POST /tenants/{id}/users, PATCH /tenants/{id}/users/{user_id}):
  - Use get_db (superuser for write — SM creates users in other tenants).
  - Require Role.SM and verify junction table assignment before proceeding.
  - SM can only manage Customer users in their assigned tenant(s).
"""
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import Role, get_current_user, require_roles
from app.models.refresh_token import RefreshToken
from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenantAssignment
from app.schemas.user import UserCreate, UserResponse, UserUpdate
from app.services.auth import hash_password

router = APIRouter(tags=["users"])


# ---------------------------------------------------------------------------
# Admin endpoints — cross-tenant user management
# ---------------------------------------------------------------------------


@router.get("/users", response_model=List[UserResponse])
async def admin_list_users(
    role: str | None = Query(default=None),
    tenant_id: uuid.UUID | None = Query(default=None),
    is_active: bool | None = Query(default=None),
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[UserResponse]:
    """List all users across all tenants (Admin only).

    Optional query filters: role, tenant_id, is_active.
    Uses superuser engine — bypasses RLS for cross-tenant visibility.
    """
    stmt = select(User)
    if role is not None:
        stmt = stmt.where(User.role == role)
    if tenant_id is not None:
        stmt = stmt.where(User.tenant_id == tenant_id)
    if is_active is not None:
        stmt = stmt.where(User.is_active == is_active)
    stmt = stmt.order_by(User.email)
    result = await db.execute(stmt)
    users = result.scalars().all()
    return [UserResponse.model_validate(u) for u in users]


@router.post("/users", status_code=status.HTTP_201_CREATED, response_model=UserResponse)
async def admin_create_user(
    body: UserCreate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a user of any role across any tenant (Admin only).

    Admin-created users are email_verified=True (skip verification).
    customer and candidate roles require tenant_id.
    sm and recruiter with tenant_id also get a UserTenantAssignment.
    """
    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    # customer and candidate must have a tenant
    if body.role in ("customer", "candidate") and body.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"role='{body.role}' requires tenant_id",
        )

    # Verify the tenant exists and is active if provided
    if body.tenant_id is not None:
        tenant = await db.get(Tenant, body.tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant not found",
            )
        if not tenant.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant is not active",
            )

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        role=body.role,
        display_name=body.display_name,
        tenant_id=body.tenant_id,
        email_verified=True,  # Admin-created users skip verification
        is_active=True,
    )
    db.add(user)
    await db.flush()

    # SM/Recruiter with tenant_id also get a junction table assignment
    if body.role in ("sm", "recruiter") and body.tenant_id is not None:
        assignment = UserTenantAssignment(user_id=user.id, tenant_id=body.tenant_id)
        db.add(assignment)
        await db.flush()

    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.get("/users/{user_id}", response_model=UserResponse)
async def admin_get_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Get a single user by ID (Admin only)."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse.model_validate(user)


@router.patch("/users/{user_id}", response_model=UserResponse)
async def admin_update_user(
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Partially update a user (Admin only).

    Apply only the fields that are provided (non-None).
    If role changes to customer/candidate, tenant_id must already be set or be provided.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.tenant_id is not None:
        # Verify tenant exists
        tenant = await db.get(Tenant, body.tenant_id)
        if tenant is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Tenant not found",
            )
        user.tenant_id = body.tenant_id
    if body.role is not None:
        # If changing role to customer/candidate, must have tenant_id
        effective_tenant_id = body.tenant_id or user.tenant_id
        if body.role in ("customer", "candidate") and effective_tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"role='{body.role}' requires tenant_id to be set",
            )
        user.role = body.role

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/deactivate", response_model=UserResponse)
async def admin_deactivate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Deactivate a user account (Admin only).

    Sets is_active=False and revokes all active refresh tokens for this user.
    """
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = False

    # Revoke all active refresh tokens
    result = await db.execute(
        select(RefreshToken).where(
            RefreshToken.user_id == user_id,
            RefreshToken.revoked_at.is_(None),
        )
    )
    now = datetime.now(timezone.utc)
    for token_record in result.scalars().all():
        token_record.revoked_at = now

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.post("/users/{user_id}/activate", response_model=UserResponse)
async def admin_activate_user(
    user_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Re-activate a deactivated user account (Admin only)."""
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    user.is_active = True
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


# ---------------------------------------------------------------------------
# SM endpoints — tenant-scoped user management
# ---------------------------------------------------------------------------


@router.post(
    "/tenants/{tenant_id}/users",
    status_code=status.HTTP_201_CREATED,
    response_model=UserResponse,
)
async def sm_create_customer_user(
    tenant_id: uuid.UUID,
    body: UserCreate,
    current_user: User = Depends(require_roles(Role.SM)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Create a Customer user in a tenant (SM only, for their assigned tenant).

    SM can only create role=customer users. SM cannot create admin, sm,
    recruiter, or candidate users. SM must be assigned to the target tenant.
    Uses superuser engine for the write (to create a user in another tenant's scope).
    """
    # SM can only create customer users
    if body.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="SM can only create users with role='customer'",
        )

    # Verify SM is assigned to this tenant
    assignment = await db.execute(
        select(UserTenantAssignment).where(
            UserTenantAssignment.user_id == current_user.id,
            UserTenantAssignment.tenant_id == tenant_id,
        )
    )
    if assignment.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SM is not assigned to this tenant",
        )

    # Verify tenant exists and is active
    tenant = await db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")
    if not tenant.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant is not active",
        )

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )

    user = User(
        id=uuid.uuid4(),
        email=body.email,
        hashed_password=hash_password(body.password),
        role="customer",
        display_name=body.display_name,
        tenant_id=tenant_id,
        email_verified=True,  # SM-created users skip verification
        is_active=True,
    )
    db.add(user)
    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)


@router.patch(
    "/tenants/{tenant_id}/users/{user_id}",
    response_model=UserResponse,
)
async def sm_update_customer_user(
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    body: UserUpdate,
    current_user: User = Depends(require_roles(Role.SM)),
    db: AsyncSession = Depends(get_db),
) -> UserResponse:
    """Update a Customer user in an assigned tenant (SM only).

    SM can update display_name and is_active of Customer users in their tenant.
    Cannot change role. SM must be assigned to the target tenant.
    """
    # Verify SM is assigned to this tenant
    assignment = await db.execute(
        select(UserTenantAssignment).where(
            UserTenantAssignment.user_id == current_user.id,
            UserTenantAssignment.tenant_id == tenant_id,
        )
    )
    if assignment.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SM is not assigned to this tenant",
        )

    # Fetch target user
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    # Verify user belongs to this tenant and is a customer
    if user.tenant_id != tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User does not belong to this tenant",
        )
    if user.role != "customer":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SM can only manage Customer users",
        )

    # SM cannot change role
    if body.role is not None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="SM cannot change user role",
        )

    if body.display_name is not None:
        user.display_name = body.display_name
    if body.is_active is not None:
        user.is_active = body.is_active

    await db.flush()
    await db.refresh(user)
    return UserResponse.model_validate(user)
