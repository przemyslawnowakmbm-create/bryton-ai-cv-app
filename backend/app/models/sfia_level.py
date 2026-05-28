import uuid

from sqlalchemy import Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class SfiaLevel(Base):
    __tablename__ = "sfia_levels"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    level: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)  # 1-7
    label: Mapped[str] = mapped_column(String(50), nullable=False)  # "Follow", "Assist", etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
