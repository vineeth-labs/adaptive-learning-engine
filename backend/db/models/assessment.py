from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import func
import sqlalchemy as sa
from .base import Base

class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(sa.String(50), default="generated", server_default=sa.text("'generated'"))
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=func.now())

    questions: Mapped[List["AssessmentQuestion"]] = relationship(
        back_populates="assessment",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.position",
    )

class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), nullable=False)
    # The concept this question targets. NULL = single-concept assessment (fall back to
    # the parent assessment's concept_id); set per question for multi-concept (frontier) ones.
    concept_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=True)
    position: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    question_text: Mapped[str] = mapped_column(sa.Text, nullable=False)
    user_response: Mapped[str] = mapped_column(sa.Text, nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="questions")

class AssessmentResult(Base):
    __tablename__ = "assessment_results"

    assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("assessments.id", ondelete="CASCADE"), primary_key=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    score_awarded: Mapped[float] = mapped_column(sa.Float, nullable=False)
    evidence_quote: Mapped[str] = mapped_column(sa.Text, nullable=True)
