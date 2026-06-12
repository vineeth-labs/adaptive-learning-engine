from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID
from typing import List

from backend.db.models import Domain, Concept, ConceptRelationship
from backend.schemas import DomainResponse, ConceptResponse, DomainGraphResponse, GraphNode, GraphEdge
from backend.api.dependencies import get_db

router = APIRouter(prefix="/domains", tags=["domains"])

@router.get("", response_model=List[DomainResponse])
async def get_domains(db: AsyncSession = Depends(get_db)):
    """
    Get a list of all available domains.
    """
    result = await db.execute(select(Domain))
    domains = result.scalars().all()
    return domains

@router.get("/{domain_id}/concepts", response_model=List[ConceptResponse])
async def get_domain_concepts(domain_id: UUID, db: AsyncSession = Depends(get_db)):
    """
    Get a list of concepts associated with a specific domain.
    """
    # Verify that the domain exists
    domain_result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = domain_result.scalar_one_or_none()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    result = await db.execute(select(Concept).where(Concept.domain_id == domain_id))
    concepts = result.scalars().all()
    return concepts

@router.get("/{domain_id}/graph", response_model=DomainGraphResponse)
async def get_domain_graph(domain_id: UUID, db: AsyncSession = Depends(get_db)):
    domain_result = await db.execute(select(Domain).where(Domain.id == domain_id))
    domain = domain_result.scalar_one_or_none()
    if not domain:
        raise HTTPException(status_code=404, detail="Domain not found")

    concepts_result = await db.execute(select(Concept).where(Concept.domain_id == domain_id))
    concepts = concepts_result.scalars().all()
    concept_ids = {c.id for c in concepts}

    edges_result = await db.execute(
        select(ConceptRelationship).where(
            ConceptRelationship.source_id.in_(concept_ids),
            ConceptRelationship.target_id.in_(concept_ids),
        )
    )
    edges = edges_result.scalars().all()

    return DomainGraphResponse(
        domain_id=domain.id,
        domain_name=domain.name,
        nodes=[GraphNode.model_validate(c) for c in concepts],
        edges=[GraphEdge.model_validate(e) for e in edges],
    )
