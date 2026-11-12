from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Query

from backend.app.core.config import Settings
from backend.app.core.dependencies import SessionDependency

from . import service
from .schemas import LearningStatus, TopicLearningSignalsPage


def build_adaptive_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/adaptive", tags=["Adaptive Learning"])

    @router.get(
        "/topics",
        operation_id="list_topic_learning_signals",
        response_model=TopicLearningSignalsPage,
        summary="List explainable learning signals for topics",
    )
    async def list_topic_learning_signals(
        session: SessionDependency,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        category_id: UUID | None = None,
        learning_status: Annotated[
            LearningStatus | None,
            Query(alias="status"),
        ] = None,
        period_days: Annotated[int, Query(ge=7, le=365)] = 30,
    ) -> TopicLearningSignalsPage:
        return service.list_topic_learning_signals(
            session,
            timezone=settings.app_timezone,
            page=page,
            limit=limit,
            category_id=category_id,
            learning_status=learning_status,
            period_days=period_days,
        )

    return router
