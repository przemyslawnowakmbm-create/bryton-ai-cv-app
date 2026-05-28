# Re-export Base from database.py to provide a single source of truth.
# All models should import Base from app.database (or here — both refer to the same class).
from app.database import Base  # noqa: F401

__all__ = ["Base"]
