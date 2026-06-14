"""Core BKT data types, vendored from the standalone knowledge-tracing engine
(``ai_generated/models.py``).

Kept deterministic and free of LLM / IO concerns so the math stays trivially
unit-testable. The LLM lives at the edges (question generation and grading);
the learner service only consumes the *result* of grading (a ``Grade``) and
turns it into an updated belief over the learner's mastery.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


@dataclass(frozen=True)
class BKTParams:
    """Bayesian Knowledge Tracing parameters.

    p_transit  P(T): chance an unknown skill becomes known between opportunities
    p_slip     P(S): chance of answering wrong despite knowing it
    p_guess    P(G): chance of answering right despite not knowing it
    base_prior P(L0): prior mastery for a root concept before any evidence.
                      For non-root concepts the prior is gated by prerequisite
                      mastery (see ``apply_diagnostic_result``), which is the
                      graph-aware extension over textbook per-skill BKT.

    These are global constants for the MVP. A production system would fit
    per-concept slip/guess from data (or vary them by difficulty).
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
