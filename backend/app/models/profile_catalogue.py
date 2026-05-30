"""ProfileCatalogue model — profile_catalogue table.

Tenant-scoped (RLS enforced via migration 005).
Represents a job/role profile template that can be used as a template for demands.
Nullable tenant_id allows global (system-wide) profiles.
Nullable contract_id allows tenant-level profiles not tied to a specific contract.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, CheckConstraint, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class ProfileCatalogue(Base):
    __tablename__ = "profile_catalogue"

    __table_args__ = (
        UniqueConstraint("contract_id", "code", name="uq_profile_code_contract"),
        CheckConstraint("sfia_level_min BETWEEN 1 AND 7", name="ck_profile_sfia_min"),
        CheckConstraint("sfia_level_max BETWEEN 1 AND 7", name="ck_profile_sfia_max"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable allows global profiles not tied to a specific tenant
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="RESTRICT"),
        nullable=True,
    )
    # Nullable allows tenant-level profiles not tied to a specific contract
    contract_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="RESTRICT"),
        nullable=True,
    )
    code: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    sfia_level_min: Mapped[int] = mapped_column(Integer, nullable=False)
    sfia_level_max: Mapped[int] = mapped_column(Integer, nullable=False)
    min_years_exp: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    min_education: Mapped[str | None] = mapped_column(String(50), nullable=True)
    required_clearance: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
