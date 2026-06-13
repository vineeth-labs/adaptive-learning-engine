"""The stateful tracer: belief state over the graph, plus the decision logic
that the diagnostic agent loop drives (which concept to probe next, what to
recommend studying, and the gap report).
"""

from __future__ import annotations

from collections import defaultdict

from . import bkt
from .graph import ConceptGraph
from .models import BKTParams, GapReport, Grade


class KnowledgeTracer:
    """Maintains P(mastery) for every concept and exposes the agent's decisions.

    Belief design:
      * A concept with *direct evidence* (it has been answered at least once)
        carries the BKT trajectory of that evidence.
      * A concept with *no direct evidence* carries a prerequisite-gated prior:
        base_prior * mean(prereq beliefs). So advanced concepts start low until
        their prerequisites look solid, and gathering evidence on a prerequisite
        lifts the priors of everything downstream. This is the graph-aware
        extension over per-skill BKT and implements the 'blocking concept' idea.

    Beliefs are recomputed in topological order after every observation, so
    prerequisite priors always reflect the latest evidence (O(n) per update).
    """

    def __init__(self, graph: ConceptGraph, params: BKTParams | None = None):
        self.graph = graph
        self.params = params or BKTParams()
        self._evidence: dict[str, float] = {}       # concept -> belief from evidence
        self.counts: dict[str, int] = defaultdict(int)
        self._belief: dict[str, float] = self._recompute()

    # -- belief state ----------------------------------------------------

    def _recompute(self) -> dict[str, float]:
        belief: dict[str, float] = {}
        for cid in self.graph.topological_order():
            if cid in self._evidence:
                belief[cid] = self._evidence[cid]
                continue
            prereqs = self.graph.prerequisites(cid)
            if not prereqs:
                belief[cid] = self.params.base_prior
            else:
                mean_prereq = sum(belief[p] for p in prereqs) / len(prereqs)
                belief[cid] = self.params.base_prior * mean_prereq
        return belief

    def mastery(self, concept_id: str) -> float:
        return self._belief[concept_id]

    def beliefs(self) -> dict[str, float]:
        return dict(self._belief)

    # -- observation -----------------------------------------------------

    def observe(self, concept_id: str, correct: bool) -> float:
        """Record a binary answer and return the concept's new belief."""
        return self.observe_grade(concept_id, Grade.CORRECT if correct else Grade.INCORRECT)

    def observe_grade(self, concept_id: str, grade: Grade) -> float:
        if concept_id not in self._belief:
            raise KeyError(f"unknown concept: {concept_id!r}")
        prior = self._belief[concept_id]
        updated = bkt.bkt_update_graded(prior, grade, self.params)
        self._evidence[concept_id] = updated
        self.counts[concept_id] += 1
        self._belief = self._recompute()
        return self._belief[concept_id]

    # -- selection (the agent's 'what to ask next') ----------------------

    def _is_ready(self, concept_id: str, mastery_threshold: float) -> bool:
        return all(
            self._belief[p] >= mastery_threshold
            for p in self.graph.prerequisites(concept_id)
        )

    def select_next(
        self,
        *,
        mastery_threshold: float = 0.6,
        confident_low: float = 0.15,
        confident_high: float = 0.85,
        min_questions: int = 3,
        strategy: str = "uncertainty",
    ) -> str | None:
        """Choose the next concept to probe.

        Candidates are concepts whose prerequisites are mastered (the learning
        'frontier') that are either under-sampled (asked fewer than
        ``min_questions`` times) or still uncertain. The under-sampling floor
        matters: without it, one unlucky slip can push a known concept below the
        low-confidence band and it would never be revisited, which also starves
        every concept downstream of it. Among candidates, 'uncertainty' picks the
        highest binary entropy (closest to 0.5); 'eig' picks the highest expected
        information gain. Returns None when the frontier has nothing left to ask.
        """
        candidates: list[str] = []
        for cid in self.graph.concepts:
            if not self._is_ready(cid, mastery_threshold):
                continue
            b = self._belief[cid]
            undersampled = self.counts[cid] < min_questions
            uncertain = confident_low < b < confident_high
            if undersampled or uncertain:
                candidates.append(cid)
        if not candidates:
            return None

        if strategy == "eig":
            score = lambda c: bkt.expected_information_gain(self._belief[c], self.params)
        elif strategy == "uncertainty":
            score = lambda c: bkt.entropy(self._belief[c])
        else:
            raise ValueError(f"unknown strategy: {strategy!r}")

        # (score, id) so ties break deterministically by id.
        return max(candidates, key=lambda c: (score(c), c))

    # -- recommendation (the 'what to study next') -----------------------

    def recommend_next_to_study(self, *, mastery_threshold: float = 0.6) -> str | None:
        """Highest-leverage learnable concept.

        Considers only concepts that are not yet mastered but whose prerequisites
        are (so they're actually learnable now). Scores each by how shaky it is
        times how many not-yet-mastered concepts it unblocks downstream. This is
        the explainable, graph-based 'recommend the next concept' core.
        """
        best: str | None = None
        best_score = -1.0
        for cid in self.graph.concepts:
            if self._belief[cid] >= mastery_threshold:
                continue
            if not self._is_ready(cid, mastery_threshold):
                continue
            downstream = [
                d for d in self.graph.descendants(cid)
                if self._belief[d] < mastery_threshold
            ]
            score = (1.0 - self._belief[cid]) * (1 + len(downstream))
            # Deterministic tie-break by id.
            if score > best_score or (score == best_score and (best is None or cid < best)):
                best_score, best = score, cid
        return best

    # -- reporting -------------------------------------------------------

    def gap_report(self, *, mastered: float = 0.85, shaky_low: float = 0.40) -> GapReport:
        report = GapReport()
        for cid in self.graph.topological_order():
            b = self._belief[cid]
            if b >= mastered:
                report.mastered.append(cid)
            elif b >= shaky_low:
                report.shaky.append(cid)
            else:
                report.not_learned.append(cid)
        report.recommended_next = self.recommend_next_to_study()
        return report
