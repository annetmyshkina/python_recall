from uuid import UUID, uuid4

import httpx
import pytest

from backend.app.core.database import Database
from backend.app.reviews.models import AnswerAttempt


async def create_category(
    client: httpx.AsyncClient, name: str = "Python"
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/categories",
        json={"name": name, "description": "Language"},
    )
    assert response.status_code == 201
    assert response.headers["location"].startswith("/api/v1/categories/")
    return response.json()


async def create_topic(
    client: httpx.AsyncClient, category_id: str, name: str = "Decorators"
) -> dict[str, object]:
    response = await client.post(
        "/api/v1/topics",
        json={"category_id": category_id, "name": name},
    )
    assert response.status_code == 201
    return response.json()


async def create_tag(
    client: httpx.AsyncClient, name: str = "important"
) -> dict[str, object]:
    response = await client.post("/api/v1/tags", json={"name": name})
    assert response.status_code == 201
    return response.json()


@pytest.mark.asyncio
async def test_category_crud_pagination_and_duplicate_error(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client, "  Python  ")
    assert category["name"] == "Python"

    duplicate = await api_client.post("/api/v1/categories", json={"name": "PYTHON"})
    assert duplicate.status_code == 409
    assert duplicate.headers["content-type"] == "application/problem+json"
    assert duplicate.json()["code"] == "duplicate_resource"

    updated = await api_client.patch(
        f"/api/v1/categories/{category['id']}",
        json={"description": None},
    )
    assert updated.status_code == 200
    assert updated.json()["description"] is None

    page = await api_client.get("/api/v1/categories?page=2&limit=1")
    assert page.status_code == 200
    assert page.json()["items"] == []
    assert page.json()["pagination"] == {
        "page": 2,
        "limit": 1,
        "total": 1,
        "pages": 1,
    }


@pytest.mark.asyncio
async def test_validation_errors_follow_problem_details_contract(
    api_client: httpx.AsyncClient,
) -> None:
    empty_patch = await api_client.patch(f"/api/v1/categories/{uuid4()}", json={})
    assert empty_patch.status_code == 422
    problem = empty_patch.json()
    assert problem["code"] == "validation_error"
    assert problem["errors"]

    malformed = await api_client.post(
        "/api/v1/categories",
        content="{",
        headers={"content-type": "application/json"},
    )
    assert malformed.status_code == 400
    assert malformed.json()["code"] == "malformed_request"


@pytest.mark.asyncio
async def test_topic_requires_parent_and_blocks_parent_deletion(
    api_client: httpx.AsyncClient,
) -> None:
    missing_parent = await api_client.post(
        "/api/v1/topics",
        json={"category_id": str(uuid4()), "name": "Missing"},
    )
    assert missing_parent.status_code == 404
    assert missing_parent.json()["code"] == "resource_not_found"

    category = await create_category(api_client)
    topic = await create_topic(api_client, str(category["id"]))

    blocked = await api_client.delete(f"/api/v1/categories/{category['id']}")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "deletion_restricted"

    moved_category = await create_category(api_client, "Databases")
    moved = await api_client.patch(
        f"/api/v1/topics/{topic['id']}",
        json={"category_id": moved_category["id"], "name": "SQL"},
    )
    assert moved.status_code == 200
    assert moved.json()["category_id"] == moved_category["id"]

    deleted = await api_client.delete(f"/api/v1/categories/{category['id']}")
    assert deleted.status_code == 204


@pytest.mark.asyncio
async def test_tag_crud_is_case_insensitively_unique(
    api_client: httpx.AsyncClient,
) -> None:
    tag = await create_tag(api_client, "  Important ")
    assert tag["name"] == "Important"

    duplicate = await api_client.post("/api/v1/tags", json={"name": "important"})
    assert duplicate.status_code == 409

    renamed = await api_client.patch(f"/api/v1/tags/{tag['id']}", json={"name": "core"})
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "core"


@pytest.mark.asyncio
async def test_card_crud_filters_tags_and_archiving(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client)
    topic = await create_topic(api_client, str(category["id"]))
    tag = await create_tag(api_client)

    created = await api_client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic["id"],
            "question": "  What does functools.wraps do?  ",
            "answer": "Copies function metadata.",
            "difficulty": "intermediate",
            "tag_ids": [tag["id"]],
        },
    )
    assert created.status_code == 201
    card = created.json()
    assert card["question"] == "What does functools.wraps do?"
    assert card["ease_factor"] == "2.50"
    assert [item["id"] for item in card["tags"]] == [tag["id"]]

    filtered = await api_client.get(
        "/api/v1/cards",
        params={
            "category_id": category["id"],
            "tag": "IMPORTANT",
            "difficulty": "intermediate",
            "search": "WRAPS",
        },
    )
    assert filtered.status_code == 200
    assert [item["id"] for item in filtered.json()["items"]] == [card["id"]]

    archived = await api_client.patch(
        f"/api/v1/cards/{card['id']}",
        json={"is_archived": True, "tag_ids": []},
    )
    assert archived.status_code == 200
    assert archived.json()["is_archived"] is True
    assert archived.json()["tags"] == []
    assert archived.json()["repetitions"] == 0

    active_page = await api_client.get("/api/v1/cards")
    archived_page = await api_client.get("/api/v1/cards?is_archived=true")
    assert active_page.json()["items"] == []
    assert [item["id"] for item in archived_page.json()["items"]] == [card["id"]]

    assert (await api_client.delete(f"/api/v1/cards/{card['id']}")).status_code == 204
    assert (await api_client.delete(f"/api/v1/topics/{topic['id']}")).status_code == 204


@pytest.mark.asyncio
async def test_card_rejects_missing_or_duplicate_tags(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client)
    topic = await create_topic(api_client, str(category["id"]))
    tag_id = str(uuid4())
    payload = {
        "topic_id": topic["id"],
        "question": "Question",
        "answer": "Answer",
        "difficulty": "beginner",
        "tag_ids": [tag_id],
    }

    missing = await api_client.post("/api/v1/cards", json=payload)
    assert missing.status_code == 404

    payload["tag_ids"] = [tag_id, tag_id]
    duplicate = await api_client.post("/api/v1/cards", json=payload)
    assert duplicate.status_code == 422
    assert duplicate.json()["code"] == "validation_error"


@pytest.mark.asyncio
async def test_card_with_learning_history_cannot_be_deleted(
    api_client: httpx.AsyncClient,
    test_database: Database,
) -> None:
    category = await create_category(api_client)
    topic = await create_topic(api_client, str(category["id"]))
    created = await api_client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic["id"],
            "question": "Question",
            "answer": "Answer",
            "difficulty": "beginner",
        },
    )
    card_id = created.json()["id"]

    with test_database.session() as session:
        session.add(AnswerAttempt(card_id=UUID(card_id), user_answer="My answer"))
        session.commit()

    blocked = await api_client.delete(f"/api/v1/cards/{card_id}")
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "deletion_restricted"


@pytest.mark.asyncio
async def test_deleting_tag_keeps_card_and_removes_only_link(
    api_client: httpx.AsyncClient,
) -> None:
    category = await create_category(api_client)
    topic = await create_topic(api_client, str(category["id"]))
    tag = await create_tag(api_client)
    created = await api_client.post(
        "/api/v1/cards",
        json={
            "topic_id": topic["id"],
            "question": "Question",
            "answer": "Answer",
            "difficulty": "beginner",
            "tag_ids": [tag["id"]],
        },
    )
    card_id = created.json()["id"]

    assert (await api_client.delete(f"/api/v1/tags/{tag['id']}")).status_code == 204
    card = await api_client.get(f"/api/v1/cards/{card_id}")
    assert card.status_code == 200
    assert card.json()["tags"] == []


@pytest.mark.asyncio
async def test_generated_openapi_contains_all_knowledge_crud_operations(
    api_client: httpx.AsyncClient,
) -> None:
    document = (await api_client.get("/api/v1/openapi.json")).json()
    operation_ids = {
        operation["operationId"]
        for path in document["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert {
        "list_categories",
        "create_category",
        "get_category",
        "update_category",
        "delete_category",
        "list_topics",
        "create_topic",
        "get_topic",
        "update_topic",
        "delete_topic",
        "list_tags",
        "create_tag",
        "get_tag",
        "update_tag",
        "delete_tag",
        "list_cards",
        "create_card",
        "get_card",
        "update_card",
        "delete_card",
    }.issubset(operation_ids)
