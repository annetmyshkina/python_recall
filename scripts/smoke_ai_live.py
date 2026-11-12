"""Exercise Release 3 against a running Backend and a real Ollama model."""

import os
import re
from uuid import UUID, uuid4

import httpx
from sqlalchemy import delete, select

from backend.app.core.config import get_settings
from backend.app.core.database import Database
from backend.app.models import (
    AiRequest,
    AiUsageLog,
    AnswerAttempt,
    AnswerEvaluation,
    Card,
    CardAnalysis,
    CardSuggestion,
    CardTag,
    Category,
    ReviewLog,
    Topic,
)

BASE_URL = os.getenv("AI_SMOKE_API_BASE_URL", "http://localhost:8000/api/v1")
EXPECTED_MODEL = os.getenv("OLLAMA_MODEL", "qwen3:4b")
LIVE_GUARD = "RUN_LIVE_AI_SMOKE"
CYRILLIC = re.compile("[А-Яа-яЁё]")


def expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"expected {status_code}, got {response.status_code}: {response.text}"
        )
    return response.json() if response.content else {}


def cleanup(created: dict[str, UUID], request_keys: list[UUID]) -> None:
    """Remove only rows created by this smoke run, including immutable AI logs."""
    database = Database(get_settings().database_url)
    try:
        with database.session() as session:
            request_ids = set(
                session.scalars(
                    select(AiRequest.id).where(
                        AiRequest.idempotency_key.in_(request_keys)
                    )
                )
            )
            topic_id = created.get("topic")
            card_ids: set[UUID] = set()
            if topic_id is not None:
                card_ids.update(
                    session.scalars(select(Card.id).where(Card.topic_id == topic_id))
                )
                request_ids.update(
                    session.scalars(
                        select(CardSuggestion.request_id).where(
                            CardSuggestion.topic_id == topic_id
                        )
                    )
                )

            attempt_ids: set[UUID] = set()
            if card_ids:
                attempt_ids.update(
                    session.scalars(
                        select(AnswerAttempt.id).where(
                            AnswerAttempt.card_id.in_(card_ids)
                        )
                    )
                )
                request_ids.update(
                    session.scalars(
                        select(CardAnalysis.request_id).where(
                            CardAnalysis.card_id.in_(card_ids)
                        )
                    )
                )
            if attempt_ids:
                request_ids.update(
                    session.scalars(
                        select(AnswerEvaluation.request_id).where(
                            AnswerEvaluation.answer_attempt_id.in_(attempt_ids)
                        )
                    )
                )

            if topic_id is not None:
                session.execute(
                    delete(CardSuggestion).where(CardSuggestion.topic_id == topic_id)
                )
            if card_ids:
                session.execute(
                    delete(CardAnalysis).where(CardAnalysis.card_id.in_(card_ids))
                )
            if attempt_ids:
                session.execute(
                    delete(AnswerEvaluation).where(
                        AnswerEvaluation.answer_attempt_id.in_(attempt_ids)
                    )
                )
            if request_ids:
                session.execute(
                    delete(AiUsageLog).where(AiUsageLog.request_id.in_(request_ids))
                )
                session.execute(delete(AiRequest).where(AiRequest.id.in_(request_ids)))
            if card_ids:
                session.execute(
                    delete(ReviewLog).where(ReviewLog.card_id.in_(card_ids))
                )
                session.execute(
                    delete(AnswerAttempt).where(AnswerAttempt.card_id.in_(card_ids))
                )
                session.execute(delete(CardTag).where(CardTag.card_id.in_(card_ids)))
                session.execute(delete(Card).where(Card.id.in_(card_ids)))
            if topic_id is not None:
                session.execute(delete(Topic).where(Topic.id == topic_id))
            if category_id := created.get("category"):
                session.execute(delete(Category).where(Category.id == category_id))
            session.commit()
    finally:
        database.dispose()


def new_key(request_keys: list[UUID]) -> str:
    key = uuid4()
    request_keys.append(key)
    return str(key)


def assert_russian(value: object, field: str) -> None:
    if not isinstance(value, str) or CYRILLIC.search(value) is None:
        raise AssertionError(f"Ollama returned non-Russian {field}: {value!r}")


def main() -> None:
    if os.getenv(LIVE_GUARD) != "1":
        raise SystemExit(
            f"Live AI smoke is opt-in: run `{LIVE_GUARD}=1 make smoke-ai-live`."
        )

    created: dict[str, UUID] = {}
    request_keys: list[UUID] = []
    suffix = uuid4().hex[:8]
    try:
        with httpx.Client(base_url=BASE_URL, timeout=180) as client:
            providers = expect(client.get("/ai/providers"), 200)
            provider = providers["items"][0]  # type: ignore[index]
            assert provider["status"] == "ready"  # type: ignore[index]
            assert provider["model"] == EXPECTED_MODEL  # type: ignore[index]

            category = expect(
                client.post("/categories", json={"name": f"Live AI smoke {suffix}"}),
                201,
            )
            created["category"] = UUID(str(category["id"]))
            topic = expect(
                client.post(
                    "/topics",
                    json={
                        "category_id": str(created["category"]),
                        "name": f"Декораторы Python {suffix}",
                    },
                ),
                201,
            )
            created["topic"] = UUID(str(topic["id"]))
            card = expect(
                client.post(
                    "/cards",
                    json={
                        "topic_id": str(created["topic"]),
                        "question": "Для чего нужен functools.wraps?",
                        "answer": "Он сохраняет метаданные исходной функции.",
                        "explanation": "Имя, документацию и другие атрибуты.",
                        "difficulty": "beginner",
                    },
                ),
                201,
            )
            created["card"] = UUID(str(card["id"]))
            attempt = expect(
                client.post(
                    f"/reviews/{created['card']}/attempts",
                    json={"user_answer": "Сохраняет имя и документацию функции."},
                ),
                201,
            )

            evaluation_key = new_key(request_keys)
            evaluation = expect(
                client.post(
                    "/ai/evaluate-answer",
                    json={"attempt_id": attempt["id"]},
                    headers={"Idempotency-Key": evaluation_key},
                ),
                201,
            )
            assert_russian(evaluation["feedback"], "answer feedback")
            replay_response = client.post(
                "/ai/evaluate-answer",
                json={"attempt_id": attempt["id"]},
                headers={"Idempotency-Key": evaluation_key},
            )
            assert expect(replay_response, 200) == evaluation
            assert replay_response.headers["Idempotency-Replayed"] == "true"

            before = expect(client.get(f"/cards/{created['card']}"), 200)
            analysis = expect(
                client.post(
                    "/ai/analyze-card",
                    json={"card_id": str(created["card"])},
                    headers={"Idempotency-Key": new_key(request_keys)},
                ),
                201,
            )
            assert_russian(analysis["feedback"], "card feedback")
            after = expect(client.get(f"/cards/{created['card']}"), 200)
            assert after == before
            assert after["repetitions"] == 0
            assert after["last_reviewed_at"] is None

            cards_before = expect(
                client.get("/cards", params={"topic_id": str(created["topic"])}),
                200,
            )
            batch = expect(
                client.post(
                    "/ai/generate-cards",
                    json={
                        "topic_id": str(created["topic"]),
                        "source_text": (
                            "Декоратор оборачивает функцию. functools.wraps сохраняет "
                            "метаданные исходной функции."
                        ),
                        "count": 2,
                    },
                    headers={"Idempotency-Key": new_key(request_keys)},
                ),
                201,
            )
            assert len(batch["items"]) == 2  # type: ignore[arg-type]
            assert_russian(batch["items"][0]["question"], "generated question")  # type: ignore[index]
            cards_pending = expect(
                client.get("/cards", params={"topic_id": str(created["topic"])}),
                200,
            )
            assert cards_pending["pagination"] == cards_before["pagination"]

            first, second = batch["items"]  # type: ignore[misc]
            accepted = expect(
                client.post(f"/ai/card-suggestions/{first['id']}/accept"), 200
            )
            rejected = expect(
                client.post(f"/ai/card-suggestions/{second['id']}/reject"), 200
            )
            assert accepted["status"] == "accepted"
            assert rejected["status"] == "rejected"
            cards_after = expect(
                client.get("/cards", params={"topic_id": str(created["topic"])}),
                200,
            )
            assert cards_after["pagination"]["total"] == 2  # type: ignore[index]
            print("Live Ollama AI smoke check passed.")
    finally:
        cleanup(created, request_keys)


if __name__ == "__main__":
    main()
