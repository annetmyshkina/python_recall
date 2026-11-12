from datetime import UTC, datetime
from uuid import UUID, uuid4

import httpx
import pytest

from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AnswerCorrectness,
    AnswerEvaluation,
)
from backend.app.cards.models import Card
from backend.app.core.database import Database
from backend.app.reviews.models import AnswerAttempt


async def create_category(client: httpx.AsyncClient, name: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/categories",
        json={"name": f"{name}-{uuid4()}"},
    )
    assert response.status_code == 201
    return response.json()


async def create_topic(
    client: httpx.AsyncClient,
    category_id: object,
    name: str,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/topics",
        json={"category_id": str(category_id), "name": name},
    )
    assert response.status_code == 201
    return response.json()


async def create_card(
    client: httpx.AsyncClient,
    topic_id: object,
    question: str,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/cards",
        json={
            "topic_id": str(topic_id),
            "question": question,
            "answer": f"Ответ: {question}",
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 201
    return response.json()


async def complete_reviews(
    client: httpx.AsyncClient,
    card_id: object,
    ratings: list[str],
) -> None:
    for rating in ratings:
        response = await client.post(
            f"/api/v1/reviews/{card_id}/complete",
            json={"rating": rating},
            headers={"Idempotency-Key": str(uuid4())},
        )
        assert response.status_code == 201


def add_ai_evaluations(
    database: Database,
    card_id: object,
    completeness_values: list[int],
) -> None:
    now = datetime.now(UTC)
    with database.session() as session:
        card = session.get(Card, UUID(str(card_id)))
        assert card is not None
        for position, completeness in enumerate(completeness_values):
            attempt = AnswerAttempt(
                card_id=card.id,
                user_answer=f"Письменный ответ {position}",
            )
            request = AiRequest(
                scenario="answer_evaluation",
                idempotency_key=uuid4(),
                request_fingerprint="a" * 64,
                status=AiRequestStatus.SUCCEEDED,
                completed_at=now,
            )
            session.add_all([attempt, request])
            session.flush()
            session.add(
                AnswerEvaluation(
                    request_id=request.id,
                    answer_attempt_id=attempt.id,
                    correctness=AnswerCorrectness.PARTIALLY_CORRECT,
                    completeness=completeness,
                    score=completeness,
                    covered_concepts=["основа"],
                    missing_concepts=["детали"],
                    mistakes=[],
                    feedback="Нужно дополнить ответ.",
                    recommendation="Повторите детали.",
                    provider="ollama",
                    model="qwen3:4b",
                    prompt_version="test",
                    question_snapshot=card.question,
                    reference_answer_snapshot=card.answer,
                    explanation_snapshot=card.explanation,
                    code_example_snapshot=card.code_example,
                    difficulty_snapshot=card.difficulty.value,
                    user_answer_snapshot=attempt.user_answer,
                )
            )
        session.commit()


@pytest.mark.asyncio
async def test_learning_signals_classify_explain_and_sort_topics(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client, "Adaptive")
    empty = await create_topic(api_client, category["id"], "Без карточек")
    new = await create_topic(api_client, category["id"], "Новая тема")
    weak = await create_topic(api_client, category["id"], "Слабая тема")
    stable = await create_topic(api_client, category["id"], "Стабильная тема")
    await create_card(api_client, new["id"], "Новая карточка")
    weak_card = await create_card(api_client, weak["id"], "Слабая карточка")
    stable_card = await create_card(
        api_client,
        stable["id"],
        "Стабильная карточка",
    )
    await complete_reviews(api_client, weak_card["id"], ["again", "good", "good"])
    await complete_reviews(api_client, stable_card["id"], ["good", "good", "good"])

    response = await api_client.get(
        "/api/v1/adaptive/topics",
        params={"category_id": category["id"]},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["period_days"] == 30
    assert body["timezone"] == "UTC"
    assert body["pagination"] == {"page": 1, "limit": 20, "total": 4, "pages": 1}
    assert [item["topic"]["id"] for item in body["items"]] == [
        weak["id"],
        empty["id"],
        new["id"],
        stable["id"],
    ]

    weak_item, empty_item, new_item, stable_item = body["items"]
    assert weak_item["status"] == "needs_attention"
    assert weak_item["reasons"] == ["frequent_again"]
    assert weak_item["reviews"] == 3
    assert weak_item["again_reviews"] == 1
    assert weak_item["success_rate"] == pytest.approx(2 / 3)
    assert weak_item["again_rate"] == pytest.approx(1 / 3)
    assert empty_item["status"] == "insufficient_data"
    assert empty_item["reasons"] == ["no_active_cards"]
    assert new_item["status"] == "insufficient_data"
    assert new_item["reasons"] == ["insufficient_history"]
    assert stable_item["status"] == "stable"
    assert stable_item["reasons"] == []
    assert stable_item["reviews"] == 3
    assert stable_item["success_rate"] == 1.0


@pytest.mark.asyncio
async def test_learning_signals_use_ai_history_without_requiring_reviews(
    api_client: httpx.AsyncClient,
    test_database: Database,
) -> None:
    category = await create_category(api_client, "AI signals")
    topic = await create_topic(api_client, category["id"], "AI topic")
    card = await create_card(api_client, topic["id"], "AI card")
    add_ai_evaluations(test_database, card["id"], [50, 60, 70])

    response = await api_client.get(
        "/api/v1/adaptive/topics",
        params={"status": "needs_attention", "period_days": 7},
    )

    assert response.status_code == 200
    item = next(
        item for item in response.json()["items"] if item["topic"]["id"] == topic["id"]
    )
    assert item["reasons"] == ["low_ai_completeness"]
    assert item["reviews"] == 0
    assert item["ai_evaluations"] == 3
    assert item["average_ai_score"] == 60.0
    assert item["average_ai_completeness"] == 60.0


@pytest.mark.asyncio
async def test_learning_signals_exclude_archived_cards_and_validate_filters(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client, "Archived signals")
    topic = await create_topic(api_client, category["id"], "Archived topic")
    card = await create_card(api_client, topic["id"], "Archived card")
    await complete_reviews(api_client, card["id"], ["again", "again", "again"])
    archived = await api_client.patch(
        f"/api/v1/cards/{card['id']}",
        json={"is_archived": True},
    )
    assert archived.status_code == 200

    response = await api_client.get(
        "/api/v1/adaptive/topics",
        params={"category_id": category["id"]},
    )
    invalid_period = await api_client.get(
        "/api/v1/adaptive/topics",
        params={"period_days": 6},
    )
    invalid_status = await api_client.get(
        "/api/v1/adaptive/topics",
        params={"status": "unknown"},
    )

    assert response.status_code == 200
    item = response.json()["items"][0]
    assert item["status"] == "insufficient_data"
    assert item["reasons"] == ["no_active_cards"]
    assert item["active_cards"] == 0
    assert item["reviews"] == 0
    assert invalid_period.status_code == 422
    assert invalid_status.status_code == 422
