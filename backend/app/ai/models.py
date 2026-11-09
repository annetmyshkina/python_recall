from datetime import datetime
from enum import StrEnum
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    JSON,
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.core.database import Base
from backend.app.core.models import CreatedAtMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from backend.app.cards.models import Card
    from backend.app.reviews.models import AnswerAttempt

JSON_DOCUMENT = JSON().with_variant(JSONB(), "postgresql")


class AiRequestStatus(StrEnum):
    PENDING = "pending"
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AiUsageStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"


class AnswerCorrectness(StrEnum):
    CORRECT = "correct"
    PARTIALLY_CORRECT = "partially_correct"
    INCORRECT = "incorrect"
    NEEDS_REVIEW = "needs_review"


class CardQuality(StrEnum):
    GOOD = "good"
    NEEDS_IMPROVEMENT = "needs_improvement"
    NEEDS_REVIEW = "needs_review"


class AiRequest(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Idempotent user command reserved before an external AI call."""

    __tablename__ = "ai_requests"
    __table_args__ = (
        CheckConstraint(
            "length(btrim(scenario)) > 0",
            name="ck_ai_requests_scenario_present",
        ),
        CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_ai_requests_fingerprint_length",
        ),
        CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL AND error_code IS NULL) OR "
            "(status = 'succeeded' AND completed_at IS NOT NULL "
            "AND error_code IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL "
            "AND error_code IS NOT NULL)",
            name="ck_ai_requests_status_fields_match",
        ),
        Index("uq_ai_requests_idempotency_key", "idempotency_key", unique=True),
        Index("ix_ai_requests_scenario_created", "scenario", "created_at"),
    )

    scenario: Mapped[str] = mapped_column(String(50), nullable=False)
    idempotency_key: Mapped[UUID] = mapped_column(nullable=False)
    request_fingerprint: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[AiRequestStatus] = mapped_column(
        Enum(
            AiRequestStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="ai_request_status",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
        default=AiRequestStatus.PENDING,
    )
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    answer_evaluation: Mapped["AnswerEvaluation | None"] = relationship(
        back_populates="request",
        uselist=False,
        passive_deletes=True,
    )
    usage_log: Mapped["AiUsageLog | None"] = relationship(
        back_populates="request",
        uselist=False,
        passive_deletes=True,
    )
    card_analysis: Mapped["CardAnalysis | None"] = relationship(
        back_populates="request",
        uselist=False,
        passive_deletes=True,
    )


class AnswerEvaluation(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable Answer Evaluator result and the exact evaluated snapshot."""

    __tablename__ = "answer_evaluations"
    __table_args__ = (
        CheckConstraint(
            "completeness BETWEEN 0 AND 100",
            name="ck_answer_evaluations_completeness_range",
        ),
        CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_answer_evaluations_score_range",
        ),
        CheckConstraint(
            "length(btrim(feedback)) > 0 AND length(feedback) <= 5000",
            name="ck_answer_evaluations_feedback_length",
        ),
        CheckConstraint(
            "length(btrim(recommendation)) > 0 AND length(recommendation) <= 5000",
            name="ck_answer_evaluations_recommendation_length",
        ),
        UniqueConstraint("request_id", name="uq_answer_evaluations_request_id"),
        Index(
            "ix_answer_evaluations_attempt_created",
            "answer_attempt_id",
            "created_at",
        ),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_requests.id", ondelete="RESTRICT"), nullable=False
    )
    answer_attempt_id: Mapped[UUID] = mapped_column(
        ForeignKey("answer_attempts.id", ondelete="RESTRICT"), nullable=False
    )
    correctness: Mapped[AnswerCorrectness] = mapped_column(
        Enum(
            AnswerCorrectness,
            values_callable=lambda enum: [item.value for item in enum],
            name="answer_correctness",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    completeness: Mapped[int] = mapped_column(Integer, nullable=False)
    score: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_concepts: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    missing_concepts: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    mistakes: Mapped[list[str]] = mapped_column(JSON_DOCUMENT, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    question_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    reference_answer_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_example_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)
    user_answer_snapshot: Mapped[str] = mapped_column(Text, nullable=False)

    request: Mapped[AiRequest] = relationship(back_populates="answer_evaluation")
    answer_attempt: Mapped["AnswerAttempt"] = relationship(
        back_populates="answer_evaluations"
    )


class AiUsageLog(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """One technical usage record for one attempted AI command."""

    __tablename__ = "ai_usage_logs"
    __table_args__ = (
        CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0",
            name="ck_ai_usage_logs_tokens_nonnegative",
        ),
        CheckConstraint(
            "total_duration_ns IS NULL OR total_duration_ns >= 0",
            name="ck_ai_usage_logs_duration_nonnegative",
        ),
        CheckConstraint(
            "(status = 'succeeded' AND error_code IS NULL) OR "
            "(status = 'failed' AND error_code IS NOT NULL)",
            name="ck_ai_usage_logs_status_error_match",
        ),
        UniqueConstraint("request_id", name="uq_ai_usage_logs_request_id"),
        Index("ix_ai_usage_logs_scenario_created", "scenario", "created_at"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_requests.id", ondelete="RESTRICT"), nullable=False
    )
    scenario: Mapped[str] = mapped_column(String(50), nullable=False)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    status: Mapped[AiUsageStatus] = mapped_column(
        Enum(
            AiUsageStatus,
            values_callable=lambda enum: [item.value for item in enum],
            name="ai_usage_status",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    input_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    output_tokens: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_duration_ns: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    error_code: Mapped[str | None] = mapped_column(String(100), nullable=True)

    request: Mapped[AiRequest] = relationship(back_populates="usage_log")


class CardAnalysis(UUIDPrimaryKeyMixin, CreatedAtMixin, Base):
    """Immutable quality analysis and suggestions for one card snapshot."""

    __tablename__ = "card_analyses"
    __table_args__ = (
        CheckConstraint(
            "clarity_score BETWEEN 0 AND 100 AND "
            "completeness_score BETWEEN 0 AND 100 AND "
            "accuracy_score BETWEEN 0 AND 100 AND "
            "specificity_score BETWEEN 0 AND 100 AND "
            "learning_value_score BETWEEN 0 AND 100",
            name="ck_card_analyses_scores_range",
        ),
        UniqueConstraint("request_id", name="uq_card_analyses_request_id"),
        Index("ix_card_analyses_card_created", "card_id", "created_at"),
    )

    request_id: Mapped[UUID] = mapped_column(
        ForeignKey("ai_requests.id", ondelete="RESTRICT"), nullable=False
    )
    card_id: Mapped[UUID] = mapped_column(
        ForeignKey("cards.id", ondelete="RESTRICT"), nullable=False
    )
    quality: Mapped[CardQuality] = mapped_column(
        Enum(
            CardQuality,
            values_callable=lambda enum: [item.value for item in enum],
            name="card_quality",
            native_enum=False,
            create_constraint=True,
        ),
        nullable=False,
    )
    clarity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    completeness_score: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_score: Mapped[int] = mapped_column(Integer, nullable=False)
    specificity_score: Mapped[int] = mapped_column(Integer, nullable=False)
    learning_value_score: Mapped[int] = mapped_column(Integer, nullable=False)
    issues: Mapped[list[dict[str, str]]] = mapped_column(JSON_DOCUMENT, nullable=False)
    feedback: Mapped[str] = mapped_column(Text, nullable=False)
    recommendation: Mapped[str] = mapped_column(Text, nullable=False)
    suggested_question: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_explanation: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_code_example: Mapped[str | None] = mapped_column(Text, nullable=True)
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    model: Mapped[str] = mapped_column(String(200), nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(100), nullable=False)
    question_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    answer_snapshot: Mapped[str] = mapped_column(Text, nullable=False)
    explanation_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    code_example_snapshot: Mapped[str | None] = mapped_column(Text, nullable=True)
    difficulty_snapshot: Mapped[str] = mapped_column(String(20), nullable=False)

    request: Mapped[AiRequest] = relationship(back_populates="card_analysis")
    card: Mapped["Card"] = relationship(back_populates="card_analyses")
