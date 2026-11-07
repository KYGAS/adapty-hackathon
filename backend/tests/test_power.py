import math

import pytest

from referee.stats.power import (
    mde_at_sample_size,
    power_at_sample_size,
    required_sample_size_per_arm,
    sample_size_per_arm_exact,
)


def test_textbook_sample_size():
    # 10% baseline, 20% relative lift, alpha 0.05, power 0.8 -> 3,841 per arm
    assert required_sample_size_per_arm(0.10, 0.20) == 3841


def test_sample_size_grows_with_power_and_shrinks_with_effect():
    assert required_sample_size_per_arm(0.10, 0.20, power=0.9) > required_sample_size_per_arm(0.10, 0.20)
    assert required_sample_size_per_arm(0.10, 0.50) < required_sample_size_per_arm(0.10, 0.20)
    assert required_sample_size_per_arm(0.10, -0.20) > 0


def test_exact_sample_size_is_unrounded():
    exact = sample_size_per_arm_exact(0.10, 0.12)
    assert 3840 < exact < 3841


@pytest.mark.parametrize("kwargs", [
    {"p_control": 0.0, "p_treatment": 0.1},
    {"p_control": 1.0, "p_treatment": 0.1},
    {"p_control": 0.1, "p_treatment": 0.0},
    {"p_control": 0.1, "p_treatment": 1.0},
    {"p_control": 0.1, "p_treatment": 0.2, "alpha": 0.0},
    {"p_control": 0.1, "p_treatment": 0.2, "alpha": 1.0},
    {"p_control": 0.1, "p_treatment": 0.2, "power": 0.0},
    {"p_control": 0.1, "p_treatment": 0.2, "power": 1.0},
    {"p_control": 0.1, "p_treatment": 0.1},
])
def test_exact_sample_size_validation(kwargs):
    with pytest.raises(ValueError):
        sample_size_per_arm_exact(**kwargs)


def test_required_sample_size_rejects_zero_mde():
    with pytest.raises(ValueError):
        required_sample_size_per_arm(0.1, 0.0)


def test_power_at_designed_sample_size_is_the_design_power():
    n = required_sample_size_per_arm(0.10, 0.20)
    assert power_at_sample_size(0.10, 0.12, n) == pytest.approx(0.80, abs=0.005)


def test_power_is_alpha_without_effect_and_one_with_huge_effect():
    assert power_at_sample_size(0.10, 0.1000001, 1000) == pytest.approx(0.05, abs=0.01)
    assert power_at_sample_size(0.10, 0.60, 1000) == pytest.approx(1.0, abs=1e-9)
    assert power_at_sample_size(0.60, 0.10, 1000) == pytest.approx(1.0, abs=1e-9)


def test_power_validation():
    with pytest.raises(ValueError):
        power_at_sample_size(0.1, 0.2, 0)
    with pytest.raises(ValueError):
        power_at_sample_size(0.1, 0.2, 100, alpha=1.0)


def test_mde_inverts_required_sample_size():
    mde = mde_at_sample_size(0.10, 3841)
    assert mde == pytest.approx(0.20, abs=1e-3)
    assert required_sample_size_per_arm(0.10, mde) <= 3842


def test_mde_is_infinite_when_unreachable():
    # Even a lift to a 99.9% conversion rate needs two viewers per arm.
    assert math.isinf(mde_at_sample_size(0.001, 1))
    assert mde_at_sample_size(0.001, 5) < 999.0


def test_mde_validation():
    with pytest.raises(ValueError):
        mde_at_sample_size(0.1, 0)
    with pytest.raises(ValueError):
        mde_at_sample_size(0.0, 100)
