from pydantic import BaseModel, Field, ConfigDict, AliasChoices
from uuid import UUID
from typing import Dict, Any

class DomainResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    name: str
    version: str

class ConceptResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    domain_id: UUID
    name: str
    path: str
    difficulty: float = Field(..., ge=0.0, le=1.0)
    metadata: Dict[str, Any] = Field(default_factory=dict, validation_alias=AliasChoices("concept_metadata", "metadata"))
