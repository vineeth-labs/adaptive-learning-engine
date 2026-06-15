"""Beta-Bernoulli mastery estimator: the math, with no DB or framework coupling.

A learner's belief about one concept is a ``Beta(alpha, beta)`` posterior. ``alpha``
accumulates (fractional) evidence *for* mastery and ``beta`` evidence *against*; the
posterior mean ``alpha / (alpha + beta)`` is the headline mastery number in [0, 1].
This is the principled form of the "average score + evidence count" model — it carries
a prior and an uncertainty for free, and a continuous answer score in [0, 1] splits a
single observation between the two counts instead of forcing a 0/1 outcome.

Per graded answer the caller runs: decay (forgetting) -> apply_score (one per answer)
-> read the new mean. Everything here is closed-form, deterministic, and per-user — no
training corpus, no gradient descent. ``mastery.py`` composes these helpers with the
persisted ``LearnerState`` and the prerequisite graph; ``docs/mastery-update.md`` has
the full write-up.
"""

from __future__ import annotations

from dataclasses import dataclass


def _clamp01(v: float) -> float:
    return max(0.0, min(1.0, v))


@dataclass(frozen=True)
class BetaState:
    """A Beta(alpha, beta) belief. Persisted as two floats per (user, concept)."""

    alpha: float
    beta: float

    def mastery(self) -> float:
        """Posterior mean — the headline mastery number in [0, 1]."""
        return self.alpha / (self.alpha + self.beta)

    def concentration(self) -> float:
        """Total Beta concentration; grows as evidence accumulates."""
        return self.alpha + self.beta

    def variance(self) -> float:
        """Variance of the Beta posterior; shrinks as concentration grows."""
        c = self.concentration()
        return (self.alpha * self.beta) / (c * c * (c + 1.0))


def apply_score(state: BetaState, score: float, weight: float = 1.0) -> BetaState:
    """Fold one graded answer into the belief.

    ``score`` is the answer's quality in [0, 1]; ``weight`` is its evidence mass
    (1.0 = a normal answer). The score splits ``weight`` between the two counts, so
    a 0.7 adds 0.7*weight of support and 0.3*weight of doubt.
    """
    score = _clamp01(score)
    return BetaState(
        alpha=state.alpha + weight * score,
        beta=state.beta + weight * (1.0 - score),
    )


def decay_toward_prior(
    state: BetaState,
    prior: BetaState,
    elapsed_days: float,
    half_life_days: float,
) -> BetaState:
    """Forgetting: pull alpha/beta back toward the prior as time passes.

    ``gamma = 0.5 ** (elapsed_days / half_life_days)`` — accumulated evidence halves
    every ``half_life_days``. Decaying toward the prior (not toward zero) preserves
    the cold-start belief and keeps the mean well-defined; it both drifts the estimate
    back and shrinks confidence, which is what forgetting actually looks like.
    """
    if elapsed_days <= 0.0 or half_life_days <= 0.0:
        return state
    gamma = 0.5 ** (elapsed_days / half_life_days)
    return BetaState(
        alpha=prior.alpha + (state.alpha - prior.alpha) * gamma,
        beta=prior.beta + (state.beta - prior.beta) * gamma,
    )


def prior_from_mean(mean: float, concentration: float) -> BetaState:
    """Build a Beta prior with the given mean and total concentration.

    Used for the graph-aware cold start: ``mean`` comes from the prerequisite-gated
    prior so advanced concepts start low, while ``concentration`` sets how much that
    belief resists the first few answers.
    """
    mean = _clamp01(mean)
    return BetaState(alpha=mean * concentration, beta=(1.0 - mean) * concentration)


def lower_bound(state: BetaState, z: float) -> float:
    """One-sided credible lower bound on mastery (mean - z * std), clamped to [0, 1].

    Low value = uncertain; the natural signal for picking what to reassess.
    """
    return _clamp01(state.mastery() - z * state.variance() ** 0.5)


def evidence_mass(state: BetaState, prior: BetaState) -> float:
    """Effective number of observations seen (concentration above the prior)."""
    return max(0.0, state.concentration() - prior.concentration())


def is_mastered(
    state: BetaState,
    prior: BetaState,
    threshold: float,
    min_evidence_mass: float,
) -> bool:
    """Verdict: best estimate clears the bar AND enough evidence backs it.

    Gating on the mean (not the lower bound) keeps it responsive; the evidence floor
    guards against a single lucky answer. Swap ``state.mastery()`` for
    ``lower_bound(state, z)`` for a stricter, lucky-streak-proof gate.
    """
    return state.mastery() >= threshold and evidence_mass(state, prior) >= min_evidence_mass
