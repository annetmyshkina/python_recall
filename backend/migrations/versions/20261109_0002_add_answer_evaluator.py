"""Add Answer Evaluator persistence.

Revision ID: 20261109_0002
Revises: 20261106_0001
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261109_0002"
down_revision: str | None = "20261106_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ai_requests",
        sa.Column("scenario", sa.String(length=50), nullable=False),
        sa.Column("idempotency_key", sa.Uuid(), nullable=False),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "pending",
                "succeeded",
                "failed",
                name="ai_request_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "length(request_fingerprint) = 64",
            name="ck_ai_requests_fingerprint_length",
        ),
        sa.CheckConstraint(
            "length(btrim(scenario)) > 0",
            name="ck_ai_requests_scenario_present",
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND completed_at IS NULL AND error_code IS NULL) OR "
            "(status = 'succeeded' AND completed_at IS NOT NULL "
            "AND error_code IS NULL) OR "
            "(status = 'failed' AND completed_at IS NOT NULL "
            "AND error_code IS NOT NULL)",
            name="ck_ai_requests_status_fields_match",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_ai_requests_scenario_created",
        "ai_requests",
        ["scenario", "created_at"],
    )
    op.create_index(
        "uq_ai_requests_idempotency_key",
        "ai_requests",
        ["idempotency_key"],
        unique=True,
    )

    op.create_table(
        "answer_evaluations",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("answer_attempt_id", sa.Uuid(), nullable=False),
        sa.Column(
            "correctness",
            sa.Enum(
                "correct",
                "partially_correct",
                "incorrect",
                "needs_review",
                name="answer_correctness",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("completeness", sa.Integer(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column(
            "covered_concepts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "missing_concepts",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "mistakes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("question_snapshot", sa.Text(), nullable=False),
        sa.Column("reference_answer_snapshot", sa.Text(), nullable=False),
        sa.Column("explanation_snapshot", sa.Text(), nullable=True),
        sa.Column("code_example_snapshot", sa.Text(), nullable=True),
        sa.Column("difficulty_snapshot", sa.String(length=20), nullable=False),
        sa.Column("user_answer_snapshot", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "completeness BETWEEN 0 AND 100",
            name="ck_answer_evaluations_completeness_range",
        ),
        sa.CheckConstraint(
            "length(btrim(feedback)) > 0 AND length(feedback) <= 5000",
            name="ck_answer_evaluations_feedback_length",
        ),
        sa.CheckConstraint(
            "length(btrim(recommendation)) > 0 AND length(recommendation) <= 5000",
            name="ck_answer_evaluations_recommendation_length",
        ),
        sa.CheckConstraint(
            "score BETWEEN 0 AND 100",
            name="ck_answer_evaluations_score_range",
        ),
        sa.ForeignKeyConstraint(
            ["answer_attempt_id"],
            ["answer_attempts.id"],
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_answer_evaluations_request_id"),
    )
    op.create_index(
        "ix_answer_evaluations_attempt_created",
        "answer_evaluations",
        ["answer_attempt_id", "created_at"],
    )

    op.create_table(
        "ai_usage_logs",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("scenario", sa.String(length=50), nullable=False),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column(
            "status",
            sa.Enum(
                "succeeded",
                "failed",
                name="ai_usage_status",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("input_tokens", sa.Integer(), nullable=False),
        sa.Column("output_tokens", sa.Integer(), nullable=False),
        sa.Column("total_duration_ns", sa.BigInteger(), nullable=True),
        sa.Column("error_code", sa.String(length=100), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "total_duration_ns IS NULL OR total_duration_ns >= 0",
            name="ck_ai_usage_logs_duration_nonnegative",
        ),
        sa.CheckConstraint(
            "(status = 'succeeded' AND error_code IS NULL) OR "
            "(status = 'failed' AND error_code IS NOT NULL)",
            name="ck_ai_usage_logs_status_error_match",
        ),
        sa.CheckConstraint(
            "input_tokens >= 0 AND output_tokens >= 0",
            name="ck_ai_usage_logs_tokens_nonnegative",
        ),
        sa.ForeignKeyConstraint(
            ["request_id"],
            ["ai_requests.id"],
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_ai_usage_logs_request_id"),
    )
    op.create_index(
        "ix_ai_usage_logs_scenario_created",
        "ai_usage_logs",
        ["scenario", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("ai_usage_logs")
    op.drop_table("answer_evaluations")
    op.drop_table("ai_requests")
