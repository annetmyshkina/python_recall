from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import Field, field_serializer, field_validator, model_validator

from backend.app.cards.models import CardDifficulty
from backend.app.core.schemas import ApiSchema, Page
from backend.app.tags.schemas import TagRead


def normalize_required_text(value: str, field_name: str) -> str:
    value = value.strip()
    if not value:
        raise ValueError(f"{field_name} must not be empty.")
    return value


def validate_unique_tag_ids(value: list[UUID]) -> list[UUID]:
    if len(value) != len(set(value)):
        raise ValueError("Tag ids must be unique.")
    return value


class CardCreate(ApiSchema):
    topic_id: UUID
    question: str = Field(min_length=1, max_length=10000)
    answer: str = Field(min_length=1, max_length=50000)
    explanation: str | None = Field(default=None, max_length=50000)
    code_example: str | None = Field(default=None, max_length=50000)
    difficulty: CardDifficulty
    tag_ids: list[UUID] = Field(default_factory=list, max_length=50)

    @field_validator("question")
    @classmethod
    def normalize_question(cls, value: str) -> str:
        return normalize_required_text(value, "Question")

    @field_validator("answer")
    @classmethod
    def normalize_answer(cls, value: str) -> str:
        return normalize_required_text(value, "Answer")

    _validate_tag_ids = field_validator("tag_ids")(validate_unique_tag_ids)


class CardPatch(ApiSchema):
    topic_id: UUID | None = None
    question: str | None = Field(default=None, min_length=1, max_length=10000)
    answer: str | None = Field(default=None, min_length=1, max_length=50000)
    explanation: str | None = Field(default=None, max_length=50000)
    code_example: str | None = Field(default=None, max_length=50000)
    difficulty: CardDifficulty | None = None
    is_archived: bool | None = None
    tag_ids: list[UUID] | None = Field(default=None, max_length=50)

    @field_validator("topic_id")
    @classmethod
    def topic_must_not_be_null(cls, value: UUID | None) -> UUID:
        if value is None:
            raise ValueError("Topic id must not be null.")
        return value

    @field_validator("question")
    @classmethod
    def validate_question(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Question must not be null.")
        return normalize_required_text(value, "Question")

    @field_validator("answer")
    @classmethod
    def validate_answer(cls, value: str | None) -> str:
        if value is None:
            raise ValueError("Answer must not be null.")
        return normalize_required_text(value, "Answer")

    @field_validator("difficulty")
    @classmethod
    def difficulty_must_not_be_null(
        cls, value: CardDifficulty | None
    ) -> CardDifficulty:
        if value is None:
            raise ValueError("Difficulty must not be null.")
        return value

    @field_validator("is_archived")
    @classmethod
    def archive_flag_must_not_be_null(cls, value: bool | None) -> bool:
        if value is None:
            raise ValueError("Archive flag must not be null.")
        return value

    @field_validator("tag_ids")
    @classmethod
    def tags_must_not_be_null(cls, value: list[UUID] | None) -> list[UUID]:
        if value is None:
            raise ValueError("Tag ids must not be null.")
        return validate_unique_tag_ids(value)

    @model_validator(mode="after")
    def require_field(self) -> "CardPatch":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided.")
        return self


class CardRead(ApiSchema):
    id: UUID
    topic_id: UUID
    question: str
    answer: str
    explanation: str | None
    code_example: str | None
    difficulty: CardDifficulty
    is_archived: bool
    tags: list[TagRead]
    repetitions: int
    interval_days: int
    ease_factor: Decimal
    next_review_at: datetime | None
    last_reviewed_at: datetime | None
    created_at: datetime
    updated_at: datetime

    @field_serializer("ease_factor")
    def serialize_ease_factor(self, value: Decimal) -> str:
        return f"{value:.2f}"


class CardPage(Page[CardRead]):
    pass
