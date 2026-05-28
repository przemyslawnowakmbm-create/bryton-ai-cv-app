"""ApprovalRequest model — approval_requests table.

Tenant-scoped (RLS enforced via migration 004).
Used for governance workflows: shortlist_submission, rate_override, candidate_above_rate.
Status lifecycle: pending -> approved | rejected | changes_requested.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ApprovalRequest(Base):
    __tablename__ = "approval_requests"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    requester_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # approver_id is null until assigned/routed
    approver_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Values: 'shortlist_submission', 'rate_override', 'candidate_above_rate'
    type: Mapped[str] = mapped_column(String(50), nullable=False)
    # Values: 'pending', 'approved', 'rejected', 'changes_requested'
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    # Contextual data: demand_id, candidate_id, rate info, etc.
    context_data: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    justification: Mapped[str] = mapped_column(Text, nullable=False)
    decision_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    decided_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
