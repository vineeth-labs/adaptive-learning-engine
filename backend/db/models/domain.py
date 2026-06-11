from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import uuid
from typing import List
from .base import Base

class Domain(Base):
    __tablename__ = "domains"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(nullable=False)
    version: Mapped[str] = mapped_column(default="1.0")
    
    concepts: Mapped[List["Concept"]] = relationship(back_populates="domain", cascade="all, delete-orphan")
