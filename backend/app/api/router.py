from fastapi import APIRouter

from backend.app import models as _models  # noqa: F401  # register ORM relationships
from backend.app.ai.manager import AiManager
from backend.app.ai.router import build_ai_router
from backend.app.cards.router import router as cards_router
from backend.app.categories.router import router as categories_router
from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.health.router import build_health_router
from backend.app.reviews.router import build_review_router
from backend.app.statistics.router import build_statistics_router
from backend.app.tags.router import router as tags_router
from backend.app.topics.router import router as topics_router


def build_api_router(
    settings: Settings,
    database: Database,
    ai_manager: AiManager,
) -> APIRouter:
    """Compose core and optional feature routers."""
    router = APIRouter()
    router.include_router(categories_router)
    router.include_router(topics_router)
    router.include_router(tags_router)
    router.include_router(cards_router)
    router.include_router(build_review_router(settings))
    router.include_router(build_statistics_router(settings))
    router.include_router(build_ai_router(ai_manager))
    router.include_router(build_health_router(settings, database, ai_manager))
    return router
