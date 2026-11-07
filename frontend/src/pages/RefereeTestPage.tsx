import { Link, useParams } from 'react-router-dom';
import Icon from '../components/Icon';
import DossierPanel from '../components/referee/DossierPanel';
import { Breadcrumb, ErrorBox, Skeleton } from '../components/common';
import { adapty } from '../lib/api';
import { useAsync } from '../lib/useAsync';

export default function RefereeTestPage() {
  const { id = '' } = useParams();
  const { data, error, loading } = useAsync(() => adapty.getTest(id), [id]);
  if (error) return <ErrorBox error={error} />;
  if (loading || !data) return <Skeleton width={420} height={24} />;
  return (
    <>
      <div className="ad-page-header ad-page-header--center">
        <Breadcrumb parent="Experiment Referee" parentHref="/referee" current={data.title} extra={<span className="ad-tag ad-tag--violet" style={{ marginLeft: 8 }}>A/B test</span>} />
        <div className="ad-header-actions ad-header-actions--links">
          <Link className="ad-btn ad-btn--ghost" to={`/ab-tests/flows/${id}/metrics`}><Icon name="metrics" />View metrics</Link>
        </div>
      </div>
      {data.goal && <p className="ad-caption rf-mb-24">Goal: {data.goal}</p>}
      <DossierPanel testId={id} />
    </>
  );
}
