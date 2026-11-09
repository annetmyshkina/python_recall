import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from backend.app.ai.manager import AiManager
from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AiUsageLog,
    AiUsageStatus,
    AnswerEvaluation,
)
from backend.app.ai.providers.base import StructuredRequest
from backend.app.ai.providers.errors import (
    AiDisabledError,
    AiModelMissingError,
    AiProviderError,
    AiProviderResponseError,
    AiProviderTimeoutError,
)
from backend.app.ai.scenarios.answer_evaluator import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    AnswerEvaluationOutput,
    build_user_prompt,
)
from backend.app.ai.schemas import (
    AnswerEvaluationCreate,
    AnswerEvaluationPage,
    AnswerEvaluationRead,
    evaluation_to_read,
)
from backend.app.cards.models import Card
from backend.app.core.exceptions import (
    ApiError,
    ai_disabled,
    ai_invalid_response,
    ai_model_missing,
    ai_provider_timeout,
    ai_provider_unavailable,
    ai_request_in_progress,
    card_archived,
    idempotency_conflict,
    resource_not_found,
)
from backend.app.core.pagination import build_pagination
from backend.app.reviews.models import AnswerAttempt

ANSWER_EVALUATION_SCENARIO = "answer_evaluation"


def _fingerprint(payload: AnswerEvaluationCreate) -> str:
    content = json.dumps(
        {
            "attempt_id": str(payload.attempt_id),
            "scenario": ANSWER_EVALUATION_SCENARIO,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode()).hexdigest()


def _provider_error(error: AiProviderError) -> tuple[str, ApiError]:
    if isinstance(error, AiDisabledError):
        return "ai_disabled", ai_disabled()
    if isinstance(error, AiModelMissingError):
        return "ai_model_missing", ai_model_missing()
    if isinstance(error, AiProviderTimeoutError):
        return "ai_provider_timeout", ai_provider_timeout()
    if isinstance(error, AiProviderResponseError):
        return "ai_invalid_response", ai_invalid_response()
    return "ai_provider_unavailable", ai_provider_unavailable()


def _stored_error(error_code: str | None) -> ApiError:
    factories = {
        "ai_disabled": ai_disabled,
        "ai_model_missing": ai_model_missing,
        "ai_provider_timeout": ai_provider_timeout,
        "ai_invalid_response": ai_invalid_response,
        "ai_provider_unavailable": ai_provider_unavailable,
    }
    return factories.get(error_code, ai_provider_unavailable)()


def _load_request(session: Session, idempotency_key: UUID) -> AiRequest | None:
    return session.scalar(
        select(AiRequest)
        .where(AiRequest.idempotency_key == idempotency_key)
        .options(
            joinedload(AiRequest.answer_evaluation).joinedload(
                AnswerEvaluation.answer_attempt
            )
        )
    )


def _replay_existing(
    request: AiRequest,
    fingerprint: str,
) -> tuple[AnswerEvaluationRead, bool]:
    if request.request_fingerprint != fingerprint:
        raise idempotency_conflict()
    if request.status == AiRequestStatus.PENDING:
        raise ai_request_in_progress()
    if request.status == AiRequestStatus.FAILED:
        raise _stored_error(request.error_code)
    if request.answer_evaluation is None:
        raise RuntimeError("Succeeded AI request has no result")
    return evaluation_to_read(request.answer_evaluation), True


def _load_attempt_snapshot(session: Session, attempt_id: UUID) -> AnswerAttempt:
    attempt = session.scalar(
        select(AnswerAttempt)
        .where(AnswerAttempt.id == attempt_id)
        .options(joinedload(AnswerAttempt.card))
    )
    if attempt is None:
        raise resource_not_found("AnswerAttempt")
    if attempt.card.is_archived:
        raise card_archived()
    return attempt


def _finalize_failure(
    session: Session,
    request: AiRequest,
    manager: AiManager,
    error_code: str,
) -> None:
    request.status = AiRequestStatus.FAILED
    request.error_code = error_code
    request.completed_at = datetime.now(UTC)
    session.add(
        AiUsageLog(
            request_id=request.id,
            scenario=ANSWER_EVALUATION_SCENARIO,
            provider=manager.provider_name,
            model=manager.model,
            status=AiUsageStatus.FAILED,
            input_tokens=0,
            output_tokens=0,
            error_code=error_code,
        )
    )
    session.commit()


async def evaluate_answer(
    session: Session,
    payload: AnswerEvaluationCreate,
    idempotency_key: UUID,
    manager: AiManager,
) -> tuple[AnswerEvaluationRead, bool]:
    """Reserve, execute, and atomically persist one Answer Evaluator command."""
    fingerprint = _fingerprint(payload)
    existing = _load_request(session, idempotency_key)
    if existing is not None:
        return _replay_existing(existing, fingerprint)

    attempt = _load_attempt_snapshot(session, payload.attempt_id)
    card: Card = attempt.card
    request = AiRequest(
        scenario=ANSWER_EVALUATION_SCENARIO,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
        status=AiRequestStatus.PENDING,
    )
    session.add(request)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        existing = _load_request(session, idempotency_key)
        if existing is None:
            raise ai_request_in_progress() from error
        return _replay_existing(existing, fingerprint)

    source = {
        "question": card.question,
        "reference_answer": card.answer,
        "explanation": card.explanation,
        "code_example": card.code_example,
        "difficulty": card.difficulty,
        "user_answer": attempt.user_answer,
    }
    structured_request = StructuredRequest(
        scenario=ANSWER_EVALUATION_SCENARIO,
        system_prompt=SYSTEM_PROMPT,
        user_prompt=build_user_prompt(**source),
    )
    try:
        result = await manager.generate_structured(
            structured_request,
            AnswerEvaluationOutput,
        )
    except AiProviderError as error:
        error_code, api_error = _provider_error(error)
        _finalize_failure(session, request, manager, error_code)
        raise api_error from error

    evaluation = AnswerEvaluation(
        request_id=request.id,
        answer_attempt_id=attempt.id,
        correctness=result.data.correctness,
        completeness=result.data.completeness,
        score=result.data.score,
        covered_concepts=result.data.covered_concepts,
        missing_concepts=result.data.missing_concepts,
        mistakes=result.data.mistakes,
        feedback=result.data.feedback,
        recommendation=result.data.recommendation,
        provider=result.provider,
        model=result.model,
        prompt_version=PROMPT_VERSION,
        question_snapshot=source["question"],
        reference_answer_snapshot=source["reference_answer"],
        explanation_snapshot=source["explanation"],
        code_example_snapshot=source["code_example"],
        difficulty_snapshot=source["difficulty"].value,
        user_answer_snapshot=source["user_answer"],
    )
    request.status = AiRequestStatus.SUCCEEDED
    request.completed_at = datetime.now(UTC)
    session.add(evaluation)
    session.add(
        AiUsageLog(
            request_id=request.id,
            scenario=ANSWER_EVALUATION_SCENARIO,
            provider=result.provider,
            model=result.model,
            status=AiUsageStatus.SUCCEEDED,
            input_tokens=result.usage.input_tokens,
            output_tokens=result.usage.output_tokens,
            total_duration_ns=result.usage.total_duration_ns,
        )
    )
    session.commit()
    session.refresh(evaluation)
    evaluation.answer_attempt = attempt
    return evaluation_to_read(evaluation), False


def get_answer_evaluation(
    session: Session,
    evaluation_id: UUID,
) -> AnswerEvaluationRead:
    evaluation = session.scalar(
        select(AnswerEvaluation)
        .where(AnswerEvaluation.id == evaluation_id)
        .options(joinedload(AnswerEvaluation.answer_attempt))
    )
    if evaluation is None:
        raise resource_not_found("AnswerEvaluation")
    return evaluation_to_read(evaluation)


def list_answer_evaluations(
    session: Session,
    *,
    page: int,
    limit: int,
    attempt_id: UUID | None,
) -> AnswerEvaluationPage:
    statement = select(AnswerEvaluation)
    if attempt_id is not None:
        statement = statement.where(AnswerEvaluation.answer_attempt_id == attempt_id)
    total = (
        session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    evaluations = session.scalars(
        statement.options(joinedload(AnswerEvaluation.answer_attempt))
        .order_by(AnswerEvaluation.created_at.desc(), AnswerEvaluation.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return AnswerEvaluationPage(
        items=[evaluation_to_read(item) for item in evaluations],
        pagination=build_pagination(page=page, limit=limit, total=total),
    )
