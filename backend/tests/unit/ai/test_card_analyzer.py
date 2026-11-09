from uuid import uuid4

import pytest
from pydantic import ValidationError

from backend.app.ai.card_analysis_service import analyze_card
from backend.app.ai.manager import AiProviderStatus
from backend.app.ai.providers.base import (
    ProviderUsage,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.ai.scenarios.card_analyzer import (
    SYSTEM_PROMPT,
    CardAnalysisOutput,
)
from backend.app.ai.schemas import CardAnalysisCreate
from backend.app.cards.models import Card, CardDifficulty
from backend.app.categories.models import Category
from backend.app.core.database import Database
from backend.app.topics.models import Topic


def valid_output() -> dict[str, object]:
    return {
        "quality": "needs_improvement",
        "clarity_score": 80,
        "completeness_score": 70,
        "accuracy_score": 90,
        "specificity_score": 75,
        "learning_value_score": 85,
        "issues": [
            {"field": "answer", "severity": "warning", "message": "Добавьте пример."}
        ],
        "feedback": "Карточка в целом полезна.",
        "recommendation": "Уточните ответ.",
        "suggested_question": None,
        "suggested_answer": "Уточнённый ответ.",
        "suggested_explanation": None,
        "suggested_code_example": None,
    }


def test_card_analysis_output_and_russian_prompt() -> None:
    result = CardAnalysisOutput.model_validate(valid_output())
    assert result.accuracy_score == 90
    assert "русском языке" in SYSTEM_PROMPT


@pytest.mark.parametrize("field", ["clarity_score", "accuracy_score"])
def test_card_analysis_rejects_invalid_score(field: str) -> None:
    payload = valid_output()
    payload[field] = 101
    with pytest.raises(ValidationError):
        CardAnalysisOutput.model_validate(payload)


def test_card_analysis_requires_suggestion_for_serious_field_issue() -> None:
    payload = valid_output()
    payload["suggested_answer"] = None
    with pytest.raises(ValidationError, match="suggestion is required"):
        CardAnalysisOutput.model_validate(payload)


class FakeManager:
    provider_name = "ollama"
    model = "qwen3:4b"

    def __init__(self) -> None:
        self.calls = 0

    async def get_status(self) -> AiProviderStatus:
        return AiProviderStatus("ollama", True, "ready", self.model)

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        self.calls += 1
        return StructuredResult(
            data=response_model.model_validate(valid_output()),
            provider="ollama",
            model=self.model,
            usage=ProviderUsage(10, 5, 100),
        )


@pytest.mark.asyncio
async def test_card_analysis_is_persisted_and_replayed_without_editing_card(
    test_database: Database,
) -> None:
    with test_database.session() as session:
        category = Category(name="Python")
        topic = Topic(name="Decorators", category=category)
        card = Card(
            topic=topic,
            question="Что такое декоратор?",
            answer="Обёртка.",
            difficulty=CardDifficulty.BEGINNER,
        )
        session.add(card)
        session.commit()
        card_id = card.id

    manager = FakeManager()
    key = uuid4()
    with test_database.session() as session:
        first, replayed = await analyze_card(
            session, CardAnalysisCreate(card_id=card_id), key, manager
        )
        second, replayed_second = await analyze_card(
            session, CardAnalysisCreate(card_id=card_id), key, manager
        )
        unchanged = session.get(Card, card_id)

    assert replayed is False
    assert replayed_second is True
    assert first == second
    assert first.suggested_answer == "Уточнённый ответ."
    assert manager.calls == 1
    assert unchanged is not None
    assert unchanged.answer == "Обёртка."
