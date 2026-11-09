import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from uuid import uuid4

import httpx
import pytest
from sqlalchemy import func, select

from backend.app.ai.manager import AiProviderStatus
from backend.app.ai.models import (
    AiRequest,
    AiRequestStatus,
    AiUsageLog,
    AiUsageStatus,
    AnswerEvaluation,
)
from backend.app.ai.providers.base import (
    ProviderUsage,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.ai.providers.errors import (
    AiDisabledError,
    AiModelMissingError,
    AiProviderResponseError,
    AiProviderTimeoutError,
    AiProviderUnavailableError,
)
from backend.app.core.config import Settings
from backend.app.core.database import Database
from backend.app.main import create_app


class FakeEvaluationManager:
    provider_name = "ollama"
    model = "qwen3:4b"

    def __init__(
        self,
        *,
        outcome: dict[str, Any] | Exception | None = None,
    ) -> None:
        self.outcome = outcome or {
            "correctness": "partially_correct",
            "completeness": 75,
            "score": 80,
            "covered_concepts": ["Оборачивание вызываемого объекта"],
            "missing_concepts": ["functools.wraps"],
            "mistakes": [],
            "feedback": "Основная идея раскрыта верно.",
            "recommendation": "Повторить сохранение метаданных функции.",
        }
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
        data = response_model.model_validate(self.outcome)
        return StructuredResult(
            data=data,
            provider=self.provider_name,
            model=self.model,
            usage=ProviderUsage(
                input_tokens=120,
                output_tokens=45,
                total_duration_ns=2_500_000_000,
            ),
        )


class BlockingEvaluationManager(FakeEvaluationManager):
    def __init__(self) -> None:
        super().__init__()
        self.started = asyncio.Event()
        self.release = asyncio.Event()

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        self.started.set()
        await self.release.wait()
        return await super().generate_structured(request, response_model)


@asynccontextmanager
async def ai_client(
    database: Database,
    manager: FakeEvaluationManager,
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


async def create_card_and_attempt(
    client: httpx.AsyncClient,
) -> tuple[dict[str, object], dict[str, object]]:
    category = (
        await client.post("/api/v1/categories", json={"name": f"C-{uuid4()}"})
    ).json()
    topic = (
        await client.post(
            "/api/v1/topics",
            json={"category_id": category["id"], "name": f"T-{uuid4()}"},
        )
    ).json()
    card_response = await client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic["id"],
            "question": "Что такое декоратор?",
            "answer": "Вызываемый объект, оборачивающий другой вызываемый объект.",
            "explanation": "Часто применяется с синтаксисом @.",
            "code_example": "@decorator\ndef function(): ...",
            "difficulty": "beginner",
        },
    )
    assert card_response.status_code == 201
    card = card_response.json()
    attempt_response = await client.post(
        f"/api/v1/reviews/{card['id']}/attempts",
        json={"user_answer": "Это функция, которая оборачивает другую функцию."},
    )
    assert attempt_response.status_code == 201
    return card, attempt_response.json()


@pytest.mark.asyncio
async def test_evaluation_is_persisted_replayed_and_read_without_changing_sm2(
    test_database: Database,
) -> None:
    manager = FakeEvaluationManager()
    async with ai_client(test_database, manager) as client:
        card, attempt = await create_card_and_attempt(client)
        key = str(uuid4())
        response = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )

        assert response.status_code == 201
        result = response.json()
        assert result["attempt_id"] == attempt["id"]
        assert result["card_id"] == card["id"]
        assert result["correctness"] == "partially_correct"
        assert result["completeness"] == 75
        assert result["score"] == 80
        assert result["prompt_version"] == "answer-evaluator-v2-ru"

        replay = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )
        assert replay.status_code == 200
        assert replay.headers["idempotency-replayed"] == "true"
        assert replay.json() == result
        assert len(manager.calls) == 1

        await client.patch(
            f"/api/v1/cards/{card['id']}",
            json={"is_archived": True},
        )
        replay_after_archive = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )
        assert replay_after_archive.status_code == 200
        assert replay_after_archive.json() == result
        assert len(manager.calls) == 1

        by_id = await client.get(f"/api/v1/ai/answer-evaluations/{result['id']}")
        history = await client.get(
            "/api/v1/ai/answer-evaluations",
            params={"attempt_id": attempt["id"]},
        )
        unchanged_card = await client.get(f"/api/v1/cards/{card['id']}")

    assert by_id.status_code == 200
    assert by_id.json() == result
    assert history.status_code == 200
    assert history.json()["pagination"]["total"] == 1
    assert history.json()["items"] == [result]
    assert unchanged_card.json()["repetitions"] == 0
    assert unchanged_card.json()["last_reviewed_at"] is None

    source = manager.calls[0]
    assert source.scenario == "answer_evaluation"
    assert "SM-2" in source.system_prompt
    assert "Что такое декоратор?" in source.user_prompt

    with test_database.session() as session:
        request = session.scalar(select(AiRequest))
        evaluation = session.scalar(select(AnswerEvaluation))
        usage = session.scalar(select(AiUsageLog))
        assert request is not None
        assert request.status == AiRequestStatus.SUCCEEDED
        assert evaluation is not None
        assert evaluation.question_snapshot == "Что такое декоратор?"
        assert evaluation.user_answer_snapshot == attempt["user_answer"]
        assert usage is not None
        assert usage.status == AiUsageStatus.SUCCEEDED
        assert usage.input_tokens == 120
        assert usage.output_tokens == 45
        assert usage.total_duration_ns == 2_500_000_000


@pytest.mark.asyncio
async def test_new_key_creates_new_evaluation_and_reused_key_conflicts(
    test_database: Database,
) -> None:
    manager = FakeEvaluationManager()
    async with ai_client(test_database, manager) as client:
        card, first_attempt = await create_card_and_attempt(client)
        second_attempt = (
            await client.post(
                f"/api/v1/reviews/{card['id']}/attempts",
                json={"user_answer": "Другой ответ"},
            )
        ).json()
        first_key = str(uuid4())
        first = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": first_attempt["id"]},
            headers={"Idempotency-Key": first_key},
        )
        second = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": first_attempt["id"]},
            headers={"Idempotency-Key": str(uuid4())},
        )
        conflict = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": second_attempt["id"]},
            headers={"Idempotency-Key": first_key},
        )

    assert first.status_code == 201
    assert second.status_code == 201
    assert first.json()["id"] != second.json()["id"]
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"
    assert len(manager.calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("error", "status_code", "error_code"),
    [
        (AiDisabledError("private"), 503, "ai_disabled"),
        (AiModelMissingError("private"), 503, "ai_model_missing"),
        (AiProviderUnavailableError("private"), 503, "ai_provider_unavailable"),
        (AiProviderTimeoutError("private"), 504, "ai_provider_timeout"),
        (AiProviderResponseError("private"), 502, "ai_invalid_response"),
    ],
)
async def test_provider_failure_is_persisted_and_replayed_without_second_call(
    test_database: Database,
    error: Exception,
    status_code: int,
    error_code: str,
) -> None:
    manager = FakeEvaluationManager(outcome=error)
    async with ai_client(test_database, manager) as client:
        _, attempt = await create_card_and_attempt(client)
        key = str(uuid4())
        first = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )
        replay = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )

    assert first.status_code == status_code
    assert first.json()["code"] == error_code
    assert "private" not in first.text
    assert replay.status_code == status_code
    assert replay.json()["code"] == error_code
    assert len(manager.calls) == 1

    with test_database.session() as session:
        request = session.scalar(select(AiRequest))
        usage = session.scalar(select(AiUsageLog))
        assert request is not None
        assert request.status == AiRequestStatus.FAILED
        assert request.error_code == error_code
        assert usage is not None
        assert usage.status == AiUsageStatus.FAILED
        assert usage.error_code == error_code
        assert session.scalar(select(func.count(AnswerEvaluation.id))) == 0


@pytest.mark.asyncio
async def test_missing_or_archived_attempt_is_rejected_before_provider_call(
    test_database: Database,
) -> None:
    manager = FakeEvaluationManager()
    async with ai_client(test_database, manager) as client:
        missing = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": str(uuid4())},
            headers={"Idempotency-Key": str(uuid4())},
        )
        card, attempt = await create_card_and_attempt(client)
        await client.patch(
            f"/api/v1/cards/{card['id']}",
            json={"is_archived": True},
        )
        archived = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": str(uuid4())},
        )

    assert missing.status_code == 404
    assert archived.status_code == 409
    assert archived.json()["code"] == "card_archived"
    assert manager.calls == []
    with test_database.session() as session:
        assert session.scalar(select(func.count(AiRequest.id))) == 0


@pytest.mark.asyncio
async def test_parallel_duplicate_is_in_progress_and_snapshot_stays_immutable(
    test_database: Database,
) -> None:
    manager = BlockingEvaluationManager()
    async with ai_client(test_database, manager) as client:
        card, attempt = await create_card_and_attempt(client)
        key = str(uuid4())
        first_task = asyncio.create_task(
            client.post(
                "/api/v1/ai/evaluate-answer",
                json={"attempt_id": attempt["id"]},
                headers={"Idempotency-Key": key},
            )
        )
        await manager.started.wait()

        duplicate = await client.post(
            "/api/v1/ai/evaluate-answer",
            json={"attempt_id": attempt["id"]},
            headers={"Idempotency-Key": key},
        )
        changed = await client.patch(
            f"/api/v1/cards/{card['id']}",
            json={"question": "Изменённый вопрос"},
        )
        manager.release.set()
        first = await first_task

    assert duplicate.status_code == 409
    assert duplicate.json()["code"] == "ai_request_in_progress"
    assert changed.status_code == 200
    assert first.status_code == 201
    assert len(manager.calls) == 1

    with test_database.session() as session:
        evaluation = session.scalar(select(AnswerEvaluation))
        assert evaluation is not None
        assert evaluation.question_snapshot == "Что такое декоратор?"
