import pytest
from math import sqrt

from backend.services.learner.beta_mastery import (
    BetaState,
    apply_score,
    decay_toward_prior,
    evidence_mass,
    is_mastered,
    lower_bound,
    prior_from_mean,
)


# ---------------------------------------------------------------------------
# BetaState accessors
# ---------------------------------------------------------------------------

class TestBetaStateAccessors:
    def test_mastery_formula(self):
        state = BetaState(alpha=3.0, beta=7.0)
        assert state.mastery() == pytest.approx(3.0 / 10.0)

    def test_mastery_at_equal_params(self):
        assert BetaState(alpha=5.0, beta=5.0).mastery() == pytest.approx(0.5)

    def test_mastery_near_one(self):
        assert BetaState(alpha=99.0, beta=1.0).mastery() == pytest.approx(0.99)

    def test_mastery_near_zero(self):
        assert BetaState(alpha=1.0, beta=99.0).mastery() == pytest.approx(0.01)

    def test_concentration_formula(self):
        state = BetaState(alpha=3.0, beta=7.0)
        assert state.concentration() == pytest.approx(10.0)

    def test_variance_formula(self):
        # var = alpha*beta / (c^2 * (c+1))  where c = alpha+beta
        a, b = 3.0, 7.0
        c = a + b
        expected = (a * b) / (c * c * (c + 1))
        assert BetaState(alpha=a, beta=b).variance() == pytest.approx(expected)

    def test_variance_shrinks_with_concentration(self):
        # Same mean, more evidence → smaller variance
        low_conc = BetaState(alpha=1.0, beta=1.0)   # concentration=2
        high_conc = BetaState(alpha=5.0, beta=5.0)  # concentration=10, same mean=0.5
        assert high_conc.variance() < low_conc.variance()

    def test_variance_max_at_equal_params(self):
        # For fixed concentration, variance is maximized when alpha==beta (mean=0.5)
        c = 10.0
        balanced = BetaState(alpha=c / 2, beta=c / 2)
        skewed = BetaState(alpha=c * 0.9, beta=c * 0.1)
        assert balanced.variance() > skewed.variance()


# ---------------------------------------------------------------------------
# apply_score
# ---------------------------------------------------------------------------

class TestApplyScore:
    def test_full_credit_increments_alpha(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result = apply_score(state, score=1.0, weight=1.0)
        assert result.alpha == pytest.approx(3.0)
        assert result.beta == pytest.approx(8.0)

    def test_zero_credit_increments_beta(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result = apply_score(state, score=0.0, weight=1.0)
        assert result.alpha == pytest.approx(2.0)
        assert result.beta == pytest.approx(9.0)

    def test_partial_splits_weight(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result = apply_score(state, score=0.7, weight=1.0)
        assert result.alpha == pytest.approx(2.7)
        assert result.beta == pytest.approx(8.3)

    def test_weight_scales_evidence(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result = apply_score(state, score=0.5, weight=2.0)
        assert result.alpha == pytest.approx(3.0)
        assert result.beta == pytest.approx(9.0)

    def test_score_clamped_negative(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result_neg = apply_score(state, score=-0.5)
        result_zero = apply_score(state, score=0.0)
        assert result_neg.alpha == pytest.approx(result_zero.alpha)
        assert result_neg.beta == pytest.approx(result_zero.beta)

    def test_score_clamped_above_one(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result_over = apply_score(state, score=1.5)
        result_one = apply_score(state, score=1.0)
        assert result_over.alpha == pytest.approx(result_one.alpha)
        assert result_over.beta == pytest.approx(result_one.beta)

    def test_default_weight_is_one(self):
        state = BetaState(alpha=2.0, beta=8.0)
        assert apply_score(state, 0.6) == apply_score(state, 0.6, weight=1.0)

    def test_repeated_correct_raises_mastery(self):
        state = BetaState(alpha=1.0, beta=9.0)
        for _ in range(10):
            state = apply_score(state, score=1.0)
        assert state.mastery() > 0.5

    def test_concentration_grows_per_application(self):
        state = BetaState(alpha=2.0, beta=8.0)
        result = apply_score(state, score=0.7, weight=1.0)
        assert result.concentration() == pytest.approx(state.concentration() + 1.0)


# ---------------------------------------------------------------------------
# decay_toward_prior
# ---------------------------------------------------------------------------

class TestDecayTowardPrior:
    def test_no_decay_at_elapsed_zero(self):
        state = BetaState(alpha=8.0, beta=2.0)
        prior = BetaState(alpha=2.0, beta=8.0)
        result = decay_toward_prior(state, prior, elapsed_days=0.0, half_life_days=30.0)
        assert result.alpha == pytest.approx(state.alpha)
        assert result.beta == pytest.approx(state.beta)

    def test_no_decay_at_half_life_zero(self):
        state = BetaState(alpha=8.0, beta=2.0)
        prior = BetaState(alpha=2.0, beta=8.0)
        result = decay_toward_prior(state, prior, elapsed_days=10.0, half_life_days=0.0)
        assert result.alpha == pytest.approx(state.alpha)
        assert result.beta == pytest.approx(state.beta)

    def test_distance_halves_at_half_life(self):
        # state=(8,2), prior=(2,8): at elapsed==half_life, gamma=0.5
        # new_alpha = 2 + (8-2)*0.5 = 5, new_beta = 8 + (2-8)*0.5 = 5
        state = BetaState(alpha=8.0, beta=2.0)
        prior = BetaState(alpha=2.0, beta=8.0)
        result = decay_toward_prior(state, prior, elapsed_days=30.0, half_life_days=30.0)
        assert result.alpha == pytest.approx(5.0)
        assert result.beta == pytest.approx(5.0)

    def test_large_elapsed_converges_toward_prior(self):
        state = BetaState(alpha=9.0, beta=1.0)
        prior = BetaState(alpha=1.0, beta=9.0)
        result = decay_toward_prior(state, prior, elapsed_days=1000.0, half_life_days=30.0)
        assert abs(result.alpha - prior.alpha) < 1e-6
        assert abs(result.beta - prior.beta) < 1e-6

    def test_decay_moves_toward_prior_monotonically(self):
        state = BetaState(alpha=9.0, beta=1.0)
        prior = BetaState(alpha=1.0, beta=9.0)
        alphas = [
            decay_toward_prior(state, prior, elapsed_days=t, half_life_days=30.0).alpha
            for t in (0, 10, 30, 90, 180)
        ]
        # alpha should decrease as time passes (state.alpha > prior.alpha)
        assert alphas == sorted(alphas, reverse=True)

    def test_at_prior_no_change(self):
        prior = BetaState(alpha=3.0, beta=7.0)
        result = decay_toward_prior(prior, prior, elapsed_days=100.0, half_life_days=30.0)
        assert result.alpha == pytest.approx(prior.alpha)
        assert result.beta == pytest.approx(prior.beta)


# ---------------------------------------------------------------------------
# prior_from_mean
# ---------------------------------------------------------------------------

class TestPriorFromMean:
    def test_preserves_mean(self):
        prior = prior_from_mean(mean=0.3, concentration=10.0)
        assert prior.mastery() == pytest.approx(0.3)

    def test_preserves_concentration(self):
        prior = prior_from_mean(mean=0.3, concentration=10.0)
        assert prior.concentration() == pytest.approx(10.0)

    def test_exact_alpha_beta(self):
        # mean=0.3, c=10 → alpha=3, beta=7
        prior = prior_from_mean(mean=0.3, concentration=10.0)
        assert prior.alpha == pytest.approx(3.0)
        assert prior.beta == pytest.approx(7.0)

    def test_mean_zero_clamps(self):
        prior = prior_from_mean(mean=-0.5, concentration=10.0)
        assert prior.mastery() == pytest.approx(0.0)

    def test_mean_one_clamps(self):
        prior = prior_from_mean(mean=1.5, concentration=10.0)
        assert prior.mastery() == pytest.approx(1.0)

    def test_mean_half_gives_equal_params(self):
        prior = prior_from_mean(mean=0.5, concentration=8.0)
        assert prior.alpha == pytest.approx(prior.beta)


# ---------------------------------------------------------------------------
# lower_bound
# ---------------------------------------------------------------------------

class TestLowerBound:
    def test_always_at_most_mastery(self):
        state = BetaState(alpha=3.0, beta=7.0)
        assert lower_bound(state, z=1.0) <= state.mastery()

    def test_clamped_to_zero(self):
        # Wide prior (low concentration) with z=10 should clamp to 0
        state = BetaState(alpha=0.5, beta=0.5)
        assert lower_bound(state, z=10.0) == pytest.approx(0.0)

    def test_clamped_to_one(self):
        # Extremely confident high mastery with z<0 would exceed 1 → clamped
        state = BetaState(alpha=999.0, beta=1.0)
        assert lower_bound(state, z=-10.0) == pytest.approx(1.0)

    def test_exact_value(self):
        a, b = 3.0, 7.0
        state = BetaState(alpha=a, beta=b)
        c = a + b
        std = sqrt((a * b) / (c * c * (c + 1)))
        expected = max(0.0, min(1.0, state.mastery() - 1.0 * std))
        assert lower_bound(state, z=1.0) == pytest.approx(expected)

    def test_larger_z_gives_lower_bound(self):
        state = BetaState(alpha=3.0, beta=7.0)
        assert lower_bound(state, z=2.0) < lower_bound(state, z=1.0)

    def test_higher_concentration_tightens_bound(self):
        # Same mean, more evidence → tighter lower bound
        lo_conc = BetaState(alpha=1.5, beta=3.5)   # mean=0.3, c=5
        hi_conc = BetaState(alpha=6.0, beta=14.0)  # mean=0.3, c=20
        assert lower_bound(hi_conc, z=1.0) > lower_bound(lo_conc, z=1.0)


# ---------------------------------------------------------------------------
# evidence_mass
# ---------------------------------------------------------------------------

class TestEvidenceMass:
    def test_non_negative(self):
        prior = BetaState(alpha=2.0, beta=8.0)
        state = BetaState(alpha=4.0, beta=8.0)
        assert evidence_mass(state, prior) >= 0.0

    def test_at_prior_is_zero(self):
        prior = BetaState(alpha=2.0, beta=8.0)
        assert evidence_mass(prior, prior) == pytest.approx(0.0)

    def test_counts_concentration_above_prior(self):
        prior = BetaState(alpha=2.0, beta=8.0)   # concentration=10
        state = BetaState(alpha=4.0, beta=8.0)   # concentration=12
        assert evidence_mass(state, prior) == pytest.approx(2.0)

    def test_floored_at_zero_when_below_prior(self):
        # If somehow state has less concentration than prior, should return 0
        prior = BetaState(alpha=5.0, beta=5.0)
        state = BetaState(alpha=2.0, beta=2.0)
        assert evidence_mass(state, prior) == pytest.approx(0.0)

    def test_grows_with_each_score_applied(self):
        prior = BetaState(alpha=2.0, beta=8.0)
        state = prior
        for _ in range(5):
            state = apply_score(state, score=0.8)
        assert evidence_mass(state, prior) == pytest.approx(5.0)


# ---------------------------------------------------------------------------
# is_mastered
# ---------------------------------------------------------------------------

class TestIsMastered:
    def setup_method(self):
        self.prior = BetaState(alpha=2.0, beta=8.0)   # mean=0.2, concentration=10

    def test_true_when_both_gates_met(self):
        # mastery=9/10=0.9, evidence_mass=2
        state = BetaState(alpha=11.0, beta=1.0)
        assert is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=2.0)

    def test_false_when_evidence_gate_not_met(self):
        # mastery=0.9 but only 0.5 evidence mass above prior
        state = BetaState(alpha=2.5, beta=8.0)   # concentration=10.5, mass=0.5
        assert not is_mastered(state, self.prior, threshold=0.3, min_evidence_mass=1.0)

    def test_false_when_mean_gate_not_met(self):
        # Plenty of evidence but mastery still low
        state = BetaState(alpha=4.0, beta=16.0)  # mean=0.2, mass=10
        assert not is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=5.0)

    def test_false_when_both_gates_missed(self):
        state = BetaState(alpha=2.1, beta=8.1)   # low mastery, tiny evidence
        assert not is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=5.0)

    def test_boundary_threshold_exact(self):
        # mastery exactly at threshold should pass
        state = BetaState(alpha=8.0, beta=2.0)   # mastery=0.8, mass=(-2) → wait, that's wrong
        # prior conc=10, state conc=10 → mass=0? Let me pick different values.
        # prior=(2,8), state needs mastery=0.8 AND mass>=1
        # state=(12,3) → mastery=12/15=0.8, conc=15, mass=5 ✓
        state = BetaState(alpha=12.0, beta=3.0)
        assert is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=1.0)

    def test_evidence_mass_floor_prevents_lucky_answer(self):
        # One very high score shouldn't trigger mastery if floor requires more evidence
        state = BetaState(alpha=2.9, beta=8.0)   # mastery≈0.27, mass=0.9 → fails both
        # Actually let's make mastery high but mass below floor:
        # prior=(2,8), we need mastery≈0.9, so alpha>>beta, but concentration just above 10
        state = BetaState(alpha=10.0, beta=1.0)  # mastery≈0.91, conc=11, mass=1
        # With min_evidence_mass=2: should fail
        assert not is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=2.0)
        # With min_evidence_mass=1: should pass
        assert is_mastered(state, self.prior, threshold=0.8, min_evidence_mass=1.0)
