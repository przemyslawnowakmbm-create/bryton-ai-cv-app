"""Approval chain and audit log API endpoints.

All approval endpoints use get_db (superuser engine) for cross-tenant visibility:
  - Approvals can cross tenant boundaries (SM in tenant A approving for tenant B)
  - Admin needs to see all approvals across all tenants
  - Audit log is cross-tenant by definition

Endpoints:
  POST /approvals                     — Create approval request (any authenticated user)
  GET  /approvals                     — List approvals (filtered by role)
  GET  /approvals/{id}                — Get single approval (requester, approver, or Admin)
  POST /approvals/{id}/decide         — Decide on approval (approver or Admin)
  GET  /audit-log                     — Query audit log (Admin only)
"""
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.deps import Role, get_current_user, require_roles
from app.models.approval import ApprovalRequest
from app.models.audit_log import AuditLog
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.approval import (
    ApprovalCreate,
    ApprovalDecision,
    ApprovalResponse,
    AuditLogResponse,
)
from app.services.approval import route_approval
from app.services.audit import log_audit_event

router = APIRouter(tags=["approvals"])


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


# ---------------------------------------------------------------------------
# POST /approvals — Create approval request
# ---------------------------------------------------------------------------


@router.post("/approvals", status_code=status.HTTP_201_CREATED, response_model=ApprovalResponse)
async def create_approval_request(
    body: ApprovalCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Create an approval request with justification and context data.

    Determines the approver via route_approval() based on tenant config.
    Logs 'approval.created' to the audit trail.
    Uses superuser engine for cross-tenant approval routing and Admin visibility.
    """
    # Resolve tenant context from current user
    tenant_id = body.approver_id  # approver_id is optional override; use user's tenant
    if current_user.tenant_id is None and body.approver_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User has no tenant context — cannot create an approval request",
        )

    # Use current_user.tenant_id as the approval's tenant
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User must belong to a tenant to create an approval request",
        )

    effective_tenant_id = current_user.tenant_id

    # Load tenant for approval gate config
    tenant = await db.get(Tenant, effective_tenant_id)
    if tenant is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Tenant not found",
        )

    # Use body.approver_id if provided, otherwise route automatically
    if body.approver_id is not None:
        approver_uuid = body.approver_id
    else:
        approver_uuid = await route_approval(db, tenant, body.type)

    approval = ApprovalRequest(
        id=uuid.uuid4(),
        tenant_id=effective_tenant_id,
        requester_id=current_user.id,
        approver_id=approver_uuid,
        type=body.type,
        status="pending",
        context_data=body.context_data,
        justification=body.justification,
    )
    db.add(approval)
    await db.flush()

    # Log audit event
    await log_audit_event(
        db,
        action="approval.created",
        tenant_id=effective_tenant_id,
        actor_id=current_user.id,
        entity_type="approval_request",
        entity_id=approval.id,
        payload={
            "type": approval.type,
            "requester_id": str(current_user.id),
            "approver_id": str(approver_uuid) if approver_uuid else None,
            "justification": approval.justification,
            "context_data": approval.context_data,
        },
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(approval)
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# GET /approvals — List approvals (role-filtered)
# ---------------------------------------------------------------------------


@router.get("/approvals", response_model=List[ApprovalResponse])
async def list_approvals(
    approval_status: Optional[str] = Query(default=None, alias="status"),
    approval_type: Optional[str] = Query(default=None, alias="type"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> List[ApprovalResponse]:
    """List approval requests filtered by caller's role.

    Admin: all approvals (optional filter by status, type).
    SM: approvals where approver_id = current_user.id.
    Recruiter: approvals where requester_id = current_user.id.
    Other roles: 403.
    """
    user_role = Role(current_user.role)

    if user_role == Role.ADMIN:
        stmt = select(ApprovalRequest)
    elif user_role == Role.SM:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.approver_id == current_user.id
        )
    elif user_role == Role.RECRUITER:
        stmt = select(ApprovalRequest).where(
            ApprovalRequest.requester_id == current_user.id
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Admin, SM, and Recruiter can list approvals",
        )

    if approval_status is not None:
        stmt = stmt.where(ApprovalRequest.status == approval_status)
    if approval_type is not None:
        stmt = stmt.where(ApprovalRequest.type == approval_type)

    stmt = stmt.order_by(ApprovalRequest.created_at.desc())
    result = await db.execute(stmt)
    approvals = result.scalars().all()
    return [ApprovalResponse.model_validate(a) for a in approvals]


# ---------------------------------------------------------------------------
# GET /approvals/{approval_id} — Get single approval
# ---------------------------------------------------------------------------


@router.get("/approvals/{approval_id}", response_model=ApprovalResponse)
async def get_approval_request(
    approval_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Get a single approval request.

    Access: requester, assigned approver, or Admin.
    Returns 404 if not found, 403 if not authorized.
    """
    approval = await db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    user_role = Role(current_user.role)
    is_requester = approval.requester_id == current_user.id
    is_approver = approval.approver_id == current_user.id
    is_admin = user_role == Role.ADMIN

    if not (is_requester or is_approver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this approval request",
        )

    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# POST /approvals/{approval_id}/decide — Make a decision
# ---------------------------------------------------------------------------


@router.post("/approvals/{approval_id}/decide", response_model=ApprovalResponse)
async def decide_approval_request(
    approval_id: uuid.UUID,
    body: ApprovalDecision,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ApprovalResponse:
    """Make a decision on an approval request (approve, reject, or request changes).

    Access: assigned approver or Admin.
    Logs 'approval.{status}' to the audit trail with full context.
    Uses superuser engine for cross-tenant visibility.
    """
    approval = await db.get(ApprovalRequest, approval_id)
    if approval is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Approval request not found",
        )

    user_role = Role(current_user.role)
    is_approver = approval.approver_id == current_user.id
    is_admin = user_role == Role.ADMIN

    if not (is_approver or is_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only the assigned approver or an Admin can decide on this approval request",
        )

    # Update approval
    now = datetime.now(timezone.utc)
    approval.status = body.status
    approval.decision_reason = body.decision_reason
    approval.decided_at = now

    # Log audit event with full context
    await log_audit_event(
        db,
        action=f"approval.{body.status}",
        tenant_id=approval.tenant_id,
        actor_id=current_user.id,
        entity_type="approval_request",
        entity_id=approval.id,
        payload={
            "approval_id": str(approval.id),
            "type": approval.type,
            "requester_id": str(approval.requester_id),
            "approver_id": str(current_user.id),
            "justification": approval.justification,
            "decision_reason": body.decision_reason,
            "context_data": approval.context_data,
            "decided_at": now.isoformat(),
        },
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(approval)
    return ApprovalResponse.model_validate(approval)


# ---------------------------------------------------------------------------
# GET /audit-log — Admin query
# ---------------------------------------------------------------------------


@router.get("/audit-log", response_model=List[AuditLogResponse])
async def query_audit_log(
    date_from: Optional[datetime] = Query(default=None),
    date_to: Optional[datetime] = Query(default=None),
    actor_id: Optional[uuid.UUID] = Query(default=None),
    action: Optional[str] = Query(default=None),
    entity_type: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_db),
) -> List[AuditLogResponse]:
    """Query audit log with optional filters (Admin only).

    Filters: date_from, date_to, actor_id, action, entity_type.
    Paginated via limit/offset.
    Returns newest entries first.
    """
    stmt = select(AuditLog)

    if date_from is not None:
        stmt = stmt.where(AuditLog.created_at >= date_from)
    if date_to is not None:
        stmt = stmt.where(AuditLog.created_at <= date_to)
    if actor_id is not None:
        stmt = stmt.where(AuditLog.actor_id == actor_id)
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if entity_type is not None:
        stmt = stmt.where(AuditLog.entity_type == entity_type)

    stmt = stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    result = await db.execute(stmt)
    entries = result.scalars().all()
    return [AuditLogResponse.model_validate(e) for e in entries]
