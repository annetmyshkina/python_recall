from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response, status

from backend.app.core.config import Settings
from backend.app.core.dependencies import SessionDependency
from backend.app.reviews import service
from backend.app.reviews.algorithms.sm2 import ReviewRating
from backend.app.reviews.schemas import (
    AnswerAttemptCreate,
    AnswerAttemptRead,
    DueCards,
    OffsetDateTime,
    ReviewComplete,
    ReviewHistoryPage,
    ReviewReference,
    ReviewResult,
    SessionRequest,
    SessionResponse,
)


def build_review_router(settings: Settings) -> APIRouter:
    router = APIRouter(prefix="/reviews", tags=["Reviews"])

    @router.get("/due", operation_id="list_due_cards", response_model=DueCards)
    async def list_due_cards(
        session: SessionDependency,
        topic_id: UUID | None = None,
        category_id: UUID | None = None,
        include_new: bool = True,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
    ) -> DueCards:
        return service.list_due_cards(
            session,
            timezone=settings.app_timezone,
            new_cards_per_day=settings.app_new_cards_per_day,
            topic_id=topic_id,
            category_id=category_id,
            include_new=include_new,
            limit=limit,
        )

    @router.post(
        "/session", operation_id="build_review_session", response_model=SessionResponse
    )
    async def build_review_session(
        payload: SessionRequest,
        session: SessionDependency,
    ) -> SessionResponse:
        return service.build_session(
            session,
            payload,
            timezone=settings.app_timezone,
            new_cards_per_day=settings.app_new_cards_per_day,
        )

    @router.get(
        "/history", operation_id="list_review_history", response_model=ReviewHistoryPage
    )
    async def list_review_history(
        session: SessionDependency,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        card_id: UUID | None = None,
        topic_id: UUID | None = None,
        rating: ReviewRating | None = None,
        reviewed_from: OffsetDateTime | None = None,
        reviewed_to: OffsetDateTime | None = None,
    ) -> ReviewHistoryPage:
        return service.list_history(
            session,
            page=page,
            limit=limit,
            card_id=card_id,
            topic_id=topic_id,
            rating=rating,
            reviewed_from=reviewed_from,
            reviewed_to=reviewed_to,
        )

    @router.get(
        "/{card_id}/reference",
        operation_id="get_review_reference",
        response_model=ReviewReference,
    )
    async def get_review_reference(
        card_id: UUID, session: SessionDependency
    ) -> ReviewReference:
        return service.get_reference(session, card_id)

    @router.post(
        "/{card_id}/attempts",
        operation_id="create_answer_attempt",
        response_model=AnswerAttemptRead,
        status_code=status.HTTP_201_CREATED,
    )
    async def create_answer_attempt(
        card_id: UUID,
        payload: AnswerAttemptCreate,
        session: SessionDependency,
    ) -> AnswerAttemptRead:
        return service.create_attempt(session, card_id, payload)

    @router.post(
        "/{card_id}/complete",
        operation_id="complete_review",
        response_model=ReviewResult,
        status_code=status.HTTP_201_CREATED,
    )
    async def complete_review(
        card_id: UUID,
        payload: ReviewComplete,
        response: Response,
        session: SessionDependency,
        idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    ) -> ReviewResult:
        result, replayed = service.complete_review(
            session,
            card_id,
            payload,
            idempotency_key,
            timezone=settings.app_timezone,
        )
        if replayed:
            response.status_code = status.HTTP_200_OK
            response.headers["Idempotency-Replayed"] = "true"
        return result

    return router
