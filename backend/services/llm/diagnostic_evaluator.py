"""
Agent 2: Diagnostic Evaluator.

Given a target concept, its prerequisites, and the user's Q&A pairs, produce a
structured evaluation containing a mastery score, supporting evidence, and any
detected misconception. Uses OpenAI Structured Outputs when an API key is
configured; otherwise falls back to a deterministic mock.
"""
from typing import List, Tuple

from backend.core.config import settings
from backend.schemas import DiagnosticResult, QuestionGrade
from .client import make_llm_client

SYSTEM_PROMPT = (
    "You are an expert Java technical evaluator. "
    "Given a target concept, its prerequisite context, and the candidate's responses to diagnostic "
    "questions, grade EACH question independently.\n\n"
    "For every question, return one entry in question_grades with:\n"
    "- position: the 1-based question number exactly as given.\n"
    "- grade: one of CORRECT (clearly demonstrates correct understanding), PARTIAL (partially correct, "
    "incomplete, or correct but with a flaw), or INCORRECT (wrong, irrelevant, or no response).\n"
    "- evidence_quote: copy a verbatim phrase from THAT answer that best justifies the grade "
    "(empty string if the candidate wrote nothing).\n"
    "- misconception: if that answer reveals a specific anti-pattern or foundational error, describe it "
    "precisely (e.g. 'Believes synchronized blocks prevent all visibility issues without volatile'); "
    "otherwise null.\n"
    "Also return a top-level answer_quality: a single float from 0.0 to 1.0 summarizing the overall "
    "quality of the candidate's understanding across all answers, where 0.0 means no understanding and "
    "1.0 means full mastery of the target concept.\n"
    "Also return a top-level misconception: the single most significant misconception across all "
    "answers, or null if none.\n"
    "Grade strictly on what the candidate wrote — do not infer unstated knowledge.\n\n"
    "You MUST respond with a JSON object in exactly this format:\n"
    "{\n"
    '  "question_grades": [\n'
    '    {\n'
    '      "position": 1,\n'
    '      "grade": "CORRECT",\n'
    '      "evidence_quote": "verbatim excerpt from the answer",\n'
    '      "misconception": null\n'
    '    }\n'
    '  ],\n'
    '  "answer_quality": 0.0,\n'
    '  "misconception": null\n'
    "}"
)


def _build_user_prompt(
    concept,
    prerequisite_names: List[str],
    qa_pairs: List[Tuple[str, str]],
) -> str:
    prereqs = ", ".join(prerequisite_names) if prerequisite_names else "none"
    metadata = concept.concept_metadata or {}
    lines = [
        f"Target concept: {concept.name}",
        f"Difficulty (0.0-1.0): {concept.difficulty}",
        f"Prerequisite concepts (assume known): {prereqs}",
        f"Additional metadata: {metadata}",
        "",
        "Questions and user responses:",
    ]
    for i, (question, answer) in enumerate(qa_pairs, start=1):
        lines.append(f"Q{i}: {question}")
        lines.append(f"A{i}: {answer or '[no response provided]'}")
    lines.append("")
    lines.append(
        f'Grade each answer for the candidate\'s understanding of "{concept.name}", '
        "one question_grades entry per question above."
    )
    return "\n".join(lines)


def _mock_result(num_questions: int) -> DiagnosticResult:
    """Deterministic offline fallback: one PARTIAL grade per question."""
    return DiagnosticResult(
        question_grades=[
            QuestionGrade(
                position=i,
                grade="PARTIAL",
                evidence_quote="[MOCK] No real evaluation — API key not set.",
                misconception=None,
            )
            for i in range(1, max(1, num_questions) + 1)
        ],
        answer_quality=0.5,
        misconception=None,
    )


async def evaluate_response(
    concept,
    prerequisite_names: List[str],
    qa_pairs: List[Tuple[str, str]],
) -> DiagnosticResult:
    """Return a DiagnosticResult for the user's responses to the given concept's questions."""
    if not settings.EVALUATOR_LLM_API_KEY:
        return _mock_result(len(qa_pairs))

    from backend.services.llm.scenario_generator import LLMGenerationError

    client = make_llm_client(settings.EVALUATOR_LLM_PROVIDER, settings.EVALUATOR_LLM_API_KEY)
    try:
        completion = await client.chat.completions.create(
            model=settings.EVALUATOR_LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(concept, prerequisite_names, qa_pairs)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = DiagnosticResult.model_validate_json(completion.choices[0].message.content)
    except Exception as exc:
        raise LLMGenerationError(str(exc)) from exc

    if not parsed:
        raise LLMGenerationError("LLM returned no evaluation")

    return parsed
