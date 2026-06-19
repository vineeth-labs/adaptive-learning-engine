import pytest

from backend.services.learner.bkt import (
    bkt_posterior,
    bkt_update,
    bkt_update_graded,
    entropy,
    expected_information_gain,
)
from backend.services.learner.bkt_models import BKTParams, Grade


# ---------------------------------------------------------------------------
# Shared fixture
# ---------------------------------------------------------------------------

DEFAULT = BKTParams(p_transit=0.10, p_slip=0.10, p_guess=0.20, base_prior=0.30)


# ---------------------------------------------------------------------------
# bkt_posterior
# ---------------------------------------------------------------------------

class TestBktPosterior:
    def test_correct_answer_raises_belief(self):
        p = 0.5
        assert bkt_posterior(p, correct=True, params=DEFAULT) > p

    def test_incorrect_answer_lowers_belief(self):
        p = 0.5
        assert bkt_posterior(p, correct=False, params=DEFAULT) < p

    def test_correct_high_prior_stays_high(self):
        # Very confident learner slips occasionally, but posterior stays high
        p = 0.95
        post = bkt_posterior(p, correct=True, params=DEFAULT)
        assert post > 0.9

    def test_incorrect_low_prior_stays_low(self):
        p = 0.05
        post = bkt_posterior(p, correct=False, params=DEFAULT)
        assert post < 0.1

    def test_posterior_bounds_correct(self):
        for p in (0.01, 0.3, 0.5, 0.7, 0.99):
            post = bkt_posterior(p, correct=True, params=DEFAULT)
            assert 0.0 < post < 1.0

    def test_posterior_bounds_incorrect(self):
        for p in (0.01, 0.3, 0.5, 0.7, 0.99):
            post = bkt_posterior(p, correct=False, params=DEFAULT)
            assert 0.0 < post < 1.0

    def test_correct_exact_value(self):
        # p=0.5, s=0.1, g=0.2 → num=0.45, den=0.55 → 9/11
        post = bkt_posterior(0.5, correct=True, params=DEFAULT)
        assert post == pytest.approx(9 / 11)

    def test_incorrect_exact_value(self):
        # p=0.5, s=0.1, g=0.2 → num=0.05, den=0.45 → 1/9
        post = bkt_posterior(0.5, correct=False, params=DEFAULT)
        assert post == pytest.approx(1 / 9)

    def test_correct_monotone_in_prior(self):
        # Higher prior → higher posterior for a correct answer
        posts = [bkt_posterior(p, correct=True, params=DEFAULT) for p in (0.1, 0.3, 0.5, 0.7, 0.9)]
        assert posts == sorted(posts)

    def test_incorrect_monotone_in_prior(self):
        # Higher prior → higher posterior for an incorrect answer too
        posts = [bkt_posterior(p, correct=False, params=DEFAULT) for p in (0.1, 0.3, 0.5, 0.7, 0.9)]
        assert posts == sorted(posts)


# ---------------------------------------------------------------------------
# bkt_update
# ---------------------------------------------------------------------------

class TestBktUpdate:
    def test_update_exceeds_posterior(self):
        # Learning transition means update ≥ raw posterior
        p = 0.5
        post = bkt_posterior(p, correct=True, params=DEFAULT)
        updated = bkt_update(p, correct=True, params=DEFAULT)
        assert updated >= post

    def test_update_exceeds_posterior_incorrect(self):
        p = 0.5
        post = bkt_posterior(p, correct=False, params=DEFAULT)
        updated = bkt_update(p, correct=False, params=DEFAULT)
        assert updated >= post

    def test_correct_answer_exact(self):
        # post=9/11, update = 9/11 + 2/11 * 0.1 = 9.2/11
        updated = bkt_update(0.5, correct=True, params=DEFAULT)
        assert updated == pytest.approx(9.2 / 11)

    def test_incorrect_answer_exact(self):
        # post=1/9, update = 1/9 + 8/9 * 0.1 = 1.8/9 = 0.2
        updated = bkt_update(0.5, correct=False, params=DEFAULT)
        assert updated == pytest.approx(0.2)

    def test_repeated_correct_monotonic(self):
        p = 0.3
        history = [p]
        for _ in range(5):
            p = bkt_update(p, correct=True, params=DEFAULT)
            history.append(p)
        assert history == sorted(history)

    def test_repeated_incorrect_then_correct_recovers(self):
        p = 0.5
        for _ in range(3):
            p = bkt_update(p, correct=False, params=DEFAULT)
        p_after_wrong = p
        p = bkt_update(p, correct=True, params=DEFAULT)
        assert p > p_after_wrong

    def test_result_stays_below_one(self):
        p = 0.99
        updated = bkt_update(p, correct=True, params=DEFAULT)
        assert updated < 1.0

    def test_result_stays_above_zero(self):
        p = 0.01
        updated = bkt_update(p, correct=False, params=DEFAULT)
        assert updated > 0.0


# ---------------------------------------------------------------------------
# bkt_update_graded
# ---------------------------------------------------------------------------

class TestBktUpdateGraded:
    def test_correct_matches_binary_true(self):
        p = 0.4
        assert bkt_update_graded(p, Grade.CORRECT, DEFAULT) == pytest.approx(
            bkt_update(p, True, DEFAULT)
        )

    def test_incorrect_matches_binary_false(self):
        p = 0.4
        assert bkt_update_graded(p, Grade.INCORRECT, DEFAULT) == pytest.approx(
            bkt_update(p, False, DEFAULT)
        )

    def test_partial_is_between_correct_and_incorrect(self):
        p = 0.5
        wrong = bkt_update_graded(p, Grade.INCORRECT, DEFAULT)
        partial = bkt_update_graded(p, Grade.PARTIAL, DEFAULT)
        right = bkt_update_graded(p, Grade.CORRECT, DEFAULT)
        assert wrong < partial < right

    def test_partial_exact_value(self):
        # blended = 0.5*(9/11) + 0.5*(1/9) = (4.5/11 + 0.5/9)
        # = (40.5 + 5.5) / 99 = 46/99
        # update = 46/99 + (53/99)*0.1 = 51.3/99
        p = 0.5
        result = bkt_update_graded(p, Grade.PARTIAL, DEFAULT)
        assert result == pytest.approx(51.3 / 99)

    def test_all_grades_apply_learning_transition(self):
        # update always > raw blended posterior because P(T) adds probability mass
        p = 0.5
        for grade in Grade:
            w = grade.value
            post_c = bkt_posterior(p, True, DEFAULT)
            post_i = bkt_posterior(p, False, DEFAULT)
            blended_post = w * post_c + (1.0 - w) * post_i
            updated = bkt_update_graded(p, grade, DEFAULT)
            assert updated >= blended_post

    def test_partial_closer_to_correct_than_incorrect(self):
        # PARTIAL weight=0.5, so distance to CORRECT == distance to INCORRECT
        p = 0.5
        wrong = bkt_update_graded(p, Grade.INCORRECT, DEFAULT)
        partial = bkt_update_graded(p, Grade.PARTIAL, DEFAULT)
        right = bkt_update_graded(p, Grade.CORRECT, DEFAULT)
        assert abs(partial - right) == pytest.approx(abs(partial - wrong))


# ---------------------------------------------------------------------------
# entropy
# ---------------------------------------------------------------------------

class TestEntropy:
    def test_zero_at_zero(self):
        assert entropy(0.0) == 0.0

    def test_zero_at_one(self):
        assert entropy(1.0) == 0.0

    def test_max_at_half(self):
        assert entropy(0.5) == pytest.approx(1.0)

    def test_symmetric(self):
        for p in (0.1, 0.2, 0.3, 0.4):
            assert entropy(p) == pytest.approx(entropy(1.0 - p))

    def test_strictly_positive_in_interior(self):
        for p in (0.01, 0.25, 0.5, 0.75, 0.99):
            assert entropy(p) > 0.0

    def test_monotone_increasing_to_half(self):
        values = [entropy(p) for p in (0.1, 0.2, 0.3, 0.4, 0.5)]
        assert values == sorted(values)

    def test_monotone_decreasing_from_half(self):
        values = [entropy(p) for p in (0.5, 0.6, 0.7, 0.8, 0.9)]
        assert values == sorted(values, reverse=True)

    def test_bounded_by_one(self):
        for p in (0.0, 0.1, 0.5, 0.9, 1.0):
            assert 0.0 <= entropy(p) <= 1.0


# ---------------------------------------------------------------------------
# expected_information_gain
# ---------------------------------------------------------------------------

class TestExpectedInformationGain:
    def test_positive_in_interior(self):
        for p in (0.1, 0.3, 0.5, 0.7, 0.9):
            assert expected_information_gain(p, DEFAULT) > 0.0

    def test_lower_near_zero_than_at_half(self):
        eig_uncertain = expected_information_gain(0.5, DEFAULT)
        eig_near_zero = expected_information_gain(0.02, DEFAULT)
        assert eig_near_zero < eig_uncertain

    def test_lower_near_one_than_at_half(self):
        eig_uncertain = expected_information_gain(0.5, DEFAULT)
        eig_near_one = expected_information_gain(0.98, DEFAULT)
        assert eig_near_one < eig_uncertain

    def test_bounded_by_prior_entropy(self):
        # EIG can't exceed entropy before the question
        for p in (0.1, 0.3, 0.5, 0.7, 0.9):
            assert expected_information_gain(p, DEFAULT) <= entropy(p) + 1e-9

    def test_eig_at_half_exact(self):
        # Compute reference manually:
        # p_correct = 0.5*0.9 + 0.5*0.2 = 0.55
        # post_c = 9/11, post_i = 1/9
        # h_before = 1.0
        # h_after = 0.55*entropy(9/11) + 0.45*entropy(1/9)
        from math import log2
        p_correct = 0.55
        post_c = 9 / 11
        post_i = 1 / 9
        h_after = p_correct * entropy(post_c) + (1 - p_correct) * entropy(post_i)
        expected = 1.0 - h_after
        assert expected_information_gain(0.5, DEFAULT) == pytest.approx(expected)

    def test_symmetric_around_half_with_no_slip_guess(self):
        # With equal slip and guess the model is symmetric around 0.5
        symmetric_params = BKTParams(p_transit=0.10, p_slip=0.15, p_guess=0.15, base_prior=0.30)
        eig_lo = expected_information_gain(0.3, symmetric_params)
        eig_hi = expected_information_gain(0.7, symmetric_params)
        assert eig_lo == pytest.approx(eig_hi)
