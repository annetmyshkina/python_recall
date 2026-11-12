from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.ai.models import AnswerEvaluation
from backend.app.cards.models import Card
from backend.app.categories.models import Category
from backend.app.core.pagination import build_pagination
from backend.app.reviews.algorithms.calendar import local_date_range_bounds
from backend.app.reviews.models import AnswerAttempt, ReviewLog
from backend.app.topics.models import Topic
from backend.app.topics.schemas import TopicRead

from .schemas import (
    LearningReason,
    LearningStatus,
    TopicLearningSignals,
    TopicLearningSignalsPage,
)

MINIMUM_ACTIVITY = 3
MINIMUM_AI_FOR_COMPLETENESS = 2
LOW_AI_COMPLETENESS = 70
INACTIVITY_DAYS = 14

STATUS_PRIORITY = {
    LearningStatus.NEEDS_ATTENTION: 0,
    LearningStatus.INSUFFICIENT_DATA: 1,
    LearningStatus.STABLE: 2,
}


@dataclass(frozen=True, slots=True)
class _CardMetrics:
    active_cards: int
    overdue_cards: int


@dataclass(frozen=True, slots=True)
class _ReviewMetrics:
    reviews: int
    again_reviews: int
    hard_reviews: int
    successful_reviews: int


@dataclass(frozen=True, slots=True)
class _AiMetrics:
    evaluations: int
    average_score: float | None
    average_completeness: float | None


def _rate(total: int, part: int) -> float | None:
    return part / total if total else None


def _period_start(generated_at: datetime, timezone: str, days: int) -> datetime:
    current_date = generated_at.astimezone(ZoneInfo(timezone)).date()
    first_date = current_date - timedelta(days=days - 1)
    start, _ = local_date_range_bounds(first_date, current_date, timezone)
    return start


def _classify(
    *,
    active_cards: int,
    overdue_cards: int,
    reviews: int,
    again_reviews: int,
    hard_reviews: int,
    ai_evaluations: int,
    average_ai_completeness: float | None,
    last_reviewed_at: datetime | None,
    generated_at: datetime,
) -> tuple[LearningStatus, list[LearningReason]]:
    if active_cards == 0:
        return LearningStatus.INSUFFICIENT_DATA, [LearningReason.NO_ACTIVE_CARDS]
    if reviews < MINIMUM_ACTIVITY and ai_evaluations < MINIMUM_ACTIVITY:
        return LearningStatus.INSUFFICIENT_DATA, [LearningReason.INSUFFICIENT_HISTORY]

    reasons: list[LearningReason] = []
    if reviews and again_reviews * 3 >= reviews:
        reasons.append(LearningReason.FREQUENT_AGAIN)
    if reviews and hard_reviews * 2 >= reviews:
        reasons.append(LearningReason.FREQUENT_HARD)
    if (
        ai_evaluations >= MINIMUM_AI_FOR_COMPLETENESS
        and average_ai_completeness is not None
        and average_ai_completeness < LOW_AI_COMPLETENESS
    ):
        reasons.append(LearningReason.LOW_AI_COMPLETENESS)
    if active_cards >= 2 and overdue_cards * 2 >= active_cards:
        reasons.append(LearningReason.OVERDUE_BACKLOG)
    comparable_last_review = last_reviewed_at
    if comparable_last_review is not None and comparable_last_review.tzinfo is None:
        comparable_last_review = comparable_last_review.replace(tzinfo=UTC)
    if (
        overdue_cards > 0
        and comparable_last_review is not None
        and comparable_last_review < generated_at - timedelta(days=INACTIVITY_DAYS)
    ):
        reasons.append(LearningReason.LONG_INACTIVITY)
    if reasons:
        return LearningStatus.NEEDS_ATTENTION, reasons
    return LearningStatus.STABLE, []


def list_topic_learning_signals(
    session: Session,
    *,
    timezone: str,
    page: int,
    limit: int,
    category_id: UUID | None,
    learning_status: LearningStatus | None,
    period_days: int,
    now: datetime | None = None,
) -> TopicLearningSignalsPage:
    generated_at = now or datetime.now(UTC)
    period_start = _period_start(generated_at, timezone, period_days)
    topic_filter = [Topic.category_id == category_id] if category_id else []
    topic_rows = session.execute(
        select(Topic, Category.name.label("category_name"))
        .join(Category, Category.id == Topic.category_id)
        .where(*topic_filter)
    ).all()
    topic_ids = [topic.id for topic, _ in topic_rows]

    card_metrics: dict[UUID, _CardMetrics] = {}
    review_metrics: dict[UUID, _ReviewMetrics] = {}
    last_reviews: dict[UUID, datetime | None] = {}
    ai_metrics: dict[UUID, _AiMetrics] = {}
    if topic_ids:
        card_metrics = {
            topic_id: _CardMetrics(
                active_cards=int(active_cards),
                overdue_cards=int(overdue_cards),
            )
            for topic_id, active_cards, overdue_cards in session.execute(
                select(
                    Card.topic_id,
                    func.count(Card.id).label("active_cards"),
                    func.count(Card.id)
                    .filter(
                        Card.next_review_at.is_not(None),
                        Card.next_review_at <= generated_at,
                    )
                    .label("overdue_cards"),
                )
                .where(
                    Card.topic_id.in_(topic_ids),
                    Card.is_archived.is_(False),
                )
                .group_by(Card.topic_id)
            )
        }
        review_metrics = {
            topic_id: _ReviewMetrics(
                reviews=int(reviews),
                again_reviews=int(again_reviews),
                hard_reviews=int(hard_reviews),
                successful_reviews=int(successful_reviews),
            )
            for (
                topic_id,
                reviews,
                again_reviews,
                hard_reviews,
                successful_reviews,
            ) in session.execute(
                select(
                    Card.topic_id,
                    func.count(ReviewLog.id).label("reviews"),
                    func.count(ReviewLog.id)
                    .filter(ReviewLog.quality == 1)
                    .label("again_reviews"),
                    func.count(ReviewLog.id)
                    .filter(ReviewLog.quality == 3)
                    .label("hard_reviews"),
                    func.count(ReviewLog.id)
                    .filter(ReviewLog.quality >= 3)
                    .label("successful_reviews"),
                )
                .join(Card, Card.id == ReviewLog.card_id)
                .where(
                    Card.topic_id.in_(topic_ids),
                    Card.is_archived.is_(False),
                    ReviewLog.reviewed_at >= period_start,
                    ReviewLog.reviewed_at <= generated_at,
                )
                .group_by(Card.topic_id)
            )
        }
        last_reviews = {
            topic_id: reviewed_at
            for topic_id, reviewed_at in session.execute(
                select(Card.topic_id, func.max(ReviewLog.reviewed_at))
                .join(Card, Card.id == ReviewLog.card_id)
                .where(
                    Card.topic_id.in_(topic_ids),
                    Card.is_archived.is_(False),
                    ReviewLog.reviewed_at <= generated_at,
                )
                .group_by(Card.topic_id)
            )
        }
        ai_metrics = {
            topic_id: _AiMetrics(
                evaluations=int(evaluations),
                average_score=(
                    float(average_score) if average_score is not None else None
                ),
                average_completeness=(
                    float(average_completeness)
                    if average_completeness is not None
                    else None
                ),
            )
            for (
                topic_id,
                evaluations,
                average_score,
                average_completeness,
            ) in session.execute(
                select(
                    Card.topic_id,
                    func.count(AnswerEvaluation.id).label("ai_evaluations"),
                    func.avg(AnswerEvaluation.score).label("average_ai_score"),
                    func.avg(AnswerEvaluation.completeness).label(
                        "average_ai_completeness"
                    ),
                )
                .join(
                    AnswerAttempt,
                    AnswerAttempt.id == AnswerEvaluation.answer_attempt_id,
                )
                .join(Card, Card.id == AnswerAttempt.card_id)
                .where(
                    Card.topic_id.in_(topic_ids),
                    Card.is_archived.is_(False),
                    AnswerEvaluation.created_at >= period_start,
                    AnswerEvaluation.created_at <= generated_at,
                )
                .group_by(Card.topic_id)
            )
        }

    items: list[TopicLearningSignals] = []
    for topic, category_name in topic_rows:
        cards = card_metrics.get(topic.id)
        reviews_row = review_metrics.get(topic.id)
        ai_row = ai_metrics.get(topic.id)
        active_cards = cards.active_cards if cards else 0
        overdue_cards = cards.overdue_cards if cards else 0
        reviews = reviews_row.reviews if reviews_row else 0
        again_reviews = reviews_row.again_reviews if reviews_row else 0
        hard_reviews = reviews_row.hard_reviews if reviews_row else 0
        successful_reviews = reviews_row.successful_reviews if reviews_row else 0
        ai_evaluations = ai_row.evaluations if ai_row else 0
        average_ai_score = ai_row.average_score if ai_row else None
        average_ai_completeness = ai_row.average_completeness if ai_row else None
        status, reasons = _classify(
            active_cards=active_cards,
            overdue_cards=overdue_cards,
            reviews=reviews,
            again_reviews=again_reviews,
            hard_reviews=hard_reviews,
            ai_evaluations=ai_evaluations,
            average_ai_completeness=average_ai_completeness,
            last_reviewed_at=last_reviews.get(topic.id),
            generated_at=generated_at,
        )
        item = TopicLearningSignals(
            topic=TopicRead.model_validate(topic),
            category_name=category_name,
            status=status,
            reasons=reasons,
            active_cards=active_cards,
            overdue_cards=overdue_cards,
            overdue_rate=_rate(active_cards, overdue_cards),
            reviews=reviews,
            again_reviews=again_reviews,
            hard_reviews=hard_reviews,
            successful_reviews=successful_reviews,
            success_rate=_rate(reviews, successful_reviews),
            again_rate=_rate(reviews, again_reviews),
            hard_rate=_rate(reviews, hard_reviews),
            ai_evaluations=ai_evaluations,
            average_ai_score=average_ai_score,
            average_ai_completeness=average_ai_completeness,
            last_reviewed_at=last_reviews.get(topic.id),
        )
        if learning_status is None or item.status == learning_status:
            items.append(item)

    items.sort(
        key=lambda item: (
            STATUS_PRIORITY[item.status],
            item.category_name.casefold(),
            item.topic.name.casefold(),
            str(item.topic.id),
        )
    )
    total = len(items)
    offset = (page - 1) * limit
    return TopicLearningSignalsPage(
        items=items[offset : offset + limit],
        pagination=build_pagination(page=page, limit=limit, total=total),
        period_days=period_days,
        period_start=period_start,
        timezone=timezone,
        generated_at=generated_at,
    )
