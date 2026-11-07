from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from backend.app.api.router import build_api_router
from backend.app.core.config import Settings, get_settings
from backend.app.core.database import Database
from backend.app.core.error_handlers import install_exception_handlers


def create_app(
    settings: Settings | None = None,
    database: Database | None = None,
) -> FastAPI:
    """Create an application instance with explicit, testable configuration."""
    resolved_settings = settings or get_settings()
    resolved_database = database or Database(resolved_settings.database_url)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        yield
        resolved_database.dispose()

    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.app_debug,
        openapi_url=f"{resolved_settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    application.state.database = resolved_database
    install_exception_handlers(application)
    application.include_router(
        build_api_router(resolved_settings, resolved_database),
        prefix=resolved_settings.api_v1_prefix,
    )
    return application


app = create_app()
