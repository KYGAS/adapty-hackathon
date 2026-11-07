import Icon from './Icon';
import { Hint } from './common';
import { EMPTY, money, num, pValue, pct } from '../lib/format';
import type { AdaptyArm, AdaptyMetricsRow } from '../lib/types';

export const SERIES = ['var(--series-a)', 'var(--series-b)', 'var(--series-c)', 'var(--series-d)', 'var(--series-e)'];

interface Props {
  arms: AdaptyArm[];
  rows: AdaptyMetricsRow[]; // per-arm metrics (items of the metrics list row, or metrics total)
  total?: AdaptyMetricsRow | null;
  single?: boolean;
}

export function RangeCell({ row, color }: { row: AdaptyMetricsRow; color: string }) {
  const payers = row.unique_paid_subscribers ?? 0;
  if (!row.average_per_1000) return <td className="is-right is-empty">{EMPTY}</td>;
  if (payers < 50) {
    return (
      <td className="is-right">
        <Hint muted text={`Adapty estimates the range from 50 payers. This arm has ${payers}, so the range is shown as zero to twice the mean.`}>
          <span className="ad-text-secondary">not enough payers</span>
        </Hint>
      </td>
    );
  }
  return (
    <td className="is-right">
      <div className="ad-range" style={{ ['--series-color' as string]: color }}>
        <span>{money(row.low_boundary)}</span>
        <span className="ad-range__track">
          <span className="ad-range__point" style={{ left: '50%' }} />
          <span className="ad-range__value" style={{ left: '50%' }}>{money(row.average_per_1000)}</span>
        </span>
        <span>{money(row.upper_boundary)}</span>
      </div>
    </td>
  );
}

export default function VariantTable({ arms, rows, total, single }: Props) {
  const byFlow = new Map(rows.map((r) => [r.flow_id, r]));
  const leaderFlow = rows.reduce<AdaptyMetricsRow | null>((best, r) => ((r.probability ?? 0) > (best?.probability ?? 0) ? r : best), null)?.flow_id;
  const cols = ['Predicted P2BB', 'p-value', 'Proceeds', 'Net proceeds', 'CR purchases', 'CR trials', 'Views'];
  return (
    <div className="ad-table-scroll">
      <table className="ad-vtable" style={{ minWidth: 1700 }}>
        <colgroup>
          <col style={{ width: 40 }} />
          <col style={{ width: 310 }} />
          <col style={{ width: 150 }} />
          <col style={{ width: 300 }} />
          <col style={{ width: 150 }} />
          {cols.map((c) => (
            <col key={c} style={{ width: 150 }} />
          ))}
        </colgroup>
        <thead>
          <tr>
            <th className="ad-col-settings" data-hint="Configure columns">
              <Icon name="sliders" size={16} />
            </th>
            <th>{single ? 'Flow' : 'Variant/Flow'}</th>
            <th className="is-right">
              <Hint muted title="Revenue" text="Total revenue from purchases made after viewing the variant.">Revenue</Hint>
            </th>
            <th className="is-right">
              <Hint muted title="Revenue per 1K users" text="Estimated revenue per 1,000 unique viewers with a 99% range. Needs 50 payers.">Revenue per 1K users</Hint>
            </th>
            <th className="is-right">
              <Hint muted title="P2BB" text="Probability to be best by revenue per viewer, from Adapty's Bayesian model.">P2BB</Hint>
            </th>
            {cols.map((c) => (
              <th key={c} className="is-right">
                <Hint muted text={c}>{c}</Hint>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {arms.map((arm, i) => {
            const r = byFlow.get(arm.flow_id) ?? ({ views: 0, revenue: 0, proceeds: 0, net_revenue: 0, purchases: 0, trials: 0, unique_paid_subscribers: 0, conversion_rate_purchases: 0, conversion_rate_trials: 0 } as AdaptyMetricsRow);
            const winner = !single && leaderFlow === arm.flow_id && (r.probability ?? 0) > 50;
            return (
              <tr key={arm.flow_id} className="is-pressable">
                <td className="ad-variant__letter" style={{ textAlign: 'center' }}>{single ? '' : arm.title}</td>
                <td>
                  <div className="ad-variant">
                    <span className="ad-thumb">
                      <Icon name="image" size={16} />
                    </span>
                    <div style={{ minWidth: 0 }}>
                      <div className="ad-variant__name ad-ellipsis ad-hint" data-hint-title={arm.flow_name} data-hint="Open the flow in Flow Builder">{arm.flow_name}</div>
                      {!single && (
                        <div className="ad-variant__sub">
                          {arm.title} · <span className="ad-tag ad-tag--white ad-hint" data-hint="Share of audience traffic">Weight: {arm.weight}%</span>
                        </div>
                      )}
                    </div>
                  </div>
                </td>
                <td className="is-right">{money(r.revenue)}</td>
                <RangeCell row={r} color={SERIES[i % SERIES.length]} />
                <td className={`is-right ${winner ? 'ad-text-winner' : ''}`}>{single || r.probability === undefined ? <span className="is-empty">{EMPTY}</span> : pct(r.probability, 2)}</td>
                <td className="is-right ad-text-secondary">insufficient data</td>
                <td className="is-right">{pValue(r.p_value ?? null)}</td>
                <td className="is-right">{money(r.proceeds)}</td>
                <td className="is-right">{money(r.net_revenue)}</td>
                <td className="is-right">{pct(r.conversion_rate_purchases)}</td>
                <td className="is-right">{pct(r.conversion_rate_trials, 1)}</td>
                <td className="is-right">{num(r.views)}</td>
              </tr>
            );
          })}
          {!single && total && (
            <tr>
              <td className="is-total" colSpan={2}>Total</td>
              <td className="is-right is-total">{money(total.revenue)}</td>
              <td className="is-right is-empty">{EMPTY}</td>
              <td className="is-right is-empty">{EMPTY}</td>
              <td className="is-right is-empty">{EMPTY}</td>
              <td className="is-right is-empty">{EMPTY}</td>
              <td className="is-right is-total">{money(total.proceeds)}</td>
              <td className="is-right is-total">{money(total.net_revenue)}</td>
              <td className="is-right is-total">{pct(total.conversion_rate_purchases)}</td>
              <td className="is-right is-total">{pct(total.conversion_rate_trials, 1)}</td>
              <td className="is-right is-total">{num(total.views)}</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
