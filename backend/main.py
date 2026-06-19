import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from backend.api.routes.domains import router as domains_router
from backend.api.routes.users import router as users_router
from backend.api.routes.assessments import router as assessments_router
from backend.api.routes.recommendations import router as recommendations_router
from backend.db.session import engine

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        async with engine.connect() as conn:
            await conn.execute(text("SELECT 1"))
        logger.info("Database connection OK")
    except Exception as exc:
        logger.error(
            "Cannot reach the database at startup — is PostgreSQL running? (%s)", exc
        )
    yield


app = FastAPI(
    title="AI Competency Mapping API",
    description="Backend API for managing competency mapping, learner state, and assessments.",
    version="1.0.0",
    lifespan=lifespan,
)

# Allow the local Vite dev server (frontend/) to call the API from the browser.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Base API v1 router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(domains_router)
api_v1_router.include_router(users_router)
api_v1_router.include_router(assessments_router)
api_v1_router.include_router(recommendations_router)

# Mount API v1 router to the FastAPI application
app.include_router(api_v1_router)

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}
