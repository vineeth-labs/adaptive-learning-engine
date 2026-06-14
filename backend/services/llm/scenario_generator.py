"""
Agent 1: Scenario Generator.

Given a target concept (plus its prerequisite context), produce N open-ended,
free-text diagnostic questions. Uses OpenAI Structured Outputs when an API key is
configured; otherwise falls back to a deterministic mock so the endpoint stays
fully runnable without a key.
"""
from typing import List

from backend.core.config import settings
from backend.schemas import GeneratedQuestions
from .client import make_llm_client

SYSTEM_PROMPT = (
    "You are an expert Java technical interviewer designing a diagnostic assessment. "
    "Given a single target concept and its prerequisite context, write open-ended, "
    "free-text questions that probe genuine depth of understanding, common misconceptions, "
    "and the ability to reason about trade-offs.\n\n"
    "Rules:\n"
    "- Questions must be free-text / open-ended. Never multiple choice, true/false, or fill-in-the-blank.\n"
    "- Each question must target the given concept specifically (not just its prerequisites).\n"
    "- Calibrate difficulty to the provided difficulty score (0.0 = beginner, 1.0 = expert).\n"
    "- Prefer scenario- or code-grounded prompts that force the candidate to explain reasoning.\n"
    "- Produce exactly the requested number of distinct questions.\n\n"
    "You MUST respond with a JSON object in exactly this format:\n"
    "{\n"
    '  "questions": [\n'
    '    {"question_text": "Your first question here?"},\n'
    '    {"question_text": "Your second question here?"}\n'
    "  ]\n"
    "}"
)


class LLMGenerationError(Exception):
    """Raised when the LLM call fails to produce valid questions."""


def _build_user_prompt(concept, prerequisite_names: List[str], num_questions: int) -> str:
    prereqs = ", ".join(prerequisite_names) if prerequisite_names else "none"
    metadata = concept.concept_metadata or {}
    return (
        f"Generate exactly {num_questions} diagnostic question(s).\n\n"
        f"Target concept: {concept.name}\n"
        f"Hierarchical path: {concept.path or 'n/a'}\n"
        f"Difficulty (0.0-1.0): {concept.difficulty}\n"
        f"Prerequisite concepts (assume known): {prereqs}\n"
        f"Additional metadata: {metadata}\n"
    )


def _mock_questions(concept, num_questions: int) -> List[str]:
    return [
        f"[MOCK] Explain how {concept.name} works in Java and describe a real-world "
        f"scenario where misunderstanding it would cause a bug. (variant {i + 1})"
        for i in range(num_questions)
    ]


async def generate_questions(concept, prerequisite_names: List[str], num_questions: int) -> List[str]:
    """Return a list of question strings for the given concept."""
    if not settings.SCENARIO_LLM_API_KEY:
        return _mock_questions(concept, num_questions)

    client = make_llm_client(settings.SCENARIO_LLM_PROVIDER, settings.SCENARIO_LLM_API_KEY)
    try:
        completion = await client.chat.completions.create(
            model=settings.SCENARIO_LLM_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(concept, prerequisite_names, num_questions)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = GeneratedQuestions.model_validate_json(completion.choices[0].message.content)
    except Exception as exc:
        raise LLMGenerationError(str(exc)) from exc

    if not parsed.questions:
        raise LLMGenerationError("LLM returned no questions")

    return [q.question_text for q in parsed.questions]
