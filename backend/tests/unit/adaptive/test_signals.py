from datetime import UTC, datetime, timedelta

from backend.app.adaptive.schemas import LearningReason, LearningStatus
from backend.app.adaptive.service import _classify, _period_start


def classify(**overrides: object) -> tuple[LearningStatus, list[LearningReason]]:
    values = {
        "active_cards": 1,
        "overdue_cards": 0,
        "reviews": 3,
        "again_reviews": 0,
        "hard_reviews": 0,
        "ai_evaluations": 0,
        "average_ai_completeness": None,
        "last_reviewed_at": datetime(2026, 11, 12, tzinfo=UTC),
        "generated_at": datetime(2026, 11, 12, tzinfo=UTC),
    }
    values.update(overrides)
    return _classify(**values)  # type: ignore[arg-type]


def test_two_failures_are_still_insufficient_history() -> None:
    assert classify(reviews=2, again_reviews=2) == (
        LearningStatus.INSUFFICIENT_DATA,
        [LearningReason.INSUFFICIENT_HISTORY],
    )


def test_half_hard_reviews_require_attention() -> None:
    assert classify(reviews=4, hard_reviews=2) == (
        LearningStatus.NEEDS_ATTENTION,
        [LearningReason.FREQUENT_HARD],
    )


def test_overdue_backlog_and_long_inactivity_are_reported_together() -> None:
    generated_at = datetime(2026, 11, 12, tzinfo=UTC)

    assert classify(
        active_cards=4,
        overdue_cards=2,
        generated_at=generated_at,
        last_reviewed_at=generated_at - timedelta(days=15),
    ) == (
        LearningStatus.NEEDS_ATTENTION,
        [LearningReason.OVERDUE_BACKLOG, LearningReason.LONG_INACTIVITY],
    )


def test_exactly_fourteen_days_is_not_long_inactivity() -> None:
    generated_at = datetime(2026, 11, 12, tzinfo=UTC)

    assert classify(
        active_cards=1,
        overdue_cards=1,
        generated_at=generated_at,
        last_reviewed_at=generated_at - timedelta(days=14),
    ) == (LearningStatus.STABLE, [])


def test_naive_database_timestamp_is_treated_as_utc() -> None:
    generated_at = datetime(2026, 11, 12, tzinfo=UTC)

    assert classify(
        active_cards=1,
        overdue_cards=1,
        generated_at=generated_at,
        last_reviewed_at=datetime(2026, 10, 20),
    ) == (
        LearningStatus.NEEDS_ATTENTION,
        [LearningReason.LONG_INACTIVITY],
    )


def test_period_starts_at_first_local_calendar_day() -> None:
    generated_at = datetime(2026, 11, 12, 20, 30, tzinfo=UTC)

    assert _period_start(generated_at, "Europe/Kirov", 7) == datetime(
        2026,
        11,
        5,
        21,
        tzinfo=UTC,
    )
