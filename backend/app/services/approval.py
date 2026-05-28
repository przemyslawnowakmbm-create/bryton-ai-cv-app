"""Approval routing service.

Provides route_approval() — determines the correct approver user_id for a given
approval type within a tenant. Reads tenant.config["approval_gates"] to check
whether the gate is active.

Routing rules:
  shortlist_submission  -> SM assigned to this tenant
  rate_override         -> any active Admin user
  candidate_above_rate  -> SM assigned to this tenant

Returns None if the gate is disabled (auto-approve) or no suitable approver is found.
"""
import uuid
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tenant import Tenant
from app.models.user import User
from app.models.user_tenant import UserTenantAssignment


async def route_approval(
    db: AsyncSession,
    tenant: Tenant,
    approval_type: str,
) -> Optional[uuid.UUID]:
    """Determine the approver user_id for an approval request.

    Reads tenant.config["approval_gates"] to check if this gate is active.
    If the gate is disabled, returns None (auto-approve semantics).

    Args:
        db:            AsyncSession — superuser session for cross-tenant lookup.
        tenant:        Tenant instance — used for config lookup and SM assignment.
        approval_type: One of 'shortlist_submission', 'rate_override', 'candidate_above_rate'.

    Returns:
        UUID of the assigned approver, or None if gate is disabled or no approver found.
    """
    # Check if this gate is active in tenant config
    config = tenant.config or {}
    approval_gates = config.get("approval_gates", {})

    # Default: all gates active if not specified
    gate_active = approval_gates.get(approval_type, True)
    if not gate_active:
        return None  # auto-approve

    if approval_type in ("shortlist_submission", "candidate_above_rate"):
        # Find an SM assigned to this tenant
        result = await db.execute(
            select(UserTenantAssignment)
            .where(UserTenantAssignment.tenant_id == tenant.id)
            .join(User, User.id == UserTenantAssignment.user_id)
            .where(User.role == "sm", User.is_active == True)  # noqa: E712
        )
        assignment = result.scalars().first()
        if assignment is not None:
            return assignment.user_id
        return None

    elif approval_type == "rate_override":
        # Find any active Admin user
        result = await db.execute(
            select(User)
            .where(User.role == "admin", User.is_active == True)  # noqa: E712
        )
        admin = result.scalars().first()
        if admin is not None:
            return admin.id
        return None

    # Unknown type — no approver
    return None
