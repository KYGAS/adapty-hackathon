// Types mirror backend/referee/models.py and the Adapty developer API answers.

export type VerdictCode =
  | 'NOT_STARTED'
  | 'COMPLETED'
  | 'WAIT_TRIAL_LAG'
  | 'INSUFFICIENT_PAYERS'
  | 'WAIT_MIN_RUNTIME'
  | 'WAIT_SAMPLE'
  | 'NOT_DECIDABLE'
  | 'CALL_WINNER'
  | 'CALL_NO_DIFFERENCE';

export interface TrialProduct {
  product_id: string;
  title: string;
  price_usd: number;
  trial_days: number;
}

export interface PendingRevenue {
  pending_trials: number;
  conversions_low: number;
  conversions_expected: number;
  conversions_high: number;
  revenue_low: number;
  revenue_expected: number;
  revenue_high: number;
}

export interface ArmStats {
  flow_id: string;
  title: string;
  flow_name: string;
  weight: number;
  is_control: boolean;
  is_leader: boolean;
  views: number;
  purchases: number;
  trials: number;
  payers: number;
  revenue: number;
  conversion_rate: number;
  conversion_ci_low: number;
  conversion_ci_high: number;
  trial_rate: number;
  revenue_per_viewer: number;
  p2bb: number | null;
  range_low: number | null;
  range_mean: number | null;
  range_high: number | null;
  range_reliable: boolean;
  trial_products: TrialProduct[];
  trial_days_max: number;
  trials_pending: number;
  trials_matured: number;
  maturation_fraction: number;
  matures_at: string | null;
  pending: PendingRevenue;
  projected_rpv_low: number;
  projected_rpv_expected: number;
  projected_rpv_high: number;
}

export interface PairwiseTest {
  arm_title: string;
  control_title: string;
  control_rate: number;
  arm_rate: number;
  difference: number;
  relative_lift: number | null;
  z: number;
  p_value: number;
  adjusted_p: number;
  significant: boolean;
}

export interface SampleSize {
  alpha: number;
  power: number;
  mde_relative: number;
  baseline_rate: number;
  baseline_source: string;
  required_per_arm: number | null;
  min_views_per_arm: number;
  progress: number;
  viewers_per_day: number;
  viewers_per_day_smallest_arm: number;
  days_to_sample: number | null;
  sample_reached_at: string | null;
  mde_detectable_now: number | null;
  mde_detectable_at_horizon: number | null;
  views_per_arm_at_horizon: number;
}

export interface RateEstimate {
  rate: number;
  low: number;
  high: number;
  sample_size: number;
}

export interface TrialLagSummary {
  history_rate: RateEstimate;
  history_source: string;
  pending_trials_total: number;
  pending_revenue_expected_total: number;
  leader_could_flip: boolean;
  matures_at: string | null;
  days_to_maturity: number;
  min_maturation_fraction: number;
}

export interface Timeline {
  now: string;
  started_at: string | null;
  days_running: number;
  horizon_days: number;
  horizon_date: string | null;
  maturity_date: string | null;
  sample_date: string | null;
  min_runtime_date: string | null;
  decision_date: string | null;
  days_to_decision: number | null;
}

export interface Verdict {
  code: VerdictCode;
  headline: string;
  leader_title: string | null;
  leader_flow_id: string | null;
  runner_up_title: string | null;
  p2bb_leader: number | null;
  wait_days: number;
  decision_date: string | null;
  reasons: string[];
  is_call: boolean;
}

export type ActionKind = 'stop_winner' | 'stop_other' | 'keep_running' | 'start_draft' | 'archive' | 'none';

export interface ActionPreview {
  id: string;
  kind: ActionKind;
  title: string;
  description: string;
  recommended: boolean;
  risk: 'none' | 'reversible' | 'irreversible';
  cli_command: string | null;
  api_method: string | null;
  api_path: string | null;
  api_body: Record<string, unknown> | null;
  requires_approval: boolean;
  dry_run: boolean;
}

export interface EvidenceAtStop {
  payers_leader: number;
  min_views_per_arm: number;
  required_per_arm: number | null;
  sample_progress: number;
  p_value: number | null;
  p2bb_leader: number | null;
  days_running: number;
}

export interface RealizedOutcome {
  winner_flow_views: number;
  winner_flow_revenue: number;
  winner_rpv: number;
  alternative_flow_views: number;
  alternative_flow_revenue: number;
  alternative_rpv: number;
  delta_rpv: number;
  status: 'confirmed' | 'reversed' | 'inconclusive';
  source: string;
}

export interface AuditResult {
  stopped_at: string | null;
  duration_days: number;
  declared_winner_flow_id: string | null;
  declared_winner_title: string | null;
  evidence: EvidenceAtStop;
  score: number;
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  grade_reasons: string[];
  realized: RealizedOutcome | null;
}

export interface TestSummary {
  test_id: string;
  title: string;
  goal: string | null;
  type: string;
  state: string;
  placement_id: string | null;
  placement_title: string | null;
  segment_ids: string[];
  started_at: string | null;
  stopped_at: string | null;
  arm_count: number;
}

export interface Assumptions {
  alpha: number;
  power: number;
  mde_relative: number;
  p2bb_threshold: number;
  payers_threshold: number;
  min_runtime_days: number;
  max_wait_days: number;
  grace_days: number;
  correction: string;
  default_horizon_days: number;
}

export interface Dossier {
  generated_at: string;
  app_id: string;
  test: TestSummary;
  assumptions: Assumptions;
  arms: ArmStats[];
  control_title: string;
  leader_title: string | null;
  pairwise: PairwiseTest[];
  correction_method: string;
  sample: SampleSize;
  trial_lag: TrialLagSummary;
  timeline: Timeline;
  verdict: Verdict;
  warnings: string[];
  actions: ActionPreview[];
  audit: AuditResult | null;
}

export interface Memo {
  headline: string;
  summary: string;
  memo_markdown: string;
  risks: string[];
  next_steps: string[];
}

export interface Narration {
  provider: string;
  model: string | null;
  memo: Memo;
  guard_passed: boolean;
  guard_violations: string[];
  attempts: number;
  fallback_used: boolean;
  elapsed_ms: number;
}

export interface OverviewRow {
  test_id: string;
  title: string;
  state: string;
  placement_id?: string | null;
  placement_title?: string | null;
  started_at?: string | null;
  stopped_at?: string | null;
  verdict?: Verdict;
  timeline?: Timeline;
  warnings?: string[];
  recommended_action?: ActionPreview | null;
  audit_grade?: string | null;
  pending_trials?: number;
  sample_progress?: number;
  error?: string;
}

export interface Opportunity {
  placement_id: string;
  developer_id: string;
  title: string;
  has_live_test: boolean;
  draft_test_id: string | null;
  draft_test_title: string | null;
  flows: string[];
  views: number;
  revenue: number;
  revenue_per_viewer: number;
  score: number;
  rank: number;
  suggestion: string;
  action: ActionPreview | null;
}

export interface ExecuteResult {
  status: 'dry_run' | 'executed' | 'nothing_to_run';
  test_id: string;
  verdict: string;
  command: string;
  action: ActionPreview;
  adapty_status?: number;
  adapty_response?: unknown;
}

export interface AuditLogEntry {
  at: string;
  mode: string;
  event: 'dry_run' | 'executed' | 'blocked' | 'failed';
  test_id: string;
  verdict: string;
  command: string;
  action: ActionPreview;
  approver?: string;
  note?: string | null;
  adapty_status?: number;
}

export interface Health {
  ok: boolean;
  adapty_mode: 'mock' | 'live';
  app_id: string;
  live_writes_allowed: boolean;
  llm_provider_setting: string;
  anthropic_api_key_present: boolean;
  claude_cli_found: boolean;
  fixed_now: string | null;
}

// ---- Adapty developer API shapes

export interface Page<T> {
  data: T[];
  meta?: { pagination?: { count: number; page: number; pages: number } };
}

export type TestState = 'live' | 'completed' | 'draft' | 'archived' | 'inactive';

export interface AdaptyTestListed {
  ab_test_id: string;
  title: string;
  type: 'flow' | 'paywall';
  state: TestState;
  placement: { placement_id: string; title: string };
  segment_ids: string[];
  priority: number;
  started_at: string | null;
  stopped_at: string | null;
}

export interface AdaptyArm {
  flow_id: string;
  flow_name: string;
  weight: number;
  title: string;
  variation_id: string;
}

export interface AdaptyTestDetail extends AdaptyTestListed {
  goal: string | null;
  flows: AdaptyArm[];
}

export interface AdaptyMetricsRow {
  views: number;
  unique_profiles_views: number;
  total_completions?: number;
  total_uniq_completions?: number;
  revenue: number;
  proceeds: number;
  net_revenue: number;
  purchases: number;
  trials: number;
  unique_subscribers?: number;
  unique_paid_subscribers: number;
  arppu: number;
  arpu: number;
  conversion_rate_purchases: number;
  conversion_rate_trials: number;
  trials_cancelled?: number;
  refunds?: number;
  conversion_rate_trial_paid?: number;
  users?: number;
  installs?: number;
  title?: string;
  variation_id?: string;
  flow_id?: string;
  weight?: number;
  low_boundary?: number;
  average_per_1000?: number;
  upper_boundary?: number;
  probability?: number;
  p_value?: number | null;
  active_trials_rate?: number;
  ab_test_id?: string;
  level?: string;
  items?: AdaptyMetricsRow[];
}

export interface AdaptyMetricsTotal {
  metrics: AdaptyMetricsRow[];
  ab_test: { ab_test_id: string; title: string; goal: string | null };
  state: TestState;
  started_at: string | null;
  stopped_at: string | null;
  active_trials_rate: number;
}

export interface AdaptyAudience {
  content_type: string;
  segment_ids: string[];
  priority: number;
  ab_test_id?: string;
  ab_test_title?: string;
  flow_id?: string;
  flow_title?: string;
}

export interface AdaptyPlacement {
  id: string;
  developer_id: string;
  title: string;
  is_active: boolean;
  type: 'flow' | 'paywall';
  audiences?: AdaptyAudience[];
}

export interface AdaptyFlow {
  id: string;
  name: string;
  status: string;
  creation_source: string;
  updated_at: string;
}

export interface AdaptyFlowMetrics {
  flow_id: string;
  views: number;
  unique_profiles_views: number;
  total_completions?: number;
  total_uniq_completions?: number;
  purchases: number;
  trials: number;
  revenue: number;
  refunds?: number;
  unique_paid_subscribers: number;
  arpu: number;
}

export interface AdaptySegment {
  id: string;
  title: string;
  description: string;
}
