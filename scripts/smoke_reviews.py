"""Exercise the Review API against a running Backend and PostgreSQL."""

import os
from uuid import UUID, uuid4

import httpx
from sqlalchemy import delete, select

from backend.app.core.config import get_settings
from backend.app.core.database import Database
from backend.app.models import AnswerAttempt, Card, Category, ReviewLog, Topic

BASE_URL = os.getenv("SMOKE_API_BASE_URL", "http://localhost:8000/api/v1")
SMOKE_CATEGORY_PREFIX = "Review smoke "


def expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"expected {status_code}, got {response.status_code}: {response.text}"
        )
    return response.json() if response.content else {}


def cleanup(created: dict[str, UUID]) -> None:
    """Remove only this smoke run's rows; review history has no public delete API."""
    if not created:
        return
    database = Database(get_settings().database_url)
    try:
        with database.session() as session:
            card_id = created.get("card")
            if card_id is not None:
                session.execute(delete(ReviewLog).where(ReviewLog.card_id == card_id))
                session.execute(
                    delete(AnswerAttempt).where(AnswerAttempt.card_id == card_id)
                )
                session.execute(delete(Card).where(Card.id == card_id))
            if topic_id := created.get("topic"):
                session.execute(delete(Topic).where(Topic.id == topic_id))
            if category_id := created.get("category"):
                session.execute(delete(Category).where(Category.id == category_id))
            session.commit()
    finally:
        database.dispose()


def cleanup_stale_runs() -> None:
    """Remove rows left by an interrupted earlier smoke run."""
    database = Database(get_settings().database_url)
    try:
        with database.session() as session:
            category_ids = select(Category.id).where(
                Category.name.like(f"{SMOKE_CATEGORY_PREFIX}%")
            )
            topic_ids = select(Topic.id).where(Topic.category_id.in_(category_ids))
            card_ids = select(Card.id).where(Card.topic_id.in_(topic_ids))
            session.execute(delete(ReviewLog).where(ReviewLog.card_id.in_(card_ids)))
            session.execute(
                delete(AnswerAttempt).where(AnswerAttempt.card_id.in_(card_ids))
            )
            session.execute(delete(Card).where(Card.id.in_(card_ids)))
            session.execute(delete(Topic).where(Topic.id.in_(topic_ids)))
            session.execute(delete(Category).where(Category.id.in_(category_ids)))
            session.commit()
    finally:
        database.dispose()


def main() -> None:
    suffix = uuid4().hex[:8]
    created: dict[str, UUID] = {}

    cleanup_stale_runs()
    try:
        with httpx.Client(base_url=BASE_URL, timeout=10) as client:
            category = expect(
                client.post(
                    "/categories",
                    json={"name": f"{SMOKE_CATEGORY_PREFIX}{suffix}"},
                ),
                201,
            )
            created["category"] = UUID(str(category["id"]))

            topic = expect(
                client.post(
                    "/topics",
                    json={
                        "category_id": str(created["category"]),
                        "name": f"Review smoke topic {suffix}",
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
                        "question": "What does a Python decorator do?",
                        "answer": "It wraps or transforms another callable.",
                        "difficulty": "beginner",
                    },
                ),
                201,
            )
            created["card"] = UUID(str(card["id"]))

            due = expect(
                client.get("/reviews/due", params={"topic_id": str(created["topic"])}),
                200,
            )
            assert [item["id"] for item in due["items"]] == [str(created["card"])]
            assert "answer" not in due["items"][0]

            reference = expect(
                client.get(f"/reviews/{created['card']}/reference"),
                200,
            )
            assert reference["answer"] == card["answer"]

            attempt = expect(
                client.post(
                    f"/reviews/{created['card']}/attempts",
                    json={"user_answer": "It wraps another callable."},
                ),
                201,
            )
            created["attempt"] = UUID(str(attempt["id"]))

            key = str(uuid4())
            body = {"rating": "good", "attempt_id": str(created["attempt"])}
            completed = expect(
                client.post(
                    f"/reviews/{created['card']}/complete",
                    json=body,
                    headers={"Idempotency-Key": key},
                ),
                201,
            )
            assert completed["quality"] == 4
            assert completed["new_state"]["repetitions"] == 1

            replay_response = client.post(
                f"/reviews/{created['card']}/complete",
                json=body,
                headers={"Idempotency-Key": key},
            )
            replay = expect(replay_response, 200)
            assert replay_response.headers["Idempotency-Replayed"] == "true"
            assert replay == completed

            history = expect(
                client.get(
                    "/reviews/history", params={"card_id": str(created["card"])}
                ),
                200,
            )
            assert history["pagination"]["total"] == 1
            assert history["items"][0]["id"] == completed["id"]
            print("Review smoke check passed.")
    finally:
        cleanup(created)


if __name__ == "__main__":
    main()
