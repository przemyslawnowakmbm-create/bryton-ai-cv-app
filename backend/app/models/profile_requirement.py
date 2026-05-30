"""ProfileRequirement model — profile_requirements table.

Tenant-scoped (RLS enforced via migration 005).
Stores individual requirements for a profile (skills, certifications, languages, etc.).
tenant_id is DENORMALISED from the parent profile for RLS enforcement — avoids complex
JOIN-based policies. Set at INSERT time from the parent profile's tenant_id.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProfileRequirement(Base):
    __tablename__ = "profile_requirements"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_catalogue.id", ondelete="CASCADE"),
        nullable=False,
    )
    # Denormalised for RLS — mirrors the parent profile's tenant_id
    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Values: skill, certification, language, clearance, education
    req_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    # Only used when req_type='language' (e.g., 'A1', 'B2', 'C1')
    min_cefr_level: Mapped[str | None] = mapped_column(String(2), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
