import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import TestCard from '../components/TestCard';
import VariantTable from '../components/VariantTable';
import { Breadcrumb, ErrorBox, Skeleton, StatusText, toast } from '../components/common';
import { adapty, referee } from '../lib/api';
import { useAsync } from '../lib/useAsync';
import type { AdaptyFlowMetrics, AdaptyMetricsRow, AdaptyTestDetail, OverviewRow } from '../lib/types';

export default function PlacementDetailPage() {
  const { id = '' } = useParams();
  const { data, error, loading } = useAsync(async () => {
    const [placement, tests, segments, flows] = await Promise.all([adapty.getPlacement(id), adapty.listTests(), adapty.listSegments(), adapty.listFlows()]);
    const here = tests.data.filter((t) => t.placement.placement_id === id);
    const details = new Map<string, AdaptyTestDetail>();
    await Promise.all(here.map(async (t) => details.set(t.ab_test_id, await adapty.getTest(t.ab_test_id))));
    const measurable = here.filter((t) => t.state !== 'draft').map((t) => t.ab_test_id);
    const metrics = measurable.length ? (await adapty.metricsRows(measurable)).data : [];
    const flowMetrics = (await adapty.flowMetrics(flows.data.map((f) => f.id))).data;
    let overview: OverviewRow[] = [];
    try {
      overview = await referee.overview();
    } catch {
      overview = [];
    }
    return { placement, tests: here, details, metrics, segments: segments.data, flows: flows.data, flowMetrics, overview };
  }, [id]);
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return <Skeleton width={600} height={200} />;
  const { placement } = data;
  const segmentName = (ids: string[]) => (ids.length ? data.segments.find((s) => s.id === ids[0])?.title ?? 'Segment' : 'All users');
  const metricsOf = (testId: string): AdaptyMetricsRow | null => data.metrics.find((m) => m.ab_test_id === testId) ?? null;
  const audiences = [...(placement.audiences ?? [])].sort((a, b) => a.priority - b.priority);
  return (
    <>
      <div className="ad-page-header ad-page-header--center">
        <Breadcrumb
          parent="Placements"
          parentHref="/placements/flows"
          current={placement.title}
          extra={
            <>
              <span className="ad-tag ad-tag--violet" style={{ marginLeft: 8 }}>Flow placement</span>
              <span style={{ marginLeft: 8 }}><StatusText state={placement.is_active ? 'live' : 'inactive'} /></span>
            </>
          }
        />
        <div className="ad-header-actions">
          <button className="ad-btn ad-btn--secondary ad-btn--with-icon" onClick={() => toast('Placement metrics use the same shapes as A/B metrics. Not part of this demo.', 'info')}><Icon name="metrics" />Metrics</button>
          <button className="ad-btn ad-btn--danger-outline ad-btn--with-icon" onClick={() => toast('Deleting a placement is a write and is not part of this demo', 'warning')}><Icon name="trash" />Delete</button>
        </div>
      </div>
      <form className="ad-toolbar" style={{ alignItems: 'flex-end', marginBottom: 36 }} onSubmit={(e) => e.preventDefault()}>
        <div className="ad-row" style={{ gap: 8, alignItems: 'flex-end' }}>
          <div className="ad-field" style={{ width: 300, margin: 0 }}>
            <div className="ad-field__label"><span className="ad-field__label-text">Placement name</span><span className="ad-field__required">Required</span></div>
            <input className="ad-input" defaultValue={placement.title} />
          </div>
          <div className="ad-field" style={{ width: 300, margin: 0 }}>
            <div className="ad-field__label">
              <span className="ad-field__label-text ad-row" style={{ gap: 4 }}>
                Placement ID
                <span data-hint="The ID can't be changed after the placement is created. Use it in the SDK to fetch this placement." style={{ color: 'var(--yellow-400)', display: 'flex' }}><Icon name="warning" size={16} /></span>
              </span>
              <span className="ad-field__required">Required</span>
            </div>
            <div className="ad-input-wrap">
              <input className="ad-input" value={placement.developer_id} disabled style={{ paddingRight: 36 }} readOnly />
              <span className="ad-input-wrap__right"><button type="button" data-copy={placement.developer_id} aria-label="Copy"><Icon name="copy" /></button></span>
            </div>
          </div>
        </div>
        <div className="ad-toolbar__group">
          <button type="button" className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => toast('Edit priority is not part of this demo', 'info')}><Icon name="hash" />Edit priority</button>
          <button type="button" className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => toast('Add audience is not part of this demo', 'info')}><Icon name="user-plus" />Add audience</button>
        </div>
      </form>
      <div className="ad-stack">
        {audiences.length === 0 && <p className="ad-caption">This placement has no audiences.</p>}
        {audiences.map((aud, index) => {
          if (aud.ab_test_id) {
            const test = data.tests.find((t) => t.ab_test_id === aud.ab_test_id);
            if (!test) return null;
            return (
              <TestCard key={`${aud.ab_test_id}-${index}`} test={test} detail={data.details.get(test.ab_test_id) ?? null} metrics={metricsOf(test.ab_test_id)} verdict={data.overview.find((o) => o.test_id === test.ab_test_id)?.verdict ?? null} audience={segmentName(aud.segment_ids)} priority={index + 1} audienceIcon />
            );
          }
          const flow = data.flows.find((f) => f.id === aud.flow_id);
          const fm: AdaptyFlowMetrics | undefined = data.flowMetrics.find((m) => m.flow_id === aud.flow_id);
          const row: AdaptyMetricsRow = { views: fm?.views ?? 0, unique_profiles_views: fm?.unique_profiles_views ?? 0, revenue: fm?.revenue ?? 0, proceeds: 0, net_revenue: 0, purchases: fm?.purchases ?? 0, trials: fm?.trials ?? 0, unique_paid_subscribers: fm?.unique_paid_subscribers ?? 0, arppu: 0, arpu: fm?.arpu ?? 0, conversion_rate_purchases: fm && fm.views ? (fm.purchases / fm.views) * 100 : 0, conversion_rate_trials: fm && fm.views ? (fm.trials / fm.views) * 100 : 0, flow_id: aud.flow_id };
          return (
            <article key={`${aud.flow_id}-${index}`} className="ad-card">
              <div className="ad-card__header">
                <div className="ad-card__header-main">
                  <span className="ad-tile"><Icon name="users" /><span className="ad-tile__priority"><span className="ad-tag">#{index + 1}</span></span></span>
                  <div style={{ minWidth: 0 }}>
                    <div className="ad-card__title-row">
                      <h5 className="ad-h5 ad-bold ad-hint" data-hint="Audience segment">{segmentName(aud.segment_ids)}</h5>
                      <h5 className="ad-h5">·</h5>
                      <h5 className="ad-h5">{flow?.name ?? aud.flow_title ?? 'Flow'}</h5>
                      <span className="ad-tag ad-tag--violet ad-hint" data-hint="A single flow is shown to this audience">Flow</span>
                    </div>
                    <div className="ad-card__meta"><span className="ad-card__meta-item"><Icon name="clock" />Published</span></div>
                  </div>
                </div>
                <div className="ad-card__actions">
                  <button className="ad-btn ad-btn--v2 ad-btn--with-icon" onClick={() => toast('Change Flow is not part of this demo', 'info')}><Icon name="pencil" />Change Flow</button>
                  <Link className="ad-btn ad-btn--v2 ad-btn--with-icon" to="/referee"><Icon name="play" />Run A/B test</Link>
                </div>
              </div>
              <VariantTable single arms={[{ flow_id: aud.flow_id ?? '', flow_name: flow?.name ?? aud.flow_title ?? 'Flow', weight: 100, title: '', variation_id: '' }]} rows={[row]} />
            </article>
          );
        })}
      </div>
    </>
  );
}
