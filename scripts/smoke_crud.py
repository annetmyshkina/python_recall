import os
from uuid import uuid4

import httpx

BASE_URL = os.getenv("SMOKE_API_BASE_URL", "http://localhost:8000/api/v1")


def expect(response: httpx.Response, status_code: int) -> dict[str, object]:
    if response.status_code != status_code:
        raise RuntimeError(
            f"{response.request.method} {response.request.url}: "
            f"expected {status_code}, got {response.status_code}: {response.text}"
        )
    return response.json() if response.content else {}


def main() -> None:
    suffix = uuid4().hex[:8]
    created: dict[str, str] = {}

    with httpx.Client(base_url=BASE_URL, timeout=10) as client:
        try:
            missing = client.get("/not-an-endpoint")
            assert missing.status_code == 404
            assert missing.headers["content-type"] == "application/problem+json"
            assert missing.json()["code"] == "resource_not_found"

            oversized = client.post(
                "/categories",
                content=b'{"name":"' + b"x" * (1024 * 1024) + b'"}',
                headers={"content-type": "application/json"},
            )
            assert oversized.status_code == 413
            assert oversized.json()["code"] == "request_too_large"

            category = expect(
                client.post("/categories", json={"name": f"Smoke {suffix}"}),
                201,
            )
            created["category"] = str(category["id"])

            topic = expect(
                client.post(
                    "/topics",
                    json={
                        "category_id": created["category"],
                        "name": f"Smoke topic {suffix}",
                    },
                ),
                201,
            )
            created["topic"] = str(topic["id"])

            tag = expect(
                client.post("/tags", json={"name": f"smoke-{suffix}"}),
                201,
            )
            created["tag"] = str(tag["id"])

            card = expect(
                client.post(
                    "/cards",
                    json={
                        "topic_id": created["topic"],
                        "question": "Smoke question",
                        "answer": "Smoke answer",
                        "difficulty": "beginner",
                        "tag_ids": [created["tag"]],
                    },
                ),
                201,
            )
            created["card"] = str(card["id"])

            page = expect(
                client.get("/cards", params={"tag": f"SMOKE-{suffix}"}),
                200,
            )
            assert [item["id"] for item in page["items"]] == [created["card"]]

            archived = expect(
                client.patch(f"/cards/{created['card']}", json={"is_archived": True}),
                200,
            )
            assert archived["is_archived"] is True
            print("CRUD smoke check passed.")
        finally:
            resources = (
                ("card", "cards"),
                ("tag", "tags"),
                ("topic", "topics"),
                ("category", "categories"),
            )
            for resource, endpoint in resources:
                resource_id = created.get(resource)
                if resource_id is not None:
                    client.delete(f"/{endpoint}/{resource_id}")


if __name__ == "__main__":
    main()
