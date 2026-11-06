from fastapi import FastAPI

from backend.app.api.router import build_api_router
from backend.app.core.config import Settings, get_settings


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create an application instance with explicit, testable configuration."""
    resolved_settings = settings or get_settings()
    application = FastAPI(
        title=resolved_settings.app_name,
        version=resolved_settings.app_version,
        debug=resolved_settings.app_debug,
        openapi_url=f"{resolved_settings.api_v1_prefix}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
    )
    application.include_router(
        build_api_router(resolved_settings),
        prefix=resolved_settings.api_v1_prefix,
    )
    return application


app = create_app()
