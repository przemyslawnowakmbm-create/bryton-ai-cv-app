"""FastAPI dependencies for database sessions and auth.

Convenience re-exports and placeholders for future dependencies.
"""
from app.database import get_db  # noqa: F401 — re-exported for use with Depends()

# TODO (Phase 02): Add get_tenant_db — returns app_async_session with RLS tenant context set
# TODO (Phase 02): Add get_current_user — decodes JWT, returns User model
