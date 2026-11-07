import { useState } from 'react';
import Icon from '../Icon';
import VerdictText, { reasonLabel } from '../VerdictText';
import { ErrorBox, Hint, Skeleton, StatusText } from '../common';
import RangeBars from '../charts/RangeBars';
import TimelineChart from '../charts/TimelineChart';
import ActionsPanel from './ActionsPanel';
import MemoPanel from './MemoPanel';
import AuditPanel from './AuditPanel';
import { referee, type AssumptionParams } from '../../lib/api';
import { daysText, durationBetween, fmtDate, money, num, pValue, pct, ratio, relativeLift } from '../../lib/format';
import { useAsync } from '../../lib/useAsync';
import type { Dossier } from '../../lib/types';

const WARNING_LABEL: Record<string, string> = {
  trial_to_paid_rate_borrowed_from_account_history: 'Trial-to-paid rate borrowed from account history, not from this test.',
  no_trial_history_rate_unknown: 'No trial history: pending revenue cannot be projected.',
  revenue_range_unreliable_under_50_payers: "Leader has fewer than 50 payers: Adapty's revenue range is not reliable yet.",
  significance_uses_paid_conversion_while_p2bb_uses_revenue: 'Significance is tested on paid conversion; P2BB ranks revenue per viewer. Both must agree.',
  sample_ratio_mismatch: 'Traffic split does not match the weights. Check the assignment before trusting anything.',
  p2bb_not_computed_by_adapty: 'Adapty has not computed P2BB yet (no purchases).',
  trial_length_assumed: 'A trial length was unknown; 7 days assumed.',
  three_or_more_arms_adapty_p_value_absent_pairwise_holm_used: 'Three or more arms: pairwise tests against the control with Holm correction.',
};

const MDE_OPTIONS = [0.1, 0.2, 0.3, 0.5, 1.0];

export function useDossier(testId: string) {
  const [params, setParams] = useState<AssumptionParams>({});
  const state = useAsync(() => referee.dossier(testId, params), [testId, JSON.stringify(params)]);
  return { ...state, params, setParams };
}

export default function DossierPanel({ testId, onChanged }: { testId: string; onChanged?: () => void }) {
  const { data, error, loading, reload, params, setParams } = useDossier(testId);
  const refresh = () => {
    reload();
    onChanged?.();
  };
  if (loading && !data) {
    return (
      <div className="ad-panel">
        <Skeleton width={420} height={20} className="rf-mb-16" />
        <Skeleton width={600} className="rf-mb-8" />
        <Skeleton width={520} />
      </div>
    );
  }
  if (error) return <ErrorBox error={error} />;
  if (!data) return null;
  const d: Dossier = data;
  const { verdict, sample, trial_lag: lag, timeline } = d;
  const leader = d.arms.find((a) => a.is_leader);
  return (
    <div className="rf-panel-grid">
      <div className="ad-stack ad-stack--16">
        <div className="ad-panel">
          <div className="ad-row rf-mb-8" style={{ justifyContent: 'space-between' }}>
            <VerdictText verdict={verdict} compact />
            <label className="ad-row ad-caption" style={{ gap: 8 }}>
              Planned minimum effect
              <select className="ad-input" style={{ height: 32, width: 90, padding: '2px 8px' }} value={params.mde ?? d.assumptions.mde_relative} onChange={(e) => setParams({ ...params, mde: Number(e.target.value) })}>
                {MDE_OPTIONS.map((m) => (
                  <option key={m} value={m}>{Math.round(m * 100)}%</option>
                ))}
              </select>
            </label>
          </div>
          <h3 className="rf-headline">{verdict.headline}</h3>
          <ul className="rf-reasons">
            {verdict.reasons.map((r) => (
              <li key={r}>{reasonLabel(r)}</li>
            ))}
          </ul>
          {d.test.state === 'live' && (
            <div className="rf-mt-24">
              <TimelineChart timeline={timeline} />
            </div>
          )}
        </div>

        <MemoPanel testId={testId} />

        <div className="ad-panel">
          <h4 className="ad-h4 rf-mb-8">Arms</h4>
          <div className="ad-table-scroll">
            <table className="rf-table">
              <thead>
                <tr>
                  <th>Arm</th>
                  <th className="is-right">Viewers</th>
                  <th className="is-right">Purchases</th>
                  <th className="is-right">Payers</th>
                  <th className="is-right">
                    <Hint muted text="Paid conversion with a 95% Wilson interval">CR (95% CI)</Hint>
                  </th>
                  <th className="is-right">Revenue</th>
                  <th className="is-right">Per viewer</th>
                  <th className="is-right">P2BB</th>
                  <th className="is-right">Open trials</th>
                  <th className="is-right">
                    <Hint muted text="Open trials times the historical trial-to-paid rate times the trial plan price">Pending revenue</Hint>
                  </th>
                  <th className="is-right">Matures</th>
                </tr>
              </thead>
              <tbody>
                {d.arms.map((a) => (
                  <tr key={a.flow_id} className={a.is_leader ? 'is-leader' : ''}>
                    <td>
                      <b>{a.title}</b> <span className="rf-muted">{a.flow_name}</span>
                      {a.is_control && <span className="ad-tag ad-tag--gray" style={{ marginLeft: 6 }}>control</span>}
                      {a.is_leader && <span className="ad-tag ad-tag--green" style={{ marginLeft: 6 }}>leader</span>}
                    </td>
                    <td className="is-right">{num(a.views)}</td>
                    <td className="is-right">{num(a.purchases)}</td>
                    <td className="is-right">{num(a.payers)}</td>
                    <td className="is-right">{ratio(a.conversion_rate)} <span className="rf-muted">({ratio(a.conversion_ci_low, 1)} to {ratio(a.conversion_ci_high, 1)})</span></td>
                    <td className="is-right">{money(a.revenue)}</td>
                    <td className="is-right">{money(a.revenue_per_viewer, { exact: true })}</td>
                    <td className="is-right">{a.p2bb === null ? '-' : pct(a.p2bb, 1)}</td>
                    <td className="is-right">{a.trials_pending} <span className="rf-muted">of {a.trials}</span></td>
                    <td className="is-right">{a.trials_pending ? `${money(a.pending.revenue_low)} to ${money(a.pending.revenue_high)}` : '-'}</td>
                    <td className="is-right">{a.matures_at ? fmtDate(a.matures_at) : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          {d.arms.some((a) => a.trials_pending > 0) && (
            <div className="rf-mt-24">
              <h5 className="ad-h5 rf-mb-8">Revenue per viewer once the open trials resolve</h5>
              <RangeBars arms={d.arms} />
            </div>
          )}
        </div>

        <div className="ad-panel">
          <h4 className="ad-h4 rf-mb-8">Statistics</h4>
          <div className="ad-grid" style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 24 }}>
            <div>
              <h5 className="ad-h5 rf-mb-8">Sample size plan</h5>
              <dl className="rf-kv">
                <dt>Baseline conversion</dt><dd>{ratio(sample.baseline_rate)} <span className="rf-muted">({sample.baseline_source})</span></dd>
                <dt>Minimum detectable effect</dt><dd>{Math.round(sample.mde_relative * 100)}% relative</dd>
                <dt>Alpha / power</dt><dd>{sample.alpha} / {sample.power}</dd>
                <dt>Viewers needed per arm</dt><dd>{sample.required_per_arm === null ? 'not plannable yet' : num(sample.required_per_arm)}</dd>
                <dt>Smallest arm today</dt><dd>{num(sample.min_views_per_arm)}</dd>
                <dt>Traffic</dt><dd>{num(sample.viewers_per_day)} viewers/day</dd>
                <dt>Sample reached</dt><dd>{sample.days_to_sample === null ? 'not within reach' : sample.days_to_sample === 0 ? 'yes' : `${fmtDate(sample.sample_reached_at)} (${daysText(sample.days_to_sample)})`}</dd>
                <dt>Detectable effect now</dt><dd>{sample.mde_detectable_now === null ? '-' : `${Math.round(sample.mde_detectable_now * 100)}%`}</dd>
                <dt>Detectable at {timeline.horizon_days}-day horizon</dt><dd>{sample.mde_detectable_at_horizon === null ? '-' : `${Math.round(sample.mde_detectable_at_horizon * 100)}%`}</dd>
              </dl>
              <div className="rf-progress rf-mt-24"><span style={{ width: `${Math.round(sample.progress * 100)}%` }} /></div>
              <div className="ad-caption-sm" style={{ marginTop: 4 }}>{Math.round(sample.progress * 100)}% of the planned sample</div>
            </div>
            <div>
              <h5 className="ad-h5 rf-mb-8">Pairwise vs control ({d.correction_method} correction)</h5>
              {d.pairwise.length === 0 ? (
                <p className="ad-caption">No conversions to compare yet.</p>
              ) : (
                <table className="rf-table">
                  <thead>
                    <tr><th>Arm</th><th className="is-right">Control CR</th><th className="is-right">Arm CR</th><th className="is-right">Lift</th><th className="is-right">p</th><th className="is-right">adj. p</th><th>Result</th></tr>
                  </thead>
                  <tbody>
                    {d.pairwise.map((p) => (
                      <tr key={p.arm_title}>
                        <td>{p.arm_title} vs {p.control_title}</td>
                        <td className="is-right">{ratio(p.control_rate)}</td>
                        <td className="is-right">{ratio(p.arm_rate)}</td>
                        <td className="is-right">{relativeLift(p.relative_lift)}</td>
                        <td className="is-right">{pValue(p.p_value)}</td>
                        <td className="is-right">{pValue(p.adjusted_p)}</td>
                        <td>{p.significant ? <span className="ad-text-success">significant</span> : <span className="rf-muted">not significant</span>}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              )}
              {d.warnings.length > 0 && (
                <>
                  <h5 className="ad-h5 rf-mt-24 rf-mb-8">Caveats</h5>
                  <ul className="rf-reasons">
                    {d.warnings.map((w) => (
                      <li key={w}>{WARNING_LABEL[w] ?? w.replace(/_/g, ' ')}</li>
                    ))}
                  </ul>
                </>
              )}
            </div>
          </div>
        </div>
      </div>

      <aside className="ad-stack ad-stack--16">
        <div className="ad-panel">
          <dl className="ad-dl">
            <dt>Status</dt><dd><StatusText state={d.test.state} /></dd>
            <dt>Started at</dt><dd>{fmtDate(d.test.started_at)}</dd>
            <dt>Duration</dt><dd>{durationBetween(d.test.started_at, d.test.stopped_at ?? timeline.now)}</dd>
            <dt>Placement</dt><dd className="ad-ellipsis">{d.test.placement_title ?? '-'}</dd>
            <dt>Audience</dt><dd>{d.test.segment_ids.length ? 'One segment' : 'All users'}</dd>
            <dt>Goal horizon</dt><dd>{timeline.horizon_days} days</dd>
            <dt>Safe to call</dt><dd>{timeline.decision_date ? fmtDate(timeline.decision_date) : '-'}</dd>
            {leader && (<><dt>Leader</dt><dd>{leader.title} · {leader.p2bb === null ? '-' : pct(leader.p2bb, 1)} P2BB</dd></>)}
          </dl>
        </div>
        <div className="ad-panel">
          <h4 className="ad-h4 rf-mb-8">Trial lag</h4>
          <dl className="rf-kv">
            <dt>Open trials</dt><dd>{num(lag.pending_trials_total)}</dd>
            <dt>Expected pending revenue</dt><dd>{money(lag.pending_revenue_expected_total)}</dd>
            <dt>Trial-to-paid (history)</dt><dd>{ratio(lag.history_rate.rate, 1)} <span className="rf-muted">({ratio(lag.history_rate.low, 1)} to {ratio(lag.history_rate.high, 1)}, n={num(lag.history_rate.sample_size)})</span></dd>
            <dt>All trials mature</dt><dd>{lag.matures_at ? `${fmtDate(lag.matures_at)} (${daysText(lag.days_to_maturity)})` : '-'}</dd>
            <dt>Can flip the leader</dt><dd className={lag.leader_could_flip ? 'ad-text-warning' : ''}>{lag.leader_could_flip ? 'Yes' : 'No'}</dd>
          </dl>
          <p className="ad-caption-sm rf-mt-24">
            <Icon name="info" size={16} style={{ verticalAlign: '-3px', marginRight: 4 }} />
            Rate source: {lag.history_source}.
          </p>
        </div>
        <ActionsPanel testId={testId} actions={d.actions} onChanged={refresh} />
        {d.audit && <AuditPanel audit={d.audit} />}
      </aside>
    </div>
  );
}
