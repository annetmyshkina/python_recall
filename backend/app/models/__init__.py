"""Import all ORM models so SQLAlchemy and Alembic share one metadata graph."""

from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AiUsageLog,
    AiUsageStatus,
    AnswerCorrectness,
    AnswerEvaluation,
    CardAnalysis,
    CardQuality,
)
from backend.app.cards.models import Card, CardDifficulty
from backend.app.categories.models import Category
from backend.app.reviews.models import AnswerAttempt, ReviewLog, ReviewRating
from backend.app.tags.models import CardTag, Tag
from backend.app.topics.models import Topic

__all__ = [
    "AnswerAttempt",
    "AnswerCorrectness",
    "AnswerEvaluation",
    "AiRequest",
    "AiRequestStatus",
    "AiUsageLog",
    "AiUsageStatus",
    "Card",
    "CardAnalysis",
    "CardDifficulty",
    "CardQuality",
    "CardTag",
    "Category",
    "ReviewLog",
    "ReviewRating",
    "Tag",
    "Topic",
]
