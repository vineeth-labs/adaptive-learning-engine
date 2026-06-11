from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID
import uuid
from datetime import datetime
from sqlalchemy import func
import sqlalchemy as sa
from .base import Base

class Recommendation(Base):
    __tablename__ = "recommendations"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    concept_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), nullable=False)
    action_type: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    score_calculated: Mapped[float] = mapped_column(sa.Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(sa.DateTime(timezone=True), server_default=func.now())
