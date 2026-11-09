from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from backend.app.ai.models import AnswerCorrectness, AnswerEvaluation
from backend.app.core.schemas import ApiSchema, Page

AiProviderName = Literal["ollama"]
AiProviderState = Literal["disabled", "ready", "unavailable", "model_missing"]


class AiProviderResponse(ApiSchema):
    """Diagnostic state of one configured provider."""

    name: AiProviderName
    enabled: bool
    status: AiProviderState
    model: str = Field(min_length=1, max_length=200)


class AiProvidersResponse(ApiSchema):
    """Provider inventory; Release 3 supports one local provider."""

    default_provider: AiProviderName
    items: list[AiProviderResponse] = Field(min_length=1, max_length=1)


class AnswerEvaluationCreate(ApiSchema):
    """Select one previously saved learner answer for analysis."""

    attempt_id: UUID


class AnswerEvaluationRead(ApiSchema):
    """Immutable persisted Answer Evaluator result."""

    id: UUID
    request_id: UUID
    attempt_id: UUID
    card_id: UUID
    correctness: AnswerCorrectness
    completeness: int = Field(ge=0, le=100)
    score: int = Field(ge=0, le=100)
    covered_concepts: list[str]
    missing_concepts: list[str]
    mistakes: list[str]
    feedback: str
    recommendation: str
    provider: str
    model: str
    prompt_version: str
    created_at: datetime


class AnswerEvaluationPage(Page[AnswerEvaluationRead]):
    pass


def evaluation_to_read(evaluation: AnswerEvaluation) -> AnswerEvaluationRead:
    return AnswerEvaluationRead(
        id=evaluation.id,
        request_id=evaluation.request_id,
        attempt_id=evaluation.answer_attempt_id,
        card_id=evaluation.answer_attempt.card_id,
        correctness=evaluation.correctness,
        completeness=evaluation.completeness,
        score=evaluation.score,
        covered_concepts=evaluation.covered_concepts,
        missing_concepts=evaluation.missing_concepts,
        mistakes=evaluation.mistakes,
        feedback=evaluation.feedback,
        recommendation=evaluation.recommendation,
        provider=evaluation.provider,
        model=evaluation.model,
        prompt_version=evaluation.prompt_version,
        created_at=evaluation.created_at,
    )
