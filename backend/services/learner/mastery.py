import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from backend.schemas import DiagnosticResult


async def apply_diagnostic_result(
    user_id: uuid.UUID,
    concept_id: uuid.UUID,
    result: DiagnosticResult,
    db: AsyncSession,
) -> None:
    """Stub: will update LearnerState mastery/evidence_count/misconceptions here."""
    pass
