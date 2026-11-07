import pytest

from referee.stats.proportions import (
    Interval,
    proportion,
    relative_lift,
    two_proportion_z_test,
    wilson_interval,
)


def test_proportion_basic_and_empty():
    assert proportion(35, 285) == pytest.approx(0.12280701754)
    assert proportion(0, 0) == 0.0


@pytest.mark.parametrize("x,n", [(-1, 10), (11, 10), (1, -1)])
def test_count_validation(x, n):
    with pytest.raises(ValueError):
        proportion(x, n)
    with pytest.raises(ValueError):
        wilson_interval(x, n)


def test_wilson_known_values():
    # 35 of 285: textbook Wilson 95% interval
    iv = wilson_interval(35, 285)
    assert iv.low == pytest.approx(0.0896, abs=2e-3)
    assert iv.high == pytest.approx(0.1664, abs=2e-3)
    assert wilson_interval(0, 0) == Interval(0.0, 1.0)


def test_wilson_bounds_are_clamped_and_ordered():
    zero = wilson_interval(0, 50)
    full = wilson_interval(50, 50)
    assert zero.low == 0.0 and zero.high > 0.0
    assert full.high == 1.0 and full.low < 1.0
    assert zero.low <= zero.high


def test_relative_lift():
    assert relative_lift(0.10, 0.12) == pytest.approx(0.2)
    assert relative_lift(0.0, 0.12) is None


def test_two_proportion_matches_textbook():
    # Control 20/200 vs treatment 35/200: pooled p 0.1375, se 0.03444, z 2.178, p 0.0294
    r = two_proportion_z_test(20, 200, 35, 200)
    assert r.p1 == pytest.approx(0.10)
    assert r.p2 == pytest.approx(0.175)
    assert r.difference == pytest.approx(0.075)
    assert r.relative_lift == pytest.approx(0.75)
    assert r.standard_error == pytest.approx(0.034437, abs=1e-5)
    assert r.z == pytest.approx(2.1779, abs=1e-3)
    assert r.p_value == pytest.approx(0.0294, abs=1e-3)


def test_two_proportion_onboarding_arms_are_significant():
    r = two_proportion_z_test(0, 254, 35, 285)
    assert r.p_value < 1e-6
    assert r.relative_lift is None


def test_two_proportion_no_events_gives_no_evidence():
    r = two_proportion_z_test(0, 40, 0, 37)
    assert r.z == 0.0
    assert r.p_value == 1.0
    assert r.standard_error == 0.0


def test_two_proportion_requires_viewers():
    with pytest.raises(ValueError):
        two_proportion_z_test(0, 0, 1, 10)
    with pytest.raises(ValueError):
        two_proportion_z_test(1, 10, 0, 0)
