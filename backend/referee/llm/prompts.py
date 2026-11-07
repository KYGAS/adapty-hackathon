"""The narration view of a dossier (what the LLM sees) and the system prompt with the hard rules."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from ..models import AuditResult, Memo, TestDossier

SYSTEM_PROMPT = """You narrate decisions for the Adapty Experimentation Referee, a tool that stops premature A/B test calls.
You receive a JSON "dossier view" computed by deterministic statistics. Your job is to explain it to a product manager in plain English.

Hard rules, no exceptions:
1. Never calculate, estimate, extrapolate, convert, round differently, or invent any number. Every digit you write must be copied from a value in the dossier view. If a figure is not there, describe it in words without digits.
2. Never contradict the verdict code, the headline, or the recommended action. Do not propose actions that are not in `actions`.
3. Use only dates that appear in the view, written as they appear.
4. Keep `memo_markdown` under 180 words, sentence case, no headings larger than "###", no tables, no em dashes.
5. `headline` is one sentence restating the verdict. `summary` is two sentences at most. `risks` and `next_steps` are short bullet strings (at most four each). `next_steps` must only reference the actions in the view.
6. Output JSON only, matching the schema you were given.
"""

MEMO_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "summary": {"type": "string"},
        "memo_markdown": {"type": "string"},
        "risks": {"type": "array", "items": {"type": "string"}},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["headline", "summary", "memo_markdown", "risks", "next_steps"],
    "additionalProperties": False,
}


def fmt_date(value: datetime | None) -> str | None:
    return value.strftime("%d %b %Y").lstrip("0") if value else None


def r(value: float | None, digits: int = 2) -> float | None:
    return None if value is None else round(value, digits)


def pct(value: float | None, digits: int = 1) -> float | None:
    return None if value is None else round(value * 100.0, digits)


def narration_view(dossier: TestDossier, audit: AuditResult | None = None) -> dict[str, Any]:
    """A compact, pre-rounded view. Every number the memo may use comes from here."""
    t, v, s, tl = dossier.test, dossier.verdict, dossier.sample, dossier.trial_lag
    arms = []
    for a in dossier.arms:
        arms.append({
            "title": a.title, "flow": a.flow_name, "is_control": a.is_control, "is_leader": a.is_leader,
            "weight_pct": r(a.weight, 0), "views": a.views, "purchases": a.purchases, "trials": a.trials, "payers": a.payers,
            "revenue_usd": r(a.revenue), "conversion_rate_pct": pct(a.conversion_rate, 2),
            "conversion_ci_pct": [pct(a.conversion_ci_low, 1), pct(a.conversion_ci_high, 1)],
            "revenue_per_viewer_usd": r(a.revenue_per_viewer), "p2bb_pct": r(a.p2bb, 1),
            "revenue_per_1000_range": None if a.range_mean is None else [r(a.range_low, 0), r(a.range_mean, 0), r(a.range_high, 0)],
            "revenue_range_reliable": a.range_reliable,
            "trial_products": [f"{p.title} ({p.trial_days}-day trial, ${p.price_usd})" for p in a.trial_products],
            "trial_days": a.trial_days_max, "open_trials": a.trials_pending, "matured_trials": a.trials_matured,
            "trial_to_paid_pct": pct(a.trial_to_paid.rate, 1), "trial_to_paid_source": a.trial_to_paid_source,
            "open_trials_expected_conversions": r(a.pending.conversions_expected, 0),
            "open_trials_revenue_usd": {"low": r(a.pending.revenue_low, 0), "expected": r(a.pending.revenue_expected, 0), "high": r(a.pending.revenue_high, 0)},
            "projected_revenue_per_viewer_usd": {"low": r(a.projected_rpv_low), "expected": r(a.projected_rpv_expected), "high": r(a.projected_rpv_high)},
            "trials_mature_on": fmt_date(a.matures_at),
        })
    view: dict[str, Any] = {
        "test": {
            "title": t.title, "goal": t.goal, "state": t.state, "placement": t.placement_title,
            "audience": "one segment" if t.segment_ids else "All users", "arms": t.arm_count,
            "started_on": fmt_date(t.started_at), "stopped_on": fmt_date(t.stopped_at),
            "days_running": r(dossier.timeline.days_running, 1),
        },
        "verdict": {
            "code": v.code, "headline": v.headline, "leader": v.leader_title, "runner_up": v.runner_up_title,
            "leader_p2bb_pct": r(v.p2bb_leader, 1), "wait_days": r(v.wait_days, 1), "decision_date": fmt_date(v.decision_date),
            "is_call": v.is_call, "reasons": list(v.reasons),
        },
        "arms": arms,
        "pairwise_vs_control": [{
            "arm": p.arm_title, "control": p.control_title, "control_rate_pct": pct(p.control_rate, 2), "arm_rate_pct": pct(p.arm_rate, 2),
            "relative_lift_pct": pct(p.relative_lift, 1), "p_value": r(p.p_value, 4), "adjusted_p_value": r(p.adjusted_p, 4),
            "significant": p.significant,
        } for p in dossier.pairwise],
        "correction": dossier.correction_method,
        "sample": {
            "alpha": s.alpha, "power": s.power, "minimum_detectable_effect_pct": pct(s.mde_relative, 0),
            "baseline_rate_pct": pct(s.baseline_rate, 2), "baseline_source": s.baseline_source,
            "required_viewers_per_arm": s.required_per_arm, "smallest_arm_viewers": s.min_views_per_arm,
            "progress_pct": pct(s.progress, 0), "viewers_per_day": r(s.viewers_per_day, 0),
            "days_to_sample": r(s.days_to_sample, 1), "sample_reached_on": fmt_date(s.sample_reached_at),
            "detectable_effect_now_pct": pct(s.mde_detectable_now, 0),
            "detectable_effect_at_horizon_pct": pct(s.mde_detectable_at_horizon, 0),
            "horizon_days": dossier.timeline.horizon_days, "horizon_date": fmt_date(dossier.timeline.horizon_date),
        },
        "trial_lag": {
            "history_trial_to_paid_pct": pct(tl.history_rate.rate, 1),
            "history_ci_pct": [pct(tl.history_rate.low, 1), pct(tl.history_rate.high, 1)],
            "history_trials": tl.history_rate.sample_size, "history_source": tl.history_source,
            "open_trials_total": tl.pending_trials_total, "open_trials_revenue_expected_usd": r(tl.pending_revenue_expected_total, 0),
            "open_trials_can_flip_leader": tl.leader_could_flip, "all_trials_mature_on": fmt_date(tl.matures_at),
            "days_to_maturity": r(tl.days_to_maturity, 1),
        },
        "timeline": {
            "today": fmt_date(dossier.timeline.now), "min_runtime_until": fmt_date(dossier.timeline.min_runtime_date),
            "decision_date": fmt_date(dossier.timeline.decision_date), "days_to_decision": r(dossier.timeline.days_to_decision, 1),
        },
        "warnings": list(dossier.warnings),
        "actions": [{"id": a.id, "kind": a.kind, "title": a.title, "recommended": a.recommended, "risk": a.risk,
                     "cli_command": a.cli_command} for a in dossier.actions],
        "audit": None,
    }
    if audit:
        view["audit"] = {
            "grade": audit.grade, "score": audit.score, "reasons": list(audit.grade_reasons),
            "declared_winner": audit.declared_winner_title, "duration_days": r(audit.duration_days, 1),
            "evidence": {"payers": audit.evidence.payers_leader, "smallest_arm_viewers": audit.evidence.min_views_per_arm,
                         "required_viewers_per_arm": audit.evidence.required_per_arm, "progress_pct": pct(audit.evidence.sample_progress, 0),
                         "p_value": r(audit.evidence.p_value, 4), "p2bb_pct": r(audit.evidence.p2bb_leader, 1)},
            "realized": None if not audit.realized else {
                "status": audit.realized.status, "winner_views": audit.realized.winner_flow_views,
                "winner_revenue_usd": r(audit.realized.winner_flow_revenue), "winner_revenue_per_viewer_usd": r(audit.realized.winner_rpv),
                "alternative_views": audit.realized.alternative_flow_views, "alternative_revenue_usd": r(audit.realized.alternative_flow_revenue),
                "alternative_revenue_per_viewer_usd": r(audit.realized.alternative_rpv), "source": audit.realized.source,
            },
        }
    return view


def user_prompt(view: dict[str, Any]) -> str:
    import json
    return ("Dossier view (JSON). Write the memo now.\n\n" + json.dumps(view, indent=1, ensure_ascii=False))


REASON_TEXT = {
    "open_trials_can_flip_leader": "{open_trials_total} trials are still open. At the account's historical trial-to-paid rate of {history_trial_to_paid_pct}% they are worth about ${open_trials_revenue_expected_usd}, enough to move the leader.",
    "wait_for_maturation": "The last trial matures on {all_trials_mature_on}. Calling before that counts day-one cash against unfinished trials.",
    "sample_unreachable_within_max_wait": "Detecting a {minimum_detectable_effect_pct}% lift needs {required_viewers_per_arm} viewers per arm; the smallest arm has {smallest_arm_viewers} and that is {days_to_sample} days away.",
    "consider_bigger_change_or_wider_audience": "Either test a bolder change, widen the audience, or accept that only a {detectable_effect_at_horizon_pct}% lift is detectable by the horizon.",
    "revenue_range_not_estimable": "Adapty's revenue range per 1,000 viewers is only estimated from 50 payers; below that it is shown as zero to twice the mean.",
    "sample_reached": "Each arm has at least {required_viewers_per_arm} viewers, the planned sample for a {minimum_detectable_effect_pct}% effect.",
    "min_runtime_not_reached": "The test has run {days_running} days; a full week covers weekday and weekend behaviour.",
    "weekly_seasonality_guard": "Weekend and weekday users convert differently, so the referee waits for a full week.",
    "significant_after_correction": "The paid conversion difference is significant after the {correction} correction.",
    "not_significant": "The paid conversion difference is not significant after correction.",
    "p2bb_above_threshold": "Adapty's probability to be best for the leader is {leader_p2bb_pct}%.",
    "p2bb_below_threshold": "Adapty's probability to be best for the leader is only {leader_p2bb_pct}%.",
    "effect_below_mde": "Whatever difference exists is smaller than the {minimum_detectable_effect_pct}% effect the test was sized for.",
    "sample_not_reached": "The smallest arm has {smallest_arm_viewers} of the {required_viewers_per_arm} viewers needed; {progress_pct}% of the way.",
    "peeking_guard": "Checking early and stopping on a good day inflates false positives; the referee holds until the sample is in.",
    "state_draft": "The test has not started yet.",
}

WARNING_TEXT = {
    "trial_to_paid_rate_borrowed_from_account_history": "The trial-to-paid rate comes from account history ({history_trials} trials), not from this test.",
    "no_trial_history_rate_unknown": "No trial history is available, so pending revenue cannot be projected.",
    "revenue_range_unreliable_under_50_payers": "The leader has fewer than 50 payers, so Adapty's revenue range is not reliable yet.",
    "significance_uses_paid_conversion_while_p2bb_uses_revenue": "Significance is tested on paid conversion while P2BB ranks revenue per viewer; both must agree before a call.",
    "sample_ratio_mismatch": "The traffic split does not match the configured weights; check the assignment before trusting any result.",
    "p2bb_not_computed_by_adapty": "Adapty has not computed P2BB yet (no purchases).",
    "trial_length_assumed": "The trial length of a product was not known and a 7-day trial was assumed.",
    "three_or_more_arms_adapty_p_value_absent_pairwise_holm_used": "With three or more arms Adapty shows no p-value; pairwise tests against the control with Holm correction are used instead.",
}


def _flat(view: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key in ("verdict", "sample", "trial_lag", "timeline", "test"):
        flat.update(view.get(key) or {})
    flat["correction"] = view.get("correction")
    return flat


def money(value: float | None) -> str:
    """Adapty's money style: whole dollars for totals, two decimals under $100."""
    if value is None:
        return "$0"
    return f"${value:,.0f}" if abs(value) >= 100 else f"${value:,.2f}"


def _fmt_flat(flat: dict[str, Any]) -> dict[str, Any]:
    pretty = dict(flat)
    for key in ("open_trials_revenue_expected_usd",):
        if pretty.get(key) is not None:
            pretty[key] = money(pretty[key]).lstrip("$")
    for key in ("required_viewers_per_arm", "smallest_arm_viewers", "history_trials"):
        if isinstance(pretty.get(key), int):
            pretty[key] = f"{pretty[key]:,}"
    return pretty


def template_memo(view: dict[str, Any]) -> Memo:
    """Deterministic narration from the view, used when no LLM is available or when the guard rejects the LLM."""
    flat = _fmt_flat(_flat(view))
    verdict = view["verdict"]
    lines: list[str] = []
    for arm in view["arms"]:
        role = " (control)" if arm["is_control"] else (" (leader)" if arm["is_leader"] else "")
        line = (f"- Arm {arm['title']}{role}, {arm['flow']}: {arm['views']:,} viewers, {arm['purchases']} purchases, "
                f"{arm['payers']} payers, {money(arm['revenue_usd'])} revenue, {money(arm['revenue_per_viewer_usd'])} per viewer")
        if arm["p2bb_pct"] is not None:
            line += f", P2BB {arm['p2bb_pct']}%"
        if arm["open_trials"]:
            pending = arm["open_trials_revenue_usd"]
            line += (f". {arm['open_trials']} trials still open, worth about {money(pending['expected'])} "
                     f"if they convert at the historical rate (range {money(pending['low'])} to "
                     f"{money(pending['high'])}), maturing on {arm['trials_mature_on']}")
        lines.append(line + ".")
    reasons = [REASON_TEXT[k].format(**flat) for k in verdict["reasons"] if k in REASON_TEXT]
    recommended = next((a for a in view["actions"] if a["recommended"]), None)
    parts = [f"### {verdict['headline']}", "", "**What the numbers say**", *lines, "", "**Why**", *[f"- {s}" for s in reasons]]
    if recommended:
        parts += ["", "**Next step**", f"- {recommended['title']}." + (f" Dry run: `{recommended['cli_command']}`" if recommended["cli_command"] else "")]
    if view.get("audit"):
        audit = view["audit"]
        parts += ["", "**Audit**", f"- Grade {audit['grade']} ({audit['score']} of 100). " + " ".join(audit["reasons"])]
        if audit.get("realized"):
            rz = audit["realized"]
            parts.append(f"- Realized since: winner {money(rz['winner_revenue_per_viewer_usd'])} per viewer on {rz['winner_views']} views "
                         f"vs alternative {money(rz['alternative_revenue_per_viewer_usd'])} on {rz['alternative_views']} views: {rz['status']}.")
    risks = [WARNING_TEXT[w].format(**flat) for w in view["warnings"] if w in WARNING_TEXT]
    next_steps = [a["title"] + (" (recommended)" if a["recommended"] else " (not recommended)") for a in view["actions"]]
    summary = reasons[0] if reasons else verdict["headline"]
    return Memo(headline=verdict["headline"], summary=summary, memo_markdown="\n".join(parts), risks=risks[:4], next_steps=next_steps[:4])
