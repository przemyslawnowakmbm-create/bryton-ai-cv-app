"""Demand model — demands table (STUB).

Tenant-scoped (RLS enforced via migration 005).
MINIMAL STUB for Phase 3. Phase 5 will add remaining columns via ALTER TABLE:
  - title, description, sfia_level_min/max, required_skills, etc.
  - status, priority, target_start_date, budget, etc.

Phase 3 fields only:
  - id, tenant_id, profile_id (FK for pre-population), profile_snapshot (JSONB diff)
  - created_at, updated_at

profile_snapshot: serialised profile state at demand creation time.
Used by PROFILE-03 profile-diff endpoint to compute field-level deviations.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class Demand(Base):
    __tablename__ = "demands"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # The profile this demand was optionally created from (pre-population)
    profile_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_catalogue.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Serialised profile state at demand creation time — supports PROFILE-03 diff
    profile_snapshot: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
