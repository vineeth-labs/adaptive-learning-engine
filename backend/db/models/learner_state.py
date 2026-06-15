from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import List, Any
from datetime import datetime
import sqlalchemy as sa
from .base import Base

class LearnerState(Base):
    __tablename__ = "learner_state"
    
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    mastery: Mapped[float] = mapped_column(sa.Float, default=0.0, server_default=sa.text("0.0"))
    # Beta(alpha, beta) posterior; mastery is its mean (alpha / (alpha + beta)).
    # Nullable — populated in code on the first write from the cold-start prior.
    alpha: Mapped[float] = mapped_column(sa.Float, nullable=True)
    beta: Mapped[float] = mapped_column(sa.Float, nullable=True)
    evidence_count: Mapped[int] = mapped_column(sa.Integer, default=0, server_default=sa.text("0"))
    misconceptions: Mapped[List[Any]] = mapped_column(JSONB, default=list, server_default=sa.text("'[]'::jsonb"))
    last_interaction_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), nullable=True)
