from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Header, Query, Response, status

from backend.app.ai import card_analysis_service, service
from backend.app.ai.manager import AiManager
from backend.app.ai.schemas import (
    AiProviderResponse,
    AiProvidersResponse,
    AnswerEvaluationCreate,
    AnswerEvaluationPage,
    AnswerEvaluationRead,
    CardAnalysisCreate,
    CardAnalysisPage,
    CardAnalysisRead,
)
from backend.app.core.dependencies import SessionDependency
from backend.app.core.schemas import ProblemDetails


def build_ai_router(manager: AiManager) -> APIRouter:
    """Expose diagnostics without making the core API depend on AI."""
    router = APIRouter(prefix="/ai", tags=["AI"])

    @router.get(
        "/providers",
        operation_id="list_ai_providers",
        response_model=AiProvidersResponse,
        summary="Inspect configured AI providers without affecting core health",
    )
    async def list_ai_providers() -> AiProvidersResponse:
        provider = await manager.get_status()
        return AiProvidersResponse(
            default_provider=provider.name,
            items=[
                AiProviderResponse(
                    name=provider.name,
                    enabled=provider.enabled,
                    status=provider.status,
                    model=provider.model,
                )
            ],
        )

    @router.post(
        "/evaluate-answer",
        operation_id="evaluate_answer",
        response_model=AnswerEvaluationRead,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_200_OK: {
                "model": AnswerEvaluationRead,
                "description": "Idempotent replay of a saved evaluation",
            },
            status.HTTP_409_CONFLICT: {
                "model": ProblemDetails,
                "description": "Idempotency conflict or request still in progress",
            },
            status.HTTP_502_BAD_GATEWAY: {
                "model": ProblemDetails,
                "description": "Provider returned an invalid structured response",
            },
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": ProblemDetails,
                "description": "AI is disabled or its provider/model is unavailable",
            },
            status.HTTP_504_GATEWAY_TIMEOUT: {
                "model": ProblemDetails,
                "description": "AI provider timed out",
            },
        },
        summary="Evaluate one saved learner answer without changing SM-2",
    )
    async def evaluate_answer(
        payload: AnswerEvaluationCreate,
        response: Response,
        session: SessionDependency,
        idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    ) -> AnswerEvaluationRead:
        evaluation, replayed = await service.evaluate_answer(
            session,
            payload,
            idempotency_key,
            manager,
        )
        if replayed:
            response.status_code = status.HTTP_200_OK
            response.headers["Idempotency-Replayed"] = "true"
        return evaluation

    @router.get(
        "/answer-evaluations",
        operation_id="list_answer_evaluations",
        response_model=AnswerEvaluationPage,
        summary="List saved answer evaluations",
    )
    async def list_answer_evaluations(
        session: SessionDependency,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        attempt_id: UUID | None = None,
    ) -> AnswerEvaluationPage:
        return service.list_answer_evaluations(
            session,
            page=page,
            limit=limit,
            attempt_id=attempt_id,
        )

    @router.get(
        "/answer-evaluations/{evaluation_id}",
        operation_id="get_answer_evaluation",
        response_model=AnswerEvaluationRead,
        summary="Get one immutable answer evaluation",
    )
    async def get_answer_evaluation(
        evaluation_id: UUID,
        session: SessionDependency,
    ) -> AnswerEvaluationRead:
        return service.get_answer_evaluation(session, evaluation_id)

    @router.post(
        "/analyze-card",
        operation_id="analyze_card",
        response_model=CardAnalysisRead,
        status_code=status.HTTP_201_CREATED,
        responses={
            status.HTTP_200_OK: {"model": CardAnalysisRead},
            status.HTTP_409_CONFLICT: {"model": ProblemDetails},
            status.HTTP_502_BAD_GATEWAY: {"model": ProblemDetails},
            status.HTTP_503_SERVICE_UNAVAILABLE: {"model": ProblemDetails},
            status.HTTP_504_GATEWAY_TIMEOUT: {"model": ProblemDetails},
        },
        summary="Analyze a saved card without modifying it",
    )
    async def analyze_card(
        payload: CardAnalysisCreate,
        response: Response,
        session: SessionDependency,
        idempotency_key: Annotated[UUID, Header(alias="Idempotency-Key")],
    ) -> CardAnalysisRead:
        analysis, replayed = await card_analysis_service.analyze_card(
            session, payload, idempotency_key, manager
        )
        if replayed:
            response.status_code = status.HTTP_200_OK
            response.headers["Idempotency-Replayed"] = "true"
        return analysis

    @router.get(
        "/card-analyses",
        operation_id="list_card_analyses",
        response_model=CardAnalysisPage,
    )
    async def list_card_analyses(
        session: SessionDependency,
        page: Annotated[int, Query(ge=1)] = 1,
        limit: Annotated[int, Query(ge=1, le=100)] = 20,
        card_id: UUID | None = None,
    ) -> CardAnalysisPage:
        return card_analysis_service.list_analyses(
            session, page=page, limit=limit, card_id=card_id
        )

    @router.get(
        "/card-analyses/{analysis_id}",
        operation_id="get_card_analysis",
        response_model=CardAnalysisRead,
    )
    async def get_card_analysis(
        analysis_id: UUID, session: SessionDependency
    ) -> CardAnalysisRead:
        return card_analysis_service.get_analysis(session, analysis_id)

    return router
