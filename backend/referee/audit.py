"""Retroactive audit of a completed test: how strong was the evidence at the stop, and did the winner hold up?"""

from __future__ import annotations

from .models import AuditResult, EvidenceAtStop, RealizedOutcome, TestDossier

MIN_VIEWS_FOR_REALIZED = 200  # below this, a 5% gap in revenue per viewer is noise, so the realized verdict stays inconclusive


def grade_from_score(score: int) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"


def audit_completed(dossier: TestDossier, winner_flow_id: str | None, flow_metrics: dict[str, dict]) -> AuditResult:
    """flow_metrics maps flow_id to the lifetime flow metrics row (views, revenue) from GET /flows/metrics/."""
    arms = dossier.arms
    winner = next((a for a in arms if a.flow_id == winner_flow_id), None) if winner_flow_id else None
    reference = winner or next((a for a in arms if a.is_leader), None) or arms[0]
    pair = next((p for p in dossier.pairwise if p.arm_title == reference.title or p.control_title == reference.title), None)
    p_value = pair.adjusted_p if pair else None
    evidence = EvidenceAtStop(
        payers_leader=reference.payers,
        min_views_per_arm=dossier.sample.min_views_per_arm,
        required_per_arm=dossier.sample.required_per_arm,
        sample_progress=dossier.sample.progress,
        p_value=p_value,
        p2bb_leader=reference.p2bb,
        days_running=dossier.timeline.days_running,
    )
    score = 100
    reasons: list[str] = []
    if evidence.payers_leader < dossier.assumptions.payers_threshold:
        score -= 40
        reasons.append(f"winner had {evidence.payers_leader} payers at the stop, under the {dossier.assumptions.payers_threshold} needed for a revenue range")
    if evidence.required_per_arm is None:
        score -= 30
        reasons.append("no conversions at the stop, so no sample size could even be planned")
    elif evidence.sample_progress < 1.0:
        score -= 30
        reasons.append(f"sample at {evidence.sample_progress * 100:.0f}% of the {evidence.required_per_arm} viewers per arm needed")
    if p_value is None or p_value > dossier.assumptions.alpha:
        score -= 20
        reasons.append("difference not significant after correction")
    if evidence.days_running < dossier.assumptions.min_runtime_days:
        score -= 10
        reasons.append(f"ran {evidence.days_running:.1f} days, under the {dossier.assumptions.min_runtime_days:.0f}-day minimum")
    if (evidence.p2bb_leader or 0.0) < dossier.assumptions.p2bb_threshold:
        reasons.append(f"P2BB at the stop was {evidence.p2bb_leader or 0.0:.1f}%, under {dossier.assumptions.p2bb_threshold:.0f}%")
    score = max(0, score)

    realized = None
    other = next((a for a in arms if a.flow_id != reference.flow_id), None)
    if other is not None:
        w = flow_metrics.get(reference.flow_id, {})
        o = flow_metrics.get(other.flow_id, {})
        w_views, w_rev = int(w.get("views", 0) or 0), float(w.get("revenue", 0.0) or 0.0)
        o_views, o_rev = int(o.get("views", 0) or 0), float(o.get("revenue", 0.0) or 0.0)
        w_rpv = w_rev / w_views if w_views else 0.0
        o_rpv = o_rev / o_views if o_views else 0.0
        if w_views >= MIN_VIEWS_FOR_REALIZED and o_views >= MIN_VIEWS_FOR_REALIZED and (w_rpv or o_rpv):
            status = "confirmed" if w_rpv > o_rpv * 1.05 else ("reversed" if w_rpv < o_rpv * 0.95 else "inconclusive")
        else:
            status = "inconclusive"
        realized = RealizedOutcome(
            winner_flow_views=w_views, winner_flow_revenue=w_rev, winner_rpv=w_rpv,
            alternative_flow_views=o_views, alternative_flow_revenue=o_rev, alternative_rpv=o_rpv,
            delta_rpv=w_rpv - o_rpv, status=status,
            source="lifetime flow metrics across all placements (GET /flows/metrics/)",
        )
    return AuditResult(
        stopped_at=dossier.test.stopped_at, duration_days=dossier.timeline.days_running,
        declared_winner_flow_id=winner.flow_id if winner else None,
        declared_winner_title=f"{winner.title} ({winner.flow_name})" if winner else None,
        evidence=evidence, score=score, grade=grade_from_score(score), grade_reasons=reasons, realized=realized,
    )
