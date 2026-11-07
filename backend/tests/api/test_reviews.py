from uuid import uuid4

import httpx
import pytest


async def create_card(client: httpx.AsyncClient) -> dict[str, object]:
    category = (
        await client.post("/api/v1/categories", json={"name": f"C-{uuid4()}"})
    ).json()
    topic = (
        await client.post(
            "/api/v1/topics",
            json={"category_id": category["id"], "name": f"T-{uuid4()}"},
        )
    ).json()
    response = await client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic["id"],
            "question": "What is a decorator?",
            "answer": "A callable that wraps another callable.",
            "explanation": "Decorators use the @ syntax.",
            "difficulty": "beginner",
        },
    )
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_due_queue_hides_answer_and_reference_reveals_it(
    api_client: httpx.AsyncClient,
) -> None:
    card = await create_card(api_client)

    due = await api_client.get("/api/v1/reviews/due")
    assert due.status_code == 200
    item = due.json()["items"][0]
    assert item["id"] == card["id"]
    assert "answer" not in item
    assert item["is_new"] is True

    reference = await api_client.get(f"/api/v1/reviews/{card['id']}/reference")
    assert reference.status_code == 200
    assert reference.json()["answer"] == card["answer"]


@pytest.mark.asyncio
async def test_attempt_does_not_change_sm2_and_complete_is_idempotent(
    api_client: httpx.AsyncClient,
) -> None:
    card = await create_card(api_client)
    attempt = await api_client.post(
        f"/api/v1/reviews/{card['id']}/attempts",
        json={"user_answer": "  It wraps a function.  "},
    )
    assert attempt.status_code == 201
    assert attempt.json()["user_answer"] == "It wraps a function."

    unchanged = await api_client.get(f"/api/v1/cards/{card['id']}")
    assert unchanged.json()["repetitions"] == 0
    assert unchanged.json()["last_reviewed_at"] is None

    key = str(uuid4())
    body = {"rating": "good", "attempt_id": attempt.json()["id"]}
    completed = await api_client.post(
        f"/api/v1/reviews/{card['id']}/complete",
        json=body,
        headers={"Idempotency-Key": key},
    )
    assert completed.status_code == 201
    result = completed.json()
    assert result["quality"] == 4
    assert result["previous_state"]["repetitions"] == 0
    assert result["new_state"]["repetitions"] == 1
    assert result["new_state"]["interval_days"] == 1

    replay = await api_client.post(
        f"/api/v1/reviews/{card['id']}/complete",
        json=body,
        headers={"Idempotency-Key": key},
    )
    assert replay.status_code == 200
    assert replay.headers["idempotency-replayed"] == "true"
    assert replay.json() == result

    updated = await api_client.get(f"/api/v1/cards/{card['id']}")
    assert updated.json()["repetitions"] == 1
    history = await api_client.get("/api/v1/reviews/history")
    assert history.json()["pagination"]["total"] == 1
    assert history.json()["items"][0]["id"] == result["id"]


@pytest.mark.asyncio
async def test_reusing_key_for_different_result_is_conflict(
    api_client: httpx.AsyncClient,
) -> None:
    card = await create_card(api_client)
    key = str(uuid4())
    url = f"/api/v1/reviews/{card['id']}/complete"
    assert (
        await api_client.post(
            url,
            json={"rating": "good"},
            headers={"Idempotency-Key": key},
        )
    ).status_code == 201

    conflict = await api_client.post(
        url,
        json={"rating": "easy"},
        headers={"Idempotency-Key": key},
    )
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


@pytest.mark.asyncio
async def test_archived_card_rejects_learning_operations(
    api_client: httpx.AsyncClient,
) -> None:
    card = await create_card(api_client)
    await api_client.patch(f"/api/v1/cards/{card['id']}", json={"is_archived": True})

    reference = await api_client.get(f"/api/v1/reviews/{card['id']}/reference")
    attempt = await api_client.post(
        f"/api/v1/reviews/{card['id']}/attempts", json={"user_answer": "Answer"}
    )
    complete = await api_client.post(
        f"/api/v1/reviews/{card['id']}/complete",
        json={"rating": "good"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert {reference.status_code, attempt.status_code, complete.status_code} == {409}
    assert reference.json()["code"] == "card_archived"


@pytest.mark.asyncio
async def test_manual_and_difficult_sessions_preserve_rules(
    api_client: httpx.AsyncClient,
) -> None:
    first = await create_card(api_client)
    second = await create_card(api_client)
    manual = await api_client.post(
        "/api/v1/reviews/session",
        json={"mode": "manual", "card_ids": [second["id"], first["id"]]},
    )
    assert manual.status_code == 200
    assert [item["id"] for item in manual.json()["items"]] == [
        second["id"],
        first["id"],
    ]

    await api_client.post(
        f"/api/v1/reviews/{first['id']}/complete",
        json={"rating": "hard"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    difficult = await api_client.post(
        "/api/v1/reviews/session", json={"mode": "difficult", "limit": 20}
    )
    assert difficult.status_code == 200
    assert [item["id"] for item in difficult.json()["items"]] == [first["id"]]

    await api_client.post(
        f"/api/v1/reviews/{first['id']}/complete",
        json={"rating": "good"},
        headers={"Idempotency-Key": str(uuid4())},
    )
    no_longer_difficult = await api_client.post(
        "/api/v1/reviews/session", json={"mode": "difficult", "limit": 20}
    )
    assert no_longer_difficult.status_code == 200
    assert no_longer_difficult.json()["items"] == []


@pytest.mark.asyncio
async def test_attempt_cannot_be_used_for_another_or_second_review(
    api_client: httpx.AsyncClient,
) -> None:
    first = await create_card(api_client)
    second = await create_card(api_client)
    attempt = await api_client.post(
        f"/api/v1/reviews/{first['id']}/attempts",
        json={"user_answer": "Answer"},
    )
    body = {"rating": "good", "attempt_id": attempt.json()["id"]}

    wrong_card = await api_client.post(
        f"/api/v1/reviews/{second['id']}/complete",
        json=body,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert wrong_card.status_code == 404
    assert (await api_client.get(f"/api/v1/cards/{second['id']}")).json()[
        "repetitions"
    ] == 0

    first_result = await api_client.post(
        f"/api/v1/reviews/{first['id']}/complete",
        json=body,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert first_result.status_code == 201
    reused = await api_client.post(
        f"/api/v1/reviews/{first['id']}/complete",
        json=body,
        headers={"Idempotency-Key": str(uuid4())},
    )
    assert reused.status_code == 409
    assert reused.json()["code"] == "review_conflict"


@pytest.mark.asyncio
async def test_history_requires_timestamp_with_offset(
    api_client: httpx.AsyncClient,
) -> None:
    response = await api_client.get(
        "/api/v1/reviews/history", params={"reviewed_from": "2026-11-07T12:00:00"}
    )

    assert response.status_code == 422
    assert response.json()["code"] == "validation_error"
