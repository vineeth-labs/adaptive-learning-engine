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


CLUSTER_SYSTEM_PROMPT = (
    "You are an expert Java technical interviewer designing a single, cohesive diagnostic. "
    "Given a CLUSTER of related target concepts, invent ONE realistic scenario (a debugging "
    "task, a code review, or an architectural decision) that naturally exercises all of them, "
    "then write exactly one focused open-ended question per concept, in the SAME ORDER the "
    "concepts are listed.\n\n"
    "Rules:\n"
    "- One shared scenario, established up front; each question builds on that shared context.\n"
    "- Question i must specifically probe concept i (in the given order) -- not the others.\n"
    "- Questions must be free-text / open-ended. Never multiple choice, true/false, or fill-in-the-blank.\n"
    "- Prefer scenario- or code-grounded prompts that force the candidate to explain reasoning.\n"
    "- Produce exactly one question per concept, in order.\n\n"
    "You MUST respond with a JSON object in exactly this format:\n"
    "{\n"
    '  "questions": [\n'
    '    {"question_text": "Question probing the FIRST concept?"},\n'
    '    {"question_text": "Question probing the SECOND concept?"}\n'
    "  ]\n"
    "}"
)


def _build_cluster_prompt(concepts: List, prerequisite_names: List[str]) -> str:
    prereqs = ", ".join(prerequisite_names) if prerequisite_names else "none"
    lines = [
        "Design one cohesive scenario and exactly one question per concept below, in order.",
        "",
        f"Prerequisite concepts shared across the cluster (assume known): {prereqs}",
        "",
        "Target concepts (write one question for each, in this order):",
    ]
    for i, c in enumerate(concepts, start=1):
        meta = c.concept_metadata or {}
        lines.append(
            f"{i}. {c.name} (difficulty {c.difficulty}, path {c.path or 'n/a'}, metadata {meta})"
        )
    return "\n".join(lines)


def _mock_cluster_questions(concepts: List) -> List[str]:
    names = ", ".join(c.name for c in concepts)
    return [
        f"[MOCK] In a system involving {names}, explain how {c.name} comes into play and "
        f"a mistake that would cause a subtle bug."
        for c in concepts
    ]


async def generate_cluster_scenario(concepts: List, prerequisite_names: List[str]) -> List[str]:
    """Return one question per concept (in the given order) under a single cohesive scenario.

    ``questions[i]`` targets ``concepts[i]``. Falls back to one deterministic mock
    question per concept when no API key is configured.
    """
    if not concepts:
        return []
    if not settings.SCENARIO_LLM_API_KEY:
        return _mock_cluster_questions(concepts)

    client = make_llm_client(settings.SCENARIO_LLM_PROVIDER, settings.SCENARIO_LLM_API_KEY)
    try:
        completion = await client.chat.completions.create(
            model=settings.SCENARIO_LLM_MODEL,
            messages=[
                {"role": "system", "content": CLUSTER_SYSTEM_PROMPT},
                {"role": "user", "content": _build_cluster_prompt(concepts, prerequisite_names)},
            ],
            response_format={"type": "json_object"},
        )
        parsed = GeneratedQuestions.model_validate_json(completion.choices[0].message.content)
    except Exception as exc:
        raise LLMGenerationError(str(exc)) from exc

    questions = [q.question_text for q in parsed.questions]
    if len(questions) != len(concepts):
        raise LLMGenerationError(
            f"expected {len(concepts)} questions (one per concept), got {len(questions)}"
        )
    return questions


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
