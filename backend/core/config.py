from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load variables from a local .env file (if present); ignore unrelated env vars.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # LLM / OpenAI configuration
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"

    # Number of free-text questions generated per assessment (default 1 for MVP)
    NUM_QUESTIONS: int = 1

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_async_driver(cls, v: str) -> str:
        # Ensure the URL uses the asyncpg driver required by the async engine.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
