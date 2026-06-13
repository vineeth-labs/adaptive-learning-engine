"""
Agent 2: Diagnostic Evaluator.

Given a target concept, its prerequisites, and the user's Q&A pairs, produce a
structured evaluation containing a mastery score, supporting evidence, and any
detected misconception. Uses OpenAI Structured Outputs when an API key is
configured; otherwise falls back to a deterministic mock.
"""
from typing import List, Tuple

from backend.core.config import settings
from backend.schemas import DiagnosticResult

SYSTEM_PROMPT = (
    "You are an expert Java technical evaluator. "
    "Given a target concept, its prerequisite context, and the candidate's responses "
    "to diagnostic questions, score their understanding.\n"
    "Rules:\n"
    "- mastery_score: 0.0 (no understanding whatsoever) to 1.0 (expert-level mastery).\n"
    "- evidence_quote: copy a verbatim phrase from the responses that best justifies the score.\n"
    "- misconception: if there is a specific anti-pattern or foundational error, describe it "
    "precisely (e.g. 'Believes synchronized blocks prevent all visibility issues without volatile'); "
    "otherwise return null.\n"
    "Base your score strictly on what the candidate wrote — do not infer unstated knowledge."
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
    lines.append(f'Evaluate the candidate\'s understanding of "{concept.name}".')
    return "\n".join(lines)


def _mock_result() -> DiagnosticResult:
    return DiagnosticResult(
        mastery_score=0.5,
        evidence_quote="[MOCK] No real evaluation — API key not set.",
        misconception=None,
    )


async def evaluate_response(
    concept,
    prerequisite_names: List[str],
    qa_pairs: List[Tuple[str, str]],
) -> DiagnosticResult:
    """Return a DiagnosticResult for the user's responses to the given concept's questions."""
    if not settings.OPENAI_API_KEY:
        return _mock_result()

    from openai import AsyncOpenAI
    from backend.services.llm.scenario_generator import LLMGenerationError

    client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)
    try:
        completion = await client.beta.chat.completions.parse(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": _build_user_prompt(concept, prerequisite_names, qa_pairs)},
            ],
            response_format=DiagnosticResult,
        )
        parsed = completion.choices[0].message.parsed
    except Exception as exc:
        raise LLMGenerationError(str(exc)) from exc

    if not parsed:
        raise LLMGenerationError("LLM returned no evaluation")

    return parsed
