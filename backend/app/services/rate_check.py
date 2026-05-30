"""Rate ceiling enforcement service.

CONTRACT-03: When a candidate is shortlisted for a demand linked to a contract,
this service checks the candidate's rate against the active rate card ceiling.
Raises RateCeilingExceeded (HTTP 409 at the caller) if the rate exceeds the ceiling.

Returns silently (None) when:
  - contract_id is None (demand has no linked contract)
  - profile_id is None
  - candidate_rate is None
  - No matching rate card entry found for the date range (no constraint applies)
  - An approved rate_override approval exists for the (demand, candidate) pair

Phase 5/6 shortlist endpoint usage:
  override = await has_approved_rate_override(db, demand_id, candidate_id)
  if not override:
      await check_rate_ceiling(db, contract_id, profile_id, sfia_level, candidate_rate)
  # proceeds if no exception raised
"""
import uuid
from datetime import date
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# IMPORTANT: RateCardEntry is in app.models.rate_card (NOT app.models.rate_card_entry)
from app.models.approval import ApprovalRequest
from app.models.profile_catalogue import ProfileCatalogue
from app.models.rate_card import RateCardEntry


class RateCeilingExceeded(Exception):
    """Raised when a candidate's rate exceeds the active rate card ceiling.

    Callers should catch this and return HTTP 409 with the structured error body
    per the architecture spec (Section 3.5).

    Attributes:
        candidate_rate: The candidate's requested rate (Decimal).
        ceiling:        The active max_daily_rate from the rate card entry.
        profile_code:   Profile code from the contract's profile catalogue entry.
        sfia_level:     The SFIA level (1-7) used for the ceiling lookup.
    """

    def __init__(
        self,
        candidate_rate: Decimal,
        ceiling: Decimal,
        profile_code: str,
        sfia_level: int,
    ) -> None:
        self.candidate_rate = candidate_rate
        self.ceiling = ceiling
        self.profile_code = profile_code
        self.sfia_level = sfia_level
        super().__init__(
            f"Candidate rate {candidate_rate} exceeds ceiling {ceiling} "
            f"for profile {profile_code} at SFIA level {sfia_level}"
        )


async def check_rate_ceiling(
    db: AsyncSession,
    contract_id: Optional[uuid.UUID],
    profile_id: Optional[uuid.UUID],
    sfia_level: int,
    candidate_rate: Optional[Decimal],
    today: Optional[date] = None,
) -> None:
    """Check candidate rate against the active rate card ceiling.

    Raises RateCeilingExceeded if candidate_rate > active ceiling.
    Returns None (silently) if:
      - contract_id is None
      - profile_id is None
      - candidate_rate is None
      - No matching active rate card entry found (no constraint applies)

    Args:
        db:             AsyncSession for database queries.
        contract_id:    The contract linked to the demand. None = no check.
        profile_id:     The profile UUID from the demand. None = no check.
        sfia_level:     The SFIA level (1-7) to look up in the rate card.
        candidate_rate: The candidate's requested daily rate. None = no check.
        today:          Override for the date comparison (default: date.today()).

    Raises:
        RateCeilingExceeded: When candidate_rate > active max_daily_rate.
    """
    # Skip check when inputs are missing — Pitfall 3 from RESEARCH.md
    if contract_id is None:
        return
    if profile_id is None:
        return
    if candidate_rate is None:
        return

    today = today or date.today()

    stmt = (
        select(RateCardEntry)
        .where(
            RateCardEntry.contract_id == contract_id,
            RateCardEntry.profile_id == profile_id,
            RateCardEntry.sfia_level == sfia_level,
            RateCardEntry.effective_from <= today,
            RateCardEntry.effective_to >= today,
        )
        .limit(1)
    )
    result = await db.execute(stmt)
    entry = result.scalar_one_or_none()

    # No active entry — no constraint applies
    if entry is None:
        return

    if candidate_rate > entry.max_daily_rate:
        # Load profile code for error context
        # The rate_card table does not denormalise profile_code; join to profile_catalogue
        profile = await db.get(ProfileCatalogue, entry.profile_id)
        profile_code = profile.code if profile else str(entry.profile_id)

        raise RateCeilingExceeded(
            candidate_rate=candidate_rate,
            ceiling=Decimal(str(entry.max_daily_rate)),
            profile_code=profile_code,
            sfia_level=sfia_level,
        )


async def has_approved_rate_override(
    db: AsyncSession,
    demand_id: uuid.UUID,
    candidate_id: uuid.UUID,
) -> bool:
    """Check if an approved rate_override approval exists for a (demand, candidate) pair.

    Returns True if a matching approved rate_override ApprovalRequest is found.
    Called by the Phase 5/6 shortlist endpoint BEFORE check_rate_ceiling.
    If True, the rate check is bypassed.

    Args:
        db:           AsyncSession for database queries.
        demand_id:    The demand UUID to match in context_data.
        candidate_id: The candidate UUID to match in context_data.

    Returns:
        True if an approved rate_override approval exists for this pair.

    Note:
        # TODO (Phase 5/6): Replace Python-side filtering with a JSONB containment query
        # for production performance. Example:
        #   .where(ApprovalRequest.context_data.contains(
        #       {"demand_id": str(demand_id), "candidate_id": str(candidate_id)}
        #   ))
        # Currently using Python-side filter for SQLite test compatibility.
    """
    # TODO (Phase 5/6): Replace Python-side filtering with a JSONB containment query
    # for production performance. Example:
    #   .where(ApprovalRequest.context_data.contains(
    #       {"demand_id": str(demand_id), "candidate_id": str(candidate_id)}
    #   ))
    # Currently using Python-side filter for SQLite test compatibility.
    stmt = select(ApprovalRequest).where(
        ApprovalRequest.type == "rate_override",
        ApprovalRequest.status == "approved",
    )
    result = await db.execute(stmt)
    for approval in result.scalars().all():
        ctx = approval.context_data or {}
        if (
            ctx.get("demand_id") == str(demand_id)
            and ctx.get("candidate_id") == str(candidate_id)
        ):
            return True
    return False
