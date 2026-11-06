from uuid import uuid4

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.health.schemas import (
    DatabaseHealthResponse,
    HealthResponse,
    ProblemDetails,
)


def build_health_router(settings: Settings, database: Database) -> APIRouter:
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
    async def get_database_health(
        request: Request,
    ) -> DatabaseHealthResponse | JSONResponse:
        try:
            database.check_connection()
        except SQLAlchemyError:
            problem = ProblemDetails(
                type="urn:python-recall:error:database-unavailable",
                title="Database unavailable",
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="PostgreSQL is temporarily unavailable.",
                instance=request.url.path,
                code="database_unavailable",
                trace_id=uuid4().hex,
                errors=[],
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content=problem.model_dump(mode="json"),
                media_type="application/problem+json",
            )

        return DatabaseHealthResponse(status="ok")

    return router
