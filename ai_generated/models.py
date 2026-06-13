"""Core data types for the knowledge-tracing engine.

Everything here is deterministic and free of LLM / IO concerns so it can be
unit-tested in isolation. The LLM lives at the edges (question generation and
grading); this package only consumes the *result* of grading (a Grade) and
turns it into an updated belief over the learner's mastery.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


@dataclass(frozen=True)
class Concept:
    """A single node in the knowledge graph.

    prerequisites are the ids of concepts that must be understood first. The
    edges they define must form a DAG (validated by ConceptGraph).
    """

    id: str
    name: str
    prerequisites: tuple[str, ...] = ()
    difficulty: float = 0.5  # 0 (trivial) .. 1 (hard); reserved for question targeting

    def __post_init__(self) -> None:
        if not 0.0 <= self.difficulty <= 1.0:
            raise ValueError(f"difficulty for {self.id!r} must be in [0, 1]")


@dataclass(frozen=True)
class BKTParams:
    """Bayesian Knowledge Tracing parameters.

    p_transit  P(T): chance an unknown skill becomes known between opportunities
    p_slip     P(S): chance of answering wrong despite knowing it
    p_guess    P(G): chance of answering right despite not knowing it
    base_prior P(L0): prior mastery for a root concept before any evidence.
                      For non-root concepts the prior is gated by prerequisite
                      mastery (see KnowledgeTracer), which is the graph-aware
                      extension over textbook per-skill BKT.
    """

    p_transit: float = 0.10
    p_slip: float = 0.10
    p_guess: float = 0.20
    base_prior: float = 0.30

    def __post_init__(self) -> None:
        for name in ("p_transit", "p_slip", "p_guess", "base_prior"):
            v = getattr(self, name)
            if not 0.0 < v < 1.0:
                raise ValueError(f"{name} must be in the open interval (0, 1), got {v}")
        # Identifiability: a guess+slip that sum to >= 1 makes a correct answer
        # *lower* evidence than an incorrect one, which is nonsensical.
        if self.p_slip + self.p_guess >= 1.0:
            raise ValueError("p_slip + p_guess must be < 1 for the model to be identifiable")


class Grade(Enum):
    """Outcome of grading a learner's answer.

    The float value is the 'fraction known' signal used for the soft-evidence
    update. CORRECT and INCORRECT reduce to the standard binary BKT update;
    PARTIAL is a pragmatic interpolation between the two posteriors.
    """

    CORRECT = 1.0
    PARTIAL = 0.5
    INCORRECT = 0.0


@dataclass
class GapReport:
    """A snapshot of the learner's competency, bucketed for presentation."""

    mastered: list[str] = field(default_factory=list)
    shaky: list[str] = field(default_factory=list)
    not_learned: list[str] = field(default_factory=list)
    recommended_next: str | None = None
