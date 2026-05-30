"""Contracts and Rate Cards API endpoints.

All contract and rate card endpoints use get_tenant_db for RLS-enforced tenant scoping.
Admin callers must provide X-Tenant-ID header (required by get_tenant_db).
SM callers use their resolved tenant (from X-Tenant-ID header or primary tenant_id).

Endpoints:
  POST   /contracts                           — Create contract (Admin, SM)
  GET    /contracts                           — List contracts (Admin, SM, Recruiter)
  GET    /contracts/{id}                      — Contract detail (Admin, SM, Recruiter)
  PATCH  /contracts/{id}                      — Update contract (Admin, SM)
  POST   /contracts/{id}/deactivate           — Deactivate contract (Admin)

  POST   /contracts/{id}/rate-card            — Add rate card entry (Admin, SM)
  GET    /contracts/{id}/rate-card            — List rate card entries (all authenticated roles)
  PATCH  /contracts/{id}/rate-card/{rid}      — Update rate card entry (Admin, SM)
  DELETE /contracts/{id}/rate-card/{rid}      — Delete rate card entry (Admin, SM)
"""
import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.sql import text

from app.deps import Role, get_tenant_db, require_roles
from app.models.contract import Contract
from app.models.profile_catalogue import ProfileCatalogue
from app.models.rate_card import RateCardEntry
from app.models.user import User
from app.schemas.contract import (
    ContractCreate,
    ContractResponse,
    ContractUpdate,
    RateCardEntryCreate,
    RateCardEntryResponse,
    RateCardEntryUpdate,
)
from app.services.audit import log_audit_event

router = APIRouter(tags=["contracts"])


def _get_client_ip(request: Request) -> Optional[str]:
    """Extract client IP from request, handling proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else None


async def _resolve_tenant_id(
    current_user: User,
    db: AsyncSession,
    x_tenant_id: Optional[str] = None,
) -> uuid.UUID:
    """Resolve the effective tenant_id for write operations.

    Resolution strategy (mirrors get_tenant_db logic):
    1. Try to read from the PostgreSQL GUC set by get_tenant_db via SET LOCAL.
       This is the canonical source of truth in production.
    2. Fall back: Admin uses X-Tenant-ID header directly.
    3. Fall back: SM/Recruiter/Customer use current_user.tenant_id.

    The dual strategy ensures correctness in production (GUC always set by get_tenant_db)
    AND test compatibility (SQLite doesn't support current_setting GUC).
    """
    # Try PostgreSQL GUC first (set by get_tenant_db via SET LOCAL)
    try:
        result = await db.execute(
            text("SELECT current_setting('app.current_tenant', true)")
        )
        raw = result.scalar_one_or_none()
        if raw and raw.strip():
            tenant_uuid = uuid.UUID(raw.strip())
            return tenant_uuid
    except Exception:
        # SQLite or other non-PostgreSQL backends don't support current_setting
        pass

    # Fall back to header (Admin cross-tenant) or user's tenant
    user_role = Role(current_user.role)
    if user_role == Role.ADMIN:
        if x_tenant_id:
            try:
                return uuid.UUID(x_tenant_id)
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid X-Tenant-ID header — must be a valid UUID",
                )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin must provide X-Tenant-ID header to create/update tenant-scoped resources",
        )

    # SM, Recruiter, Customer: use their primary tenant_id
    if current_user.tenant_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No tenant context — user is not assigned to a tenant",
        )
    return current_user.tenant_id


# ---------------------------------------------------------------------------
# POST /contracts — Create contract
# ---------------------------------------------------------------------------


@router.post("/contracts", status_code=status.HTTP_201_CREATED, response_model=ContractResponse)
async def create_contract(
    body: ContractCreate,
    request: Request,
    x_tenant_id: Optional[str] = Header(default=None, alias="X-Tenant-ID"),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ContractResponse:
    """Create a framework contract (Admin or SM).

    The tenant_id is resolved from the RLS session context (PostgreSQL GUC),
    falling back to X-Tenant-ID header (Admin) or user.tenant_id (SM).
    Admin must pass X-Tenant-ID header. SM uses their resolved tenant.
    """
    tenant_id = await _resolve_tenant_id(current_user, db, x_tenant_id)

    contract = Contract(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        reference=body.reference,
        title=body.title,
        lot_number=body.lot_number,
        start_date=body.start_date,
        end_date=body.end_date,
        max_value=body.max_value,
        currency=body.currency,
        status=body.status,
    )
    db.add(contract)
    await db.flush()

    await log_audit_event(
        db,
        action="contract.created",
        tenant_id=tenant_id,
        actor_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        payload={
            "reference": contract.reference,
            "title": contract.title,
            "lot_number": contract.lot_number,
            "status": contract.status,
        },
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(contract)
    return ContractResponse.model_validate(contract)


# ---------------------------------------------------------------------------
# GET /contracts — List contracts
# ---------------------------------------------------------------------------


@router.get("/contracts", response_model=List[ContractResponse])
async def list_contracts(
    contract_status: Optional[str] = Query(default=None, alias="status"),
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM, Role.RECRUITER)),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[ContractResponse]:
    """List all contracts for the current tenant (Admin, SM, Recruiter).

    RLS on contracts table ensures only tenant-scoped rows are returned.
    Optional filter by status query param.
    """
    stmt = select(Contract)

    if contract_status is not None:
        stmt = stmt.where(Contract.status == contract_status)

    stmt = stmt.order_by(Contract.created_at.desc())
    result = await db.execute(stmt)
    contracts = result.scalars().all()
    return [ContractResponse.model_validate(c) for c in contracts]


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id} — Contract detail
# ---------------------------------------------------------------------------


@router.get("/contracts/{contract_id}", response_model=ContractResponse)
async def get_contract(
    contract_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM, Role.RECRUITER)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ContractResponse:
    """Get a single contract by ID (Admin, SM, Recruiter).

    Returns 404 if not found or outside current tenant (RLS filters out other tenants).
    """
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )
    return ContractResponse.model_validate(contract)


# ---------------------------------------------------------------------------
# PATCH /contracts/{contract_id} — Update contract
# ---------------------------------------------------------------------------


@router.patch("/contracts/{contract_id}", response_model=ContractResponse)
async def update_contract(
    contract_id: uuid.UUID,
    body: ContractUpdate,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ContractResponse:
    """Partially update a contract (Admin or SM).

    Only non-None fields in the body are applied. Logs contract.updated to audit trail.
    """
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(contract, field, value)

    # Serialize update_data for audit payload — convert date/Decimal to string
    serialized = {
        k: v.isoformat() if hasattr(v, "isoformat") else float(v) if hasattr(v, "__float__") and not isinstance(v, bool) else v
        for k, v in update_data.items()
    }

    await log_audit_event(
        db,
        action="contract.updated",
        tenant_id=contract.tenant_id,
        actor_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        payload={"updated_fields": list(update_data.keys()), **serialized},
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(contract)
    return ContractResponse.model_validate(contract)


# ---------------------------------------------------------------------------
# POST /contracts/{contract_id}/deactivate — Deactivate contract
# ---------------------------------------------------------------------------


@router.post("/contracts/{contract_id}/deactivate", response_model=ContractResponse)
async def deactivate_contract(
    contract_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN)),
    db: AsyncSession = Depends(get_tenant_db),
) -> ContractResponse:
    """Deactivate a contract (Admin only) — sets status to 'suspended'.

    Logs contract.deactivated to the audit trail.
    """
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    previous_status = contract.status
    contract.status = "suspended"

    await log_audit_event(
        db,
        action="contract.deactivated",
        tenant_id=contract.tenant_id,
        actor_id=current_user.id,
        entity_type="contract",
        entity_id=contract.id,
        payload={"previous_status": previous_status, "new_status": "suspended"},
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(contract)
    return ContractResponse.model_validate(contract)


# ---------------------------------------------------------------------------
# POST /contracts/{contract_id}/rate-card — Add rate card entry
# ---------------------------------------------------------------------------


@router.post(
    "/contracts/{contract_id}/rate-card",
    status_code=status.HTTP_201_CREATED,
    response_model=RateCardEntryResponse,
)
async def create_rate_card_entry(
    contract_id: uuid.UUID,
    body: RateCardEntryCreate,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> RateCardEntryResponse:
    """Add a rate card entry to a contract (Admin or SM).

    Verifies the contract and profile exist within the current tenant (RLS-enforced).
    margin is always None in Phase 3 (cost_rate context not available until Phase 5/6).
    """
    # Verify contract exists (RLS ensures it belongs to current tenant)
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    # Verify profile exists
    profile = await db.get(ProfileCatalogue, body.profile_id)
    if profile is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Profile not found",
        )

    entry = RateCardEntry(
        id=uuid.uuid4(),
        contract_id=contract_id,
        profile_id=body.profile_id,
        sfia_level=body.sfia_level,
        max_daily_rate=body.max_daily_rate,
        currency=body.currency,
        effective_from=body.effective_from,
        effective_to=body.effective_to,
    )
    db.add(entry)
    await db.flush()

    await log_audit_event(
        db,
        action="rate_card.created",
        tenant_id=contract.tenant_id,
        actor_id=current_user.id,
        entity_type="rate_card_entry",
        entity_id=entry.id,
        payload={
            "contract_id": str(contract_id),
            "profile_id": str(body.profile_id),
            "sfia_level": body.sfia_level,
            "max_daily_rate": float(body.max_daily_rate),
            "effective_from": body.effective_from.isoformat(),
            "effective_to": body.effective_to.isoformat(),
        },
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(entry)

    # margin is None in Phase 3 — cost_rate context not available until Phase 5/6
    response = RateCardEntryResponse.model_validate(entry)
    response.margin = None
    return response


# ---------------------------------------------------------------------------
# GET /contracts/{contract_id}/rate-card — List rate card entries
# ---------------------------------------------------------------------------


@router.get(
    "/contracts/{contract_id}/rate-card",
    response_model=List[RateCardEntryResponse],
)
async def list_rate_card_entries(
    contract_id: uuid.UUID,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM, Role.RECRUITER, Role.CUSTOMER)),
    db: AsyncSession = Depends(get_tenant_db),
) -> List[RateCardEntryResponse]:
    """List all rate card entries for a contract.

    Customer CAN view rate card entries (they see the ceilings) but margin is hidden.
    SM/Admin/Recruiter see margin=None in Phase 3 (no candidate context yet).
    CONTRACT-04: margin visibility is role-gated — always None in Phase 3 since
    margin calculation requires a candidate's cost_rate (available Phase 5/6).
    """
    # Verify contract exists
    contract = await db.get(Contract, contract_id)
    if contract is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Contract not found",
        )

    stmt = (
        select(RateCardEntry)
        .where(RateCardEntry.contract_id == contract_id)
        .order_by(RateCardEntry.sfia_level, RateCardEntry.effective_from)
    )
    result = await db.execute(stmt)
    entries = result.scalars().all()

    # margin=None for all in Phase 3 — candidate cost_rate not available yet
    responses = []
    for entry in entries:
        r = RateCardEntryResponse.model_validate(entry)
        r.margin = None
        responses.append(r)
    return responses


# ---------------------------------------------------------------------------
# PATCH /contracts/{contract_id}/rate-card/{rate_card_id} — Update entry
# ---------------------------------------------------------------------------


@router.patch(
    "/contracts/{contract_id}/rate-card/{rate_card_id}",
    response_model=RateCardEntryResponse,
)
async def update_rate_card_entry(
    contract_id: uuid.UUID,
    rate_card_id: uuid.UUID,
    body: RateCardEntryUpdate,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> RateCardEntryResponse:
    """Partially update a rate card entry (Admin or SM).

    Verifies the entry belongs to the specified contract.
    Logs rate_card.updated to the audit trail.
    """
    entry = await db.get(RateCardEntry, rate_card_id)
    if entry is None or entry.contract_id != contract_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card entry not found",
        )

    update_data = body.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(entry, field, value)

    # Reload contract for audit tenant_id
    contract = await db.get(Contract, contract_id)
    tenant_id = contract.tenant_id if contract else None

    await log_audit_event(
        db,
        action="rate_card.updated",
        tenant_id=tenant_id,
        actor_id=current_user.id,
        entity_type="rate_card_entry",
        entity_id=entry.id,
        payload={
            "updated_fields": list(update_data.keys()),
            **{
                k: float(v) if hasattr(v, "__float__") and not isinstance(v, bool)
                else v.isoformat() if hasattr(v, "isoformat")
                else v
                for k, v in update_data.items()
            },
        },
        ip_address=_get_client_ip(request),
    )

    await db.commit()
    await db.refresh(entry)

    response = RateCardEntryResponse.model_validate(entry)
    response.margin = None
    return response


# ---------------------------------------------------------------------------
# DELETE /contracts/{contract_id}/rate-card/{rate_card_id} — Delete entry
# ---------------------------------------------------------------------------


@router.delete(
    "/contracts/{contract_id}/rate-card/{rate_card_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_rate_card_entry(
    contract_id: uuid.UUID,
    rate_card_id: uuid.UUID,
    request: Request,
    current_user: User = Depends(require_roles(Role.ADMIN, Role.SM)),
    db: AsyncSession = Depends(get_tenant_db),
) -> None:
    """Hard delete a rate card entry (Admin or SM).

    Verifies the entry belongs to the specified contract.
    Logs rate_card.deleted to the audit trail.
    Returns 204 No Content on success.
    """
    entry = await db.get(RateCardEntry, rate_card_id)
    if entry is None or entry.contract_id != contract_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Rate card entry not found",
        )

    # Reload contract for audit tenant_id
    contract = await db.get(Contract, contract_id)
    tenant_id = contract.tenant_id if contract else None

    await log_audit_event(
        db,
        action="rate_card.deleted",
        tenant_id=tenant_id,
        actor_id=current_user.id,
        entity_type="rate_card_entry",
        entity_id=entry.id,
        payload={
            "contract_id": str(contract_id),
            "profile_id": str(entry.profile_id),
            "sfia_level": entry.sfia_level,
        },
        ip_address=_get_client_ip(request),
    )

    await db.delete(entry)
    await db.commit()
