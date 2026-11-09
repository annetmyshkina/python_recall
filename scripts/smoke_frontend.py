"""Check the production Frontend, SPA fallback, assets, and API proxy."""

import os
import re

import httpx

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:8080")
ASSET_PATTERN = re.compile(r'(?:src|href)="(/assets/[^"]+)"')


def require_ok(response: httpx.Response, description: str) -> None:
    if response.status_code != 200:
        raise RuntimeError(
            f"{description}: expected 200, got {response.status_code}: "
            f"{response.text[:300]}"
        )


def main() -> None:
    with httpx.Client(
        base_url=FRONTEND_URL,
        timeout=10,
        follow_redirects=True,
    ) as client:
        index = client.get("/")
        require_ok(index, "Frontend index")
        assert '<div id="root"></div>' in index.text
        assert "Python Recall" in index.text

        spa_route = client.get("/statistics")
        require_ok(spa_route, "SPA fallback")
        assert '<div id="root"></div>' in spa_route.text

        assets = ASSET_PATTERN.findall(index.text)
        if not assets:
            raise RuntimeError("Frontend index does not reference production assets.")
        for asset_path in assets:
            require_ok(client.get(asset_path), f"Frontend asset {asset_path}")

        health = client.get("/api/v1/health/database")
        require_ok(health, "Frontend API proxy")
        assert health.json() == {"status": "ok"}

    print("Frontend production smoke check passed.")


if __name__ == "__main__":
    main()
