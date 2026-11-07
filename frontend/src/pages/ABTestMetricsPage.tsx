import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import { RangeCell, SERIES } from '../components/VariantTable';
import BarCompare from '../components/charts/BarCompare';
import DossierPanel from '../components/referee/DossierPanel';
import { Breadcrumb, ErrorBox, Skeleton, SortTh, StatusText, toast } from '../components/common';
import { adapty } from '../lib/api';
import { durationBetween, fmtDate, money, num, pValue, pct } from '../lib/format';
import { useAsync } from '../lib/useAsync';

const METRICS: Array<[string, string]> = [
  ['Revenue', 'Total revenue from purchases after viewing the variant'],
  ['Revenue per 1K users', '99% range of revenue per 1,000 unique viewers. Needs 50 payers.'],
  ['P2BB', 'Probability to be best by revenue per viewer'],
  ['p-value', 'Two-arm flow tests only'],
  ['Purchases', 'Paid purchases'],
  ['Trials', 'Trials started'],
  ['Views', 'Flow views'],
  ['Unique views', 'Unique profiles that viewed the flow'],
  ['CR purchases', 'Purchases over views'],
  ['CR trials', 'Trials over views'],
  ['ARPU', 'Revenue per viewer'],
  ['ARPPU', 'Revenue per paying user'],
  ['Proceeds', 'Revenue after store commission'],
  ['Net proceeds', 'Proceeds after taxes'],
];

export default function ABTestMetricsPage() {
  const { id = '' } = useParams();
  const page = useAsync(async () => {
    const detail = await adapty.getTest(id);
    const total = detail.state === 'draft' ? null : (await adapty.metricsTotal(id)).data;
    return { detail, total };
  }, [id]);
  const { data, error, loading, reload } = page;
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) {
    return (
      <>
        <Skeleton width={420} height={24} className="rf-mb-24" />
        <Skeleton width={900} height={160} />
      </>
    );
  }
  const { detail, total } = data;
  const arms = total?.metrics ?? [];
  const totalRevenue = arms.reduce((s, a) => s + (a.revenue || 0), 0);
  const leader = arms.reduce<typeof arms[number] | null>((best, a) => ((a.probability ?? 0) > (best?.probability ?? 0) ? a : best), null);
  const sorted = [...arms].sort((a, b) => (b.probability ?? 0) - (a.probability ?? 0) || b.revenue - a.revenue);
  return (
    <>
      <div className="ad-page-header ad-page-header--center">
        <Breadcrumb parent="A/B tests" parentHref="/ab-tests/flows" current={detail.title} />
        <div className="ad-header-actions ad-header-actions--links">
          <button className="ad-btn ad-btn--ghost" onClick={() => toast('Analytics is not part of this demo', 'info')}><Icon name="trend" />View in analytics</button>
          <button className="ad-btn ad-btn--ghost" onClick={() => toast('A/B test duplicated as draft (demo)')}><Icon name="copy" />Duplicate</button>
          <button className="ad-btn ad-btn--ghost" onClick={() => toast('Modify opens the create form in Adapty. Not part of this demo.', 'info')}><Icon name="pencil" />Modify</button>
          {detail.state === 'live' && (
            <a className="ad-btn ad-btn--ghost" href="#referee" data-hint="Stopping goes through the Referee below"><Icon name="stop" />Stop</a>
          )}
        </div>
      </div>
      <div className="ad-toolbar" style={{ marginBottom: 8 }}>
        <div className="ad-toolbar__group" style={{ gap: 16 }}>
          <div className="ad-menu-anchor">
            <button className="ad-dropdown-btn" data-menu-trigger="">
              <Icon name="calendar" size={16} />{fmtDate(detail.started_at)} - today <span className="ad-dropdown-btn__sep" /> Lifetime <Icon name="chevron-down" size={16} />
            </button>
            <ul className="ad-menu ad-menu--left">
              <li className="ad-menu__item">Lifetime (flow tests report lifetime numbers without a date)</li>
            </ul>
          </div>
          <div className="ad-menu-anchor">
            <button className="ad-dropdown-btn" data-menu-trigger="">Group by Flow <Icon name="chevron-down" size={16} /></button>
            <ul className="ad-menu ad-menu--left"><li className="ad-menu__item">Flow</li><li className="ad-menu__item">Country</li><li className="ad-menu__item">Store</li></ul>
          </div>
        </div>
        <div className="ad-toolbar__group" style={{ gap: 16 }}>
          <label className="ad-checkbox">
            <input type="checkbox" />
            <span className="ad-checkbox__box"><svg viewBox="0 0 20 20"><path d="m4 10.5 4 4 8-9" /></svg></span>
            Filter metrics by install date
          </label>
          <button className="ad-icon-btn ad-icon-btn--plain" data-hint="Export CSV" onClick={() => toast('CSV export is not part of this demo', 'info')}><Icon name="download" /></button>
        </div>
      </div>
      <button className="ad-add-filter rf-mb-24"><span className="ad-add-filter__icon"><Icon name="plus" size={16} /></span>Add filter</button>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 244px', gap: 8, marginBottom: 24, alignItems: 'start' }}>
        <div className="ad-panel" style={{ display: 'grid', gridTemplateColumns: '140px 1fr', gap: 24, alignItems: 'start' }}>
          <div className="ad-kpi">
            <span className="ad-kpi__label">Revenue <Icon name="chevron-down" size={16} /></span>
            <span className="ad-kpi__value">{money(totalRevenue)}</span>
          </div>
          {arms.length ? (
            <BarCompare bars={arms.map((a, i) => ({ key: a.flow_id ?? String(i), label: a.title ?? String.fromCharCode(65 + i), sublabel: detail.flows.find((f) => f.flow_id === a.flow_id)?.flow_name, value: a.revenue, format: (v) => money(v) }))} />
          ) : (
            <p className="ad-caption">No metrics yet: the test has not started.</p>
          )}
        </div>
        <div className="ad-panel">
          <dl className="ad-dl">
            <dt>Status</dt><dd><StatusText state={detail.state} /></dd>
            <dt>Started at</dt><dd>{fmtDate(detail.started_at)}</dd>
            <dt>Duration</dt><dd>{durationBetween(detail.started_at, detail.stopped_at)}</dd>
            <dt>Placement</dt><dd className="ad-ellipsis"><Link className="ad-link" to={`/placements/flows/${detail.placement.placement_id}`}>{detail.placement.title}</Link></dd>
          </dl>
        </div>
      </div>

      {arms.length > 0 && (
        <div className="ad-table-scroll rf-mb-24">
          <table className="ad-grid">
            <thead>
              <tr>
                <th className="c-name" style={{ minWidth: 360 }}><Icon name="chevron-down" size={16} /> Flow</th>
                {METRICS.map(([m, help], i) => <SortTh key={m} label={m} right help={help} sorted={i === 0} />)}
              </tr>
            </thead>
            <tbody>
              {sorted.map((a, i) => {
                const flow = detail.flows.find((f) => f.flow_id === a.flow_id);
                const winner = leader?.flow_id === a.flow_id && (a.probability ?? 0) > 50;
                const cell = (content: React.ReactNode, sortedCol = false) => <td className={`is-right ${sortedCol ? 'is-sorted' : ''} ${winner ? 'is-winner' : ''}`}>{content}</td>;
                return (
                  <tr key={a.flow_id}>
                    <td>
                      <div className="ad-row" style={{ justifyContent: 'space-between' }}>
                        <span className="ad-row">
                          <Icon name="chevron-down" size={16} />
                          <label className="ad-checkbox ad-checkbox--series" style={{ ['--series-color' as string]: SERIES[i % SERIES.length] }}>
                            <input type="checkbox" defaultChecked />
                            <span className="ad-checkbox__box"><svg viewBox="0 0 20 20"><path d="m4 10.5 4 4 8-9" /></svg></span>
                            {a.title} <span className="rf-muted" style={{ marginLeft: 6 }}>{flow?.flow_name}</span>
                          </label>
                        </span>
                        <span className="ad-pill ad-pill--grayborder">{a.weight}%</span>
                      </div>
                    </td>
                    {cell(money(a.revenue), true)}
                    <RangeCell row={a} color={SERIES[i % SERIES.length]} />
                    {cell(a.probability === undefined ? '-' : pct(a.probability, 2))}
                    {cell(pValue(a.p_value ?? null))}
                    {cell(num(a.purchases))}
                    {cell(num(a.trials))}
                    {cell(num(a.views))}
                    {cell(num(a.unique_profiles_views))}
                    {cell(pct(a.conversion_rate_purchases))}
                    {cell(pct(a.conversion_rate_trials, 1))}
                    {cell(money(a.arpu, { exact: true }))}
                    {cell(money(a.arppu, { exact: true }))}
                    {cell(money(a.proceeds))}
                    {cell(money(a.net_revenue))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      <div id="referee" className="rf-mt-40">
        <div className="ad-row rf-mb-16" style={{ gap: 8 }}>
          <Icon name="flask" />
          <h4 className="ad-h4">Experiment Referee</h4>
          <span className="ad-pill ad-pill--beta">Beta</span>
          <Link className="ad-link ad-link--small" to={`/referee/${id}`} style={{ marginLeft: 'auto' }}>Open the full dossier</Link>
        </div>
        <DossierPanel testId={id} onChanged={reload} />
      </div>
    </>
  );
}
