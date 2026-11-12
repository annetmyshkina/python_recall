"""Exercise every AI workflow with an in-process deterministic fake provider."""

import asyncio
from typing import Any
from uuid import uuid4

import httpx
from sqlalchemy import event

from backend.app.ai.manager import AiProviderStatus
from backend.app.ai.providers.base import (
    ProviderUsage,
    StructuredModelT,
    StructuredRequest,
    StructuredResult,
)
from backend.app.core.config import Settings
from backend.app.core.database import Base, Database
from backend.app.main import create_app


class FakeAiManager:
    provider_name = "ollama"
    model = "qwen3:4b"

    def __init__(self, *, enabled: bool = True) -> None:
        self.enabled = enabled
        self.calls: list[StructuredRequest] = []

    async def get_status(self) -> AiProviderStatus:
        return AiProviderStatus(
            "ollama",
            self.enabled,
            "ready" if self.enabled else "disabled",
            self.model,
        )

    async def generate_structured(
        self,
        request: StructuredRequest,
        response_model: type[StructuredModelT],
    ) -> StructuredResult[StructuredModelT]:
        if not self.enabled:
            raise AssertionError("disabled AI must not generate")
        self.calls.append(request)
        outputs: dict[str, dict[str, Any]] = {
            "answer_evaluation": {
                "correctness": "correct",
                "completeness": 95,
                "score": 96,
                "covered_concepts": ["functools.wraps"],
                "missing_concepts": [],
                "mistakes": [],
                "feedback": "Ответ верный и конкретный.",
                "recommendation": "Продолжайте практику.",
            },
            "card_analysis": {
                "quality": "good",
                "clarity_score": 95,
                "completeness_score": 95,
                "accuracy_score": 98,
                "specificity_score": 94,
                "learning_value_score": 96,
                "issues": [],
                "feedback": "Карточка сформулирована ясно.",
                "recommendation": "Изменения не требуются.",
                "suggested_question": None,
                "suggested_answer": None,
                "suggested_explanation": None,
                "suggested_code_example": None,
            },
            "card_generation": {
                "cards": [
                    {
                        "question": "Зачем декоратору принимать *args и **kwargs?",
                        "answer": "Чтобы прозрачно передавать аргументы функции.",
                        "explanation": None,
                        "code_example": "def wrapper(*args, **kwargs): ...",
                        "difficulty": "intermediate",
                    },
                    {
                        "question": "Что сохраняет functools.wraps?",
                        "answer": "Метаданные исходной функции.",
                        "explanation": "Например, __name__ и __doc__.",
                        "code_example": None,
                        "difficulty": "beginner",
                    },
                ]
            },
        }
        return StructuredResult(
            data=response_model.model_validate(outputs[request.scenario]),
            provider=self.provider_name,
            model=self.model,
            usage=ProviderUsage(100, 40, 1_000_000),
        )


def expect(response: httpx.Response, status_code: int) -> dict[str, Any]:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"expected {status_code}, got {response.status_code}: {response.text}"
        )
    return response.json() if response.content else {}


def create_test_app(manager: FakeAiManager) -> tuple[Database, object]:
    database = Database("sqlite+pysqlite:///:memory:")

    @event.listens_for(database.engine, "connect")
    def configure_sqlite(dbapi_connection: Any, _: Any) -> None:
        dbapi_connection.create_function("btrim", 1, str.strip)
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(database.engine)
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
        ai_enabled=manager.enabled,
    )
    return database, create_app(settings, database, manager)


async def check_disabled_mode() -> None:
    database, application = create_test_app(FakeAiManager(enabled=False))
    try:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            providers = expect(await client.get("/api/v1/ai/providers"), 200)
            ai_health = expect(await client.get("/api/v1/health/ai"), 200)
            core_health = expect(await client.get("/api/v1/health"), 200)
        assert providers["items"][0]["status"] == "disabled"
        assert ai_health["status"] == "disabled"
        assert core_health["status"] == "ok"
    finally:
        database.dispose()


async def check_ai_workflows() -> None:
    manager = FakeAiManager()
    database, application = create_test_app(manager)
    suffix = uuid4().hex[:8]
    try:
        transport = httpx.ASGITransport(app=application)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://test",
        ) as client:
            category = expect(
                await client.post(
                    "/api/v1/categories",
                    json={"name": f"AI smoke {suffix}"},
                ),
                201,
            )
            topic = expect(
                await client.post(
                    "/api/v1/topics",
                    json={
                        "category_id": category["id"],
                        "name": f"Decorators {suffix}",
                    },
                ),
                201,
            )
            card = expect(
                await client.post(
                    "/api/v1/cards",
                    json={
                        "topic_id": topic["id"],
                        "question": "Что делает functools.wraps?",
                        "answer": "Сохраняет метаданные исходной функции.",
                        "explanation": "Применяется к функции-обёртке.",
                        "difficulty": "beginner",
                    },
                ),
                201,
            )
            attempt = expect(
                await client.post(
                    f"/api/v1/reviews/{card['id']}/attempts",
                    json={"user_answer": "Сохраняет имя и документацию функции."},
                ),
                201,
            )

            evaluation_key = str(uuid4())
            evaluation = expect(
                await client.post(
                    "/api/v1/ai/evaluate-answer",
                    json={"attempt_id": attempt["id"]},
                    headers={"Idempotency-Key": evaluation_key},
                ),
                201,
            )
            replay_response = await client.post(
                "/api/v1/ai/evaluate-answer",
                json={"attempt_id": attempt["id"]},
                headers={"Idempotency-Key": evaluation_key},
            )
            replay = expect(replay_response, 200)
            assert replay_response.headers["Idempotency-Replayed"] == "true"
            assert replay == evaluation
            assert evaluation["score"] == 96

            before_analysis = expect(
                await client.get(f"/api/v1/cards/{card['id']}"),
                200,
            )
            analysis = expect(
                await client.post(
                    "/api/v1/ai/analyze-card",
                    json={"card_id": card["id"]},
                    headers={"Idempotency-Key": str(uuid4())},
                ),
                201,
            )
            after_analysis = expect(
                await client.get(f"/api/v1/cards/{card['id']}"),
                200,
            )
            assert analysis["quality"] == "good"
            assert before_analysis == after_analysis
            assert after_analysis["repetitions"] == 0
            assert after_analysis["last_reviewed_at"] is None

            cards_before_generation = expect(
                await client.get("/api/v1/cards", params={"topic_id": topic["id"]}),
                200,
            )
            batch = expect(
                await client.post(
                    "/api/v1/ai/generate-cards",
                    json={"topic_id": topic["id"], "count": 2},
                    headers={"Idempotency-Key": str(uuid4())},
                ),
                201,
            )
            cards_after_generation = expect(
                await client.get("/api/v1/cards", params={"topic_id": topic["id"]}),
                200,
            )
            assert cards_before_generation["pagination"]["total"] == 1
            assert cards_after_generation["pagination"]["total"] == 1
            assert len(batch["items"]) == 2

            accepted = expect(
                await client.post(
                    f"/api/v1/ai/card-suggestions/{batch['items'][0]['id']}/accept"
                ),
                200,
            )
            rejected = expect(
                await client.post(
                    f"/api/v1/ai/card-suggestions/{batch['items'][1]['id']}/reject"
                ),
                200,
            )
            assert accepted["accepted_card_id"] is not None
            assert accepted["status"] == "accepted"
            assert rejected["status"] == "rejected"

            cards_after_accept = expect(
                await client.get("/api/v1/cards", params={"topic_id": topic["id"]}),
                200,
            )
            assert cards_after_accept["pagination"]["total"] == 2

            usage = expect(await client.get("/api/v1/ai/usage"), 200)
            assert usage["request_count"] == 3
            assert usage["success_count"] == 3
            assert usage["error_count"] == 0
            assert usage["total_tokens"] == 420
            assert [request.scenario for request in manager.calls] == [
                "answer_evaluation",
                "card_analysis",
                "card_generation",
            ]
    finally:
        database.dispose()


async def async_main() -> None:
    await check_disabled_mode()
    await check_ai_workflows()
    print("AI fake-provider smoke check passed.")


if __name__ == "__main__":
    asyncio.run(async_main())
