from datetime import datetime
from decimal import Decimal
from typing import Annotated, Literal
from uuid import UUID

from pydantic import AfterValidator, Field, field_serializer, field_validator

from backend.app.cards.models import CardDifficulty
from backend.app.core.schemas import ApiSchema, Page
from backend.app.reviews.algorithms.sm2 import ReviewRating
from backend.app.reviews.models import AnswerAttempt, ReviewLog
from backend.app.tags.schemas import TagRead


def _require_utc_offset(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("Timestamp must include a UTC offset.")
    return value


OffsetDateTime = Annotated[datetime, AfterValidator(_require_utc_offset)]


class ReviewCard(ApiSchema):
    id: UUID
    topic_id: UUID
    question: str
    difficulty: CardDifficulty
    tags: list[TagRead]
    repetitions: int
    is_new: bool
    next_review_at: datetime | None


class DueCards(ApiSchema):
    items: list[ReviewCard]
    due_count: int = Field(ge=0)
    new_count: int = Field(ge=0)
    new_remaining_today: int = Field(ge=0)
    timezone: str
    generated_at: datetime


class DueSessionRequest(ApiSchema):
    mode: Literal["due"]
    include_new: bool = True
    limit: int = Field(default=20, ge=1, le=100)


class TopicSessionRequest(ApiSchema):
    mode: Literal["topic"]
    topic_id: UUID
    limit: int = Field(default=20, ge=1, le=100)


class DifficultSessionRequest(ApiSchema):
    mode: Literal["difficult"]
    limit: int = Field(default=20, ge=1, le=100)


class ManualSessionRequest(ApiSchema):
    mode: Literal["manual"]
    card_ids: list[UUID] = Field(min_length=1, max_length=100)

    @field_validator("card_ids")
    @classmethod
    def unique_card_ids(cls, value: list[UUID]) -> list[UUID]:
        if len(value) != len(set(value)):
            raise ValueError("Card ids must be unique.")
        return value


SessionRequest = Annotated[
    DueSessionRequest
    | TopicSessionRequest
    | DifficultSessionRequest
    | ManualSessionRequest,
    Field(discriminator="mode"),
]


class SessionResponse(ApiSchema):
    mode: Literal["due", "topic", "difficult", "manual"]
    generated_at: datetime
    timezone: str
    items: list[ReviewCard]
    total: int = Field(ge=0)


class ReviewReference(ApiSchema):
    card_id: UUID
    answer: str
    explanation: str | None
    code_example: str | None


class AnswerAttemptCreate(ApiSchema):
    user_answer: str = Field(min_length=1, max_length=50000)

    @field_validator("user_answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("User answer must not be empty.")
        return value


class AnswerAttemptRead(ApiSchema):
    id: UUID
    card_id: UUID
    user_answer: str
    created_at: datetime


class ReviewComplete(ApiSchema):
    rating: ReviewRating
    attempt_id: UUID | None = None


class ReviewStateRead(ApiSchema):
    repetitions: int
    interval_days: int
    ease_factor: Decimal
    next_review_at: datetime | None

    @field_serializer("ease_factor")
    def serialize_ease_factor(self, value: Decimal) -> str:
        return f"{value:.2f}"


class ReviewResult(ApiSchema):
    id: UUID
    card_id: UUID
    attempt_id: UUID | None
    rating: ReviewRating
    quality: int
    reviewed_at: datetime
    previous_state: ReviewStateRead
    new_state: ReviewStateRead

    @classmethod
    def from_log(cls, log: ReviewLog) -> "ReviewResult":
        return cls(
            id=log.id,
            card_id=log.card_id,
            attempt_id=log.answer_attempt_id,
            rating=log.rating,
            quality=log.quality,
            reviewed_at=log.reviewed_at,
            previous_state=ReviewStateRead(
                repetitions=log.previous_repetitions,
                interval_days=log.previous_interval_days,
                ease_factor=log.previous_ease_factor,
                next_review_at=log.previous_next_review_at,
            ),
            new_state=ReviewStateRead(
                repetitions=log.new_repetitions,
                interval_days=log.new_interval_days,
                ease_factor=log.new_ease_factor,
                next_review_at=log.new_next_review_at,
            ),
        )


class ReviewHistoryPage(Page[ReviewResult]):
    pass


def attempt_to_read(attempt: AnswerAttempt) -> AnswerAttemptRead:
    return AnswerAttemptRead.model_validate(attempt)
