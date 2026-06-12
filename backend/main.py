from fastapi import FastAPI, APIRouter
from backend.api.routes.domains import router as domains_router
from backend.api.routes.users import router as users_router

app = FastAPI(
    title="AI Competency Mapping API",
    description="Backend API for managing competency mapping, learner state, and assessments.",
    version="1.0.0"
)

# Base API v1 router
api_v1_router = APIRouter(prefix="/api/v1")
api_v1_router.include_router(domains_router)
api_v1_router.include_router(users_router)

# Mount API v1 router to the FastAPI application
app.include_router(api_v1_router)

@app.get("/health")
async def health_check():
    """
    Simple health check endpoint.
    """
    return {"status": "ok"}
