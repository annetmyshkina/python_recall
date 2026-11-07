from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session


async def get_session(request: Request) -> AsyncIterator[Session]:
    """Yield one SQLAlchemy session per request without implicit commit."""
    with request.app.state.database.session() as session:
        yield session


SessionDependency = Annotated[Session, Depends(get_session)]
