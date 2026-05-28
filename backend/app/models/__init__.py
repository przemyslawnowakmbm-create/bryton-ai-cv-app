# Import all models so Alembic autodiscovery works.
# Wildcard-style imports ensure Base.metadata has all table definitions
# before alembic revision --autogenerate runs.
from app.models.tenant import Tenant  # noqa: F401
from app.models.user import User  # noqa: F401
from app.models.sfia_level import SfiaLevel  # noqa: F401
from app.models.esco_skill import EscoSkill  # noqa: F401
from app.models.refresh_token import RefreshToken  # noqa: F401
from app.models.email_token import EmailToken  # noqa: F401
from app.models.user_tenant import UserTenantAssignment  # noqa: F401

__all__ = ["Tenant", "User", "SfiaLevel", "EscoSkill", "RefreshToken", "EmailToken", "UserTenantAssignment"]
