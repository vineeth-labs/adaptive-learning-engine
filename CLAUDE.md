# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project

AI Competency Mapping MVP — a backend that models a learning domain (currently **Java Interview Preparation**) as a Directed Acyclic Graph of concepts, tracks each user's per-concept mastery, generates LLM-driven free-text diagnostic assessments, and recommends the next best action. `TECH_SPEC.md` is the authoritative design doc; read it before touching the assessment/recommendation/learner-model logic.

## Commands

All commands run from the repo root with the venv active and `PYTHONPATH=.` (the `backend` package is imported as `backend.*`, so the root must be on the path).

```bash
source .venv/bin/activate
pip install -r backend/requirements.txt

# Run the API (auto-reload)
PYTHONPATH=. uvicorn backend.main:app --reload      # serves on http://localhost:8000, docs at /docs

# Smoke-test the API in-process (no running server needed; uses httpx ASGITransport)
PYTHONPATH=. python scripts/verify_api.py

# Seed the DB with the Java curriculum (domain + concepts + relationships)
python scripts/populate_java_curriculum.py            # reads DATABASE_URL env var
```

There is no formal test suite yet — `scripts/verify_api.py` is the de-facto integration check, and `api_tests.http` holds manual request examples (VS Code REST Client). The VS Code launch config "Python Debugger: FastAPI" runs the same uvicorn command with `PYTHONPATH` set.

## Database

PostgreSQL with the **`ltree`** extension (hierarchical concept paths) and **JSONB** (misconceptions, metadata). The schema is **hand-maintained in `backend/db/schema.sql` and applied manually** — Alembic is listed as a dependency but migrations are not yet wired up, so schema changes mean editing `schema.sql`, re-applying it, AND updating the matching SQLAlchemy model. Keep `schema.sql` and `backend/db/models/` in sync by hand.

`DATABASE_URL` is given as `postgresql://...`; `core/config.py` rewrites it to `postgresql+asyncpg://...` automatically for the async engine. Note the seed script (`scripts/populate_java_curriculum.py`) uses **psycopg2 (sync)** directly, while the app uses **asyncpg (async)** — both talk to the same DB but through different drivers.

## Architecture

Modular monolith. Request flow: `main.py` mounts route routers under `/api/v1` → routes depend on `get_db` (`api/dependencies.py`, yields an `AsyncSession` from `db/session.py`) → routes call into `services/` → results serialized through `schemas/`.

- **`backend/db/models/`** — SQLAlchemy 2.0 ORM models, all re-exported from `models/__init__.py` (import models from `backend.db.models`, not submodules). Core entities: `Concept`/`ConceptRelationship` (the DAG; edges carry a `relation_type`, e.g. `"prerequisite"`), `LearnerState` (per-user-per-concept mastery, evidence count, JSONB misconceptions), `Assessment`/`AssessmentQuestion`/`AssessmentResult`, `Recommendation`.
- **`backend/schemas/`** — Pydantic models for API I/O **and** LLM structured-output parsing, all re-exported from `schemas/__init__.py`. `GeneratedQuestions` doubles as the OpenAI `response_format`.
- **`backend/services/llm/`** — Single-purpose LLM agents (see TECH_SPEC §3.4). `scenario_generator.py` (Agent 1) generates questions. **Key pattern: every LLM call has a deterministic mock fallback** — when `OPENAI_API_KEY` is empty, it returns mock output so the whole app runs offline. Preserve this when adding agents (e.g. the Diagnostic Evaluator). OpenAI is imported lazily inside the call, and uses `client.beta.chat.completions.parse` with Structured Outputs.
- **`backend/api/routes/`** — One router per resource (`domains`, `users`, `assessments`), each with its own `prefix` and `tags`. Endpoints are listed in TECH_SPEC §5.

Planned-but-not-yet-present service packages from the spec: `services/graph` (DAG traversal), `services/learner` (BKT/FSRS mastery math), `services/recommender` (next-best-action scoring). The DAG-traversal "Frontier" heuristic and the priority-based recommendation routing (Remediation → Exploration → Improvement) are the core domain logic described in TECH_SPEC §3.3 and §3.5.

## Conventions

- Routes are `async def`; all DB access goes through the injected `AsyncSession` using `select()` + `await db.execute(...)`. Commit explicitly and `await db.refresh(...)` when returning generated rows with relationships.
- Map domain failures to `HTTPException` (404 for missing entities, 502 for LLM failures); LLM agents raise their own typed error (`LLMGenerationError`) that routes translate.
- Config is read once via the `settings` singleton in `backend/core/config.py` — a Pydantic `BaseSettings` class (from `pydantic-settings`) that loads `.env`. Add new env vars as typed fields there and document them in `.env.example`.
