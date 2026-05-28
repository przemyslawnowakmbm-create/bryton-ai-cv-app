"""AuditLog model — audit_log table.

Append-only — no UPDATE or DELETE operations allowed.
Not RLS-protected (cross-tenant for Admin queries; access controlled at application level).
Records: approval decisions, user management actions, and other governance events.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable — some actions are cross-tenant (e.g., admin creates user)
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Nullable — system-initiated actions have no actor
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    # Action name — e.g., 'approval.created', 'approval.approved', 'user.created'
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    # Entity being acted on — e.g., 'approval_request', 'user', 'tenant'
    entity_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    entity_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True)
    # Full context snapshot for compliance auditing
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    # IPv4 or IPv6 — up to 45 chars for IPv6
    ip_address: Mapped[str | None] = mapped_column(String(45), nullable=True)
    # No updated_at — audit log is append-only; records are immutable
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
