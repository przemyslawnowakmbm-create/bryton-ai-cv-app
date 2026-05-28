import json
from contextlib import asynccontextmanager

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from slowapi.util import get_remote_address

from app.api.health import router as health_router
from app.api.reference import router as reference_router
from app.config import settings
from app.database import async_session
from app.services.esco_sync import sync_esco_skills
from app.services.seed import seed_sfia_levels
from app.utils.logging import logger

# Rate limiter (in-memory; upgrade to Redis backend for multi-instance)
limiter = Limiter(key_func=get_remote_address)

scheduler = AsyncIOScheduler()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup tasks (seeding + scheduler) + shutdown cleanup."""
    logger.info("Starting Bryton AI CV App")

    # Seed reference data on startup
    try:
        async with async_session() as session:
            await seed_sfia_levels(session)
            await session.commit()
        logger.info("SFIA levels seeded successfully")
    except Exception as e:
        logger.warning(f"SFIA seed skipped: {e}")

    # Register weekly ESCO sync — every Monday at 02:00 UTC
    scheduler.add_job(sync_esco_skills, "cron", day_of_week="mon", hour=2)
    scheduler.start()
    logger.info("ESCO sync job scheduled: every Monday at 02:00 UTC")

    yield

    scheduler.shutdown()
    logger.info("Shutting down Bryton AI CV App")


app = FastAPI(
    title="Bryton AI CV App",
    description="AI-powered CV screening and candidate management for engineering staffing",
    version="0.1.0",
    lifespan=lifespan,
)

# Rate limiting — attach limiter to app state and add middleware
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# CORS — parse the JSON list from settings
_cors_origins = json.loads(settings.CORS_ORIGINS)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Router registration
# Health routes at root level (NO /api prefix) per architecture spec
app.include_router(health_router)
# Reference data API
app.include_router(reference_router)
# Auth API at /api/auth/*
from app.api.auth import router as auth_router  # noqa: E402 — avoid circular import at module level
app.include_router(auth_router, prefix="/api")
