import Icon, { type IconName } from './Icon';
import type { Verdict, VerdictCode } from '../lib/types';
import { daysText } from '../lib/format';

interface Style {
  label: string;
  cls: string;
  icon: IconName;
}

export const VERDICT_STYLE: Record<VerdictCode, Style> = {
  WAIT_TRIAL_LAG: { label: 'Wait: trials still open', cls: 'rf-verdict--wait', icon: 'clock' },
  WAIT_SAMPLE: { label: 'Wait: sample not reached', cls: 'rf-verdict--wait', icon: 'clock' },
  WAIT_MIN_RUNTIME: { label: 'Wait: first full week', cls: 'rf-verdict--wait', icon: 'clock' },
  INSUFFICIENT_PAYERS: { label: 'Not yet: under 50 payers', cls: 'rf-verdict--wait', icon: 'clock' },
  NOT_DECIDABLE: { label: 'Not decidable at this traffic', cls: 'rf-verdict--blocked', icon: 'warning' },
  CALL_WINNER: { label: 'Call it: winner', cls: 'rf-verdict--call', icon: 'check-circle' },
  CALL_NO_DIFFERENCE: { label: 'Call it: no difference', cls: 'rf-verdict--call', icon: 'check-circle' },
  NOT_STARTED: { label: 'Ready to start', cls: 'rf-verdict--neutral', icon: 'play' },
  COMPLETED: { label: 'Completed: audited', cls: 'rf-verdict--done', icon: 'archive' },
};

export const REASON_LABEL: Record<string, string> = {
  open_trials_can_flip_leader: 'Open trials could still change who leads on revenue per viewer.',
  wait_for_maturation: 'Day-one revenue is being compared against trials that have not finished.',
  sample_unreachable_within_max_wait: 'The planned minimum effect needs more viewers than this traffic delivers within the wait limit.',
  consider_bigger_change_or_wider_audience: 'Test a bolder change, widen the audience, or accept a larger minimum effect.',
  leader_payers_below_50: "Fewer than 50 payers: Adapty's revenue range per 1,000 viewers is not estimable yet.",
  revenue_range_not_estimable: 'Below 50 payers the range is shown as zero to twice the mean.',
  sample_reached: 'Each arm has the viewers the plan asked for.',
  min_runtime_not_reached: 'The test has not covered a full week yet.',
  weekly_seasonality_guard: 'Weekend and weekday users convert differently.',
  significant_after_correction: 'The paid conversion difference is significant after correction.',
  not_significant: 'The paid conversion difference is not significant after correction.',
  p2bb_above_threshold: "Adapty's probability to be best is above the 95% bar.",
  p2bb_below_threshold: "Adapty's probability to be best is below the 95% bar.",
  effect_below_mde: 'Any difference is smaller than the effect the test was sized to detect.',
  sample_not_reached: 'The smallest arm has not reached the planned sample yet.',
  peeking_guard: 'Stopping on a good day inflates false positives; the referee waits for the sample.',
  no_views_yet: 'No viewers attributed yet.',
  state_draft: 'The test has not started.',
};

export function reasonLabel(code: string): string {
  if (REASON_LABEL[code]) return REASON_LABEL[code];
  if (code.startsWith('leader_payers_below_')) return REASON_LABEL.leader_payers_below_50;
  if (code.startsWith('state_')) return `The test is ${code.replace('state_', '')}.`;
  return code.replace(/_/g, ' ');
}

export default function VerdictText({ verdict, compact }: { verdict: Verdict; compact?: boolean }) {
  const style = VERDICT_STYLE[verdict.code];
  const wait = verdict.wait_days > 0 && !verdict.is_call && verdict.code !== 'COMPLETED' && verdict.code !== 'NOT_STARTED'
    ? ` (${daysText(verdict.wait_days)})`
    : '';
  return (
    <span className={`rf-verdict ${style.cls}`} data-hint-title="Experiment Referee" data-hint={verdict.headline}>
      <Icon name={style.icon} size={16} />
      {compact ? style.label : `Referee: ${style.label}${wait}`}
    </span>
  );
}
