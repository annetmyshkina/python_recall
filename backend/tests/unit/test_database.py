from sqlalchemy import text

from backend.app.core.database import Database


def test_database_creates_usable_short_lived_sessions() -> None:
    database = Database("sqlite+pysqlite:///:memory:")

    with database.session() as session:
        assert session.scalar(text("SELECT 1")) == 1

    database.dispose()


def test_database_connection_check_executes_select_one() -> None:
    database = Database("sqlite+pysqlite:///:memory:")

    database.check_connection()

    database.dispose()
