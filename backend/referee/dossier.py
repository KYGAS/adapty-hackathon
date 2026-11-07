"""Build a TestDossier from typed inputs. Pure: same inputs and clock, same dossier."""

from __future__ import annotations

import math
from datetime import datetime, timedelta

from .actions import build_actions
from .models import (
    ArmInput, ArmStats, Assumptions, HistoryInput, PairwiseTest, PendingRevenueModel, RateEstimateModel,
    SampleSize, TestDossier, TestInput, TestSummary, Timeline, TrialLagSummary, Verdict,
)
from .stats.correction import correct
from .stats.decision import DecisionInputs, decide
from .stats.power import mde_at_sample_size, required_sample_size_per_arm
from .stats.proportions import two_proportion_z_test, wilson_interval
from .stats.srm import sample_ratio_mismatch
from .stats.timing import date_after, days_to_reach, elapsed_days, parse_horizon_days, viewers_per_day
from .stats.trial_lag import (
    PendingRevenue, RateEstimate, leader_could_flip, matured_count, matures_at, maturation_fraction,
    pending_count, project_pending_revenue, trial_to_paid_estimate,
)

DEFAULT_TRIAL_DAYS = 7


def fmt_date(value: datetime | None) -> str:
    """Adapty's date style: 7 Nov 2026."""
    if value is None:
        return "an unknown date"
    return value.strftime("%d %b %Y").lstrip("0")


def _days(value: timedelta) -> float:
    return value.total_seconds() / 86400.0


def _trial_rate_for(trial_products: list, trial_mix: dict[str, int], history: HistoryInput,
                    fallback: RateEstimate) -> tuple[RateEstimate, str]:
    """Trial-to-paid rate for an arm: the account's per-product rates, weighted by which trial plans this arm's
    viewers actually started (from the metrics tree), else pooled over the arm's trial plans, else the account total."""
    known = [p for p in trial_products if p.title in history.by_product]
    if not known:
        return fallback, "account history, all trial plans"
    estimates = {p.title: trial_to_paid_estimate(*history.by_product[p.title]) for p in known}
    weights = {p.title: trial_mix.get(p.title, 0) for p in known}
    total_weight = sum(weights.values())
    if total_weight > 0:
        rate = sum(estimates[t].rate * w for t, w in weights.items()) / total_weight
        low = sum(estimates[t].low * w for t, w in weights.items()) / total_weight
        high = sum(estimates[t].high * w for t, w in weights.items()) / total_weight
        sample = sum(estimates[t].sample_size for t in weights)
        mix = ", ".join(f"{t} {w / total_weight:.0%}" for t, w in weights.items() if w)
        return RateEstimate(rate, low, high, sample), f"account history weighted by this arm's trial mix ({mix})"
    started = sum(history.by_product[p.title][0] for p in known)
    paid = sum(history.by_product[p.title][1] for p in known)
    return trial_to_paid_estimate(started, paid), "account history for " + ", ".join(p.title for p in known)


def _arm_stats(arm: ArmInput, history: HistoryInput, fallback_rate: RateEstimate, now: datetime, days_running: float,
               assumptions: Assumptions, warnings: list[str]) -> tuple[ArmStats, PendingRevenue]:
    views = arm.views
    # Paid conversion is a share of viewers, so it counts paying users, not purchases (renewals would inflate it).
    cr = arm.payers / views if views else 0.0
    ci = wilson_interval(min(arm.payers, views), views) if views else wilson_interval(0, 0)
    trial_products = [p for p in arm.products if p.trial_days > 0]
    rate, rate_source = _trial_rate_for(trial_products, arm.trial_mix, history, fallback_rate)
    trial_days_max = max((p.trial_days for p in trial_products), default=0)
    prices = [p.price_usd for p in trial_products]
    if arm.trials > 0 and not trial_products:
        prices = [p.price_usd for p in arm.products]
        trial_days_max = DEFAULT_TRIAL_DAYS
        if "trial_length_assumed" not in warnings:
            warnings.append("trial_length_assumed")
    if arm.active_trials_rate is not None:
        active_rate = min(1.0, max(0.0, arm.active_trials_rate))
    else:
        active_rate = 1.0 - maturation_fraction(days_running, trial_days_max)
    pending = pending_count(arm.trials, active_rate)
    matured = matured_count(arm.trials, active_rate)
    maturation = matured / arm.trials if arm.trials else 1.0
    projected = project_pending_revenue(pending, rate, prices)
    maturity = matures_at(now, trial_days_max, assumptions.grace_days) if pending > 0 else None
    rpv = arm.revenue / views if views else 0.0
    range_reliable = arm.payers >= assumptions.payers_threshold and bool(arm.range_mean)
    stats = ArmStats(
        flow_id=arm.flow_id, title=arm.title, flow_name=arm.flow_name, weight=arm.weight,
        is_control=False, is_leader=False,
        views=views, purchases=arm.purchases, trials=arm.trials, payers=arm.payers, revenue=arm.revenue,
        conversion_rate=cr, conversion_ci_low=ci.low, conversion_ci_high=ci.high,
        trial_rate=arm.trials / views if views else 0.0,
        revenue_per_viewer=rpv,
        p2bb=arm.p2bb, range_low=arm.range_low, range_mean=arm.range_mean, range_high=arm.range_high,
        range_reliable=range_reliable,
        trial_products=trial_products, trial_days_max=trial_days_max,
        trials_pending=pending, trials_matured=matured, maturation_fraction=maturation, matures_at=maturity,
        trial_to_paid=RateEstimateModel(**rate.__dict__), trial_to_paid_source=rate_source,
        pending=PendingRevenueModel(**projected.__dict__),
        projected_rpv_low=(arm.revenue + projected.revenue_low) / views if views else 0.0,
        projected_rpv_expected=(arm.revenue + projected.revenue_expected) / views if views else 0.0,
        projected_rpv_high=(arm.revenue + projected.revenue_high) / views if views else 0.0,
    )
    return stats, projected


def _pick_leader(arms: list[ArmStats]) -> tuple[ArmStats | None, ArmStats | None]:
    scored = [a for a in arms if (a.p2bb or 0.0) > 0.0 or a.revenue > 0.0]
    if not scored:
        return None, None
    ordered = sorted(scored, key=lambda a: ((a.p2bb or 0.0), a.revenue_per_viewer, a.revenue), reverse=True)
    leader = ordered[0]
    runner = next((a for a in sorted(arms, key=lambda a: ((a.p2bb or 0.0), a.revenue_per_viewer), reverse=True)
                   if a.flow_id != leader.flow_id), None)
    return leader, runner


def _headline(code: str, d: dict) -> str:
    return {
        "WAIT_TRIAL_LAG": "Wait: {pending} open trials can still flip the leader. Earliest safe call {maturity}.",
        "NOT_DECIDABLE": "Not decidable at this traffic: {required} viewers per arm needed, {days} days away (limit {max_wait}).",
        "INSUFFICIENT_PAYERS": "Not yet: the leader has {payers} payers and Adapty needs {threshold} before the revenue range means anything.",
        "WAIT_MIN_RUNTIME": "Wait {wait} more days: a test should cover a full week before a call.",
        "WAIT_SAMPLE": "Keep running: {min_views} of {required} viewers per arm, sample reached around {sample_date}.",
        "CALL_WINNER": "Call it: {leader} wins. Stop the test and ship {flow}.",
        "CALL_NO_DIFFERENCE": "Call it: no detectable difference at a {mde}% minimum effect. Keep the control.",
        "NOT_STARTED": "Draft: ready to start on {placement}.",
        "COMPLETED": "Completed on {stopped}. See the audit.",
    }[code].format(**d)


def build_dossier(test: TestInput, history: HistoryInput, app_id: str, now: datetime,
                  assumptions: Assumptions | None = None) -> TestDossier:
    assumptions = assumptions or Assumptions()
    warnings: list[str] = []
    started = test.started_at
    end = test.stopped_at or now
    days_running = elapsed_days(started, end) if started else 0.0
    rate = trial_to_paid_estimate(history.trials_started, history.trials_paid)
    if history.trials_started == 0:
        warnings.append("no_trial_history_rate_unknown")
    else:
        warnings.append("trial_to_paid_rate_borrowed_from_account_history")

    arm_stats: list[ArmStats] = []
    pending_by_flow: dict[str, PendingRevenue] = {}
    for arm in test.arms:
        stats, projected = _arm_stats(arm, history, rate, now, days_running, assumptions, warnings)
        arm_stats.append(stats)
        pending_by_flow[arm.flow_id] = projected
    if not arm_stats:
        raise ValueError("a test needs at least one arm")
    control = next((a for a in arm_stats if a.title.upper() == "A"), arm_stats[0])
    leader, runner = _pick_leader(arm_stats)
    arm_stats = [a.model_copy(update={"is_control": a.flow_id == control.flow_id,
                                       "is_leader": leader is not None and a.flow_id == leader.flow_id}) for a in arm_stats]
    control = next(a for a in arm_stats if a.is_control)
    leader = next((a for a in arm_stats if a.is_leader), None)
    runner = next((a for a in arm_stats if runner and a.flow_id == runner.flow_id), None)

    # ---- pairwise conversion tests against the control, corrected for the family
    pairwise: list[PairwiseTest] = []
    raw_p: list[float] = []
    candidates = [a for a in arm_stats if not a.is_control and a.views > 0 and control.views > 0]
    results = [two_proportion_z_test(min(control.payers, control.views), control.views, min(a.payers, a.views), a.views) for a in candidates]
    raw_p = [r.p_value for r in results]
    corrected = correct(raw_p, assumptions.correction, assumptions.alpha) if raw_p else []
    for arm, result, adj in zip(candidates, results, corrected):
        pairwise.append(PairwiseTest(
            arm_title=arm.title, control_title=control.title, control_rate=result.p1, arm_rate=result.p2,
            difference=result.difference, relative_lift=result.relative_lift, z=result.z, p_value=result.p_value,
            adjusted_p=adj.adjusted_p, significant=adj.rejected,
        ))
    if len(arm_stats) > 2:
        warnings.append("three_or_more_arms_adapty_p_value_absent_pairwise_holm_used")

    def significant_for(arm: ArmStats | None) -> bool:
        if arm is None:
            return False
        if arm.is_control:
            return any(p.significant for p in pairwise if runner and p.arm_title == runner.title)
        return any(p.significant and p.arm_title == arm.title for p in pairwise)

    # ---- sample size and minimum detectable effect
    total_views = sum(a.views for a in arm_stats)
    total_payers = sum(min(a.payers, a.views) for a in arm_stats)
    if control.payers > 0 and control.views > 0:
        baseline, baseline_source = control.conversion_rate, "control paid conversion"
    elif total_payers > 0:
        baseline, baseline_source = total_payers / total_views, "pooled paid conversion (control has no payers yet)"
    else:
        baseline, baseline_source = 0.0, "no payers yet"
    required = required_sample_size_per_arm(baseline, assumptions.mde_relative, assumptions.alpha, assumptions.power) \
        if 0.0 < baseline < 1.0 else None
    min_views = min(a.views for a in arm_stats)
    rate_total = viewers_per_day(total_views, days_running) if started else 0.0
    rate_smallest = viewers_per_day(min_views, days_running) if started else 0.0
    days_to_sample = days_to_reach(required, min_views, rate_smallest) if required else math.inf
    horizon_days = parse_horizon_days(test.goal, assumptions.default_horizon_days)
    views_at_horizon = int(min_views + rate_smallest * max(0.0, horizon_days - days_running))
    mde_now = mde_at_sample_size(baseline, min_views) if (0.0 < baseline < 1.0 and min_views > 0) else math.inf
    mde_horizon = mde_at_sample_size(baseline, views_at_horizon) if (0.0 < baseline < 1.0 and views_at_horizon > 0) else math.inf
    sample = SampleSize(
        alpha=assumptions.alpha, power=assumptions.power, mde_relative=assumptions.mde_relative,
        baseline_rate=baseline, baseline_source=baseline_source, required_per_arm=required,
        min_views_per_arm=min_views, progress=min(1.0, min_views / required) if required else 0.0,
        viewers_per_day=rate_total, viewers_per_day_smallest_arm=rate_smallest,
        days_to_sample=None if math.isinf(days_to_sample) else days_to_sample,
        sample_reached_at=date_after(now, days_to_sample) if test.state == "live" else None,
        mde_detectable_now=None if math.isinf(mde_now) else mde_now,
        mde_detectable_at_horizon=None if math.isinf(mde_horizon) else mde_horizon,
        views_per_arm_at_horizon=views_at_horizon,
    )
    if total_views >= 100:
        srm = sample_ratio_mismatch([a.views for a in arm_stats], [a.weight for a in arm_stats])
        if srm.mismatch:
            warnings.append("sample_ratio_mismatch")
    if leader is not None and not leader.range_reliable:
        warnings.append("revenue_range_unreliable_under_50_payers")
    if all((a.p2bb or 0.0) == 0.0 for a in arm_stats) and total_views > 0:
        warnings.append("p2bb_not_computed_by_adapty")
    if pairwise:
        warnings.append("significance_uses_paid_conversion_while_p2bb_uses_revenue")

    # ---- trial lag
    flip = False
    if leader is not None and test.state == "live":
        for other in arm_stats:
            if other.flow_id == leader.flow_id or other.views == 0:
                continue
            if leader_could_flip(leader.revenue, leader.views, pending_by_flow[leader.flow_id],
                                 other.revenue, other.views, pending_by_flow[other.flow_id]):
                flip = True
    maturity_dates = [a.matures_at for a in arm_stats if a.matures_at]
    maturity_date = max(maturity_dates) if maturity_dates else None
    days_to_maturity = max(0.0, _days(maturity_date - now)) if maturity_date else 0.0
    trial_lag = TrialLagSummary(
        history_rate=RateEstimateModel(**rate.__dict__), history_source=history.source,
        pending_trials_total=sum(a.trials_pending for a in arm_stats),
        pending_revenue_expected_total=sum(a.pending.revenue_expected for a in arm_stats),
        leader_could_flip=flip, matures_at=maturity_date, days_to_maturity=days_to_maturity,
        min_maturation_fraction=min((a.maturation_fraction for a in arm_stats if a.trials > 0), default=1.0),
    )

    # ---- decision
    decision = decide(DecisionInputs(
        state=test.state, days_running=days_running, min_views_per_arm=min_views, required_views_per_arm=required,
        leader_payers=leader.payers if leader else 0, pending_could_flip=flip,
        significant_vs_control=significant_for(leader), p2bb_leader=(leader.p2bb or 0.0) if leader else 0.0,
        days_to_sample=days_to_sample, days_to_maturity=days_to_maturity,
        p2bb_threshold=assumptions.p2bb_threshold, payers_threshold=assumptions.payers_threshold,
        min_runtime_days=assumptions.min_runtime_days, max_wait_days=assumptions.max_wait_days,
    ))

    # ---- timeline
    min_runtime_date = started + timedelta(days=assumptions.min_runtime_days) if started else None
    sample_date = sample.sample_reached_at
    decision_candidates = [d for d in (maturity_date if flip else None, sample_date, min_runtime_date) if d]
    decision_date = max(decision_candidates) if (decision_candidates and test.state == "live") else None
    if decision.is_call:
        decision_date = now
    timeline = Timeline(
        now=now, started_at=started, days_running=days_running, horizon_days=horizon_days,
        horizon_date=started + timedelta(days=horizon_days) if started else None,
        maturity_date=maturity_date, sample_date=sample_date, min_runtime_date=min_runtime_date,
        decision_date=decision_date,
        days_to_decision=max(0.0, _days(decision_date - now)) if decision_date else None,
    )

    wait_days = decision.wait_days if not math.isinf(decision.wait_days) else (sample.days_to_sample or 0.0)
    if "no_views_yet" in decision.reasons:
        headline = f"Keep running: no viewers attributed yet. First read on {fmt_date(min_runtime_date)}."
    else:
        headline = _headline(decision.code.value, {
            "pending": trial_lag.pending_trials_total, "maturity": fmt_date(maturity_date),
            "required": required if required is not None else "an unknown number of",
            "days": f"{days_to_sample:.0f}" if not math.isinf(days_to_sample) else "more than the limit of",
            "max_wait": f"{assumptions.max_wait_days:.0f}",
            "payers": leader.payers if leader else 0, "threshold": assumptions.payers_threshold,
            "wait": f"{decision.wait_days:.1f}", "min_views": min_views, "sample_date": fmt_date(sample_date),
            "leader": leader.title if leader else "nobody", "flow": leader.flow_name if leader else "the control",
            "mde": f"{assumptions.mde_relative * 100:.0f}", "placement": test.placement_title or "its placement",
            "stopped": fmt_date(test.stopped_at),
        })
    verdict = Verdict(
        code=decision.code.value, headline=headline,
        leader_title=leader.title if leader else None, leader_flow_id=leader.flow_id if leader else None,
        runner_up_title=runner.title if runner else None, p2bb_leader=leader.p2bb if leader else None,
        wait_days=wait_days, decision_date=decision_date, reasons=list(decision.reasons), is_call=decision.is_call,
    )

    summary = TestSummary(
        test_id=test.test_id, title=test.title, goal=test.goal, type=test.type, state=test.state,
        placement_id=test.placement_id, placement_title=test.placement_title, segment_ids=test.segment_ids,
        started_at=test.started_at, stopped_at=test.stopped_at, arm_count=len(arm_stats),
    )
    actions = build_actions(app_id, test, verdict, control, leader)
    return TestDossier(
        generated_at=now, app_id=app_id, test=summary, assumptions=assumptions, arms=arm_stats,
        control_title=control.title, leader_title=leader.title if leader else None, pairwise=pairwise,
        correction_method=assumptions.correction, sample=sample, trial_lag=trial_lag, timeline=timeline,
        verdict=verdict, warnings=warnings, actions=actions,
    )
