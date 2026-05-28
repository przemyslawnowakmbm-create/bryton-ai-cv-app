from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import settings

# Superuser engine — used for migrations, pre-auth queries (login/refresh),
# cross-tenant admin operations, and seeding. Bypasses RLS.
engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# Non-superuser engine — used for tenant-scoped data queries.
# RLS policies are enforced because bryton_app is NOT a superuser.
app_engine = create_async_engine(settings.APP_DATABASE_URL, echo=False)
app_async_session = async_sessionmaker(app_engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


async def get_db():
    """Yield a raw database session that bypasses RLS.

    Uses the superuser connection. Used ONLY for pre-auth operations
    (login, refresh) and cross-tenant admin operations.
    For all authenticated endpoints, use get_tenant_db (future) instead.
    """
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
