import hashlib
import json
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from backend.app.cards.models import Card
from backend.app.core.exceptions import (
    card_archived,
    idempotency_conflict,
    resource_not_found,
    review_conflict,
)
from backend.app.core.pagination import build_pagination
from backend.app.reviews.algorithms.calendar import (
    calculate_next_review_at,
    local_day_bounds,
)
from backend.app.reviews.algorithms.sm2 import (
    ReviewState,
    calculate_sm2,
    quality_for_rating,
)
from backend.app.reviews.models import AnswerAttempt, ReviewLog, ReviewRating
from backend.app.reviews.schemas import (
    AnswerAttemptCreate,
    DueCards,
    DueSessionRequest,
    ManualSessionRequest,
    ReviewCard,
    ReviewComplete,
    ReviewHistoryPage,
    ReviewReference,
    ReviewResult,
    SessionRequest,
    SessionResponse,
    TopicSessionRequest,
    attempt_to_read,
)
from backend.app.tags.models import CardTag
from backend.app.topics.models import Topic

CARD_OPTIONS = (selectinload(Card.tag_links).selectinload(CardTag.tag),)


def _review_card(card: Card) -> ReviewCard:
    return ReviewCard(
        id=card.id,
        topic_id=card.topic_id,
        question=card.question,
        difficulty=card.difficulty,
        tags=card.tags,
        repetitions=card.repetitions,
        is_new=card.last_reviewed_at is None,
        next_review_at=card.next_review_at,
    )


def _active_card(session: Session, card_id: UUID, *, lock: bool = False) -> Card:
    statement = select(Card).where(Card.id == card_id).options(*CARD_OPTIONS)
    if lock:
        statement = statement.with_for_update()
    card = session.scalar(statement)
    if card is None:
        raise resource_not_found("Card")
    if card.is_archived:
        raise card_archived()
    return card


def list_due_cards(
    session: Session,
    *,
    timezone: str,
    new_cards_per_day: int,
    topic_id: UUID | None = None,
    category_id: UUID | None = None,
    include_new: bool = True,
    limit: int = 20,
    now: datetime | None = None,
) -> DueCards:
    generated_at = now or datetime.now(UTC)
    filters = [Card.is_archived.is_(False)]
    joins_topic = category_id is not None
    if topic_id is not None:
        filters.append(Card.topic_id == topic_id)
    if category_id is not None:
        filters.append(Topic.category_id == category_id)

    due_query = select(Card)
    if joins_topic:
        due_query = due_query.join(Topic, Topic.id == Card.topic_id)
    due_query = due_query.where(
        *filters,
        Card.next_review_at.is_not(None),
        Card.next_review_at <= generated_at,
    )
    due_count = (
        session.scalar(
            select(func.count()).select_from(due_query.order_by(None).subquery())
        )
        or 0
    )
    due_cards = list(
        session.scalars(
            due_query.options(*CARD_OPTIONS)
            .order_by(Card.next_review_at.asc(), Card.id.asc())
            .limit(limit)
        ).all()
    )

    new_query = select(Card)
    if joins_topic:
        new_query = new_query.join(Topic, Topic.id == Card.topic_id)
    new_query = new_query.where(*filters, Card.last_reviewed_at.is_(None))
    new_count = (
        session.scalar(
            select(func.count()).select_from(new_query.order_by(None).subquery())
        )
        or 0
    )

    day_start, day_end = local_day_bounds(generated_at, timezone)
    first_reviews = (
        select(
            ReviewLog.card_id.label("card_id"),
            func.min(ReviewLog.reviewed_at).label("first_reviewed_at"),
        )
        .group_by(ReviewLog.card_id)
        .subquery()
    )
    introduced_today = (
        session.scalar(
            select(func.count())
            .select_from(first_reviews)
            .where(
                first_reviews.c.first_reviewed_at >= day_start,
                first_reviews.c.first_reviewed_at < day_end,
            )
        )
        or 0
    )
    new_remaining = max(0, new_cards_per_day - introduced_today)

    new_cards: list[Card] = []
    remaining_slots = max(0, limit - len(due_cards))
    if include_new and remaining_slots and new_remaining:
        new_cards = list(
            session.scalars(
                new_query.options(*CARD_OPTIONS)
                .order_by(Card.created_at.asc(), Card.id.asc())
                .limit(min(remaining_slots, new_remaining))
            ).all()
        )

    return DueCards(
        items=[_review_card(card) for card in [*due_cards, *new_cards]],
        due_count=due_count,
        new_count=new_count,
        new_remaining_today=new_remaining,
        timezone=timezone,
        generated_at=generated_at,
    )


def build_session(
    session: Session,
    payload: SessionRequest,
    *,
    timezone: str,
    new_cards_per_day: int,
    now: datetime | None = None,
) -> SessionResponse:
    generated_at = now or datetime.now(UTC)
    if isinstance(payload, DueSessionRequest):
        due = list_due_cards(
            session,
            timezone=timezone,
            new_cards_per_day=new_cards_per_day,
            include_new=payload.include_new,
            limit=payload.limit,
            now=generated_at,
        )
        items = due.items
    elif isinstance(payload, TopicSessionRequest):
        if session.get(Topic, payload.topic_id) is None:
            raise resource_not_found("Topic")
        cards = session.scalars(
            select(Card)
            .where(Card.topic_id == payload.topic_id, Card.is_archived.is_(False))
            .options(*CARD_OPTIONS)
            .order_by(Card.created_at.asc(), Card.id.asc())
            .limit(payload.limit)
        ).all()
        items = [_review_card(card) for card in cards]
    elif isinstance(payload, ManualSessionRequest):
        cards = session.scalars(
            select(Card).where(Card.id.in_(payload.card_ids)).options(*CARD_OPTIONS)
        ).all()
        by_id = {card.id: card for card in cards}
        if len(by_id) != len(payload.card_ids):
            raise resource_not_found("Card")
        ordered = [by_id[card_id] for card_id in payload.card_ids]
        if any(card.is_archived for card in ordered):
            raise card_archived()
        items = [_review_card(card) for card in ordered]
    else:
        latest = select(
            ReviewLog.card_id.label("card_id"),
            ReviewLog.rating.label("rating"),
            ReviewLog.reviewed_at.label("reviewed_at"),
            func.row_number()
            .over(
                partition_by=ReviewLog.card_id,
                order_by=(ReviewLog.reviewed_at.desc(), ReviewLog.id.desc()),
            )
            .label("position"),
        ).subquery()
        cards = session.scalars(
            select(Card)
            .join(latest, latest.c.card_id == Card.id)
            .where(
                Card.is_archived.is_(False),
                latest.c.position == 1,
                latest.c.rating.in_([ReviewRating.AGAIN, ReviewRating.HARD]),
            )
            .options(*CARD_OPTIONS)
            .order_by(latest.c.reviewed_at.asc(), Card.id.asc())
            .limit(payload.limit)
        ).all()
        items = [_review_card(card) for card in cards]

    return SessionResponse(
        mode=payload.mode,
        generated_at=generated_at,
        timezone=timezone,
        items=items,
        total=len(items),
    )


def get_reference(session: Session, card_id: UUID) -> ReviewReference:
    card = _active_card(session, card_id)
    return ReviewReference(
        card_id=card.id,
        answer=card.answer,
        explanation=card.explanation,
        code_example=card.code_example,
    )


def create_attempt(session: Session, card_id: UUID, payload: AnswerAttemptCreate):
    _active_card(session, card_id)
    attempt = AnswerAttempt(card_id=card_id, user_answer=payload.user_answer)
    session.add(attempt)
    session.commit()
    session.refresh(attempt)
    return attempt_to_read(attempt)


def _fingerprint(card_id: UUID, payload: ReviewComplete) -> str:
    content = json.dumps(
        {
            "attempt_id": str(payload.attempt_id) if payload.attempt_id else None,
            "card_id": str(card_id),
            "rating": payload.rating.value,
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(content.encode()).hexdigest()


def complete_review(
    session: Session,
    card_id: UUID,
    payload: ReviewComplete,
    idempotency_key: UUID,
    *,
    timezone: str,
    now: datetime | None = None,
) -> tuple[ReviewResult, bool]:
    fingerprint = _fingerprint(card_id, payload)
    existing = session.scalar(
        select(ReviewLog).where(ReviewLog.idempotency_key == idempotency_key)
    )
    if existing is not None:
        if existing.request_fingerprint != fingerprint:
            raise idempotency_conflict()
        return ReviewResult.from_log(existing), True

    card = _active_card(session, card_id, lock=True)
    attempt = None
    if payload.attempt_id is not None:
        attempt = session.get(AnswerAttempt, payload.attempt_id)
        if attempt is None or attempt.card_id != card_id:
            raise resource_not_found("AnswerAttempt")
        if attempt.review_log is not None:
            raise review_conflict("Answer attempt already belongs to a review.")

    reviewed_at = now or datetime.now(UTC)
    previous = ReviewState(
        repetitions=card.repetitions,
        interval_days=card.interval_days,
        ease_factor=card.ease_factor,
    )
    quality = quality_for_rating(payload.rating)
    new = calculate_sm2(previous, quality)
    next_review_at = calculate_next_review_at(reviewed_at, new.interval_days, timezone)
    log = ReviewLog(
        card_id=card.id,
        answer_attempt_id=attempt.id if attempt else None,
        rating=payload.rating,
        quality=quality,
        previous_repetitions=previous.repetitions,
        previous_interval_days=previous.interval_days,
        previous_ease_factor=previous.ease_factor,
        previous_next_review_at=card.next_review_at,
        new_repetitions=new.repetitions,
        new_interval_days=new.interval_days,
        new_ease_factor=new.ease_factor,
        new_next_review_at=next_review_at,
        reviewed_at=reviewed_at,
        idempotency_key=idempotency_key,
        request_fingerprint=fingerprint,
    )
    card.repetitions = new.repetitions
    card.interval_days = new.interval_days
    card.ease_factor = new.ease_factor
    card.last_reviewed_at = reviewed_at
    card.next_review_at = next_review_at
    card.updated_at = reviewed_at
    session.add(log)
    try:
        session.commit()
    except IntegrityError as error:
        session.rollback()
        existing = session.scalar(
            select(ReviewLog).where(ReviewLog.idempotency_key == idempotency_key)
        )
        if existing is None:
            raise review_conflict("Review could not be completed.") from error
        if existing.request_fingerprint != fingerprint:
            raise idempotency_conflict() from error
        return ReviewResult.from_log(existing), True
    session.refresh(log)
    return ReviewResult.from_log(log), False


def list_history(
    session: Session,
    *,
    page: int,
    limit: int,
    card_id: UUID | None,
    topic_id: UUID | None,
    rating: ReviewRating | None,
    reviewed_from: datetime | None,
    reviewed_to: datetime | None,
) -> ReviewHistoryPage:
    statement = select(ReviewLog)
    filters = []
    if card_id:
        filters.append(ReviewLog.card_id == card_id)
    if topic_id:
        statement = statement.join(Card, Card.id == ReviewLog.card_id)
        filters.append(Card.topic_id == topic_id)
    if rating:
        filters.append(ReviewLog.rating == rating)
    if reviewed_from:
        filters.append(ReviewLog.reviewed_at >= reviewed_from)
    if reviewed_to:
        filters.append(ReviewLog.reviewed_at < reviewed_to)
    statement = statement.where(*filters)
    total = (
        session.scalar(
            select(func.count()).select_from(statement.order_by(None).subquery())
        )
        or 0
    )
    logs = session.scalars(
        statement.order_by(ReviewLog.reviewed_at.desc(), ReviewLog.id.desc())
        .offset((page - 1) * limit)
        .limit(limit)
    ).all()
    return ReviewHistoryPage(
        items=[ReviewResult.from_log(log) for log in logs],
        pagination=build_pagination(page=page, limit=limit, total=total),
    )
