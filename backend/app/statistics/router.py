from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from backend.app.core.config import Settings
from backend.app.core.dependencies import SessionDependency
from backend.app.statistics import service
from backend.app.statistics.schemas import (
    ActivityStatistics,
    StatisticsOverview,
    TopicStatisticsPage,
)


def build_statistics_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/statistics", tags=["Statistics"])

    @router.get(
        "/overview",
        operation_id="get_statistics_overview",
        response_model=StatisticsOverview,
    )
    async def get_statistics_overview(
        session: SessionDependency,
    ) -> StatisticsOverview:
        return service.get_overview(session, timezone=settings.app_timezone)

    @router.get(
        "/topics",
        operation_id="list_topic_statistics",
        response_model=TopicStatisticsPage,
    )
    async def list_topic_statistics(
        session: SessionDependency,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        category_id: UUID | None = None,
    ) -> TopicStatisticsPage:
        return service.list_topic_statistics(
            session,
            timezone=settings.app_timezone,
            page=page,
            limit=limit,
            category_id=category_id,
        )

    @router.get(
        "/activity",
        operation_id="get_statistics_activity",
        response_model=ActivityStatistics,
    )
    async def get_statistics_activity(
        session: SessionDependency,
        date_from: date,
        date_to: date,
    ) -> ActivityStatistics:
        return service.get_activity(
            session,
            timezone=settings.app_timezone,
            date_from=date_from,
            date_to=date_to,
        )

    return router
