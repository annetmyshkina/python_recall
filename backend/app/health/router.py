from fastapi import APIRouter, status

from backend.app.core.config import Settings
from backend.app.health.schemas import HealthResponse


def build_health_router(settings: Settings) -> APIRouter:
    """Build dependency-free liveness routes."""
    router = APIRouter(tags=["Health"])

    @router.get(
        "/health",
        operation_id="get_health",
        response_model=HealthResponse,
        status_code=status.HTTP_200_OK,
        summary="Check Backend liveness without dependencies",
    )
    async def get_health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            service=settings.app_service,
            version=settings.app_version,
        )

    return router
