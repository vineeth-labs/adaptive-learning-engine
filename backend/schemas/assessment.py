from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any
from uuid import UUID
from enum import Enum

# Agent 1 Output Specification (GPT-4o)
class ConceptEvaluation(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    concept_id: UUID
    mastery_score: float = Field(..., ge=0.0, le=1.0)
    evidence_quote: str = Field(..., description="Exact string from user response supporting the score")
    misconception: Optional[str] = Field(None, description="Anti-pattern observed if any")

# POST /api/v1/assessments/evaluate Request Payload
class AssessmentSubmissionRequest(BaseModel):
    user_id: UUID
    concept_ids: List[UUID] = Field(..., min_length=1)
    scenario_text: str = Field(..., description="The multi-concept scenario user responded to")
    user_response: str = Field(..., description="The user's response text/code")
    response_latency_ms: Optional[int] = Field(None, description="Time taken by learner in milliseconds")

# POST /api/v1/assessments/evaluate Response Receipt
class AssessmentSubmissionResponse(BaseModel):
    assessment_id: UUID
    task_id: str
    status: str = "queued"
    message: str

class TaskStatus(str, Enum):
    PENDING = "PENDING"
    STARTED = "STARTED"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"

# GET /api/v1/assessments/status/{id} Response
class AssessmentStatusResponse(BaseModel):
    task_id: str
    status: TaskStatus
    evaluations: Optional[List[ConceptEvaluation]] = None
    error: Optional[str] = None
