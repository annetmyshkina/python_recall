from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import event, func, select

from backend.app.ai.card_generation_service import accept_suggestion
from backend.app.ai.manager import AiProviderStatus
from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AiUsageLog,
    AiUsageStatus,
    CardSuggestion,
    CardSuggestionStatus,
)
from backend.app.ai.providers.base import (
    ProviderUsage,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.ai.providers.errors import AiProviderTimeoutError
from backend.app.cards.models import Card
from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.main import create_app


def generated_card(
    question: str,
    *,
    difficulty: str = "beginner",
) -> dict[str, object]:
    return {
        "question": question,
        "answer": f"Ответ на вопрос: {question}",
        "explanation": "Краткое пояснение.",
        "code_example": None,
        "difficulty": difficulty,
    }


class FakeGenerationManager:
    provider_name = "ollama"
    model = "qwen3:4b"

    def __init__(self, outcome: dict[str, Any] | Exception) -> None:
        self.outcome = outcome
        self.calls: list[StructuredRequest] = []

    async def get_status(self) -> AiProviderStatus:
        return AiProviderStatus("ollama", True, "ready", self.model)

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        self.calls.append(request)
        if isinstance(self.outcome, Exception):
            raise self.outcome
        return StructuredResult(
            data=response_model.model_validate(self.outcome),
            provider=self.provider_name,
            model=self.model,
            usage=ProviderUsage(100, 60, 3_000_000_000),
        )


@asynccontextmanager
async def ai_client(
    database: Database,
    manager: FakeGenerationManager,
) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        ai_enabled=True,
    )
    application = create_app(settings, database, manager)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


async def create_topic(client: httpx.AsyncClient) -> dict[str, object]:
    category = (
        await client.post("/api/v1/categories", json={"name": f"C-{uuid4()}"})
    ).json()
    response = await client.post(
        "/api/v1/topics",
        json={
            "category_id": category["id"],
            "name": f"T-{uuid4()}",
            "description": "Тема для генерации карточек.",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_generation_is_pending_replayable_and_does_not_create_cards(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {
            "cards": [
                generated_card("Что делает GIL?", difficulty="intermediate"),
                generated_card("Зачем нужен threading.Lock?"),
            ]
        }
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        key = str(uuid4())
        payload = {
            "topic_id": topic["id"],
            "source_text": "Конспект о потоках и синхронизации.",
            "count": 2,
        }
        response = await client.post(
            "/api/v1/ai/generate-cards",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        replay = await client.post(
            "/api/v1/ai/generate-cards",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        cards = await client.get("/api/v1/cards")
        history = await client.get(
            "/api/v1/ai/card-suggestions",
            params={"topic_id": topic["id"], "status": "pending"},
        )
        suggestion = await client.get(
            f"/api/v1/ai/card-suggestions/{response.json()['items'][0]['id']}"
        )

    assert response.status_code == 201
    result = response.json()
    assert len(result["items"]) == 2
    assert all(item["status"] == "pending" for item in result["items"])
    assert all(item["accepted_card_id"] is None for item in result["items"])
    assert replay.status_code == 200
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json() == result
    assert cards.json()["pagination"]["total"] == 0
    assert history.json()["pagination"]["total"] == 2
    assert suggestion.json() == result["items"][0]
    assert len(manager.calls) == 1
    assert manager.calls[0].scenario == "card_generation"
    assert "Конспект о потоках" in manager.calls[0].user_prompt

    with test_database.session() as session:
        request = session.scalar(select(AiRequest))
        usage = session.scalar(select(AiUsageLog))
        assert request is not None
        assert request.status == AiRequestStatus.SUCCEEDED
        assert usage is not None
        assert usage.status == AiUsageStatus.SUCCEEDED
        assert usage.input_tokens == 100
        assert usage.output_tokens == 60


@pytest.mark.asyncio
async def test_normalized_existing_and_in_package_duplicates_are_skipped(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {
            "cards": [
                generated_card("  что   такое gil? "),
                generated_card("Зачем нужен threading.Lock?"),
                generated_card("зачем\u00a0нужен  THREADING.LOCK?"),
            ]
        }
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        existing = await client.post(
            "/api/v1/cards",
            json={
                "topic_id": topic["id"],
                "question": "Что такое GIL?",
                "answer": "Глобальная блокировка интерпретатора.",
                "difficulty": "intermediate",
            },
        )
        assert existing.status_code == 201
        response = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 3},
            headers={"Idempotency-Key": str(uuid4())},
        )

    assert response.status_code == 201
    items = response.json()["items"]
    assert [item["question"] for item in items] == ["Зачем нужен threading.Lock?"]
    assert items[0]["position"] == 1


@pytest.mark.asyncio
async def test_accept_and_reject_are_explicit_one_way_transitions(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {
            "cards": [
                generated_card("Что такое mutex?"),
                generated_card("Что такое semaphore?"),
            ]
        }
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        generated = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 2},
            headers={"Idempotency-Key": str(uuid4())},
        )
        first, second = generated.json()["items"]
        accepted = await client.post(
            f"/api/v1/ai/card-suggestions/{first['id']}/accept"
        )
        rejected = await client.post(
            f"/api/v1/ai/card-suggestions/{second['id']}/reject"
        )
        accept_again = await client.post(
            f"/api/v1/ai/card-suggestions/{first['id']}/accept"
        )
        reject_again = await client.post(
            f"/api/v1/ai/card-suggestions/{second['id']}/reject"
        )
        cards = await client.get("/api/v1/cards", params={"topic_id": topic["id"]})

    assert accepted.status_code == 200
    assert accepted.json()["status"] == "accepted"
    assert accepted.json()["accepted_card_id"] is not None
    assert accepted.json()["reviewed_at"] is not None
    assert rejected.status_code == 200
    assert rejected.json()["status"] == "rejected"
    assert rejected.json()["accepted_card_id"] is None
    assert cards.json()["pagination"]["total"] == 1
    assert cards.json()["items"][0]["question"] == "Что такое mutex?"
    assert accept_again.status_code == 409
    assert accept_again.json()["code"] == "suggestion_already_reviewed"
    assert reject_again.status_code == 409
    assert reject_again.json()["code"] == "suggestion_already_reviewed"


@pytest.mark.asyncio
async def test_card_created_after_generation_blocks_duplicate_acceptance(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {"cards": [generated_card("Что такое race condition?")]}
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        generated = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 1},
            headers={"Idempotency-Key": str(uuid4())},
        )
        suggestion = generated.json()["items"][0]
        await client.post(
            "/api/v1/cards",
            json={
                "topic_id": topic["id"],
                "question": "  что такое RACE   CONDITION? ",
                "answer": "Состояние гонки.",
                "difficulty": "beginner",
            },
        )
        accepted = await client.post(
            f"/api/v1/ai/card-suggestions/{suggestion['id']}/accept"
        )

    assert accepted.status_code == 409
    assert accepted.json()["code"] == "suggestion_duplicate"
    with test_database.session() as session:
        saved = session.get(CardSuggestion, UUID(suggestion["id"]))
        assert saved is not None
        assert saved.status == CardSuggestionStatus.PENDING
        assert session.scalar(select(func.count(Card.id))) == 1


@pytest.mark.asyncio
async def test_generation_validates_command_and_replays_provider_failure(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(AiProviderTimeoutError("private timeout"))
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        invalid = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 11},
            headers={"Idempotency-Key": str(uuid4())},
        )
        key = str(uuid4())
        payload = {"topic_id": topic["id"], "count": 1}
        failed = await client.post(
            "/api/v1/ai/generate-cards",
            json=payload,
            headers={"Idempotency-Key": key},
        )
        replay = await client.post(
            "/api/v1/ai/generate-cards",
            json=payload,
            headers={"Idempotency-Key": key},
        )

    assert invalid.status_code == 422
    assert failed.status_code == 504
    assert failed.json()["code"] == "ai_provider_timeout"
    assert "private timeout" not in failed.text
    assert replay.status_code == 504
    assert len(manager.calls) == 1
    with test_database.session() as session:
        request = session.scalar(select(AiRequest))
        usage = session.scalar(select(AiUsageLog))
        assert request is not None
        assert request.status == AiRequestStatus.FAILED
        assert usage is not None
        assert usage.status == AiUsageStatus.FAILED


@pytest.mark.asyncio
async def test_wrong_package_size_fails_and_idempotency_key_cannot_be_reused(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {"cards": [generated_card("Единственная карточка")]}
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        key = str(uuid4())
        wrong_size = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 2},
            headers={"Idempotency-Key": key},
        )
        conflict = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 1},
            headers={"Idempotency-Key": key},
        )

    assert wrong_size.status_code == 502
    assert wrong_size.json()["code"] == "ai_invalid_response"
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert len(manager.calls) == 1


@pytest.mark.asyncio
async def test_accept_rolls_back_card_when_suggestion_update_fails(
    test_database: Database,
) -> None:
    manager = FakeGenerationManager(
        {"cards": [generated_card("Что проверяет транзакция?")]}
    )
    async with ai_client(test_database, manager) as client:
        topic = await create_topic(client)
        generated = await client.post(
            "/api/v1/ai/generate-cards",
            json={"topic_id": topic["id"], "count": 1},
            headers={"Idempotency-Key": str(uuid4())},
        )
    suggestion_id = UUID(generated.json()["items"][0]["id"])

    def fail_suggestion_update(
        _connection: object,
        _cursor: object,
        statement: str,
        _parameters: object,
        _context: object,
        _executemany: bool,
    ) -> None:
        if statement.lstrip().upper().startswith("UPDATE AI_SUGGESTIONS"):
            raise RuntimeError("simulated database failure")

    event.listen(
        test_database.engine,
        "before_cursor_execute",
        fail_suggestion_update,
    )
    try:
        with test_database.session() as session:
            with pytest.raises(RuntimeError, match="simulated database failure"):
                accept_suggestion(session, suggestion_id)
            session.rollback()
    finally:
        event.remove(
            test_database.engine,
            "before_cursor_execute",
            fail_suggestion_update,
        )

    with test_database.session() as session:
        suggestion = session.get(CardSuggestion, suggestion_id)
        assert suggestion is not None
        assert suggestion.status == CardSuggestionStatus.PENDING
        assert suggestion.accepted_card_id is None
        assert session.scalar(select(func.count(Card.id))) == 0
