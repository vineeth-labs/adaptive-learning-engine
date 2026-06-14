"""Pure Bayesian Knowledge Tracing math, vendored from the standalone
knowledge-tracing engine (``ai_generated/bkt.py``).

These are stateless functions over floats so they're trivial to unit-test and
reason about. No graph, no IO. ``mastery.py`` composes them with the DB-backed
learner state and prerequisite graph.
"""

from __future__ import annotations

from math import log2

from .bkt_models import BKTParams, Grade


def bkt_posterior(p_known: float, correct: bool, params: BKTParams) -> float:
    """P(mastery | observation) *before* applying the learning transition.

    Bayes rule with the slip/guess likelihoods. Denominators are guaranteed
    positive because all params live in the open interval (0, 1).
    """
    s, g = params.p_slip, params.p_guess
    if correct:
        num = p_known * (1.0 - s)
        den = num + (1.0 - p_known) * g
    else:
        num = p_known * s
        den = num + (1.0 - p_known) * (1.0 - g)
    return num / den


def bkt_update(p_known: float, correct: bool, params: BKTParams) -> float:
    """Full BKT step: condition on the observation, then apply learning P(T)."""
    posterior = bkt_posterior(p_known, correct, params)
    return posterior + (1.0 - posterior) * params.p_transit


def bkt_update_graded(p_known: float, grade: Grade, params: BKTParams) -> float:
    """Soft-evidence update for partial credit.

    CORRECT / INCORRECT reduce exactly to the binary update. PARTIAL blends the
    'correct' and 'incorrect' posteriors by the grade weight before applying
    learning. This is a pragmatic extension, not strict Bayes -- documented as
    such so it can be defended honestly in review.
    """
    w = grade.value
    if w == 1.0:
        return bkt_update(p_known, True, params)
    if w == 0.0:
        return bkt_update(p_known, False, params)
    post_c = bkt_posterior(p_known, True, params)
    post_i = bkt_posterior(p_known, False, params)
    blended = w * post_c + (1.0 - w) * post_i
    return blended + (1.0 - blended) * params.p_transit


def entropy(p: float) -> float:
    """Binary entropy in bits. Maximal (1.0) at p=0.5, zero at the extremes."""
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -(p * log2(p) + (1.0 - p) * log2(1.0 - p))


def expected_information_gain(p_known: float, params: BKTParams) -> float:
    """Expected reduction in entropy from asking one question about a concept.

    A more principled selection signal than raw uncertainty: it accounts for how
    much an answer is expected to *move* the belief, given slip/guess noise.
    Kept for the future recommender/selection logic.
    """
    p_correct = p_known * (1.0 - params.p_slip) + (1.0 - p_known) * params.p_guess
    post_c = bkt_posterior(p_known, True, params)
    post_i = bkt_posterior(p_known, False, params)
    h_before = entropy(p_known)
    h_after = p_correct * entropy(post_c) + (1.0 - p_correct) * entropy(post_i)
    return h_before - h_after
