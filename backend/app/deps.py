"""FastAPI dependencies for database sessions and auth.

Provides:
  get_db              — superuser DB session (bypasses RLS); for login/register/admin
  get_current_user    — decodes Bearer JWT, fetches and validates User from DB
  get_tenant_db       — app_async_session (bryton_app role) with SET LOCAL tenant context
  require_roles       — factory returning a dependency that enforces role membership
  get_admin_db        — convenience: superuser session + Admin role check
  Role                — StrEnum with all 5 application roles

Pattern for demand transitions (Phase 5):
  TRANSITION_ROLES = {
      ("draft", "open"): [Role.SM, Role.RECRUITER],
      ("open", "matching"): [Role.RECRUITER],
      # ... add transitions as demand lifecycle is built
  }
  def require_transition(from_state, to_state):
      allowed = TRANSITION_ROLES.get((from_state, to_state), [])
      return require_roles(*allowed)
"""
import uuid
from enum import StrEnum
from typing import AsyncGenerator, Callable

import jwt
from fastapi import Depends, Header, HTTPException, Query, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import app_async_session, get_db  # noqa: F401 — re-exported
from app.models.user import User

bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),  # superuser — user lookup is cross-tenant
) -> User:
    """Decode the Bearer JWT and return the authenticated User.

    Raises HTTP 401 if:
    - No token provided
    - Token is expired
    - Token is invalid
    - Token type is not 'access'
    - User not found, inactive, or email unverified
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials
    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id_str = payload.get("sub")
    if not user_id_str:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    try:
        user_id = uuid.UUID(user_id_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user ID in token",
        )

    user = await db.get(User, user_id)

    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )

    if not user.email_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not verified",
        )

    return user


# ---------------------------------------------------------------------------
# Role enum — all 5 application roles
# ---------------------------------------------------------------------------


class Role(StrEnum):
    """Application roles.

    ADMIN      — cross-tenant admin; uses superuser engine; bypasses RLS
    SM         — staffing manager; tenant-scoped; may be assigned to multiple tenants
    RECRUITER  — recruiter; tenant-scoped; may be assigned to multiple tenants
    CUSTOMER   — hiring manager; belongs to exactly one tenant
    CANDIDATE  — job applicant; belongs to exactly one tenant (or none)
    """

    ADMIN = "admin"
    SM = "sm"
    RECRUITER = "recruiter"
    CUSTOMER = "customer"
    CANDIDATE = "candidate"


# ---------------------------------------------------------------------------
# get_tenant_db — RLS-enforced session using bryton_app role
# ---------------------------------------------------------------------------


async def get_tenant_db(
    current_user: User = Depends(get_current_user),
    x_tenant_id: str | None = Header(default=None, alias="X-Tenant-ID"),
    tenant_id_param: uuid.UUID | None = Query(default=None, alias="tenant_id"),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield an AsyncSession with RLS tenant context set via SET LOCAL.

    Uses app_async_session (bryton_app role — NOT superuser).
    SET LOCAL scopes the GUC to the current transaction only, preventing
    tenant context from leaking across pooled connections.

    Tenant resolution:
    - Admin: requires X-Tenant-ID header or tenant_id query param (cross-tenant by nature)
    - SM/Recruiter: uses X-Tenant-ID header if provided; falls back to first assignment
    - Customer/Candidate: uses user.tenant_id directly (single tenant)

    CRITICAL: Uses SET LOCAL, never bare SET. Without LOCAL, the GUC persists
    for the entire connection lifetime and leaks tenant data across requests.
    """
    user_role = current_user.role

    # Resolve tenant_id based on role
    resolved_tenant_id: uuid.UUID | None = None

    if user_role == Role.ADMIN:
        # Admin must explicitly pass tenant context to use this dependency
        if x_tenant_id:
            try:
                resolved_tenant_id = uuid.UUID(x_tenant_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-Tenant-ID header — must be a valid UUID",
                )
        elif tenant_id_param:
            resolved_tenant_id = tenant_id_param
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Admin must provide X-Tenant-ID header or tenant_id query param to use tenant-scoped session",
            )

    elif user_role in (Role.SM, Role.RECRUITER):
        # SM/Recruiter: use header if provided, otherwise look up from assignments
        if x_tenant_id:
            try:
                resolved_tenant_id = uuid.UUID(x_tenant_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-Tenant-ID header — must be a valid UUID",
                )
        elif tenant_id_param:
            resolved_tenant_id = tenant_id_param
        elif current_user.tenant_id:
            # Fall back to primary tenant_id on user record
            resolved_tenant_id = current_user.tenant_id
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="SM/Recruiter with multiple tenant assignments must provide X-Tenant-ID header",
            )

    else:
        # Customer / Candidate — single tenant
        if current_user.tenant_id is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="No tenant context — user is not assigned to a tenant",
            )
        resolved_tenant_id = current_user.tenant_id

    # Open a bryton_app session and set tenant context via SET LOCAL
    # SET LOCAL is scoped to the current transaction only — prevents context leaks
    async with app_async_session() as session:
        try:
            await session.execute(
                text("SET LOCAL app.current_tenant = :tid"),
                {"tid": str(resolved_tenant_id)},
            )
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# require_roles — RBAC enforcement factory
# ---------------------------------------------------------------------------


def require_roles(*roles: Role) -> Callable:
    """Factory returning a FastAPI dependency that enforces role membership.

    Returns HTTP 403 if the current user's role is not in the allowed roles list.

    Usage:
        @router.post("/tenants")
        async def create_tenant(
            current_user: User = Depends(require_roles(Role.ADMIN)),
            db: AsyncSession = Depends(get_db),
        ):
            ...
    """

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        try:
            user_role = Role(current_user.role)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Unknown role: {current_user.role}",
            )
        if user_role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires one of: {[r.value for r in roles]}",
            )
        return current_user

    return _check


# ---------------------------------------------------------------------------
# get_admin_db — superuser session + Admin role check (convenience)
# ---------------------------------------------------------------------------


async def get_admin_db(
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> AsyncGenerator[AsyncSession, None]:
    """Yield the superuser DB session after verifying the caller is an Admin.

    Admin endpoints bypass RLS intentionally — they need cross-tenant visibility.
    For tenant-scoped operations, use get_tenant_db instead.
    """
    yield db
