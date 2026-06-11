from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from backend.core.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=False)
async_session_maker = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)
