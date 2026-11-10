import hashlib
import json
import unicodedata
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.app.ai.manager import AiManager
from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AiUsageLog,
    AiUsageStatus,
    CardSuggestion,
    CardSuggestionStatus,
)
from backend.app.ai.providers.base import ProviderUsage, StructuredRequest
from backend.app.ai.providers.errors import AiProviderError
from backend.app.ai.scenarios.card_generator import (
    PROMPT_VERSION,
    SYSTEM_PROMPT,
    GeneratedCardBatch,
    build_user_prompt,
)
from backend.app.ai.schemas import (
    CardGenerationCreate,
    CardSuggestionBatchRead,
    CardSuggestionPage,
    CardSuggestionRead,
    card_suggestion_to_read,
)
from backend.app.ai.service import _provider_error, _stored_error
from backend.app.cards.models import Card
from backend.app.core.exceptions import (
    ai_invalid_response,
    ai_request_in_progress,
    idempotency_conflict,
    resource_not_found,
    suggestion_already_reviewed,
    suggestion_duplicate,
)
from backend.app.core.pagination import build_pagination
from backend.app.topics.models import Topic

SCENARIO = "card_generation"
MAX_CONTEXT_QUESTIONS = 100


def normalize_question(value: str) -> str:
    """Normalize a question for deterministic duplicate detection."""
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return " ".join(normalized.split())


def _fingerprint(payload: CardGenerationCreate) -> str:
    value = json.dumps(
        {
            "topic_id": str(payload.topic_id),
            "source_text": payload.source_text,
            "count": payload.count,
            "scenario": SCENARIO,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(value.encode()).hexdigest()


def _load_request(session: Session, key: UUID) -> AiRequest | None:
    return session.scalar(select(AiRequest).where(AiRequest.idempotency_key == key))


def _batch_for_request(session: Session, request_id: UUID) -> CardSuggestionBatchRead:
    suggestions = session.scalars(
        select(CardSuggestion)
        .where(CardSuggestion.request_id == request_id)
        .order_by(CardSuggestion.position.asc())
    ).all()
    return CardSuggestionBatchRead(
        request_id=request_id,
        items=[card_suggestion_to_read(item) for item in suggestions],
    )


def _replay(
    session: Session,
    request: AiRequest,
    fingerprint: str,
) -> tuple[CardSuggestionBatchRead, bool]:
    if request.request_fingerprint != fingerprint:
        raise idempotency_conflict()
    if request.status == AiRequestStatus.PENDING:
        raise ai_request_in_progress()
    if request.status == AiRequestStatus.FAILED:
        raise _stored_error(request.error_code)
    return _batch_for_request(session, request.id), True


def _finalize_failure(
    session: Session,
    request: AiRequest,
    *,
    provider: str,
    model: str,
    error_code: str,
    usage: ProviderUsage | None = None,
) -> None:
    request.status = AiRequestStatus.FAILED
    request.error_code = error_code
    request.completed_at = datetime.now(UTC)
    session.add(
        AiUsageLog(
            request_id=request.id,
            scenario=SCENARIO,
            provider=provider,
            model=model,
            status=AiUsageStatus.FAILED,
            input_tokens=usage.input_tokens if usage else 0,
            output_tokens=usage.output_tokens if usage else 0,
            total_duration_ns=usage.total_duration_ns if usage else None,
            error_code=error_code,
        )
    )
    session.commit()


def _topic_context(
    session: Session,
    topic_id: UUID,
) -> tuple[Topic, list[str]]:
    topic = session.get(Topic, topic_id)
    if topic is None:
        raise resource_not_found("Topic")
    questions = session.scalars(
        select(Card.question)
        .where(Card.topic_id == topic_id, Card.is_archived.is_(False))
        .order_by(Card.created_at.asc(), Card.id.asc())
        .limit(MAX_CONTEXT_QUESTIONS)
    ).all()
    return topic, list(questions)


def _existing_normalized_questions(session: Session, topic_id: UUID) -> set[str]:
    card_questions = session.scalars(
        select(Card.question).where(Card.topic_id == topic_id)
    ).all()
    pending_questions = session.scalars(
        select(CardSuggestion.question).where(
            CardSuggestion.topic_id == topic_id,
            CardSuggestion.status == CardSuggestionStatus.PENDING,
        )
    ).all()
    return {
        normalize_question(question)
        for question in [*card_questions, *pending_questions]
    }


async def generate_card_suggestions(
    session: Session,
    payload: CardGenerationCreate,
    key: UUID,
    manager: AiManager,
) -> tuple[CardSuggestionBatchRead, bool]:
    fingerprint = _fingerprint(payload)
    existing = _load_request(session, key)
    if existing is not None:
        return _replay(session, existing, fingerprint)

    topic, existing_questions = _topic_context(session, payload.topic_id)
    source = {
        "topic_name": topic.name,
        "topic_description": topic.description,
        "source_text": payload.source_text,
        "requested_count": payload.count,
        "existing_questions": existing_questions,
    }
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
        return _replay(session, existing, fingerprint)

    try:
        result = await manager.generate_structured(
            StructuredRequest(
                scenario=SCENARIO,
                system_prompt=SYSTEM_PROMPT,
                user_prompt=build_user_prompt(**source),
            ),
            GeneratedCardBatch,
        )
    except AiProviderError as error:
        error_code, api_error = _provider_error(error)
        _finalize_failure(
            session,
            request,
            provider=manager.provider_name,
            model=manager.model,
            error_code=error_code,
        )
        raise api_error from error

    if len(result.data.cards) != payload.count:
        _finalize_failure(
            session,
            request,
            provider=result.provider,
            model=result.model,
            error_code="ai_invalid_response",
            usage=result.usage,
        )
        raise ai_invalid_response()

    seen = _existing_normalized_questions(session, payload.topic_id)
    suggestions: list[CardSuggestion] = []
    for position, draft in enumerate(result.data.cards):
        normalized = normalize_question(draft.question)
        if normalized in seen:
            continue
        seen.add(normalized)
        suggestion = CardSuggestion(
            request_id=request.id,
            topic_id=payload.topic_id,
            status=CardSuggestionStatus.PENDING,
            position=position,
            question=draft.question,
            answer=draft.answer,
            explanation=draft.explanation,
            code_example=draft.code_example,
            difficulty=draft.difficulty,
            provider=result.provider,
            model=result.model,
            prompt_version=PROMPT_VERSION,
        )
        suggestions.append(suggestion)

    request.status = AiRequestStatus.SUCCEEDED
    request.completed_at = datetime.now(UTC)
    session.add_all(
        [
            *suggestions,
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
    return _batch_for_request(session, request.id), False


def get_suggestion(session: Session, suggestion_id: UUID) -> CardSuggestionRead:
    suggestion = session.get(CardSuggestion, suggestion_id)
    if suggestion is None:
        raise resource_not_found("CardSuggestion")
    return card_suggestion_to_read(suggestion)


def list_suggestions(
    session: Session,
    *,
    page: int,
    limit: int,
    topic_id: UUID | None,
    suggestion_status: CardSuggestionStatus | None,
) -> CardSuggestionPage:
    statement = select(CardSuggestion)
    if topic_id is not None:
        statement = statement.where(CardSuggestion.topic_id == topic_id)
    if suggestion_status is not None:
        statement = statement.where(CardSuggestion.status == suggestion_status)
    total = (
        session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    items = session.scalars(
        statement.order_by(CardSuggestion.created_at.desc(), CardSuggestion.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return CardSuggestionPage(
        items=[card_suggestion_to_read(item) for item in items],
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def _pending_suggestion_for_update(
    session: Session,
    suggestion_id: UUID,
) -> CardSuggestion:
    suggestion = session.scalar(
        select(CardSuggestion)
        .where(CardSuggestion.id == suggestion_id)
        .with_for_update()
    )
    if suggestion is None:
        raise resource_not_found("CardSuggestion")
    if suggestion.status != CardSuggestionStatus.PENDING:
        raise suggestion_already_reviewed()
    return suggestion


def accept_suggestion(session: Session, suggestion_id: UUID) -> CardSuggestionRead:
    suggestion = _pending_suggestion_for_update(session, suggestion_id)
    existing_questions = session.scalars(
        select(Card.question).where(Card.topic_id == suggestion.topic_id)
    ).all()
    normalized = normalize_question(suggestion.question)
    if any(
        normalize_question(question) == normalized for question in existing_questions
    ):
        raise suggestion_duplicate()

    card = Card(
        topic_id=suggestion.topic_id,
        question=suggestion.question,
        answer=suggestion.answer,
        explanation=suggestion.explanation,
        code_example=suggestion.code_example,
        difficulty=suggestion.difficulty,
    )
    session.add(card)
    session.flush()
    suggestion.status = CardSuggestionStatus.ACCEPTED
    suggestion.accepted_card_id = card.id
    suggestion.reviewed_at = datetime.now(UTC)
    session.commit()
    session.refresh(suggestion)
    return card_suggestion_to_read(suggestion)


def reject_suggestion(session: Session, suggestion_id: UUID) -> CardSuggestionRead:
    suggestion = _pending_suggestion_for_update(session, suggestion_id)
    suggestion.status = CardSuggestionStatus.REJECTED
    suggestion.reviewed_at = datetime.now(UTC)
    session.commit()
    session.refresh(suggestion)
    return card_suggestion_to_read(suggestion)
