from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import Field

from backend.app.ai.models import (
    AnswerCorrectness,
    AnswerEvaluation,
    CardAnalysis,
    CardQuality,
)
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


class CardAnalysisCreate(ApiSchema):
    card_id: UUID


class CardIssueRead(ApiSchema):
    field: Literal["question", "answer", "explanation", "code_example", "general"]
    severity: Literal["info", "warning", "critical"]
    message: str


class CardAnalysisRead(ApiSchema):
    id: UUID
    request_id: UUID
    card_id: UUID
    quality: CardQuality
    clarity_score: int = Field(ge=0, le=100)
    completeness_score: int = Field(ge=0, le=100)
    accuracy_score: int = Field(ge=0, le=100)
    specificity_score: int = Field(ge=0, le=100)
    learning_value_score: int = Field(ge=0, le=100)
    issues: list[CardIssueRead]
    feedback: str
    recommendation: str
    suggested_question: str | None
    suggested_answer: str | None
    suggested_explanation: str | None
    suggested_code_example: str | None
    provider: str
    model: str
    prompt_version: str
    created_at: datetime


class CardAnalysisPage(Page[CardAnalysisRead]):
    pass


def card_analysis_to_read(analysis: CardAnalysis) -> CardAnalysisRead:
    return CardAnalysisRead.model_validate(analysis)
