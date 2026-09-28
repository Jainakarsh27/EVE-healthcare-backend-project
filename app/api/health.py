from fastapi import APIRouter, Depends, Response, status
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db

router = APIRouter(tags=["Health"])


@router.get(
    "/health",
    status_code=status.HTTP_200_OK,
    summary="Liveness check",
    description="Returns HTTP 200 if the FastAPI backend service process is running.",
)
async def health_check():
    return {"status": "ok", "service": "eve_healthcare_backend"}


@router.get(
    "/ready",
    status_code=status.HTTP_200_OK,
    summary="Readiness check",
    description="Checks database connectivity and readiness to handle incoming traffic.",
)
async def readiness_check(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        return {
            "status": "ready",
            "database": "connected",
            "service": "eve_healthcare_backend",
        }
    except Exception as e:
        return Response(
            content=f'{{"status": "unready", "database_error": "{str(e)}"}}',
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            media_type="application/json",
        )
