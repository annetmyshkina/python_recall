import pytest
from pydantic import ValidationError

from backend.app.ai.card_generation_service import normalize_question
from backend.app.ai.scenarios.card_generator import (
    SYSTEM_PROMPT,
    GeneratedCardBatch,
    build_user_prompt,
)


def valid_card(question: str = "Что такое GIL?") -> dict[str, object]:
    return {
        "question": question,
        "answer": "Механизм, ограничивающий исполнение байткода Python.",
        "explanation": None,
        "code_example": None,
        "difficulty": "intermediate",
    }


def test_generator_schema_and_prompt_are_strict_and_russian() -> None:
    result = GeneratedCardBatch.model_validate({"cards": [valid_card()]})
    prompt = build_user_prompt(
        topic_name="Потоки",
        topic_description=None,
        source_text="Краткий конспект",
        requested_count=1,
        existing_questions=[],
    )

    assert result.cards[0].question == "Что такое GIL?"
    assert "русском языке" in SYSTEM_PROMPT
    assert "Краткий конспект" in prompt


def test_partially_invalid_batch_is_rejected_as_a_whole() -> None:
    invalid = valid_card("Некорректный черновик")
    invalid.pop("answer")

    with pytest.raises(ValidationError):
        GeneratedCardBatch.model_validate(
            {"cards": [valid_card(), invalid]},
        )


@pytest.mark.parametrize("count", [0, 11])
def test_generator_rejects_package_outside_limits(count: int) -> None:
    with pytest.raises(ValidationError):
        GeneratedCardBatch.model_validate(
            {"cards": [valid_card(str(index)) for index in range(count)]}
        )


def test_question_normalization_handles_case_unicode_and_whitespace() -> None:
    assert normalize_question("  Что\u00a0такое   GIL? ") == normalize_question(
        "что такое gil?"
    )
