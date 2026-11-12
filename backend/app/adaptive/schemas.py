from datetime import datetime
from enum import StrEnum

from pydantic import Field

from backend.app.core.schemas import ApiSchema, Page
from backend.app.topics.schemas import TopicRead


class LearningStatus(StrEnum):
    INSUFFICIENT_DATA = "insufficient_data"
    STABLE = "stable"
    NEEDS_ATTENTION = "needs_attention"


class LearningReason(StrEnum):
    NO_ACTIVE_CARDS = "no_active_cards"
    INSUFFICIENT_HISTORY = "insufficient_history"
    FREQUENT_AGAIN = "frequent_again"
    FREQUENT_HARD = "frequent_hard"
    LOW_AI_COMPLETENESS = "low_ai_completeness"
    OVERDUE_BACKLOG = "overdue_backlog"
    LONG_INACTIVITY = "long_inactivity"


class TopicLearningSignals(ApiSchema):
    topic: TopicRead
    category_name: str
    status: LearningStatus
    reasons: list[LearningReason]
    active_cards: int = Field(ge=0)
    overdue_cards: int = Field(ge=0)
    overdue_rate: float | None = Field(default=None, ge=0, le=1)
    reviews: int = Field(ge=0)
    again_reviews: int = Field(ge=0)
    hard_reviews: int = Field(ge=0)
    successful_reviews: int = Field(ge=0)
    success_rate: float | None = Field(default=None, ge=0, le=1)
    again_rate: float | None = Field(default=None, ge=0, le=1)
    hard_rate: float | None = Field(default=None, ge=0, le=1)
    ai_evaluations: int = Field(ge=0)
    average_ai_score: float | None = Field(default=None, ge=0, le=100)
    average_ai_completeness: float | None = Field(default=None, ge=0, le=100)
    last_reviewed_at: datetime | None


class TopicLearningSignalsPage(Page[TopicLearningSignals]):
    period_days: int = Field(ge=7, le=365)
    period_start: datetime
    timezone: str
    generated_at: datetime
