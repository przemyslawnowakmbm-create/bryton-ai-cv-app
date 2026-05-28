from fastapi import APIRouter
from fastapi.responses import JSONResponse
from sqlalchemy import text

from app.config import settings
from app.database import async_session

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness():
    """Liveness probe — always returns 200 if the process is alive."""
    return {"status": "ok"}


@router.get("/health/ready")
async def readiness():
    """Readiness probe — checks DB and optionally Azure Blob connectivity.

    Returns:
        200 with status "ready" if all checks pass.
        503 with status "degraded" if any check fails.
    """
    checks: dict[str, str] = {}

    # Database check
    try:
        async with async_session() as db:
            await db.execute(text("SELECT 1"))
        checks["db"] = "ok"
    except Exception as e:
        checks["db"] = f"error: {e}"

    # Azure Blob check — skipped when connection string is not configured
    if settings.AZURE_STORAGE_CONNECTION_STRING:
        try:
            from azure.storage.blob.aio import BlobServiceClient

            async with BlobServiceClient.from_connection_string(
                settings.AZURE_STORAGE_CONNECTION_STRING
            ) as client:
                await client.get_service_properties()
            checks["blob"] = "ok"
        except Exception as e:
            checks["blob"] = f"error: {e}"
    else:
        checks["blob"] = "skipped"

    all_ok = all(v in ("ok", "skipped") for v in checks.values())
    return JSONResponse(
        status_code=200 if all_ok else 503,
        content={
            "status": "ready" if all_ok else "degraded",
            "checks": checks,
        },
    )
