"""RateCardEntry model — rate_cards table.

Tenant-scoped via contract (RLS enforced via migration 005).
Defines the maximum daily rate ceiling per contract, profile, and SFIA level.
sfia_level is stored as INTEGER with CHECK constraint (1-7) — NOT a UUID FK to sfia_levels.
Margin (ceiling - cost_rate) is NEVER stored — computed at read time by the API layer.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import CheckConstraint, Date, DateTime, ForeignKey, Integer, Numeric, String, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RateCardEntry(Base):
    __tablename__ = "rate_cards"

    __table_args__ = (
        UniqueConstraint(
            "contract_id", "profile_id", "sfia_level", "effective_from",
            name="uq_rate_card_entry",
        ),
        CheckConstraint("sfia_level BETWEEN 1 AND 7", name="ck_rate_card_sfia_level"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    contract_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("contracts.id", ondelete="CASCADE"),
        nullable=False,
    )
    profile_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("profile_catalogue.id", ondelete="RESTRICT"),
        nullable=False,
    )
    # Direct integer (1-7) with CHECK constraint — NOT a UUID FK to sfia_levels
    sfia_level: Mapped[int] = mapped_column(Integer, nullable=False)
    # Numeric(10, 2) — never float — avoids floating point precision issues
    max_daily_rate: Mapped[object] = mapped_column(Numeric(10, 2), nullable=False)
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="EUR")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
