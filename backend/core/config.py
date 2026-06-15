from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Load variables from a local .env file (if present); ignore unrelated env vars.
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/postgres"

    # Global LLM fallbacks (kept for backward compat — per-service fields below
    # inherit these when left blank).
    OPENAI_API_KEY: str = ""
    OPENAI_MODEL: str = "gpt-4o-mini"
    DEEPSEEK_API_KEY: str = ""   # loaded from .env; used as the deepseek-provider default

    # --- Scenario Generator (Agent 1) ---
    # Provider: openai | deepseek | gemini
    SCENARIO_LLM_PROVIDER: str = "deepseek"
    SCENARIO_LLM_API_KEY: str = ""   # falls back to the provider's key if blank
    SCENARIO_LLM_MODEL: str = "deepseek-chat"     # falls back to OPENAI_MODEL if blank

    # --- Diagnostic Evaluator (Agent 2) ---
    EVALUATOR_LLM_PROVIDER: str = "deepseek"
    EVALUATOR_LLM_API_KEY: str = ""  # falls back to the provider's key if blank
    EVALUATOR_LLM_MODEL: str = "deepseek-chat"    # falls back to OPENAI_MODEL if blank

    # Number of free-text questions generated per assessment (default 1 for MVP)
    NUM_QUESTIONS: int = 1

    # Bayesian Knowledge Tracing parameters (global constants for the MVP).
    # p_slip + p_guess must be < 1 for the model to be identifiable.
    BKT_P_TRANSIT: float = 0.10   # P(T): chance an unknown skill becomes known between opportunities
    BKT_P_SLIP: float = 0.10      # P(S): chance of answering wrong despite knowing it
    BKT_P_GUESS: float = 0.20     # P(G): chance of answering right despite not knowing it
    BKT_BASE_PRIOR: float = 0.30  # P(L0): prior mastery for a root concept before any evidence

    # Beta-Bernoulli mastery model (per-concept Beta(alpha, beta) posterior; see
    # services/learner/beta_mastery.py and docs/mastery-update.md). All hand-set;
    # any could later be fit from interaction logs without touching the update math.
    BETA_PRIOR_ALPHA: float = 2.0       # pseudo-evidence "for" mastery before any answer (prior mean 0.5)
    BETA_PRIOR_BETA: float = 2.0        # pseudo-evidence "against" mastery before any answer
    BETA_BASE_WEIGHT: float = 1.0       # evidence mass contributed by one answer
    BETA_HALF_LIFE_DAYS: float = 30.0   # forgetting: accumulated evidence halves every this many days
    BETA_MIN_EVIDENCE_MASS: float = 3.0 # gate: effective observations needed before trusting mastery
    BETA_MASTERY_THRESHOLD: float = 0.7 # gate: posterior mean at/above this counts as mastered
    BETA_CONFIDENCE_Z: float = 1.2816   # z-score for the one-sided credible lower bound (~90%)

    # Recommendation engine
    RECOMMEND_MASTERY_THRESHOLD: float = 0.7  # mastery at/above which a concept counts as "mastered"
    ROADMAP_MAX_STEPS: int = 10               # max concepts in the previewed learning roadmap

    @field_validator("DATABASE_URL")
    @classmethod
    def _force_async_driver(cls, v: str) -> str:
        # Ensure the URL uses the asyncpg driver required by the async engine.
        if v.startswith("postgresql://"):
            return v.replace("postgresql://", "postgresql+asyncpg://", 1)
        return v

    def _default_key_for(self, provider: str) -> str:
        # Resolve a blank per-service key to the matching global key for its provider.
        return self.DEEPSEEK_API_KEY if provider == "deepseek" else self.OPENAI_API_KEY

    @model_validator(mode="after")
    def _apply_global_llm_fallbacks(self) -> "Settings":
        if not self.SCENARIO_LLM_API_KEY:
            self.SCENARIO_LLM_API_KEY = self._default_key_for(self.SCENARIO_LLM_PROVIDER)
        if not self.SCENARIO_LLM_MODEL:
            self.SCENARIO_LLM_MODEL = self.OPENAI_MODEL
        if not self.EVALUATOR_LLM_API_KEY:
            self.EVALUATOR_LLM_API_KEY = self._default_key_for(self.EVALUATOR_LLM_PROVIDER)
        if not self.EVALUATOR_LLM_MODEL:
            self.EVALUATOR_LLM_MODEL = self.OPENAI_MODEL
        return self


settings = Settings()
