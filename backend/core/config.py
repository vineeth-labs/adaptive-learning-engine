import os

class Settings:
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"
    )
    # If the DATABASE_URL doesn't start with postgresql+asyncpg://, adjust it for async execution
    if DATABASE_URL.startswith("postgresql://"):
        DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://", 1)

settings = Settings()
