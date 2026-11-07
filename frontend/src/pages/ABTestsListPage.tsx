import { useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import Icon from '../components/Icon';
import TestCard from '../components/TestCard';
import { CardSkeleton, EmptyState, ErrorBox, PageHeader, Pagination } from '../components/common';
import { adapty, referee } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { AdaptyMetricsRow, AdaptyTestDetail, OverviewRow, TestState } from '../lib/types';

const TABS: Array<[TestState, string]> = [
  ['live', 'Live'],
  ['completed', 'Completed'],
  ['draft', 'Draft'],
  ['archived', 'Archive'],
];

const EMPTY_TEXT: Record<string, string> = {
  live: 'Here will be stored A/B tests that are currently running',
  completed: 'Here will be stored A/B tests that have been completed',
  draft: 'Here will be stored A/B tests drafts',
  archived: 'Here will be stored A/B tests and drafts that have been archived',
};

export default function ABTestsListPage() {
  const [search, setSearch] = useSearchParams();
  const state = (search.get('filter[state]') as TestState) || 'live';
  const [query, setQuery] = useState('');
  const [kind, setKind] = useState('flow');

  const page = useAsync(async () => {
    const [tests, segments] = await Promise.all([adapty.listTests(), adapty.listSegments()]);
    const details = await Promise.all(tests.data.map((t) => adapty.getTest(t.ab_test_id)));
    const measurable = tests.data.filter((t) => t.state !== 'draft').map((t) => t.ab_test_id);
    const metrics = measurable.length ? (await adapty.metricsRows(measurable)).data : [];
    let overview: OverviewRow[] = [];
    try {
      overview = await referee.overview();
    } catch {
      overview = [];
    }
    return { tests: tests.data, segments: segments.data, details, metrics, overview };
  }, []);

  const data = page.data;
  const visible = useMemo(() => {
    if (!data) return [];
    return data.tests.filter((t) => t.state === state && (!query || t.title.toLowerCase().includes(query.toLowerCase())));
  }, [data, state, query]);

  const counts = (s: TestState) => data?.tests.filter((t) => t.state === s).length ?? 0;
  const detailOf = (id: string): AdaptyTestDetail | null => data?.details.find((d) => d.ab_test_id === id) ?? null;
  const metricsOf = (id: string): AdaptyMetricsRow | null => data?.metrics.find((m) => m.ab_test_id === id) ?? null;
  const verdictOf = (id: string) => data?.overview.find((o) => o.test_id === id)?.verdict ?? null;
  const audienceOf = (segmentIds: string[]) => (segmentIds.length ? data?.segments.find((s) => s.id === segmentIds[0])?.title ?? 'Segment' : 'All users');

  return (
    <>
      <PageHeader title="A/B tests" right={<Link className="ad-btn ad-btn--primary" to="/stub/Create A/B test">Create A/B test</Link>} />
      <div className="ad-toolbar rf-mb-24">
        <div className={`ad-search ${query ? 'has-value' : ''}`}>
          <input className="ad-input" placeholder="Search test..." value={query} onChange={(e) => setQuery(e.target.value)} />
          <button className="ad-search__clear" aria-label="Clear" onClick={() => setQuery('')}><Icon name="x" size={16} /></button>
          <span className="ad-search__icon"><Icon name="search" /></span>
        </div>
        <div className="ad-toolbar__group">
          <div className="ad-menu-anchor">
            <button className="ad-dropdown-btn" data-menu-trigger="">All audiences <Icon name="chevron-down" size={16} /></button>
            <ul className="ad-menu ad-menu--left">
              <li className="ad-menu__item">All audiences</li>
              {data?.segments.map((s) => <li key={s.id} className="ad-menu__item">{s.title}</li>)}
            </ul>
          </div>
          <div className="ad-menu-anchor">
            <button className="ad-dropdown-btn" data-menu-trigger="">All placements <Icon name="chevron-down" size={16} /></button>
            <ul className="ad-menu ad-menu--left">
              <li className="ad-menu__item">All placements</li>
              {Array.from(new Set(data?.tests.map((t) => t.placement.title))).map((p) => <li key={p} className="ad-menu__item">{p}</li>)}
            </ul>
          </div>
        </div>
      </div>
      <div className="ad-segmented rf-mb-24">
        {[['flow', 'Flow'], ['paywall', 'Paywall'], ['cross-flow', 'Crossplacement (Flows)'], ['cross-paywall', 'Crossplacement (Paywalls)']].map(([k, label]) => (
          <button key={k} className={`ad-segmented__btn ${kind === k ? 'is-selected' : ''}`} onClick={() => setKind(k)}>{label}</button>
        ))}
      </div>
      <div className="ad-tabs ad-tabs--status rf-mb-24">
        {TABS.map(([s, label]) => (
          <button key={s} className={`ad-tabs__item ${state === s ? 'is-selected' : ''}`} onClick={() => setSearch(s === 'live' ? {} : { 'filter[state]': s })}>
            {s === 'live' && <span className="ad-live-dot" />}
            {label} {data && counts(s) > 0 && <span className="ad-count">({counts(s)})</span>}
          </button>
        ))}
      </div>
      <ErrorBox error={page.error} />
      {page.loading && !data && (
        <div className="ad-stack">
          <CardSkeleton />
          <CardSkeleton />
        </div>
      )}
      {data && kind !== 'flow' && (
        <EmptyState text={`No ${kind.replace('-', ' ')} A/B tests yet. Create one to compare ${kind.includes('paywall') ? 'paywalls' : 'flows'}.`} />
      )}
      {data && kind === 'flow' && visible.length === 0 && <EmptyState text={EMPTY_TEXT[state]} />}
      {data && kind === 'flow' && visible.length > 0 && (
        <>
          <div className="ad-stack">
            {visible.map((t) => (
              <TestCard key={t.ab_test_id} test={t} detail={detailOf(t.ab_test_id)} metrics={metricsOf(t.ab_test_id)} verdict={verdictOf(t.ab_test_id)} audience={audienceOf(t.segment_ids)} />
            ))}
          </div>
          <Pagination count={visible.length} />
        </>
      )}
    </>
  );
}
