"""Add Card Analyzer persistence.

Revision ID: 20261109_0003
Revises: 20261109_0002
Create Date: 2026-11-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20261109_0003"
down_revision: str | None = "20261109_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "card_analyses",
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("card_id", sa.Uuid(), nullable=False),
        sa.Column(
            "quality",
            sa.Enum(
                "good",
                "needs_improvement",
                "needs_review",
                name="card_quality",
                native_enum=False,
                create_constraint=True,
            ),
            nullable=False,
        ),
        sa.Column("clarity_score", sa.Integer(), nullable=False),
        sa.Column("completeness_score", sa.Integer(), nullable=False),
        sa.Column("accuracy_score", sa.Integer(), nullable=False),
        sa.Column("specificity_score", sa.Integer(), nullable=False),
        sa.Column("learning_value_score", sa.Integer(), nullable=False),
        sa.Column("issues", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("feedback", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.Text(), nullable=False),
        sa.Column("suggested_question", sa.Text(), nullable=True),
        sa.Column("suggested_answer", sa.Text(), nullable=True),
        sa.Column("suggested_explanation", sa.Text(), nullable=True),
        sa.Column("suggested_code_example", sa.Text(), nullable=True),
        sa.Column("provider", sa.String(length=50), nullable=False),
        sa.Column("model", sa.String(length=200), nullable=False),
        sa.Column("prompt_version", sa.String(length=100), nullable=False),
        sa.Column("question_snapshot", sa.Text(), nullable=False),
        sa.Column("answer_snapshot", sa.Text(), nullable=False),
        sa.Column("explanation_snapshot", sa.Text(), nullable=True),
        sa.Column("code_example_snapshot", sa.Text(), nullable=True),
        sa.Column("difficulty_snapshot", sa.String(length=20), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint(
            "clarity_score BETWEEN 0 AND 100 AND "
            "completeness_score BETWEEN 0 AND 100 AND "
            "accuracy_score BETWEEN 0 AND 100 AND "
            "specificity_score BETWEEN 0 AND 100 AND "
            "learning_value_score BETWEEN 0 AND 100",
            name="ck_card_analyses_scores_range",
        ),
        sa.ForeignKeyConstraint(["card_id"], ["cards.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["request_id"], ["ai_requests.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_id", name="uq_card_analyses_request_id"),
    )
    op.create_index(
        "ix_card_analyses_card_created",
        "card_analyses",
        ["card_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("card_analyses")
