from collections import defaultdict
from datetime import datetime, timezone
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.db.models import User, Concept, ConceptRelationship, Assessment, AssessmentQuestion, AssessmentResult
from backend.schemas import (
    AssessmentGenerateRequest,
    AssessmentGenerateResponse,
    AssessmentNextRequest,
    AssessmentNextResponse,
    TargetConcept,
    AssessmentSubmitRequest,
    AssessmentSubmitResponse,
    ConceptMasteryUpdate,
)
from backend.api.dependencies import get_db
from backend.core.config import settings
from backend.services.llm import (
    generate_questions,
    generate_cluster_scenario,
    LLMGenerationError,
    evaluate_response,
)
from backend.services.learner import apply_diagnostic_result
from backend.services.learner.rehydrate import build_tracer

router = APIRouter(prefix="/assessments", tags=["assessments"])

MAX_QUESTIONS = 5
MIN_CLUSTER = 2
MAX_CLUSTER = 3


async def _prerequisite_names(concept_id, db: AsyncSession) -> list[str]:
    """Names of concepts that are a 'prerequisite' of the given concept."""
    rows = (
        await db.execute(
            select(Concept.name)
            .join(ConceptRelationship, ConceptRelationship.source_id == Concept.id)
            .where(
                ConceptRelationship.target_id == concept_id,
                ConceptRelationship.relation_type == "prerequisite",
            )
        )
    ).scalars().all()
    return list(rows)


def _group_questions_by_concept(questions, fallback_concept_id):
    """Group questions by their target concept, ordered by position within each group.

    A question with no ``concept_id`` (legacy / single-concept assessment) falls back
    to ``fallback_concept_id`` (the parent assessment's concept). Pure function — no DB.
    Returns ``dict[concept_id, list[question]]``.
    """
    groups: dict = defaultdict(list)
    for q in sorted(questions, key=lambda q: q.position):
        groups[q.concept_id or fallback_concept_id].append(q)
    return groups


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

    prereq_names = await _prerequisite_names(concept.id, db)

    try:
        question_texts = await generate_questions(concept, prereq_names, n)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Question generation failed: {exc}")

    assessment = Assessment(user_id=req.user_id, concept_id=concept.id, status="generated")
    assessment.questions = [
        AssessmentQuestion(position=i + 1, question_text=text, concept_id=concept.id)
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


@router.post("/next", response_model=AssessmentNextResponse)
async def next_assessment(req: AssessmentNextRequest, db: AsyncSession = Depends(get_db)):
    """Generate the next diagnostic for a user without a client-supplied concept.

    The engine auto-selects a cluster of 2-3 related *frontier* concepts (prerequisites
    mastered, low/zero evidence) and generates one cohesive scenario with one focused
    question per concept (TECH_SPEC 3.3). Submitting grades each concept independently.
    """
    user = (await db.execute(select(User).where(User.id == req.user_id))).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    rehydrated = await build_tracer(req.user_id, db)
    if rehydrated is None:
        raise HTTPException(status_code=404, detail="No concepts found")

    size = req.num_concepts if req.num_concepts is not None else MAX_CLUSTER
    size = max(MIN_CLUSTER, min(size, MAX_CLUSTER))

    threshold = settings.RECOMMEND_MASTERY_THRESHOLD
    cluster_ids = rehydrated.tracer.select_frontier_cluster(size=size, mastery_threshold=threshold)
    if not cluster_ids:
        return AssessmentNextResponse(
            assessment_id=UUID(int=0),
            user_id=req.user_id,
            status="empty",
            target_concepts=[],
            questions=[],
            created_at=datetime.now(timezone.utc),
            message="No learnable frontier right now — everything reachable is mastered or blocked.",
        )

    cluster_concepts = [rehydrated.concept_by_id[cid] for cid in cluster_ids]

    # Shared prerequisite context across the cluster (exclude cluster members themselves).
    prereq_ids: set[str] = set()
    for cid in cluster_ids:
        prereq_ids.update(rehydrated.graph.prerequisites(cid))
    prereq_ids -= set(cluster_ids)
    prereq_names = [rehydrated.concept_by_id[pid].name for pid in prereq_ids if pid in rehydrated.concept_by_id]

    try:
        question_texts = await generate_cluster_scenario(cluster_concepts, prereq_names)
    except LLMGenerationError as exc:
        raise HTTPException(status_code=502, detail=f"Question generation failed: {exc}")

    # Seed concept (first cluster member) is the parent assessment's concept.
    assessment = Assessment(user_id=req.user_id, concept_id=cluster_concepts[0].id, status="generated")
    assessment.questions = [
        AssessmentQuestion(position=i + 1, question_text=text, concept_id=cluster_concepts[i].id)
        for i, text in enumerate(question_texts)
    ]
    db.add(assessment)
    await db.commit()
    await db.refresh(assessment, attribute_names=["questions"])

    return AssessmentNextResponse(
        assessment_id=assessment.id,
        user_id=assessment.user_id,
        status=assessment.status,
        target_concepts=[
            TargetConcept(concept_id=c.id, concept_name=c.name) for c in cluster_concepts
        ],
        questions=assessment.questions,
        created_at=assessment.created_at,
        message=f"Frontier assessment over {len(cluster_concepts)} related concept(s).",
    )


@router.post("/{assessment_id}/submit", response_model=AssessmentSubmitResponse)
async def submit_assessment(
    assessment_id: UUID,
    req: AssessmentSubmitRequest,
    db: AsyncSession = Depends(get_db),
):
    """Submit user responses and run the LLM diagnostic evaluator per target concept.

    Questions are grouped by their ``concept_id`` (single-concept assessments collapse
    to one group), each group is graded independently, and each concept's mastery belief
    is updated on its own ``LearnerState``.
    """
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

    # Group questions by target concept (NULL -> the assessment's seed concept).
    groups = _group_questions_by_concept(questions.values(), assessment.concept_id)

    # Load every targeted concept in one go.
    concept_ids = list(groups.keys())
    concepts = (
        await db.execute(select(Concept).where(Concept.id.in_(concept_ids)))
    ).scalars().all()
    concept_by_id = {c.id: c for c in concepts}
    missing = [cid for cid in concept_ids if cid not in concept_by_id]
    if missing:
        raise HTTPException(status_code=404, detail="Concept not found for assessment question")

    # Grade and apply each concept group independently.
    concept_results: list[ConceptMasteryUpdate] = []
    for concept_id, group_questions in groups.items():
        concept = concept_by_id[concept_id]
        prereq_names = await _prerequisite_names(concept.id, db)
        qa_pairs = [(q.question_text, q.user_response or "") for q in group_questions]

        try:
            result = await evaluate_response(concept, prereq_names, qa_pairs)
        except LLMGenerationError as exc:
            raise HTTPException(status_code=502, detail=f"Evaluation failed: {exc}")

        mastery = await apply_diagnostic_result(req.user_id, concept.id, result, db)

        evidence_quote = " | ".join(
            qg.evidence_quote for qg in result.question_grades if qg.evidence_quote
        )
        db.add(AssessmentResult(
            assessment_id=assessment_id,
            concept_id=concept.id,
            score_awarded=mastery,
            evidence_quote=evidence_quote,
        ))
        concept_results.append(ConceptMasteryUpdate(
            concept_id=concept.id,
            concept_name=concept.name,
            mastery_score=mastery,
            misconception=result.misconception,
        ))

    assessment.status = "evaluated"
    await db.commit()

    # Order results with the seed concept first so the back-compat top-level fields
    # describe the assessment's primary concept.
    concept_results.sort(key=lambda r: r.concept_id != assessment.concept_id)
    seed_result = concept_results[0]

    return AssessmentSubmitResponse(
        assessment_id=assessment_id,
        status="evaluated",
        concept_results=concept_results,
        mastery_score=seed_result.mastery_score,
        misconception=seed_result.misconception,
        message="Assessment submitted and evaluated successfully.",
    )
