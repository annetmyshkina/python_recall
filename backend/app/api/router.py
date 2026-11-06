from fastapi import APIRouter

from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.health.router import build_health_router


def build_api_router(settings: Settings, database: Database) -> APIRouter:
    """Compose all Release 1 feature routers."""
    router = APIRouter()
    router.include_router(build_health_router(settings, database))
    return router
