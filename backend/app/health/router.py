from fastapi import APIRouter, status
from sqlalchemy.exc import SQLAlchemyError

from backend.app.ai.manager import AiManager
from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.core.exceptions import (
    ai_model_missing,
    ai_provider_unavailable,
    database_unavailable,
)
from backend.app.core.schemas import ProblemDetails
from backend.app.health.schemas import (
    AiHealthResponse,
    DatabaseHealthResponse,
    HealthResponse,
)


def build_health_router(
    settings: Settings,
    database: Database,
    ai_manager: AiManager,
) -> APIRouter:
    """Build separate process liveness and database readiness routes."""
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

    @router.get(
        "/health/database",
        operation_id="get_database_health",
        response_model=DatabaseHealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": ProblemDetails,
                "description": "PostgreSQL is unavailable",
            }
        },
        status_code=status.HTTP_200_OK,
        summary="Check PostgreSQL availability",
    )
    async def get_database_health() -> DatabaseHealthResponse:
        try:
            database.check_connection()
        except SQLAlchemyError as error:
            raise database_unavailable() from error

        return DatabaseHealthResponse(status="ok")

    @router.get(
        "/health/ai",
        operation_id="get_ai_health",
        response_model=AiHealthResponse,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": ProblemDetails,
                "description": "Configured AI provider or model is unavailable",
            }
        },
        status_code=status.HTTP_200_OK,
        summary="Check optional AI provider readiness",
    )
    async def get_ai_health() -> AiHealthResponse:
        provider = await ai_manager.get_status()
        if provider.status == "unavailable":
            raise ai_provider_unavailable()
        if provider.status == "model_missing":
            raise ai_model_missing()
        return AiHealthResponse(
            status="disabled" if provider.status == "disabled" else "ok",
            provider=provider.name,
            model=provider.model,
        )

    return router
