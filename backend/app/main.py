import json
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.health import router as health_router
from app.api.reference import router as reference_router
from app.config import settings
from app.database import async_session
from app.services.seed import seed_sfia_levels
from app.utils.logging import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup tasks (seeding) + shutdown cleanup."""
    logger.info("Starting Bryton AI CV App")

    # Seed reference data on startup
    try:
        async with async_session() as session:
            await seed_sfia_levels(session)
            await session.commit()
        logger.info("SFIA levels seeded successfully")
    except Exception as e:
        logger.warning(f"SFIA seed skipped: {e}")

    yield

    logger.info("Shutting down Bryton AI CV App")


app = FastAPI(
    title="Bryton AI CV App",
    description="AI-powered CV screening and candidate management for engineering staffing",
    version="0.1.0",
    lifespan=lifespan,
)

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
