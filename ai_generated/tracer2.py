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

    # -- constructors for resuming an existing user ----------------------

    @classmethod
    def from_events(
        cls,
        graph: ConceptGraph,
        events: list[tuple[str, bool | Grade]],
        *,
        params: BKTParams | None = None,
    ) -> "KnowledgeTracer":
        """Rebuild a tracer by replaying an answer-event log (the recommended
        path). If you persist every answer in Postgres as the source of truth,
        this reproduces the exact belief state and per-concept counts -- no
        ambiguity between 'this score is real evidence' and 'this score is just
        a prior'. Events are (concept_id, correct) or (concept_id, Grade)."""
        tracer = cls(graph, params)
        for concept_id, outcome in events:
            if isinstance(outcome, Grade):
                tracer.observe_grade(concept_id, outcome)
            else:
                tracer.observe(concept_id, bool(outcome))
        return tracer

    @classmethod
    def from_state(
        cls,
        graph: ConceptGraph,
        mastery: dict[str, float],
        *,
        counts: dict[str, int] | None = None,
        params: BKTParams | None = None,
    ) -> "KnowledgeTracer":
        """Rebuild a tracer from a persisted belief snapshot. Pass only the
        concepts that carry real evidence (the ones you've actually asked about);
        every other concept keeps its dynamic prerequisite-gated prior so it can
        still respond to new evidence. Without per-concept counts the loaded
        concepts are treated as already settled (they won't be re-asked just to
        meet the min-questions floor, but a shaky one still gets re-probed
        because it falls in the uncertain band)."""
        tracer = cls(graph, params)
        for concept_id, score in mastery.items():
            if concept_id not in tracer._belief:
                raise KeyError(f"unknown concept: {concept_id!r}")
            if not 0.0 <= score <= 1.0:
                raise ValueError(f"mastery for {concept_id!r} must be in [0, 1]")
            tracer._evidence[concept_id] = score
            tracer.counts[concept_id] = (counts or {}).get(concept_id, 99)
        tracer._belief = tracer._recompute()
        return tracer

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

    def preview_path(
        self,
        *,
        max_steps: int = 10,
        mastery_threshold: float = 0.6,
        strategy: str = "uncertainty",
    ) -> list[str]:
        """An optimistic roadmap from the *current* state: the ordered series of
        distinct concepts the diagnostic would walk if the learner mastered each
        one as they went. Does not mutate this tracer. From the zero/cold-start
        state this returns the foundations-first learning order; from a populated
        state it returns the remaining path. Useful for showing the user a
        roadmap or a progress map -- but note the live loop still re-selects after
        every real answer, so the actual path adapts as evidence comes in."""
        clone = KnowledgeTracer(self.graph, self.params)
        clone._evidence = dict(self._evidence)
        clone.counts = defaultdict(int, self.counts)
        clone._belief = clone._recompute()

        path: list[str] = []
        seen: set[str] = set()
        for _ in range(max_steps):
            cid = clone.select_next(
                mastery_threshold=mastery_threshold,
                min_questions=1,  # preview wants distinct concepts, not repeats
                strategy=strategy,
            )
            if cid is None:
                break
            if cid not in seen:
                path.append(cid)
                seen.add(cid)
            # Optimistically assume mastery so the frontier expands.
            clone._evidence[cid] = max(clone._belief[cid], 0.95)
            clone.counts[cid] += 1
            clone._belief = clone._recompute()
        return path

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