from datetime import UTC, datetime

import pytest

from backend.app.reviews.algorithms.calendar import calculate_next_review_at


def test_next_review_uses_start_of_next_local_day() -> None:
    reviewed_at = datetime(2026, 11, 6, 10, 16, tzinfo=UTC)

    result = calculate_next_review_at(reviewed_at, 1, "Europe/Kirov")

    assert result == datetime(2026, 11, 6, 21, 0, tzinfo=UTC)


def test_interval_uses_calendar_day_across_dst_start() -> None:
    reviewed_at = datetime(2025, 3, 8, 12, 0, tzinfo=UTC)

    result = calculate_next_review_at(reviewed_at, 1, "America/New_York")

    assert result == datetime(2025, 3, 9, 5, 0, tzinfo=UTC)
    assert (result - reviewed_at).total_seconds() != 24 * 60 * 60


def test_skipped_local_date_moves_to_first_valid_instant() -> None:
    reviewed_at = datetime(2011, 12, 29, 12, 0, tzinfo=UTC)

    result = calculate_next_review_at(reviewed_at, 1, "Pacific/Apia")

    assert result == datetime(2011, 12, 30, 10, 0, tzinfo=UTC)


def test_naive_review_time_is_rejected() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        calculate_next_review_at(datetime(2026, 1, 1), 1, "UTC")


@pytest.mark.parametrize("interval", [0, -1, 1.5, True])
def test_invalid_interval_is_rejected(interval: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        calculate_next_review_at(  # type: ignore[arg-type]
            datetime(2026, 1, 1, tzinfo=UTC), interval, "UTC"
        )
