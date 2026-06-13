from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import User, Concept, ConceptRelationship, Assessment, AssessmentQuestion
from backend.schemas import AssessmentGenerateRequest, AssessmentGenerateResponse
from backend.api.dependencies import get_db
from backend.core.config import settings
from backend.services.llm import generate_questions, LLMGenerationError

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
