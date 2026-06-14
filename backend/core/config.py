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

    # Bayesian Knowledge Tracing parameters (global constants for the MVP).
    # p_slip + p_guess must be < 1 for the model to be identifiable.
    BKT_P_TRANSIT: float = 0.10   # P(T): chance an unknown skill becomes known between opportunities
    BKT_P_SLIP: float = 0.10      # P(S): chance of answering wrong despite knowing it
    BKT_P_GUESS: float = 0.20     # P(G): chance of answering right despite not knowing it
    BKT_BASE_PRIOR: float = 0.30  # P(L0): prior mastery for a root concept before any evidence

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_async_driver(cls, v: str) -> str:
        # Ensure the URL uses the asyncpg driver required by the async engine.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v


settings = Settings()
