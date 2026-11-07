import math

import pytest

from referee.stats.normal import norm_cdf, norm_ppf, norm_sf, two_sided_p_value, z_for_confidence


def test_cdf_known_points():
    assert norm_cdf(0.0) == pytest.approx(0.5)
    assert norm_cdf(1.959963984540054) == pytest.approx(0.975, abs=1e-9)
    assert norm_cdf(-1.959963984540054) == pytest.approx(0.025, abs=1e-9)
    assert norm_cdf(8.0) == pytest.approx(1.0)


def test_sf_is_complement_and_precise_in_tail():
    assert norm_sf(1.0) == pytest.approx(1.0 - norm_cdf(1.0))
    assert norm_sf(6.0) == pytest.approx(9.865876450377e-10, rel=1e-6)


def test_two_sided_p_value():
    assert two_sided_p_value(0.0) == pytest.approx(1.0)
    assert two_sided_p_value(1.959963984540054) == pytest.approx(0.05, abs=1e-9)
    assert two_sided_p_value(-2.5758293035489) == pytest.approx(0.01, abs=1e-9)


@pytest.mark.parametrize("p", [1e-9, 0.001, 0.02, 0.025, 0.1, 0.5, 0.9, 0.975, 0.99, 1 - 1e-9])
def test_ppf_inverts_cdf(p):
    assert norm_cdf(norm_ppf(p)) == pytest.approx(p, rel=1e-9, abs=1e-12)


def test_ppf_known_values():
    assert norm_ppf(0.975) == pytest.approx(1.959963984540054, abs=1e-9)
    assert norm_ppf(0.8) == pytest.approx(0.8416212335729143, abs=1e-9)
    assert norm_ppf(0.5) == pytest.approx(0.0, abs=1e-12)


@pytest.mark.parametrize("p", [0.0, 1.0, -0.1, 1.5])
def test_ppf_rejects_out_of_range(p):
    with pytest.raises(ValueError):
        norm_ppf(p)


def test_z_for_confidence():
    assert z_for_confidence(0.95) == pytest.approx(1.959963984540054, abs=1e-9)
    assert z_for_confidence(0.99) == pytest.approx(2.5758293035489, abs=1e-9)
    assert math.isclose(z_for_confidence(0.8), 1.2815515655446004, abs_tol=1e-9)


@pytest.mark.parametrize("c", [0.0, 1.0, 2.0])
def test_z_for_confidence_rejects_out_of_range(c):
    with pytest.raises(ValueError):
        z_for_confidence(c)
