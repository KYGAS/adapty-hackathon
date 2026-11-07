"""The referee's verdict: a fixed order of deterministic rules over precomputed facts."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import Enum


class VerdictCode(str, Enum):
    NOT_STARTED = "NOT_STARTED"
    COMPLETED = "COMPLETED"
    WAIT_TRIAL_LAG = "WAIT_TRIAL_LAG"
    INSUFFICIENT_PAYERS = "INSUFFICIENT_PAYERS"
    WAIT_MIN_RUNTIME = "WAIT_MIN_RUNTIME"
    WAIT_SAMPLE = "WAIT_SAMPLE"
    NOT_DECIDABLE = "NOT_DECIDABLE"
    CALL_WINNER = "CALL_WINNER"
    CALL_NO_DIFFERENCE = "CALL_NO_DIFFERENCE"


CALL_CODES = {VerdictCode.CALL_WINNER, VerdictCode.CALL_NO_DIFFERENCE}


@dataclass(frozen=True)
class DecisionInputs:
    state: str
    days_running: float
    min_views_per_arm: int
    required_views_per_arm: int | None
    leader_payers: int
    pending_could_flip: bool
    significant_vs_control: bool
    p2bb_leader: float
    days_to_sample: float
    days_to_maturity: float
    p2bb_threshold: float = 95.0
    payers_threshold: int = 50
    min_runtime_days: float = 7.0
    max_wait_days: float = 60.0


@dataclass(frozen=True)
class Decision:
    code: VerdictCode
    wait_days: float
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def is_call(self) -> bool:
        return self.code in CALL_CODES


def decide(inp: DecisionInputs) -> Decision:
    """Rules fire in priority order; the first blocking condition wins so a trial lag always beats a P2BB of 100."""
    if inp.state == "draft":
        return Decision(VerdictCode.NOT_STARTED, 0.0, ("state_draft",))
    if inp.state != "live":
        return Decision(VerdictCode.COMPLETED, 0.0, (f"state_{inp.state}",))

    if inp.pending_could_flip:
        return Decision(VerdictCode.WAIT_TRIAL_LAG, max(0.0, inp.days_to_maturity),
                        ("open_trials_can_flip_leader", "wait_for_maturation"))

    sample_reached = inp.required_views_per_arm is not None and inp.min_views_per_arm >= inp.required_views_per_arm
    if not sample_reached and (inp.required_views_per_arm is None or math.isinf(inp.days_to_sample)
                               or inp.days_to_sample > inp.max_wait_days):
        return Decision(VerdictCode.NOT_DECIDABLE, inp.days_to_sample,
                        ("sample_unreachable_within_max_wait", "consider_bigger_change_or_wider_audience"))

    if inp.leader_payers < inp.payers_threshold:
        return Decision(VerdictCode.INSUFFICIENT_PAYERS, max(inp.days_to_sample, 0.0),
                        (f"leader_payers_below_{inp.payers_threshold}", "revenue_range_not_estimable"))

    if sample_reached:
        if inp.days_running < inp.min_runtime_days:
            return Decision(VerdictCode.WAIT_MIN_RUNTIME, inp.min_runtime_days - inp.days_running,
                            ("sample_reached", "min_runtime_not_reached", "weekly_seasonality_guard"))
        if inp.significant_vs_control and inp.p2bb_leader >= inp.p2bb_threshold:
            return Decision(VerdictCode.CALL_WINNER, 0.0,
                            ("sample_reached", "significant_after_correction", "p2bb_above_threshold"))
        reasons = ["sample_reached"]
        reasons.append("significant_after_correction" if inp.significant_vs_control else "not_significant")
        reasons.append("p2bb_above_threshold" if inp.p2bb_leader >= inp.p2bb_threshold else "p2bb_below_threshold")
        reasons.append("effect_below_mde")
        return Decision(VerdictCode.CALL_NO_DIFFERENCE, 0.0, tuple(reasons))

    return Decision(VerdictCode.WAIT_SAMPLE, inp.days_to_sample, ("sample_not_reached", "peeking_guard"))
