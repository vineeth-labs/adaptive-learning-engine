import pytest

from backend.services.learner.bkt_models import BKTParams, GapReport, Grade


# ---------------------------------------------------------------------------
# BKTParams validation
# ---------------------------------------------------------------------------

class TestBKTParams:
    def test_defaults_are_valid(self):
        params = BKTParams()
        assert 0.0 < params.p_transit < 1.0
        assert 0.0 < params.p_slip < 1.0
        assert 0.0 < params.p_guess < 1.0
        assert 0.0 < params.base_prior < 1.0

    def test_custom_valid_params(self):
        params = BKTParams(p_transit=0.2, p_slip=0.05, p_guess=0.15, base_prior=0.4)
        assert params.p_transit == 0.2
        assert params.p_slip == 0.05

    def test_p_transit_zero_raises(self):
        with pytest.raises(ValueError, match="p_transit"):
            BKTParams(p_transit=0.0)

    def test_p_slip_zero_raises(self):
        with pytest.raises(ValueError, match="p_slip"):
            BKTParams(p_slip=0.0)

    def test_p_guess_zero_raises(self):
        with pytest.raises(ValueError, match="p_guess"):
            BKTParams(p_guess=0.0)

    def test_base_prior_zero_raises(self):
        with pytest.raises(ValueError, match="base_prior"):
            BKTParams(base_prior=0.0)

    def test_p_transit_one_raises(self):
        with pytest.raises(ValueError, match="p_transit"):
            BKTParams(p_transit=1.0)

    def test_p_slip_one_raises(self):
        with pytest.raises(ValueError, match="p_slip"):
            BKTParams(p_slip=1.0)

    def test_p_guess_one_raises(self):
        with pytest.raises(ValueError, match="p_guess"):
            BKTParams(p_guess=1.0)

    def test_base_prior_one_raises(self):
        with pytest.raises(ValueError, match="base_prior"):
            BKTParams(base_prior=1.0)

    def test_identifiability_slip_plus_guess_at_one_raises(self):
        with pytest.raises(ValueError, match=r"p_slip \+ p_guess"):
            BKTParams(p_slip=0.5, p_guess=0.5)

    def test_identifiability_slip_plus_guess_above_one_raises(self):
        with pytest.raises(ValueError, match=r"p_slip \+ p_guess"):
            BKTParams(p_slip=0.6, p_guess=0.5)

    def test_identifiability_just_below_threshold_valid(self):
        # p_slip + p_guess = 0.99 < 1.0 → valid
        params = BKTParams(p_slip=0.5, p_guess=0.49)
        assert params.p_slip + params.p_guess < 1.0

    def test_params_are_frozen(self):
        params = BKTParams()
        with pytest.raises((TypeError, AttributeError)):
            params.p_transit = 0.5  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Grade enum
# ---------------------------------------------------------------------------

class TestGrade:
    def test_correct_value(self):
        assert Grade.CORRECT.value == 1.0

    def test_partial_value(self):
        assert Grade.PARTIAL.value == 0.5

    def test_incorrect_value(self):
        assert Grade.INCORRECT.value == 0.0

    def test_three_members(self):
        assert len(Grade) == 3

    def test_values_ordered(self):
        assert Grade.INCORRECT.value < Grade.PARTIAL.value < Grade.CORRECT.value


# ---------------------------------------------------------------------------
# GapReport dataclass
# ---------------------------------------------------------------------------

class TestGapReport:
    def test_defaults_to_empty_lists(self):
        report = GapReport()
        assert report.mastered == []
        assert report.shaky == []
        assert report.not_learned == []

    def test_recommended_next_defaults_to_none(self):
        assert GapReport().recommended_next is None

    def test_lists_are_independent_across_instances(self):
        # dataclass field(default_factory=list) must give each instance its own list
        r1, r2 = GapReport(), GapReport()
        r1.mastered.append("A")
        assert r2.mastered == []

    def test_can_hold_data(self):
        report = GapReport(
            mastered=["A"],
            shaky=["B"],
            not_learned=["C"],
            recommended_next="B",
        )
        assert report.mastered == ["A"]
        assert report.shaky == ["B"]
        assert report.not_learned == ["C"]
        assert report.recommended_next == "B"
