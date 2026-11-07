import pytest

from referee.stats.correction import bonferroni, correct, holm


def test_bonferroni_scales_by_family_size():
    out = bonferroni([0.01, 0.04, 0.20])
    assert [round(t.adjusted_p, 6) for t in out] == [0.03, 0.12, 0.6]
    assert [t.rejected for t in out] == [True, False, False]
    assert out[0].index == 0 and out[0].p_value == 0.01


def test_bonferroni_caps_at_one():
    assert bonferroni([0.5, 0.9])[1].adjusted_p == 1.0


def test_holm_is_at_least_as_powerful_as_bonferroni():
    p = [0.01, 0.02, 0.03]
    h = holm(p)
    b = bonferroni(p)
    assert [t.adjusted_p for t in h] == pytest.approx([0.03, 0.04, 0.04])
    assert all(t.rejected for t in h)
    assert [t.rejected for t in b] == [True, False, False]


def test_holm_preserves_input_order_and_monotonicity():
    out = holm([0.04, 0.001, 0.03])
    assert [t.index for t in out] == [0, 1, 2]
    assert out[1].adjusted_p == pytest.approx(0.003)
    assert out[2].adjusted_p == pytest.approx(0.06)
    assert out[0].adjusted_p == pytest.approx(0.06)  # never below a smaller p's adjusted value
    assert [t.rejected for t in out] == [False, True, False]


def test_single_test_is_unchanged_and_empty_is_empty():
    assert holm([0.03])[0].adjusted_p == 0.03
    assert holm([]) == []
    assert bonferroni([]) == []


def test_correct_dispatch():
    assert correct([0.01], "holm")[0].rejected
    assert correct([0.01], "bonferroni")[0].rejected
    with pytest.raises(ValueError):
        correct([0.01], "fdr")


@pytest.mark.parametrize("p,alpha", [([1.5], 0.05), ([-0.1], 0.05), ([0.5], 0.0), ([0.5], 1.0)])
def test_validation(p, alpha):
    with pytest.raises(ValueError):
        holm(p, alpha)
