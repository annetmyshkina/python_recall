from collections.abc import AsyncIterator, Iterator

import httpx
import pytest
import pytest_asyncio
from sqlalchemy import event

from backend.app.core.config import Settings
from backend.app.core.database import Base, Database
from backend.app.main import create_app


@pytest.fixture
def test_database() -> Iterator[Database]:
    database = Database("sqlite+pysqlite:///:memory:")

    @event.listens_for(database.engine, "connect")
    def configure_sqlite(dbapi_connection: object, _: object) -> None:
        dbapi_connection.create_function("btrim", 1, str.strip)  # type: ignore[attr-defined]
        cursor = dbapi_connection.cursor()  # type: ignore[attr-defined]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    Base.metadata.create_all(database.engine)
    yield database
    Base.metadata.drop_all(database.engine)
    database.dispose()


@pytest_asyncio.fixture
async def api_client(test_database: Database) -> AsyncIterator[httpx.AsyncClient]:
    settings = Settings(
        _env_file=None,
        app_env="test",
        database_url="sqlite+pysqlite:///:memory:",
    )
    application = create_app(settings, test_database)
    transport = httpx.ASGITransport(app=application)
    async with httpx.AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        yield client
