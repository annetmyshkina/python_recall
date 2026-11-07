from datetime import date, datetime

from pydantic import Field

from backend.app.core.schemas import ApiSchema, Page
from backend.app.topics.schemas import TopicRead


class StatisticsOverview(ApiSchema):
    total_cards: int = Field(ge=0)
    active_cards: int = Field(ge=0)
    archived_cards: int = Field(ge=0)
    due_cards: int = Field(ge=0)
    new_cards: int = Field(ge=0)
    reviews_today: int = Field(ge=0)
    success_rate_30d: float | None = Field(default=None, ge=0, le=1)
    timezone: str
    generated_at: datetime


class TopicStatistics(ApiSchema):
    topic: TopicRead
    total_cards: int = Field(ge=0)
    active_cards: int = Field(ge=0)
    due_cards: int = Field(ge=0)
    new_cards: int = Field(ge=0)
    reviews_30d: int = Field(ge=0)
    success_rate_30d: float | None = Field(default=None, ge=0, le=1)


class TopicStatisticsPage(Page[TopicStatistics]):
    pass


class ActivityDay(ApiSchema):
    date: date
    reviews: int = Field(ge=0)
    successful_reviews: int = Field(ge=0)
    success_rate: float | None = Field(default=None, ge=0, le=1)


class ActivityStatistics(ApiSchema):
    timezone: str
    items: list[ActivityDay] = Field(max_length=366)
