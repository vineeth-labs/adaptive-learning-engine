from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import async_session_maker

async def get_db():
    """
    Dependency to provide an async database session for request lifecycles.
    """
    try:
        async with async_session_maker() as session:
            yield session
    except OSError as exc:
        raise HTTPException(
            status_code=503,
            detail="Database unavailable — check that PostgreSQL is running.",
        ) from exc
