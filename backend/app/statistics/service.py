from datetime import UTC, date, datetime, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import and_, func, select
from sqlalchemy.orm import Session

from backend.app.cards.models import Card
from backend.app.core.exceptions import invalid_date_range
from backend.app.core.pagination import build_pagination
from backend.app.reviews.algorithms.calendar import (
    local_date_range_bounds,
    local_day_bounds,
)
from backend.app.reviews.models import ReviewLog
from backend.app.statistics.schemas import (
    ActivityDay,
    ActivityStatistics,
    StatisticsOverview,
    TopicStatistics,
    TopicStatisticsPage,
)
from backend.app.topics.models import Topic
from backend.app.topics.schemas import TopicRead


def _success_rate(reviews: int, successful: int) -> float | None:
    return successful / reviews if reviews else None


def _thirty_day_start(generated_at: datetime, timezone: str) -> datetime:
    current_local_date = generated_at.astimezone(ZoneInfo(timezone)).date()
    date_from = current_local_date - timedelta(days=29)
    start, _ = local_date_range_bounds(date_from, current_local_date, timezone)
    return start


def get_overview(
    session: Session,
    *,
    timezone: str,
    now: datetime | None = None,
) -> StatisticsOverview:
    generated_at = now or datetime.now(UTC)
    card_metrics = session.execute(
        select(
            func.count(Card.id),
            func.count(Card.id).filter(Card.is_archived.is_(False)),
            func.count(Card.id).filter(Card.is_archived.is_(True)),
            func.count(Card.id).filter(
                Card.is_archived.is_(False),
                Card.next_review_at.is_not(None),
                Card.next_review_at <= generated_at,
            ),
            func.count(Card.id).filter(
                Card.is_archived.is_(False),
                Card.last_reviewed_at.is_(None),
            ),
        )
    ).one()

    today_start, today_end = local_day_bounds(generated_at, timezone)
    reviews_today = (
        session.scalar(
            select(func.count(ReviewLog.id)).where(
                ReviewLog.reviewed_at >= today_start,
                ReviewLog.reviewed_at < today_end,
                ReviewLog.reviewed_at <= generated_at,
            )
        )
        or 0
    )
    thirty_day_start = _thirty_day_start(generated_at, timezone)
    reviews_30d, successful_30d = session.execute(
        select(
            func.count(ReviewLog.id),
            func.count(ReviewLog.id).filter(ReviewLog.quality >= 3),
        ).where(
            ReviewLog.reviewed_at >= thirty_day_start,
            ReviewLog.reviewed_at <= generated_at,
        )
    ).one()

    return StatisticsOverview(
        total_cards=card_metrics[0],
        active_cards=card_metrics[1],
        archived_cards=card_metrics[2],
        due_cards=card_metrics[3],
        new_cards=card_metrics[4],
        reviews_today=reviews_today,
        success_rate_30d=_success_rate(reviews_30d, successful_30d),
        timezone=timezone,
        generated_at=generated_at,
    )


def list_topic_statistics(
    session: Session,
    *,
    timezone: str,
    page: int,
    limit: int,
    category_id: UUID | None,
    now: datetime | None = None,
) -> TopicStatisticsPage:
    generated_at = now or datetime.now(UTC)
    topic_filter = [Topic.category_id == category_id] if category_id else []
    total = session.scalar(select(func.count(Topic.id)).where(*topic_filter)) or 0
    topics = list(
        session.scalars(
            select(Topic)
            .where(*topic_filter)
            .order_by(Topic.name.asc(), Topic.id.asc())
            .offset((page - 1) * limit)
            .limit(limit)
        ).all()
    )
    if not topics:
        return TopicStatisticsPage(
            items=[],
            pagination=build_pagination(page=page, limit=limit, total=total),
        )

    topic_ids = [topic.id for topic in topics]
    thirty_day_start = _thirty_day_start(generated_at, timezone)
    rows = session.execute(
        select(
            Card.topic_id,
            func.count(func.distinct(Card.id)).label("total_cards"),
            func.count(func.distinct(Card.id))
            .filter(Card.is_archived.is_(False))
            .label("active_cards"),
            func.count(func.distinct(Card.id))
            .filter(
                Card.is_archived.is_(False),
                Card.next_review_at.is_not(None),
                Card.next_review_at <= generated_at,
            )
            .label("due_cards"),
            func.count(func.distinct(Card.id))
            .filter(
                Card.is_archived.is_(False),
                Card.last_reviewed_at.is_(None),
            )
            .label("new_cards"),
            func.count(ReviewLog.id).label("reviews_30d"),
            func.count(ReviewLog.id)
            .filter(ReviewLog.quality >= 3)
            .label("successful_30d"),
        )
        .outerjoin(
            ReviewLog,
            and_(
                ReviewLog.card_id == Card.id,
                ReviewLog.reviewed_at >= thirty_day_start,
                ReviewLog.reviewed_at <= generated_at,
            ),
        )
        .where(Card.topic_id.in_(topic_ids))
        .group_by(Card.topic_id)
    ).all()
    metrics = {row.topic_id: row for row in rows}
    items = []
    for topic in topics:
        row = metrics.get(topic.id)
        reviews = row.reviews_30d if row else 0
        successful = row.successful_30d if row else 0
        items.append(
            TopicStatistics(
                topic=TopicRead.model_validate(topic),
                total_cards=row.total_cards if row else 0,
                active_cards=row.active_cards if row else 0,
                due_cards=row.due_cards if row else 0,
                new_cards=row.new_cards if row else 0,
                reviews_30d=reviews,
                success_rate_30d=_success_rate(reviews, successful),
            )
        )
    return TopicStatisticsPage(
        items=items,
        pagination=build_pagination(page=page, limit=limit, total=total),
    )


def get_activity(
    session: Session,
    *,
    timezone: str,
    date_from: date,
    date_to: date,
) -> ActivityStatistics:
    if date_from > date_to:
        raise invalid_date_range("date_from must not be after date_to.")
    day_count = (date_to - date_from).days + 1
    if day_count > 366:
        raise invalid_date_range("Activity range must not exceed 366 days.")

    range_start, range_end = local_date_range_bounds(date_from, date_to, timezone)
    reviews = session.execute(
        select(ReviewLog.reviewed_at, ReviewLog.quality).where(
            ReviewLog.reviewed_at >= range_start,
            ReviewLog.reviewed_at < range_end,
        )
    ).all()
    timezone_info = ZoneInfo(timezone)
    counts: dict[date, list[int]] = {}
    for reviewed_at, quality in reviews:
        if reviewed_at.tzinfo is None:
            reviewed_at = reviewed_at.replace(tzinfo=UTC)
        local_date = reviewed_at.astimezone(timezone_info).date()
        totals = counts.setdefault(local_date, [0, 0])
        totals[0] += 1
        totals[1] += quality >= 3

    items = []
    for offset in range(day_count):
        activity_date = date_from + timedelta(days=offset)
        total, successful = counts.get(activity_date, [0, 0])
        items.append(
            ActivityDay(
                date=activity_date,
                reviews=total,
                successful_reviews=successful,
                success_rate=_success_rate(total, successful),
            )
        )
    return ActivityStatistics(timezone=timezone, items=items)
