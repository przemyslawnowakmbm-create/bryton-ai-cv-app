import uuid

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class EscoSkill(Base):
    __tablename__ = "esco_skills"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    uri: Mapped[str] = mapped_column(
        String(512), unique=True, nullable=False, index=True
    )
    preferred_label: Mapped[str] = mapped_column(
        String(512), nullable=False, index=True
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    concept_type: Mapped[str] = mapped_column(
        String(50), nullable=False
    )  # "KnowledgeSkillCompetence"
    isco_group: Mapped[str | None] = mapped_column(String(20), nullable=True)
    synced_at: Mapped[str] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
