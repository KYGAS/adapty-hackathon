"""Trial maturation: how much of an arm's revenue is still locked in open trials."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta

from .proportions import wilson_interval


@dataclass(frozen=True)
class RateEstimate:
    """A conversion rate with its confidence interval and the sample it came from."""
    rate: float
    low: float
    high: float
    sample_size: int


@dataclass(frozen=True)
class PendingRevenue:
    pending_trials: int
    conversions_low: float
    conversions_expected: float
    conversions_high: float
    revenue_low: float
    revenue_expected: float
    revenue_high: float


def maturation_fraction(elapsed_days: float, trial_days: int) -> float:
    """Share of a cohort of trials that has had time to finish, assuming trials started evenly over the run."""
    if trial_days <= 0:
        return 1.0
    if elapsed_days <= 0.0:
        return 0.0
    return min(1.0, elapsed_days / trial_days)


def matures_at(started_at: datetime, trial_days: int, grace_days: int = 0) -> datetime:
    """When the last trial started now would be resolved: trial length plus a grace period for store reporting."""
    if trial_days < 0 or grace_days < 0:
        raise ValueError("days must not be negative")
    return started_at + timedelta(days=trial_days + grace_days)


def matured_count(trials: int, active_rate: float) -> int:
    if trials < 0:
        raise ValueError("trials must not be negative")
    if not 0.0 <= active_rate <= 1.0:
        raise ValueError("active_rate must be between 0 and 1")
    return round(trials * (1.0 - active_rate))


def pending_count(trials: int, active_rate: float) -> int:
    return trials - matured_count(trials, active_rate)


def trial_to_paid_estimate(trials_started: int, trials_paid: int, confidence: float = 0.95) -> RateEstimate:
    """Historical trial-to-paid rate with a Wilson interval, e.g. from the analytics conversion endpoint."""
    if trials_started == 0:
        return RateEstimate(0.0, 0.0, 1.0, 0)
    interval = wilson_interval(trials_paid, trials_started, confidence)
    return RateEstimate(trials_paid / trials_started, interval.low, interval.high, trials_started)


def project_pending_revenue(pending_trials: int, rate: RateEstimate, prices_usd: list[float]) -> PendingRevenue:
    """Revenue the open trials may still produce. Low pairs the low rate with the cheapest plan, high the high rate with the dearest."""
    if pending_trials < 0:
        raise ValueError("pending_trials must not be negative")
    if pending_trials == 0 or not prices_usd:
        return PendingRevenue(pending_trials, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0)
    mean_price = sum(prices_usd) / len(prices_usd)
    low_c = pending_trials * rate.low
    exp_c = pending_trials * rate.rate
    high_c = pending_trials * rate.high
    return PendingRevenue(
        pending_trials,
        low_c, exp_c, high_c,
        low_c * min(prices_usd), exp_c * mean_price, high_c * max(prices_usd),
    )


def leader_could_flip(leader_revenue: float, leader_views: int, leader_pending: PendingRevenue,
                      other_revenue: float, other_views: int, other_pending: PendingRevenue,
                      materiality: float = 0.05) -> bool:
    """True when the trailing arm's optimistic revenue per viewer reaches the leader's pessimistic one, and the open
    trials are worth enough to matter (at least `materiality` of the leader's revenue). A near tie with a handful of
    open trials is a no-difference question, not a trial-lag one."""
    if leader_views <= 0 or other_views <= 0:
        return False
    pending_total = leader_pending.revenue_expected + other_pending.revenue_expected
    if pending_total <= 0.0:
        return False
    if leader_revenue > 0.0 and pending_total < materiality * leader_revenue:
        return False
    leader_floor = (leader_revenue + leader_pending.revenue_low) / leader_views
    other_ceiling = (other_revenue + other_pending.revenue_high) / other_views
    return other_ceiling >= leader_floor
