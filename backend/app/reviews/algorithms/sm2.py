from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

MINIMUM_EASE_FACTOR = Decimal("1.30")
INITIAL_EASE_FACTOR = Decimal("2.50")
EASE_FACTOR_PRECISION = Decimal("0.01")


class ReviewRating(StrEnum):
    """Learner-facing ratings supported by the first release."""

    AGAIN = "again"
    HARD = "hard"
    GOOD = "good"
    EASY = "easy"


RATING_QUALITY = {
    ReviewRating.AGAIN: 1,
    ReviewRating.HARD: 3,
    ReviewRating.GOOD: 4,
    ReviewRating.EASY: 5,
}


@dataclass(frozen=True, slots=True)
class ReviewState:
    """Immutable scheduling state consumed and returned by SM-2."""

    repetitions: int
    interval_days: int
    ease_factor: Decimal

    def __post_init__(self) -> None:
        if (
            isinstance(self.repetitions, bool)
            or not isinstance(self.repetitions, int)
            or self.repetitions < 0
        ):
            raise ValueError("repetitions must be a non-negative integer")
        if (
            isinstance(self.interval_days, bool)
            or not isinstance(self.interval_days, int)
            or self.interval_days < 0
        ):
            raise ValueError("interval_days must be a non-negative integer")
        if not isinstance(self.ease_factor, Decimal):
            raise ValueError("ease_factor must be a Decimal")
        if not self.ease_factor.is_finite():
            raise ValueError("ease_factor must be finite")
        if self.ease_factor < MINIMUM_EASE_FACTOR:
            raise ValueError("ease_factor must be at least 1.30")

    @classmethod
    def initial(cls) -> "ReviewState":
        """Return the ADR-001 state for a newly created card."""
        return cls(repetitions=0, interval_days=0, ease_factor=INITIAL_EASE_FACTOR)


def quality_for_rating(rating: ReviewRating) -> int:
    """Map a learner-facing rating to the classic SM-2 quality value."""
    return RATING_QUALITY[rating]


def calculate_sm2(state: ReviewState, quality: int) -> ReviewState:
    """Calculate one deterministic SM-2 transition from ADR-001."""
    if isinstance(quality, bool) or not isinstance(quality, int):
        raise ValueError("quality must be an integer from 0 to 5")
    if not 0 <= quality <= 5:
        raise ValueError("quality must be an integer from 0 to 5")

    if quality < 3:
        repetitions = 0
        interval_days = 1
    elif state.repetitions == 0:
        repetitions = 1
        interval_days = 1
    elif state.repetitions == 1:
        repetitions = 2
        interval_days = 6
    else:
        repetitions = state.repetitions + 1
        interval_days = max(
            1,
            int(
                (Decimal(state.interval_days) * state.ease_factor).quantize(
                    Decimal("1"), rounding=ROUND_HALF_UP
                )
            ),
        )

    difference = Decimal(5 - quality)
    adjustment = Decimal("0.1") - difference * (
        Decimal("0.08") + difference * Decimal("0.02")
    )
    ease_factor = max(MINIMUM_EASE_FACTOR, state.ease_factor + adjustment)
    ease_factor = ease_factor.quantize(
        EASE_FACTOR_PRECISION,
        rounding=ROUND_HALF_UP,
    )

    return ReviewState(
        repetitions=repetitions,
        interval_days=interval_days,
        ease_factor=ease_factor,
    )
