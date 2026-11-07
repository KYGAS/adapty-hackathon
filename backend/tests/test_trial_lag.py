from datetime import datetime, timedelta, timezone

import pytest

from referee.stats.trial_lag import (
    PendingRevenue,
    RateEstimate,
    leader_could_flip,
    matured_count,
    matures_at,
    maturation_fraction,
    pending_count,
    project_pending_revenue,
    trial_to_paid_estimate,
)

NOW = datetime(2026, 11, 7, 12, 0, tzinfo=timezone.utc)


def test_maturation_fraction_curve():
    assert maturation_fraction(0.0, 7) == 0.0
    assert maturation_fraction(-1.0, 7) == 0.0
    assert maturation_fraction(3.5, 7) == pytest.approx(0.5)
    assert maturation_fraction(10.0, 7) == 1.0
    assert maturation_fraction(0.0, 0) == 1.0


def test_matures_at_adds_trial_and_grace():
    assert matures_at(NOW, 7, 2) == NOW + timedelta(days=9)
    assert matures_at(NOW, 3) == NOW + timedelta(days=3)
    with pytest.raises(ValueError):
        matures_at(NOW, -1)


def test_matured_and_pending_counts():
    assert matured_count(66, 1.0) == 0
    assert pending_count(66, 1.0) == 66
    assert matured_count(71, 0.25) == 53
    assert pending_count(71, 0.25) == 18
    with pytest.raises(ValueError):
        matured_count(-1, 0.5)
    with pytest.raises(ValueError):
        matured_count(10, 1.5)


def test_trial_to_paid_estimate_from_history():
    est = trial_to_paid_estimate(787, 347)
    assert est.rate == pytest.approx(0.4409, abs=1e-4)
    assert est.low < est.rate < est.high
    assert est.sample_size == 787
    assert trial_to_paid_estimate(0, 0) == RateEstimate(0.0, 0.0, 1.0, 0)


def test_project_pending_revenue_ranges():
    rate = RateEstimate(0.44, 0.40, 0.48, 787)
    out = project_pending_revenue(66, rate, [49.99])
    assert out.pending_trials == 66
    assert out.conversions_expected == pytest.approx(29.04)
    assert out.revenue_low == pytest.approx(66 * 0.40 * 49.99)
    assert out.revenue_expected == pytest.approx(66 * 0.44 * 49.99)
    assert out.revenue_high == pytest.approx(66 * 0.48 * 49.99)


def test_project_pending_revenue_uses_cheapest_and_dearest_plan():
    rate = RateEstimate(0.5, 0.5, 0.5, 100)
    out = project_pending_revenue(10, rate, [6.99, 49.99])
    assert out.revenue_low == pytest.approx(5 * 6.99)
    assert out.revenue_expected == pytest.approx(5 * (6.99 + 49.99) / 2)
    assert out.revenue_high == pytest.approx(5 * 49.99)


def test_project_pending_revenue_edge_cases():
    rate = RateEstimate(0.5, 0.4, 0.6, 10)
    assert project_pending_revenue(0, rate, [9.99]).revenue_high == 0.0
    assert project_pending_revenue(5, rate, []).revenue_expected == 0.0
    with pytest.raises(ValueError):
        project_pending_revenue(-1, rate, [9.99])


def test_leader_could_flip_onboarding_case():
    # B leads with $1,528 on 285 viewers; A has $0 on 254 viewers but 66 open annual trials.
    a_pending = PendingRevenue(66, 24, 29, 32, 24 * 49.99, 29 * 49.99, 32 * 49.99)
    b_pending = PendingRevenue(71, 26, 31, 34, 26 * 6.99, 31 * 6.99, 34 * 6.99)
    assert leader_could_flip(1527.9, 285, b_pending, 0.0, 254, a_pending)


def test_leader_cannot_flip_without_pending_revenue():
    none = PendingRevenue(0, 0, 0, 0, 0.0, 0.0, 0.0)
    assert not leader_could_flip(1527.9, 285, none, 0.0, 254, none)
    assert not leader_could_flip(100.0, 0, none, 50.0, 10, none)
    assert not leader_could_flip(100.0, 10, none, 50.0, 0, none)


def test_immaterial_open_trials_do_not_count_as_trial_lag():
    # Two near-equal arms with $9,000 each and a dozen open weekly trials: a no-difference question, not a wait.
    small = PendingRevenue(12, 5, 6, 7, 35.0, 42.0, 49.0)
    assert not leader_could_flip(9000.0, 1200, small, 8950.0, 1200, small)
    # The same open trials matter when the leader has almost no revenue yet.
    assert leader_could_flip(100.0, 1200, small, 90.0, 1200, small)
    assert leader_could_flip(0.0, 254, small, 0.0, 285, small)
