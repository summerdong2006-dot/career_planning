from fastapi import APIRouter, status

from app.db.session import check_database_connection
from app.schemas.health import HealthResponse

router = APIRouter(tags=["system"])


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Application health check",
)
async def health_check() -> HealthResponse:
    database_ok = await check_database_connection()
    return HealthResponse(status="ok", database="ok" if database_ok else "unavailable")
