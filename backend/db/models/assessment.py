from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from sqlalchemy import func
import sqlalchemy as sa
from .base import Base

class Assessment(Base):
    __tablename__ = "assessments"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    scenario_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    user_response: Mapped[str] = mapped_column(sa.Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=func.now())

class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    score_awarded: Mapped[float] = mapped_column(sa.Float, nullable=False)
    evidence_quote: Mapped[str] = mapped_column(sa.Text, nullable=True)
