from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import uuid
from typing import Dict, Any, List
import sqlalchemy as sa
from .base import Base

class Ltree(sa.types.UserDefinedType):
    """
    Custom SQLAlchemy type to support PostgreSQL ltree extension.
    """
    def get_col_spec(self, **kw):
        return "ltree"

    def bind_processor(self, dialect):
        def process(value):
            return value
        return process

    def result_processor(self, dialect, coltype):
        def process(value):
            return value
        return process

class Concept(Base):
    __tablename__ = "concepts"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    domain_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(nullable=False)
    path: Mapped[str] = mapped_column(Ltree, nullable=True)
    difficulty: Mapped[float] = mapped_column(sa.Float, nullable=False)
    concept_metadata: Mapped[Dict[str, Any]] = mapped_column("metadata", JSONB, default=dict, server_default=sa.text("'{}'::jsonb"))
    
    domain: Mapped["Domain"] = relationship(back_populates="concepts")

class ConceptRelationship(Base):
    __tablename__ = "concept_relationships"
    
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), sa.ForeignKey("concepts.id", ondelete="CASCADE"), primary_key=True)
    relation_type: Mapped[str] = mapped_column(sa.String(50), primary_key=True, default="prerequisite")
