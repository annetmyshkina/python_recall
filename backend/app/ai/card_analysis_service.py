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
    CardAnalysis,
)
from backend.app.ai.providers.base import StructuredRequest
from backend.app.ai.providers.errors import AiProviderError
from backend.app.ai.scenarios.card_analyzer import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    CardAnalysisOutput,
    build_user_prompt,
)
from backend.app.ai.schemas import (
    CardAnalysisCreate,
    CardAnalysisPage,
    CardAnalysisRead,
    card_analysis_to_read,
)
from backend.app.ai.service import _provider_error, _stored_error
from backend.app.cards.service import get_card
from backend.app.core.exceptions import (
    ai_request_in_progress,
    card_archived,
    idempotency_conflict,
    resource_not_found,
)
from backend.app.core.pagination import build_pagination

SCENARIO = "card_analysis"


def _fingerprint(card_id: UUID) -> str:
    value = json.dumps(
        {"card_id": str(card_id), "scenario": SCENARIO},
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode()).hexdigest()


def _load_request(session: Session, key: UUID) -> AiRequest | None:
    return session.scalar(
        select(AiRequest)
        .where(AiRequest.idempotency_key == key)
        .options(joinedload(AiRequest.card_analysis))
    )


def _replay(request: AiRequest, fingerprint: str) -> tuple[CardAnalysisRead, bool]:
    if request.request_fingerprint != fingerprint:
        raise idempotency_conflict()
    if request.status == AiRequestStatus.PENDING:
        raise ai_request_in_progress()
    if request.status == AiRequestStatus.FAILED:
        raise _stored_error(request.error_code)
    if request.card_analysis is None:
        raise RuntimeError("Succeeded card analysis request has no result")
    return card_analysis_to_read(request.card_analysis), True


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
            scenario=SCENARIO,
            provider=manager.provider_name,
            model=manager.model,
            status=AiUsageStatus.FAILED,
            input_tokens=0,
            output_tokens=0,
            error_code=error_code,
        )
    )
    session.commit()


async def analyze_card(
    session: Session,
    payload: CardAnalysisCreate,
    key: UUID,
    manager: AiManager,
) -> tuple[CardAnalysisRead, bool]:
    fingerprint = _fingerprint(payload.card_id)
    existing = _load_request(session, key)
    if existing is not None:
        return _replay(existing, fingerprint)

    card = get_card(session, payload.card_id)
    if card.is_archived:
        raise card_archived()
    request = AiRequest(
        scenario=SCENARIO,
        idempotency_key=key,
        request_fingerprint=fingerprint,
        status=AiRequestStatus.PENDING,
    )
    session.add(request)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        existing = _load_request(session, key)
        if existing is None:
            raise ai_request_in_progress() from error
        return _replay(existing, fingerprint)

    source = {
        "question": card.question,
        "answer": card.answer,
        "explanation": card.explanation,
        "code_example": card.code_example,
        "difficulty": card.difficulty,
    }
    try:
        result = await manager.generate_structured(
            StructuredRequest(
                scenario=SCENARIO,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(**source),
            ),
            CardAnalysisOutput,
        )
    except AiProviderError as error:
        error_code, api_error = _provider_error(error)
        _finalize_failure(session, request, manager, error_code)
        raise api_error from error

    data = result.data
    analysis = CardAnalysis(
        request_id=request.id,
        card_id=card.id,
        quality=data.quality,
        clarity_score=data.clarity_score,
        completeness_score=data.completeness_score,
        accuracy_score=data.accuracy_score,
        specificity_score=data.specificity_score,
        learning_value_score=data.learning_value_score,
        issues=[issue.model_dump(mode="json") for issue in data.issues],
        feedback=data.feedback,
        recommendation=data.recommendation,
        suggested_question=data.suggested_question,
        suggested_answer=data.suggested_answer,
        suggested_explanation=data.suggested_explanation,
        suggested_code_example=data.suggested_code_example,
        provider=result.provider,
        model=result.model,
        prompt_version=PROMPT_VERSION,
        question_snapshot=source["question"],
        answer_snapshot=source["answer"],
        explanation_snapshot=source["explanation"],
        code_example_snapshot=source["code_example"],
        difficulty_snapshot=source["difficulty"].value,
    )
    request.status = AiRequestStatus.SUCCEEDED
    request.completed_at = datetime.now(UTC)
    session.add_all(
        [
            analysis,
            AiUsageLog(
                request_id=request.id,
                scenario=SCENARIO,
                provider=result.provider,
                model=result.model,
                status=AiUsageStatus.SUCCEEDED,
                input_tokens=result.usage.input_tokens,
                output_tokens=result.usage.output_tokens,
                total_duration_ns=result.usage.total_duration_ns,
            ),
        ]
    )
    session.commit()
    session.refresh(analysis)
    return card_analysis_to_read(analysis), False


def get_analysis(session: Session, analysis_id: UUID) -> CardAnalysisRead:
    analysis = session.get(CardAnalysis, analysis_id)
    if analysis is None:
        raise resource_not_found("CardAnalysis")
    return card_analysis_to_read(analysis)


def list_analyses(
    session: Session, *, page: int, limit: int, card_id: UUID | None
) -> CardAnalysisPage:
    statement = select(CardAnalysis)
    if card_id is not None:
        statement = statement.where(CardAnalysis.card_id == card_id)
    total = (
        session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    items = session.scalars(
        statement.order_by(CardAnalysis.created_at.desc(), CardAnalysis.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return CardAnalysisPage(
        items=[card_analysis_to_read(item) for item in items],
        pagination=build_pagination(page=page, limit=limit, total=total),
    )
