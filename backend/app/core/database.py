from collections.abc import Iterator

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for all Release 1 ORM models."""


class Database:
    """Own the SQLAlchemy engine and short-lived database sessions."""

    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        self.session_factory = sessionmaker(
            bind=self.engine,
            class_=Session,
            expire_on_commit=False,
        )

    def session(self) -> Session:
        """Create a session; callers control its transaction and lifetime."""
        return self.session_factory()

    def iter_session(self) -> Iterator[Session]:
        """Yield a request-scoped session for future FastAPI dependencies."""
        with self.session() as session:
            yield session

    def check_connection(self) -> None:
        """Execute the smallest useful PostgreSQL availability query."""
        with self.session() as session:
            session.execute(text("SELECT 1"))

    def dispose(self) -> None:
        """Release pooled connections during application shutdown."""
        self.engine.dispose()
