from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import User, Concept, ConceptRelationship, Assessment, AssessmentQuestion, AssessmentResult
from backend.schemas import (
    AssessmentGenerateRequest,
    AssessmentGenerateResponse,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
)
from backend.api.dependencies import get_db
from backend.core.config import settings
from backend.services.llm import generate_questions, LLMGenerationError, evaluate_response
from backend.services.learner import apply_diagnostic_result

router = APIRouter(prefix="/assessments", tags=["assessments"])

MAX_QUESTIONS = 5

@router.post("/generate", response_model=AssessmentGenerateResponse)
async def generate_assessment(req: AssessmentGenerateRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a new assessment (one or more free-text questions) for a user around a
    single target concept.
    """
    user = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    concept = (await db.execute(select(Concept).where(Concept.id == req.concept_id))).scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    # Resolve how many questions to generate (request override -> configured default), clamped.
    n = req.num_questions if req.num_questions is not None else settings.NUM_QUESTIONS
    n = max(1, min(n, MAX_QUESTIONS))

    # Prerequisite concepts = sources pointing at this concept via a 'prerequisite' edge.
    prereq_rows = (
        await db.execute(
            select(Concept.name)
            .join(ConceptRelationship, ConceptRelationship.source_id == Concept.id)
            .where(
                ConceptRelationship.target_id == concept.id,
                ConceptRelationship.relation_type == "prerequisite",
            )
        )
    ).scalars().all()

    try:
        question_texts = await generate_questions(concept, list(prereq_rows), n)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Question generation failed: {exc}")

    assessment = Assessment(user_id=req.user_id, concept_id=concept.id, status="generated")
    assessment.questions = [
        AssessmentQuestion(position=i + 1, question_text=text)
        for i, text in enumerate(question_texts)
    ]
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment, attribute_names=["questions"])

    return AssessmentGenerateResponse(
        assessment_id=assessment.id,
        user_id=assessment.user_id,
        concept_id=assessment.concept_id,
        concept_name=concept.name,
        status=assessment.status,
        questions=assessment.questions,
        created_at=assessment.created_at,
    )


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
async def submit_assessment(
    assessment_id: UUID,
    req: AssessmentSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit user responses to an assessment and run the LLM diagnostic evaluator."""
    assessment = (
        await db.execute(select(Assessment).where(Assessment.id == assessment_id))
    ).scalar_one_or_none()
    if not assessment:
        raise HTTPException(status_code=404, detail="Assessment not found")
    if assessment.user_id != req.user_id:
        raise HTTPException(status_code=403, detail="Assessment does not belong to this user")

    # Load questions and build a lookup by id.
    questions_result = await db.execute(
        select(AssessmentQuestion).where(AssessmentQuestion.assessment_id == assessment_id)
    )
    questions = {q.id: q for q in questions_result.scalars().all()}

    # Validate and store responses.
    for resp in req.responses:
        question = questions.get(resp.question_id)
        if not question:
            raise HTTPException(
                status_code=400,
                detail=f"Question {resp.question_id} does not belong to this assessment",
            )
        question.user_response = resp.response_text

    # Load concept and prerequisite names (same pattern as generate).
    concept = (
        await db.execute(select(Concept).where(Concept.id == assessment.concept_id))
    ).scalar_one_or_none()
    if not concept:
        raise HTTPException(status_code=404, detail="Concept not found")

    prereq_names = (
        await db.execute(
            select(Concept.name)
            .join(ConceptRelationship, ConceptRelationship.source_id == Concept.id)
            .where(
                ConceptRelationship.target_id == concept.id,
                ConceptRelationship.relation_type == "prerequisite",
            )
        )
    ).scalars().all()

    # Build ordered Q&A pairs for the LLM.
    qa_pairs = [
        (q.question_text, q.user_response or "")
        for q in sorted(questions.values(), key=lambda q: q.position)
    ]

    try:
        result = await evaluate_response(concept, list(prereq_names), qa_pairs)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Evaluation failed: {exc}")

    # Apply the per-question grades to the learner's BKT mastery belief.
    # The returned belief is the principled mastery score (not an LLM float).
    mastery = await apply_diagnostic_result(req.user_id, assessment.concept_id, result, db)

    # Persist the evaluation result. Join the per-question evidence quotes.
    evidence_quote = " | ".join(
        qg.evidence_quote for qg in result.question_grades if qg.evidence_quote
    )
    db.add(AssessmentResult(
        assessment_id=assessment_id,
        concept_id=assessment.concept_id,
        score_awarded=mastery,
        evidence_quote=evidence_quote,
    ))
    assessment.status = "evaluated"
    await db.commit()

    return AssessmentSubmitResponse(
        assessment_id=assessment_id,
        status="evaluated",
        mastery_score=mastery,
        misconception=result.misconception,
        message="Assessment submitted and evaluated successfully.",
    )
