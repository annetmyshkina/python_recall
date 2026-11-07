from dataclasses import FrozenInstanceError
from decimal import Decimal

import pytest

from backend.app.reviews.algorithms.sm2 import (
    ReviewRating,
    ReviewState,
    calculate_sm2,
    quality_for_rating,
)


def state(repetitions: int, interval_days: int, ease_factor: str) -> ReviewState:
    return ReviewState(repetitions, interval_days, Decimal(ease_factor))


def test_initial_state_matches_adr() -> None:
    assert ReviewState.initial() == state(0, 0, "2.50")


@pytest.mark.parametrize(
    ("rating", "quality"),
    [
        (ReviewRating.AGAIN, 1),
        (ReviewRating.HARD, 3),
        (ReviewRating.GOOD, 4),
        (ReviewRating.EASY, 5),
    ],
)
def test_rating_mapping(rating: ReviewRating, quality: int) -> None:
    assert quality_for_rating(rating) == quality


@pytest.mark.parametrize(
    ("quality", "expected_ease"),
    [
        (0, "1.70"),
        (1, "1.96"),
        (2, "2.18"),
        (3, "2.36"),
        (4, "2.50"),
        (5, "2.60"),
    ],
)
def test_all_classic_quality_values_update_ease_factor(
    quality: int, expected_ease: str
) -> None:
    result = calculate_sm2(state(2, 6, "2.50"), quality)
    assert result.ease_factor == Decimal(expected_ease)


@pytest.mark.parametrize(
    ("previous", "quality", "expected"),
    [
        (state(0, 0, "2.50"), 4, state(1, 1, "2.50")),
        (state(1, 1, "2.50"), 4, state(2, 6, "2.50")),
        (state(2, 6, "2.50"), 4, state(3, 15, "2.50")),
        (state(3, 15, "2.50"), 3, state(4, 38, "2.36")),
        (state(3, 15, "2.50"), 1, state(0, 1, "1.96")),
        (state(2, 6, "1.30"), 1, state(0, 1, "1.30")),
    ],
)
def test_adr_control_examples(
    previous: ReviewState, quality: int, expected: ReviewState
) -> None:
    assert calculate_sm2(previous, quality) == expected


def test_interval_uses_round_half_up() -> None:
    result = calculate_sm2(state(2, 5, "2.50"), 4)
    assert result.interval_days == 13


def test_interval_uses_previous_ease_factor() -> None:
    result = calculate_sm2(state(2, 10, "2.00"), 5)
    assert result.interval_days == 20
    assert result.ease_factor == Decimal("2.10")


@pytest.mark.parametrize("quality", [0, 1, 2])
def test_failed_recall_resets_successful_repetitions(quality: int) -> None:
    result = calculate_sm2(state(8, 100, "2.50"), quality)
    assert result.repetitions == 0
    assert result.interval_days == 1


@pytest.mark.parametrize("quality", [-1, 6, 2.5, True])
def test_invalid_quality_is_rejected(quality: object) -> None:
    with pytest.raises(ValueError, match="quality"):
        calculate_sm2(ReviewState.initial(), quality)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("repetitions", "interval_days", "ease_factor"),
    [
        (-1, 0, Decimal("2.50")),
        (0, -1, Decimal("2.50")),
        (0, 0, Decimal("1.29")),
        (0, 0, Decimal("NaN")),
        (1.5, 1, Decimal("2.50")),
    ],
)
def test_invalid_state_is_rejected(
    repetitions: object, interval_days: int, ease_factor: Decimal
) -> None:
    with pytest.raises(ValueError):
        ReviewState(  # type: ignore[arg-type]
            repetitions=repetitions,
            interval_days=interval_days,
            ease_factor=ease_factor,
        )


def test_input_state_is_immutable_and_unchanged() -> None:
    previous = state(2, 6, "2.50")

    calculate_sm2(previous, 4)

    assert previous == state(2, 6, "2.50")
    with pytest.raises(FrozenInstanceError):
        previous.repetitions = 10  # type: ignore[misc]
