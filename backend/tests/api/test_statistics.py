from datetime import UTC, date, datetime, timedelta
from uuid import UUID, uuid4

import httpx
import pytest
from sqlalchemy import select

from backend.app.cards.models import Card
from backend.app.core.database import Database
from backend.app.reviews.models import ReviewLog


async def create_category(client: httpx.AsyncClient, name: str) -> dict[str, object]:
    response = await client.post(
        "/api/v1/categories", json={"name": f"{name}-{uuid4()}"}
    )
    assert response.status_code == 201
    return response.json()


async def create_topic(
    client: httpx.AsyncClient,
    category_id: str,
    name: str,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/topics",
        json={"category_id": category_id, "name": name},
    )
    assert response.status_code == 201
    return response.json()


async def create_card(
    client: httpx.AsyncClient,
    topic_id: str,
    question: str,
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic_id,
            "question": question,
            "answer": f"Answer to {question}",
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 201
    return response.json()


async def complete_review(
    client: httpx.AsyncClient,
    card_id: str,
    rating: str,
) -> dict[str, object]:
    response = await client.post(
        f"/api/v1/reviews/{card_id}/complete",
        json={"rating": rating},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert response.status_code == 201
    return response.json()


def make_due(database: Database, card_id: str) -> None:
    with database.session() as session:
        card = session.get(Card, UUID(card_id))
        assert card is not None
        card.next_review_at = datetime.now(UTC) - timedelta(minutes=1)
        session.commit()


def move_review_outside_thirty_days(database: Database, card_id: str) -> None:
    with database.session() as session:
        review = session.scalar(
            select(ReviewLog).where(ReviewLog.card_id == UUID(card_id))
        )
        assert review is not None
        review.reviewed_at = datetime.now(UTC) - timedelta(days=31)
        session.commit()


@pytest.mark.asyncio
async def test_overview_counts_cards_due_reviews_and_success(
    api_client: httpx.AsyncClient,
    test_database: Database,
) -> None:
    category = await create_category(api_client, "Overview")
    topic = await create_topic(api_client, str(category["id"]), "Overview topic")
    new_card = await create_card(api_client, str(topic["id"]), "New")
    reviewed_card = await create_card(api_client, str(topic["id"]), "Reviewed")
    archived_card = await create_card(api_client, str(topic["id"]), "Archived")

    await complete_review(api_client, str(reviewed_card["id"]), "good")
    make_due(test_database, str(reviewed_card["id"]))
    archived = await api_client.patch(
        f"/api/v1/cards/{archived_card['id']}", json={"is_archived": True}
    )
    assert archived.status_code == 200

    response = await api_client.get("/api/v1/statistics/overview")

    assert response.status_code == 200
    assert response.json() == {
        "total_cards": 3,
        "active_cards": 2,
        "archived_cards": 1,
        "due_cards": 1,
        "new_cards": 1,
        "reviews_today": 1,
        "success_rate_30d": 1.0,
        "timezone": "UTC",
        "generated_at": response.json()["generated_at"],
    }
    assert response.json()["new_cards"] == int(new_card["last_reviewed_at"] is None)


@pytest.mark.asyncio
async def test_topic_statistics_include_empty_topics_and_historical_reviews(
    api_client: httpx.AsyncClient,
    test_database: Database,
) -> None:
    category = await create_category(api_client, "Topics")
    other_category = await create_category(api_client, "Other")
    alpha = await create_topic(api_client, str(category["id"]), "Alpha")
    await create_topic(api_client, str(category["id"]), "Beta")
    await create_topic(api_client, str(other_category["id"]), "Gamma")
    hard_card = await create_card(api_client, str(alpha["id"]), "Hard card")
    again_card = await create_card(api_client, str(alpha["id"]), "Again card")
    old_card = await create_card(api_client, str(alpha["id"]), "Old card")

    await complete_review(api_client, str(hard_card["id"]), "hard")
    await complete_review(api_client, str(again_card["id"]), "again")
    await complete_review(api_client, str(old_card["id"]), "again")
    move_review_outside_thirty_days(test_database, str(old_card["id"]))
    make_due(test_database, str(hard_card["id"]))
    await api_client.patch(
        f"/api/v1/cards/{again_card['id']}", json={"is_archived": True}
    )

    response = await api_client.get(
        "/api/v1/statistics/topics",
        params={"category_id": category["id"], "page": 1, "limit": 20},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["pagination"] == {"page": 1, "limit": 20, "total": 2, "pages": 1}
    assert [item["topic"]["name"] for item in body["items"]] == ["Alpha", "Beta"]
    assert body["items"][0] | {"topic": None} == {
        "topic": None,
        "total_cards": 3,
        "active_cards": 2,
        "due_cards": 1,
        "new_cards": 0,
        "reviews_30d": 2,
        "success_rate_30d": 0.5,
    }
    assert body["items"][1] | {"topic": None} == {
        "topic": None,
        "total_cards": 0,
        "active_cards": 0,
        "due_cards": 0,
        "new_cards": 0,
        "reviews_30d": 0,
        "success_rate_30d": None,
    }

    empty_page = await api_client.get(
        "/api/v1/statistics/topics",
        params={"category_id": category["id"], "page": 2, "limit": 20},
    )
    assert empty_page.status_code == 200
    assert empty_page.json()["items"] == []
    assert empty_page.json()["pagination"]["total"] == 2


@pytest.mark.asyncio
async def test_activity_fills_empty_days_and_validates_range(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client, "Activity")
    topic = await create_topic(api_client, str(category["id"]), "Activity topic")
    card = await create_card(api_client, str(topic["id"]), "Activity card")
    await complete_review(api_client, str(card["id"]), "hard")
    await complete_review(api_client, str(card["id"]), "again")

    today = datetime.now(UTC).date()
    yesterday = today - timedelta(days=1)
    response = await api_client.get(
        "/api/v1/statistics/activity",
        params={"date_from": yesterday.isoformat(), "date_to": today.isoformat()},
    )

    assert response.status_code == 200
    assert response.json() == {
        "timezone": "UTC",
        "items": [
            {
                "date": yesterday.isoformat(),
                "reviews": 0,
                "successful_reviews": 0,
                "success_rate": None,
            },
            {
                "date": today.isoformat(),
                "reviews": 2,
                "successful_reviews": 1,
                "success_rate": 0.5,
            },
        ],
    }

    reversed_range = await api_client.get(
        "/api/v1/statistics/activity",
        params={"date_from": today.isoformat(), "date_to": yesterday.isoformat()},
    )
    too_long = await api_client.get(
        "/api/v1/statistics/activity",
        params={
            "date_from": date(2025, 1, 1).isoformat(),
            "date_to": date(2026, 1, 2).isoformat(),
        },
    )
    assert reversed_range.status_code == 422
    assert reversed_range.json()["code"] == "validation_error"
    assert too_long.status_code == 422
    assert too_long.json()["code"] == "validation_error"
