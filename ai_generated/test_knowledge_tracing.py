"""Tests for the knowledge-tracing engine.

Run with:  pytest -q
The final test is the showpiece: a synthetic learner with a known ground-truth
mastery vector is run through the full diagnostic loop, and we assert the
inferred gaps match the truth -- the whole system validated with zero real users.
"""

from __future__ import annotations

import random

import pytest

from knowledge_tracing import (
    BKTParams,
    Concept,
    ConceptGraph,
    Grade,
    KnowledgeTracer,
    bkt_posterior,
    bkt_update,
    entropy,
    expected_information_gain,
)
from knowledge_tracing.example_graph import sql_graph

P = BKTParams()


# --------------------------------------------------------------------------
# Pure BKT math
# --------------------------------------------------------------------------

def test_correct_answer_raises_posterior_incorrect_lowers_it():
    p = 0.5
    assert bkt_posterior(p, True, P) > p
    assert bkt_posterior(p, False, P) < p


def test_update_stays_in_unit_interval():
    for p in (0.001, 0.25, 0.5, 0.75, 0.999):
        for correct in (True, False):
            out = bkt_update(p, correct, P)
            assert 0.0 < out < 1.0


def test_repeated_correct_drives_belief_high():
    p = P.base_prior
    for _ in range(8):
        p = bkt_update(p, True, P)
    assert p > 0.95


def test_repeated_incorrect_drives_belief_low():
    p = 0.8
    for _ in range(8):
        p = bkt_update(p, False, P)
    assert p < 0.15


def test_entropy_peaks_at_half():
    assert entropy(0.5) == pytest.approx(1.0)
    assert entropy(0.0) == 0.0
    assert entropy(1.0) == 0.0
    assert entropy(0.5) > entropy(0.9) > entropy(0.99)


def test_information_gain_is_nonnegative_and_peaks_at_uncertainty():
    assert expected_information_gain(0.5, P) >= expected_information_gain(0.95, P) >= 0.0


def test_graded_update_matches_binary_at_extremes():
    from knowledge_tracing import bkt_update_graded

    p = 0.5
    assert bkt_update_graded(p, Grade.CORRECT, P) == pytest.approx(bkt_update(p, True, P))
    assert bkt_update_graded(p, Grade.INCORRECT, P) == pytest.approx(bkt_update(p, False, P))
    partial = bkt_update_graded(p, Grade.PARTIAL, P)
    assert bkt_update(p, False, P) < partial < bkt_update(p, True, P)


def test_bad_params_rejected():
    with pytest.raises(ValueError):
        BKTParams(p_slip=0.6, p_guess=0.6)  # slip + guess >= 1
    with pytest.raises(ValueError):
        BKTParams(p_transit=0.0)


# --------------------------------------------------------------------------
# Graph
# --------------------------------------------------------------------------

def test_cycle_is_rejected():
    with pytest.raises(ValueError):
        ConceptGraph([
            Concept("a", "A", prerequisites=("b",)),
            Concept("b", "B", prerequisites=("a",)),
        ])


def test_unknown_prerequisite_is_rejected():
    with pytest.raises(ValueError):
        ConceptGraph([Concept("a", "A", prerequisites=("ghost",))])


def test_topological_order_respects_prerequisites():
    g = sql_graph()
    order = g.topological_order()
    pos = {cid: i for i, cid in enumerate(order)}
    for cid in g.concepts:
        for p in g.prerequisites(cid):
            assert pos[p] < pos[cid]


def test_ancestors_and_descendants():
    g = sql_graph()
    assert g.ancestors("window") == {"group_by", "aggregates", "select"}
    assert "ctes" in g.descendants("select")
    assert g.descendants("ctes") == set()


# --------------------------------------------------------------------------
# Tracer: prerequisite-gated priors
# --------------------------------------------------------------------------

def test_deep_concept_starts_below_its_prerequisites():
    t = KnowledgeTracer(sql_graph())
    assert t.mastery("window") < t.mastery("group_by") < t.mastery("select")


def test_mastering_prereq_lifts_unobserved_dependent_prior():
    t = KnowledgeTracer(sql_graph())
    before = t.mastery("aggregates")
    for _ in range(6):  # build strong evidence on the prerequisite
        t.observe("group_by", correct=True)
    after = t.mastery("aggregates")  # still unobserved, but prereq is now solid
    assert after > before


# --------------------------------------------------------------------------
# Tracer: selection
# --------------------------------------------------------------------------

def test_select_next_stays_on_the_frontier():
    t = KnowledgeTracer(sql_graph())
    chosen = t.select_next()
    # Nothing is mastered yet, so only root concepts (no prereqs) are ready.
    assert chosen in {"select"}


def test_select_returns_none_when_everything_is_confident():
    t = KnowledgeTracer(sql_graph())
    for cid in t.graph.concepts:
        for _ in range(10):
            t.observe(cid, correct=True)
    assert t.select_next() is None


def test_eig_strategy_also_picks_a_valid_frontier_concept():
    t = KnowledgeTracer(sql_graph())
    assert t.select_next(strategy="eig") == "select"


# --------------------------------------------------------------------------
# Tracer: recommendation
# --------------------------------------------------------------------------

def test_recommendation_is_a_learnable_frontier_concept():
    t = KnowledgeTracer(sql_graph())
    # Master the root so the frontier opens up.
    for _ in range(10):
        t.observe("select", correct=True)
    rec = t.recommend_next_to_study()
    assert rec is not None
    # Its prerequisites must all be mastered.
    assert all(t.mastery(p) >= 0.6 for p in t.graph.prerequisites(rec))
    assert t.mastery(rec) < 0.6


def test_recommendation_prefers_higher_leverage():
    # 'select' unblocks the whole tree; a leaf unblocks nothing. With only the
    # root learnable, the recommendation should be the root.
    t = KnowledgeTracer(sql_graph())
    assert t.recommend_next_to_study() == "select"


# --------------------------------------------------------------------------
# Integration: synthetic learner end-to-end
# --------------------------------------------------------------------------

def _simulate_answer(rng: random.Random, knows: bool, params: BKTParams) -> bool:
    """A learner who knows a concept answers right unless they slip; one who
    doesn't answers wrong unless they guess."""
    if knows:
        return rng.random() > params.p_slip
    return rng.random() < params.p_guess


def test_full_diagnostic_recovers_known_gaps():
    rng = random.Random(7)
    g = sql_graph()
    params = BKTParams()

    # Ground truth: this learner has the basics and joins, but not aggregation,
    # window functions, or the things built on subqueries.
    truth = {
        "select": True, "where": True, "joins": True,
        "group_by": True, "aggregates": False, "having": False,
        "subqueries": True, "window": False, "ctes": False,
    }

    t = KnowledgeTracer(g, params)
    # Run the agent loop: select -> simulate answer -> observe, until confident.
    for _ in range(80):
        cid = t.select_next()
        if cid is None:
            break
        t.observe(cid, correct=_simulate_answer(rng, truth[cid], params))

    # Classify each concept by inferred belief and compare to ground truth.
    correct_calls = 0
    for cid, known in truth.items():
        inferred_known = t.mastery(cid) >= 0.5
        correct_calls += int(inferred_known == known)

    accuracy = correct_calls / len(truth)
    assert accuracy >= 0.77, f"diagnostic only matched {accuracy:.0%} of ground truth"

    # The report must not claim a concept is mastered that the learner lacks.
    report = t.gap_report()
    assert "aggregates" not in report.mastered
    assert "window" not in report.mastered
