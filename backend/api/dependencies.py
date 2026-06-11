from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.session import async_session_maker

async def get_db():
    """
    Dependency to provide an async database session for request lifecycles.
    """
    async with async_session_maker() as session:
        yield session
