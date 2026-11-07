import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Icon from '../components/Icon';
import { EmptyState, ErrorBox, PageHeader, Pagination, Skeleton, SortTh, StatusText, toast } from '../components/common';
import { adapty } from '../lib/api';
import { money, num } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import type { AdaptyFlowMetrics, AdaptyPlacement, AdaptyTestDetail } from '../lib/types';

export interface PlacementRow {
  placement: AdaptyPlacement;
  flowIds: string[];
  views: number;
  completions: number;
  revenue: number;
  purchases: number;
  liveTest: boolean;
}

/** Flows behind a placement: its audiences' flows plus the arms of its A/B tests. */
export async function loadPlacementRows(): Promise<PlacementRow[]> {
  const [placements, tests, flows] = await Promise.all([adapty.listPlacements(), adapty.listTests(), adapty.listFlows()]);
  const details = await Promise.all(placements.data.map((p) => adapty.getPlacement(p.id)));
  const testDetails = new Map<string, AdaptyTestDetail>();
  await Promise.all(tests.data.map(async (t) => testDetails.set(t.ab_test_id, await adapty.getTest(t.ab_test_id))));
  const metrics = (await adapty.flowMetrics(flows.data.map((f) => f.id))).data;
  const byFlow = new Map<string, AdaptyFlowMetrics>(metrics.map((m) => [m.flow_id, m]));
  return details.map((p) => {
    const flowIds = new Set<string>();
    for (const aud of p.audiences ?? []) {
      if (aud.flow_id) flowIds.add(aud.flow_id);
      if (aud.ab_test_id) testDetails.get(aud.ab_test_id)?.flows.forEach((f) => flowIds.add(f.flow_id));
    }
    for (const t of tests.data) {
      if (t.placement.placement_id === p.id) testDetails.get(t.ab_test_id)?.flows.forEach((f) => flowIds.add(f.flow_id));
    }
    const rows = Array.from(flowIds).map((id) => byFlow.get(id)).filter((m): m is AdaptyFlowMetrics => !!m);
    return {
      placement: p,
      flowIds: Array.from(flowIds),
      views: rows.reduce((s, m) => s + (m.unique_profiles_views || 0), 0),
      completions: rows.reduce((s, m) => s + (m.total_uniq_completions || 0), 0),
      revenue: rows.reduce((s, m) => s + (m.revenue || 0), 0),
      purchases: rows.reduce((s, m) => s + (m.purchases || 0), 0),
      liveTest: tests.data.some((t) => t.placement.placement_id === p.id && t.state === 'live'),
    };
  });
}

export default function PlacementsPage() {
  const navigate = useNavigate();
  const [tab, setTab] = useState<'flows' | 'paywalls'>('flows');
  const [query, setQuery] = useState('');
  const { data, error, loading } = useAsync(loadPlacementRows, []);
  const rows = (data ?? []).filter((r) => r.placement.type === (tab === 'flows' ? 'flow' : 'paywall') && (!query || r.placement.title.toLowerCase().includes(query.toLowerCase()) || r.placement.developer_id.includes(query.toLowerCase())));
  return (
    <>
      <PageHeader title="Placements" />
      <div className="ad-tabs rf-mb-16">
        {(['flows', 'paywalls'] as const).map((t) => (
          <button key={t} className={`ad-tabs__item ${tab === t ? 'is-selected' : ''}`} onClick={() => setTab(t)}>{t === 'flows' ? 'Flows' : 'Paywalls'}</button>
        ))}
      </div>
      <div className="ad-toolbar rf-mb-16" style={{ flexWrap: 'nowrap' }}>
        <div className={`ad-search ${query ? 'has-value' : ''}`} style={{ flex: 1, width: 'auto' }}>
          <input className="ad-input" placeholder="Search by ID and placements names" value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="ad-search__clear" onClick={() => setQuery('')}><Icon name="x" size={16} /></button>
          <span className="ad-search__icon"><Icon name="search" /></span>
        </div>
        <button className="ad-btn ad-btn--secondary ad-btn--with-icon" onClick={() => toast('Fallbacks download is not part of this demo', 'info')}><Icon name="download" />Fallbacks</button>
        <button className="ad-btn ad-btn--secondary ad-btn--with-icon" onClick={() => toast('CSV export is not part of this demo', 'info')}><Icon name="file" />Export to CSV</button>
        <button className="ad-btn ad-btn--primary" onClick={() => toast('Create placement is not part of this demo', 'info')}>Create placement</button>
      </div>
      <ErrorBox error={error} />
      {loading && !data && <Skeleton width="100%" height={240} />}
      {data && rows.length === 0 && <EmptyState icon="pin" text="Here will be stored placements of this type" />}
      {data && rows.length > 0 && (
        <>
          <div className="ad-table-scroll">
            <table className="ad-grid">
              <thead>
                <tr>
                  <SortTh label="Placement name" className="c-name" />
                  <SortTh label="Placement ID" />
                  {[['Unique views', 'Unique profiles that viewed the flows on this placement'], ['Unique completions', 'Unique profiles that completed the flow'], ['Revenue', 'Lifetime revenue of the flows behind this placement'], ['Purchases', 'Lifetime purchases']].map(([m, help]) => (
                    <th key={m} className="is-right"><span className="ad-th-help" data-hint={help}><Icon name="help" />{m}</span></th>
                  ))}
                  <th className="is-sticky-right" style={{ minWidth: 140 }}>Activation state</th>
                  <th style={{ minWidth: 48, width: 48 }} />
                </tr>
              </thead>
              <tbody>
                {rows.map((r) => (
                  <tr key={r.placement.id} className="is-clickable" onClick={(e) => { if (!(e.target as HTMLElement).closest('[data-menu-trigger],.ad-menu,[data-copy]')) navigate(`/placements/flows/${r.placement.id}`); }}>
                    <td>{r.placement.title}{r.liveTest && <span className="ad-tag ad-tag--violet" style={{ marginLeft: 8 }}>A/B test</span>}</td>
                    <td>
                      <span className="ad-code-chip" data-copy={r.placement.developer_id} data-hint="Copy ID" style={{ maxWidth: 160 }}>
                        <span className="ad-code-chip__text">{r.placement.developer_id}</span>
                        <Icon name="copy" className="ad-code-chip__copy" />
                      </span>
                    </td>
                    <td className="is-right">{num(r.views)}</td>
                    <td className="is-right">{num(r.completions)}</td>
                    <td className="is-right">{money(r.revenue)}</td>
                    <td className="is-right">{num(r.purchases)}</td>
                    <td className="is-sticky-right"><StatusText state={r.placement.is_active ? 'live' : 'inactive'} /></td>
                    <td>
                      <div className="ad-menu-anchor">
                        <button className="ad-icon-btn ad-icon-btn--plain" data-menu-trigger="" aria-label="More"><Icon name="more" size={24} /></button>
                        <ul className="ad-menu">
                          <li className="ad-menu__item" onClick={() => navigate(`/placements/flows/${r.placement.id}`)}><Icon name="metrics" />Metrics</li>
                          <li className="ad-menu__item" onClick={() => toast('Analytics is not part of this demo', 'info')}><Icon name="trend" />View in analytics</li>
                          <li className="ad-menu__item" onClick={() => navigate(`/placements/flows/${r.placement.id}`)}><Icon name="pencil" />Edit</li>
                          <li className="ad-menu__item ad-menu__item--danger" onClick={() => toast('Deleting a placement is a write and is not part of this demo', 'warning')}><Icon name="trash" />Delete</li>
                        </ul>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <Pagination count={rows.length} />
        </>
      )}
    </>
  );
}
