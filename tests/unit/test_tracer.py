import pytest

from backend.services.graph.concept_graph import Concept, ConceptGraph
from backend.services.learner.bkt_models import BKTParams, Grade
from backend.services.learner.tracer import KnowledgeTracer


# ---------------------------------------------------------------------------
# Shared params and graph factories
# ---------------------------------------------------------------------------

DEFAULT = BKTParams(p_transit=0.10, p_slip=0.10, p_guess=0.20, base_prior=0.30)
THRESHOLD = 0.6


def _c(id: str, *prereqs: str) -> Concept:
    return Concept(id=id, name=id.upper(), prerequisites=prereqs)


def linear_graph() -> ConceptGraph:
    """A → B → C"""
    return ConceptGraph([_c("A"), _c("B", "A"), _c("C", "B")])


def fork_graph() -> ConceptGraph:
    """A → B → D, A → C  (B has downstream D; C is a leaf)"""
    return ConceptGraph([_c("A"), _c("B", "A"), _c("C", "A"), _c("D", "B")])


def twin_roots_graph() -> ConceptGraph:
    """A, B — two independent root concepts"""
    return ConceptGraph([_c("A"), _c("B")])


# ---------------------------------------------------------------------------
# Cold-start belief initialisation
# ---------------------------------------------------------------------------

class TestColdStart:
    def test_root_gets_base_prior(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer.mastery("A") == pytest.approx(DEFAULT.base_prior)

    def test_one_hop_downstream_gated(self):
        # B belief = base_prior * belief[A] = 0.3 * 0.3 = 0.09
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer.mastery("B") == pytest.approx(DEFAULT.base_prior ** 2)

    def test_two_hop_downstream_gated(self):
        # C belief = base_prior * belief[B] = 0.3 * 0.09 = 0.027
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer.mastery("C") == pytest.approx(DEFAULT.base_prior ** 3)

    def test_diamond_prereq_mean(self):
        # D prereqs are B and C; both have belief base_prior * base_prior
        # D belief = base_prior * mean(B, C) = base_prior * base_prior^2
        graph = ConceptGraph([_c("A"), _c("B", "A"), _c("C", "A"), _c("D", "B", "C")])
        tracer = KnowledgeTracer(graph, DEFAULT)
        expected = DEFAULT.base_prior * DEFAULT.base_prior ** 2
        assert tracer.mastery("D") == pytest.approx(expected)

    def test_all_concepts_present(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert set(tracer.beliefs().keys()) == {"A", "B", "C"}


# ---------------------------------------------------------------------------
# observe / observe_grade
# ---------------------------------------------------------------------------

class TestObserve:
    def test_correct_raises_belief(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        prior = tracer.mastery("A")
        tracer.observe("A", correct=True)
        assert tracer.mastery("A") > prior

    def test_incorrect_lowers_belief(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        prior = tracer.mastery("A")
        tracer.observe("A", correct=False)
        assert tracer.mastery("A") < prior

    def test_observe_grade_correct_matches_binary(self):
        g1 = KnowledgeTracer(linear_graph(), DEFAULT)
        g2 = KnowledgeTracer(linear_graph(), DEFAULT)
        g1.observe("A", correct=True)
        g2.observe_grade("A", Grade.CORRECT)
        assert g1.mastery("A") == pytest.approx(g2.mastery("A"))

    def test_observe_returns_new_belief(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        returned = tracer.observe("A", correct=True)
        assert returned == pytest.approx(tracer.mastery("A"))

    def test_observe_propagates_to_downstream_prior(self):
        # Raising A's belief must lift B's prerequisite-gated prior
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        initial_b = tracer.mastery("B")
        tracer.observe("A", correct=True)
        assert tracer.mastery("B") > initial_b

    def test_observe_upstream_does_not_affect_parent(self):
        # Observing B should not change A's belief (A has direct evidence or prior)
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        tracer.observe("A", correct=True)
        a_after_a = tracer.mastery("A")
        tracer.observe("B", correct=True)
        assert tracer.mastery("A") == pytest.approx(a_after_a)

    def test_observe_unknown_concept_raises(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        with pytest.raises(KeyError):
            tracer.observe("UNKNOWN", correct=True)

    def test_observe_grade_unknown_concept_raises(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        with pytest.raises(KeyError):
            tracer.observe_grade("UNKNOWN", Grade.CORRECT)

    def test_repeated_correct_monotonic(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        beliefs = [tracer.mastery("A")]
        for _ in range(5):
            tracer.observe("A", correct=True)
            beliefs.append(tracer.mastery("A"))
        assert beliefs == sorted(beliefs)


# ---------------------------------------------------------------------------
# from_state
# ---------------------------------------------------------------------------

class TestFromState:
    def test_loads_mastery_for_known_concept(self):
        tracer = KnowledgeTracer.from_state(
            linear_graph(), mastery={"A": 0.8}, params=DEFAULT
        )
        assert tracer.mastery("A") == pytest.approx(0.8)

    def test_unknown_concept_keeps_dynamic_prior(self):
        # B and C not in mastery dict — they retain the prereq-gated prior
        tracer = KnowledgeTracer.from_state(
            linear_graph(), mastery={"A": 0.8}, params=DEFAULT
        )
        expected_b = DEFAULT.base_prior * 0.8
        assert tracer.mastery("B") == pytest.approx(expected_b)

    def test_loaded_mastery_propagates_downstream(self):
        # Loading A=0.8 should set B's belief to base_prior * 0.8
        tracer = KnowledgeTracer.from_state(
            linear_graph(), mastery={"A": 0.8}, params=DEFAULT
        )
        assert tracer.mastery("B") == pytest.approx(DEFAULT.base_prior * 0.8)

    def test_invalid_mastery_above_one_raises(self):
        with pytest.raises(ValueError):
            KnowledgeTracer.from_state(
                linear_graph(), mastery={"A": 1.1}, params=DEFAULT
            )

    def test_invalid_mastery_below_zero_raises(self):
        with pytest.raises(ValueError):
            KnowledgeTracer.from_state(
                linear_graph(), mastery={"A": -0.1}, params=DEFAULT
            )

    def test_unknown_concept_id_raises(self):
        with pytest.raises(KeyError):
            KnowledgeTracer.from_state(
                linear_graph(), mastery={"MISSING": 0.5}, params=DEFAULT
            )

    def test_counts_loaded_when_provided(self):
        tracer = KnowledgeTracer.from_state(
            linear_graph(), mastery={"A": 0.5}, counts={"A": 2}, params=DEFAULT
        )
        assert tracer.counts["A"] == 2

    def test_counts_default_to_99_when_omitted(self):
        # Concepts in mastery but not counts → default count=99 (treated as settled)
        tracer = KnowledgeTracer.from_state(
            linear_graph(), mastery={"A": 0.5}, params=DEFAULT
        )
        assert tracer.counts["A"] == 99


# ---------------------------------------------------------------------------
# from_events
# ---------------------------------------------------------------------------

class TestFromEvents:
    def test_matches_sequential_observe(self):
        events = [("A", True), ("A", False), ("A", True)]
        tracer_ev = KnowledgeTracer.from_events(linear_graph(), events, params=DEFAULT)

        tracer_seq = KnowledgeTracer(linear_graph(), DEFAULT)
        for cid, outcome in events:
            tracer_seq.observe(cid, outcome)

        assert tracer_ev.beliefs() == pytest.approx(tracer_seq.beliefs())

    def test_grade_events_match_observe_grade(self):
        events = [("A", Grade.CORRECT), ("A", Grade.PARTIAL), ("B", Grade.INCORRECT)]
        tracer_ev = KnowledgeTracer.from_events(linear_graph(), events, params=DEFAULT)

        tracer_seq = KnowledgeTracer(linear_graph(), DEFAULT)
        for cid, grade in events:
            tracer_seq.observe_grade(cid, grade)

        assert tracer_ev.beliefs() == pytest.approx(tracer_seq.beliefs())

    def test_empty_events_equals_cold_start(self):
        tracer_ev = KnowledgeTracer.from_events(linear_graph(), [], params=DEFAULT)
        tracer_cold = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer_ev.beliefs() == pytest.approx(tracer_cold.beliefs())

    def test_counts_increment_per_event(self):
        events = [("A", True), ("A", True), ("A", False)]
        tracer = KnowledgeTracer.from_events(linear_graph(), events, params=DEFAULT)
        assert tracer.counts["A"] == 3


# ---------------------------------------------------------------------------
# select_next
# ---------------------------------------------------------------------------

class TestSelectNext:
    def test_root_returned_when_downstream_blocked(self):
        # Cold start: only A is ready (B and C have unmastered prereq A)
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer.select_next(mastery_threshold=THRESHOLD) == "A"

    def test_blocked_concept_never_returned(self):
        # Even after many calls, B is never returned while A is below threshold
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        result = tracer.select_next(mastery_threshold=THRESHOLD)
        assert result != "B" and result != "C"

    def test_returns_none_when_all_mastered(self):
        # Load all concepts as mastered with high count so none are candidates
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.95, "B": 0.95, "C": 0.95},
            counts={"A": 10, "B": 10, "C": 10},
            params=DEFAULT,
        )
        assert tracer.select_next(mastery_threshold=THRESHOLD, min_questions=3) is None

    def test_undersampled_concept_returned_despite_high_belief(self):
        # Single concept so there are no competing candidates.
        # A=0.95 (above confident_high=0.85) but count=1 < min_questions=3 → undersampled → candidate.
        single = ConceptGraph([_c("A")])
        tracer = KnowledgeTracer.from_state(
            single, mastery={"A": 0.95}, counts={"A": 1}, params=DEFAULT
        )
        assert tracer.select_next(mastery_threshold=THRESHOLD, min_questions=3) == "A"
        # With enough samples and the same high belief it drops out entirely.
        tracer2 = KnowledgeTracer.from_state(
            single, mastery={"A": 0.95}, counts={"A": 10}, params=DEFAULT
        )
        assert tracer2.select_next(mastery_threshold=THRESHOLD, min_questions=3) is None

    def test_confident_concept_excluded_when_well_sampled(self):
        # A=0.95, count=10 — not undersampled, not uncertain → excluded
        tracer = KnowledgeTracer.from_state(
            twin_roots_graph(),
            mastery={"A": 0.95, "B": 0.5},
            counts={"A": 10, "B": 10},
            params=DEFAULT,
        )
        # Only B (uncertain) should be returned
        result = tracer.select_next(mastery_threshold=THRESHOLD, min_questions=3)
        assert result == "B"

    def test_prefers_more_uncertain_concept(self):
        # A=0.5 (max entropy), B=0.8 (lower entropy) — both uncertain
        tracer = KnowledgeTracer.from_state(
            twin_roots_graph(),
            mastery={"A": 0.5, "B": 0.8},
            counts={"A": 5, "B": 5},
            params=DEFAULT,
        )
        result = tracer.select_next(strategy="uncertainty", min_questions=3)
        assert result == "A"

    def test_eig_strategy_accepted(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        # Just verify it runs without error and returns the same candidate
        result = tracer.select_next(strategy="eig")
        assert result == "A"

    def test_unknown_strategy_raises(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        with pytest.raises(ValueError, match="unknown strategy"):
            tracer.select_next(strategy="bogus")

    def test_frontier_expands_after_prereq_mastered(self):
        # After A is mastered, B should become selectable
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        # Force A to mastery via repeated correct answers
        for _ in range(20):
            tracer.observe("A", correct=True)
        assert tracer.mastery("A") >= THRESHOLD
        # Now B should be reachable
        candidates_include_b = False
        for _ in range(5):
            r = tracer.select_next(mastery_threshold=THRESHOLD, min_questions=1)
            if r == "B":
                candidates_include_b = True
                break
        assert candidates_include_b


# ---------------------------------------------------------------------------
# recommend_next_to_study
# ---------------------------------------------------------------------------

class TestRecommendNextToStudy:
    def test_returns_root_from_cold_start(self):
        # Only A is ready (no prereqs); B, C, D blocked
        tracer = KnowledgeTracer(fork_graph(), DEFAULT)
        assert tracer.recommend_next_to_study(mastery_threshold=THRESHOLD) == "A"

    def test_ready_prereqs_only(self):
        # With A below threshold, B/C/D must not be recommended
        tracer = KnowledgeTracer(fork_graph(), DEFAULT)
        rec = tracer.recommend_next_to_study(mastery_threshold=THRESHOLD)
        assert rec not in ("B", "C", "D")

    def test_scores_leverage_correctly(self):
        # A mastered; B leads to D (unblocked downstream=1), C is a leaf (0 downstream)
        # Score(B) = (1-belief_B)*(1+1) > Score(C) = (1-belief_C)*(1+0)
        tracer = KnowledgeTracer.from_state(
            fork_graph(),
            mastery={"A": 0.95},
            counts={"A": 10},
            params=DEFAULT,
        )
        rec = tracer.recommend_next_to_study(mastery_threshold=THRESHOLD)
        assert rec == "B"

    def test_returns_none_when_all_mastered(self):
        tracer = KnowledgeTracer.from_state(
            fork_graph(),
            mastery={"A": 0.95, "B": 0.95, "C": 0.95, "D": 0.95},
            counts={"A": 10, "B": 10, "C": 10, "D": 10},
            params=DEFAULT,
        )
        assert tracer.recommend_next_to_study(mastery_threshold=THRESHOLD) is None

    def test_deterministic_tie_break(self):
        # Both A and B are roots with same cold-start belief → tie broken by id ("A" < "B")
        tracer = KnowledgeTracer(twin_roots_graph(), DEFAULT)
        assert tracer.recommend_next_to_study(mastery_threshold=THRESHOLD) == "A"

    def test_skips_already_mastered_concept(self):
        # Load A as mastered; next should be B (the only ready unmastered concept)
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.95},
            counts={"A": 10},
            params=DEFAULT,
        )
        rec = tracer.recommend_next_to_study(mastery_threshold=THRESHOLD)
        assert rec == "B"


# ---------------------------------------------------------------------------
# gap_report
# ---------------------------------------------------------------------------

class TestGapReport:
    def test_all_not_learned_from_cold_start(self):
        # Cold-start beliefs: A=0.30, B=0.09, C=0.027 — all below shaky_low=0.40
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        report = tracer.gap_report(mastered=0.85, shaky_low=0.40)
        assert set(report.not_learned) == {"A", "B", "C"}
        assert report.mastered == []
        assert report.shaky == []

    def test_mastered_bucket(self):
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.90, "B": 0.90, "C": 0.90},
            counts={"A": 10, "B": 10, "C": 10},
            params=DEFAULT,
        )
        report = tracer.gap_report(mastered=0.85)
        assert set(report.mastered) == {"A", "B", "C"}
        assert report.shaky == []
        assert report.not_learned == []

    def test_shaky_bucket(self):
        # Set A to 0.6 (≥ shaky_low=0.40, < mastered=0.85)
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.60},
            counts={"A": 10},
            params=DEFAULT,
        )
        report = tracer.gap_report(mastered=0.85, shaky_low=0.40)
        assert "A" in report.shaky

    def test_recommended_next_matches_recommend_method(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        report = tracer.gap_report()
        assert report.recommended_next == tracer.recommend_next_to_study()

    def test_all_concepts_appear_in_exactly_one_bucket(self):
        tracer = KnowledgeTracer.from_state(
            fork_graph(),
            mastery={"A": 0.90, "B": 0.60},
            counts={"A": 10, "B": 10},
            params=DEFAULT,
        )
        report = tracer.gap_report(mastered=0.85, shaky_low=0.40)
        all_bucketed = set(report.mastered) | set(report.shaky) | set(report.not_learned)
        assert all_bucketed == {"A", "B", "C", "D"}
        # No concept should appear in two buckets
        total = len(report.mastered) + len(report.shaky) + len(report.not_learned)
        assert total == 4

    def test_topological_order_in_report(self):
        # Buckets are filled in topo order — A must appear before B in not_learned
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        report = tracer.gap_report()
        idx = {c: i for i, c in enumerate(report.not_learned)}
        assert idx["A"] < idx["B"] < idx["C"]


# ---------------------------------------------------------------------------
# preview_path
# ---------------------------------------------------------------------------

class TestPreviewPath:
    def test_nonempty_from_cold_start(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        path = tracer.preview_path()
        assert len(path) > 0

    def test_distinct_concepts(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        path = tracer.preview_path(max_steps=10)
        assert len(path) == len(set(path))

    def test_max_steps_respected(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        for max_steps in (1, 2, 3):
            assert len(tracer.preview_path(max_steps=max_steps)) <= max_steps

    def test_does_not_mutate_tracer(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        beliefs_before = dict(tracer.beliefs())
        counts_before = dict(tracer.counts)
        tracer.preview_path(max_steps=10)
        assert tracer.beliefs() == pytest.approx(beliefs_before)
        assert dict(tracer.counts) == counts_before

    def test_starts_with_root_from_cold_start(self):
        # First concept in the preview path should be a root (A has no prereqs)
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        path = tracer.preview_path()
        assert path[0] == "A"

    def test_returns_empty_when_all_mastered(self):
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.95, "B": 0.95, "C": 0.95},
            counts={"A": 10, "B": 10, "C": 10},
            params=DEFAULT,
        )
        assert tracer.preview_path() == []


# ---------------------------------------------------------------------------
# recommend_path
# ---------------------------------------------------------------------------

class TestRecommendPath:
    def test_first_element_matches_recommend_next(self):
        tracer = KnowledgeTracer(fork_graph(), DEFAULT)
        rec = tracer.recommend_next_to_study(mastery_threshold=THRESHOLD)
        path = tracer.recommend_path(mastery_threshold=THRESHOLD)
        assert path[0] == rec

    def test_does_not_mutate_tracer(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        beliefs_before = dict(tracer.beliefs())
        tracer.recommend_path()
        assert tracer.beliefs() == pytest.approx(beliefs_before)

    def test_max_steps_respected(self):
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        for max_steps in (1, 2):
            assert len(tracer.recommend_path(max_steps=max_steps)) <= max_steps

    def test_returns_empty_when_all_mastered(self):
        tracer = KnowledgeTracer.from_state(
            linear_graph(),
            mastery={"A": 0.95, "B": 0.95, "C": 0.95},
            counts={"A": 10, "B": 10, "C": 10},
            params=DEFAULT,
        )
        assert tracer.recommend_path() == []


# ---------------------------------------------------------------------------
# select_frontier_cluster
# ---------------------------------------------------------------------------

def _master(tracer: KnowledgeTracer, concept_id: str, n: int = 5) -> None:
    """Drive a concept above threshold with enough correct answers to be 'settled'."""
    for _ in range(n):
        tracer.observe(concept_id, correct=True)


class TestSelectFrontierCluster:
    def test_empty_when_nothing_learnable(self):
        # Both roots mastered and well-sampled -> no frontier candidates left.
        tracer = KnowledgeTracer(twin_roots_graph(), DEFAULT)
        _master(tracer, "A")
        _master(tracer, "B")
        assert tracer.select_frontier_cluster(size=3, mastery_threshold=THRESHOLD) == []

    def test_single_seed_when_frontier_thin(self):
        # Cold-start linear graph: only the root A is ready, so the cluster is just [A].
        tracer = KnowledgeTracer(linear_graph(), DEFAULT)
        assert tracer.select_frontier_cluster(size=3, mastery_threshold=THRESHOLD) == ["A"]

    def test_first_element_is_select_next_seed(self):
        # R1 -> b1,b2 ; R2 -> a0. Master both hubs equally.
        graph = ConceptGraph([
            _c("r1"), _c("r2"),
            _c("b1", "r1"), _c("b2", "r1"), _c("a0", "r2"),
        ])
        tracer = KnowledgeTracer(graph, DEFAULT)
        _master(tracer, "r1")
        _master(tracer, "r2")
        cluster = tracer.select_frontier_cluster(size=2, mastery_threshold=THRESHOLD)
        seed = tracer.select_next(mastery_threshold=THRESHOLD)
        assert cluster[0] == seed

    def test_prefers_related_over_unrelated(self):
        # b1,b2 share prereq r1 (mutually related); a0 (prereq r2) is unrelated to them.
        # Equal beliefs -> seed is max id "b2"; its related sibling b1 must be picked
        # over the unrelated a0 for a size-2 cluster.
        graph = ConceptGraph([
            _c("r1"), _c("r2"),
            _c("b1", "r1"), _c("b2", "r1"), _c("a0", "r2"),
        ])
        tracer = KnowledgeTracer(graph, DEFAULT)
        _master(tracer, "r1")
        _master(tracer, "r2")
        cluster = tracer.select_frontier_cluster(size=2, mastery_threshold=THRESHOLD)
        assert cluster == ["b2", "b1"]
        assert "a0" not in cluster

    def test_all_members_are_on_the_frontier(self):
        graph = ConceptGraph([
            _c("r"), _c("c1", "r"), _c("c2", "r"), _c("c3", "r"),
        ])
        tracer = KnowledgeTracer(graph, DEFAULT)
        _master(tracer, "r")
        cluster = tracer.select_frontier_cluster(size=3, mastery_threshold=THRESHOLD)
        assert len(cluster) == 3
        assert len(set(cluster)) == 3  # distinct
        for cid in cluster:
            assert tracer._is_ready(cid, THRESHOLD)  # prerequisites mastered

    def test_size_one_returns_only_seed(self):
        graph = ConceptGraph([_c("r"), _c("c1", "r"), _c("c2", "r")])
        tracer = KnowledgeTracer(graph, DEFAULT)
        _master(tracer, "r")
        cluster = tracer.select_frontier_cluster(size=1, mastery_threshold=THRESHOLD)
        assert len(cluster) == 1
        assert cluster[0] == tracer.select_next(mastery_threshold=THRESHOLD)

    def test_does_not_mutate_tracer(self):
        graph = ConceptGraph([_c("r"), _c("c1", "r"), _c("c2", "r")])
        tracer = KnowledgeTracer(graph, DEFAULT)
        _master(tracer, "r")
        before = tracer.beliefs()
        tracer.select_frontier_cluster(size=3, mastery_threshold=THRESHOLD)
        assert tracer.beliefs() == before
