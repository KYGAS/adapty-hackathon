"""Typed inputs and the TestDossier. Every number the LLM may mention lives in one of these models."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

VerdictLiteral = Literal[
    "NOT_STARTED", "COMPLETED", "WAIT_TRIAL_LAG", "INSUFFICIENT_PAYERS", "WAIT_MIN_RUNTIME",
    "WAIT_SAMPLE", "NOT_DECIDABLE", "CALL_WINNER", "CALL_NO_DIFFERENCE",
]


# ---------------------------------------------------------------- inputs


class TrialProduct(BaseModel):
    product_id: str
    title: str
    price_usd: float
    trial_days: int


class ArmInput(BaseModel):
    flow_id: str
    variation_id: str | None = None
    title: str
    flow_name: str
    weight: float = 50.0
    views: int = 0
    purchases: int = 0
    trials: int = 0
    payers: int = 0
    revenue: float = 0.0
    p2bb: float | None = None
    range_low: float | None = None
    range_mean: float | None = None
    range_high: float | None = None
    p_value: float | None = None
    active_trials_rate: float | None = None
    products: list[TrialProduct] = Field(default_factory=list)
    trial_mix: dict[str, int] = Field(default_factory=dict)  # product title -> trials started on it (from the metrics tree)


class TestInput(BaseModel):
    test_id: str
    title: str
    goal: str | None = None
    type: str = "flow"
    state: str
    placement_id: str | None = None
    placement_title: str | None = None
    segment_ids: list[str] = Field(default_factory=list)
    started_at: datetime | None = None
    stopped_at: datetime | None = None
    arms: list[ArmInput]
    winner_flow_id: str | None = None


class HistoryInput(BaseModel):
    """Account-level history the referee borrows when a test is too young to have its own."""
    trials_started: int = 0
    trials_paid: int = 0
    source: str = "analytics conversion trial-paid"
    by_product: dict[str, tuple[int, int]] = Field(default_factory=dict)  # product title -> (trials started, trials paid)


class Assumptions(BaseModel):
    alpha: float = 0.05
    power: float = 0.8
    mde_relative: float = 0.20
    p2bb_threshold: float = 95.0
    payers_threshold: int = 50
    min_runtime_days: float = 7.0
    max_wait_days: float = 60.0
    grace_days: int = 1
    correction: str = "holm"
    default_horizon_days: int = 30


# ---------------------------------------------------------------- dossier


class RateEstimateModel(BaseModel):
    rate: float
    low: float
    high: float
    sample_size: int


class PendingRevenueModel(BaseModel):
    pending_trials: int
    conversions_low: float
    conversions_expected: float
    conversions_high: float
    revenue_low: float
    revenue_expected: float
    revenue_high: float


class ArmStats(BaseModel):
    flow_id: str
    title: str
    flow_name: str
    weight: float
    is_control: bool
    is_leader: bool
    views: int
    purchases: int
    trials: int
    payers: int
    revenue: float
    conversion_rate: float
    conversion_ci_low: float
    conversion_ci_high: float
    trial_rate: float
    revenue_per_viewer: float
    p2bb: float | None
    range_low: float | None
    range_mean: float | None
    range_high: float | None
    range_reliable: bool
    trial_products: list[TrialProduct]
    trial_days_max: int
    trials_pending: int
    trials_matured: int
    maturation_fraction: float
    matures_at: datetime | None
    trial_to_paid: RateEstimateModel
    trial_to_paid_source: str
    pending: PendingRevenueModel
    projected_rpv_low: float
    projected_rpv_expected: float
    projected_rpv_high: float


class PairwiseTest(BaseModel):
    arm_title: str
    control_title: str
    control_rate: float
    arm_rate: float
    difference: float
    relative_lift: float | None
    z: float
    p_value: float
    adjusted_p: float
    significant: bool


class SampleSize(BaseModel):
    alpha: float
    power: float
    mde_relative: float
    baseline_rate: float
    baseline_source: str
    required_per_arm: int | None
    min_views_per_arm: int
    progress: float
    viewers_per_day: float
    viewers_per_day_smallest_arm: float
    days_to_sample: float | None
    sample_reached_at: datetime | None
    mde_detectable_now: float | None
    mde_detectable_at_horizon: float | None
    views_per_arm_at_horizon: int


class TrialLagSummary(BaseModel):
    history_rate: RateEstimateModel
    history_source: str
    pending_trials_total: int
    pending_revenue_expected_total: float
    leader_could_flip: bool
    matures_at: datetime | None
    days_to_maturity: float
    min_maturation_fraction: float


class Timeline(BaseModel):
    now: datetime
    started_at: datetime | None
    days_running: float
    horizon_days: int
    horizon_date: datetime | None
    maturity_date: datetime | None
    sample_date: datetime | None
    min_runtime_date: datetime | None
    decision_date: datetime | None
    days_to_decision: float | None


class Verdict(BaseModel):
    code: VerdictLiteral
    headline: str
    leader_title: str | None
    leader_flow_id: str | None
    runner_up_title: str | None
    p2bb_leader: float | None
    wait_days: float
    decision_date: datetime | None
    reasons: list[str]
    is_call: bool


class ActionPreview(BaseModel):
    id: str
    kind: Literal["stop_winner", "stop_other", "keep_running", "start_draft", "archive", "none"]
    title: str
    description: str
    recommended: bool
    risk: Literal["none", "reversible", "irreversible"]
    cli_command: str | None
    api_method: str | None
    api_path: str | None
    api_body: dict | None
    requires_approval: bool = True
    dry_run: bool = True


class EvidenceAtStop(BaseModel):
    payers_leader: int
    min_views_per_arm: int
    required_per_arm: int | None
    sample_progress: float
    p_value: float | None
    p2bb_leader: float | None
    days_running: float


class RealizedOutcome(BaseModel):
    winner_flow_views: int
    winner_flow_revenue: float
    winner_rpv: float
    alternative_flow_views: int
    alternative_flow_revenue: float
    alternative_rpv: float
    delta_rpv: float
    status: Literal["confirmed", "reversed", "inconclusive"]
    source: str


class AuditResult(BaseModel):
    stopped_at: datetime | None
    duration_days: float
    declared_winner_flow_id: str | None
    declared_winner_title: str | None
    evidence: EvidenceAtStop
    score: int
    grade: Literal["A", "B", "C", "D", "F"]
    grade_reasons: list[str]
    realized: RealizedOutcome | None


class TestSummary(BaseModel):
    test_id: str
    title: str
    goal: str | None
    type: str
    state: str
    placement_id: str | None
    placement_title: str | None
    segment_ids: list[str]
    started_at: datetime | None
    stopped_at: datetime | None
    arm_count: int


class TestDossier(BaseModel):
    generated_at: datetime
    app_id: str
    test: TestSummary
    assumptions: Assumptions
    arms: list[ArmStats]
    control_title: str
    leader_title: str | None
    pairwise: list[PairwiseTest]
    correction_method: str
    sample: SampleSize
    trial_lag: TrialLagSummary
    timeline: Timeline
    verdict: Verdict
    warnings: list[str]
    actions: list[ActionPreview]
    audit: AuditResult | None = None


# ---------------------------------------------------------------- narration


class Memo(BaseModel):
    headline: str
    summary: str
    memo_markdown: str
    risks: list[str] = Field(default_factory=list)
    next_steps: list[str] = Field(default_factory=list)


class Narration(BaseModel):
    provider: str
    model: str | None
    memo: Memo
    guard_passed: bool
    guard_violations: list[str] = Field(default_factory=list)
    attempts: int
    fallback_used: bool
    elapsed_ms: int


class PlacementOpportunity(BaseModel):
    placement_id: str
    developer_id: str
    title: str
    has_live_test: bool
    draft_test_id: str | None
    draft_test_title: str | None
    flows: list[str]
    views: int
    revenue: float
    revenue_per_viewer: float
    score: float
    rank: int
    suggestion: str
    action: ActionPreview | None
