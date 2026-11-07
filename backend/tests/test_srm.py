import pytest

from referee.stats.srm import sample_ratio_mismatch


def test_balanced_split_is_fine():
    r = sample_ratio_mismatch([285, 254], [50, 50])
    assert r.total == 539
    assert not r.mismatch
    assert r.p_value > 0.1
    assert r.observed_share == pytest.approx(285 / 539)


def test_broken_split_is_flagged():
    r = sample_ratio_mismatch([900, 100], [50, 50])
    assert r.mismatch
    assert r.p_value < 1e-6
    assert abs(r.z) > 20


def test_weights_other_than_even_and_three_arms():
    r = sample_ratio_mismatch([700, 200, 100], [70, 20, 10])
    assert not r.mismatch
    r2 = sample_ratio_mismatch([500, 400, 100], [70, 20, 10])
    assert r2.mismatch
    assert r2.worst_arm in (0, 1)


def test_no_traffic():
    r = sample_ratio_mismatch([0, 0], [50, 50])
    assert r.p_value == 1.0 and not r.mismatch and r.total == 0


@pytest.mark.parametrize("obs,w", [([1], [1, 2]), ([], []), ([-1, 2], [1, 1]), ([1, 2], [0, 1])])
def test_validation(obs, w):
    with pytest.raises(ValueError):
        sample_ratio_mismatch(obs, w)
