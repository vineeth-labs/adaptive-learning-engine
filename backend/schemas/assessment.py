from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional, Any, Literal
from uuid import UUID
from datetime import datetime
from enum import Enum

# --- Assessment Generation (POST /api/v1/assessments/generate) ---

# LLM Structured Output schema (Agent 1: Scenario Generator)
class GeneratedQuestion(BaseModel):
    question_text: str = Field(..., description="A single open-ended, free-text diagnostic question")

class GeneratedQuestions(BaseModel):
    questions: List[GeneratedQuestion]

class AssessmentGenerateRequest(BaseModel):
    user_id: UUID
    concept_id: UUID
    num_questions: Optional[int] = Field(
        None, description="Override the configured default number of questions for this request"
    )

class AssessmentQuestionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    position: int
    question_text: str

class AssessmentGenerateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    assessment_id: UUID
    user_id: UUID
    concept_id: UUID
    concept_name: str
    status: str
    questions: List[AssessmentQuestionOut]
    created_at: datetime

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


# --- Assessment Submission (POST /api/v1/assessments/{assessment_id}/submit) ---

class QuestionResponse(BaseModel):
    question_id: UUID
    response_text: str

class AssessmentSubmitRequest(BaseModel):
    user_id: UUID
    responses: List[QuestionResponse]

# LLM Structured Output schema (Agent 2: Diagnostic Evaluator)
#
# The evaluator grades EACH question into a three-way Grade enum (the signal the
# Bayesian Knowledge Tracing engine consumes), rather than emitting a single
# holistic float. Each QuestionGrade becomes one BKT observation; the learner's
# mastery belief is then computed by the BKT update, not by the LLM directly.
class QuestionGrade(BaseModel):
    position: int = Field(..., description="1-based position of the question being graded")
    grade: Literal["CORRECT", "PARTIAL", "INCORRECT"] = Field(...,
        description="CORRECT=demonstrates understanding, PARTIAL=partial/flawed, INCORRECT=wrong or absent")
    evidence_quote: str = Field(...,
        description="Verbatim excerpt from this answer that justifies the grade")
    misconception: Optional[str] = Field(None,
        description="Specific anti-pattern or error revealed by this answer, or null if none")

class DiagnosticResult(BaseModel):
    question_grades: List[QuestionGrade] = Field(...,
        description="One grade per question, in order")
    misconception: Optional[str] = Field(None,
        description="Overall/most significant misconception across the responses, or null if none")

class AssessmentSubmitResponse(BaseModel):
    assessment_id: UUID
    status: str
    mastery_score: float
    misconception: Optional[str]
    message: str
