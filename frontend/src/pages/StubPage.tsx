import { useParams } from 'react-router-dom';
import { EmptyState, PageHeader } from '../components/common';

export default function StubPage() {
  const { name = 'Section' } = useParams();
  return (
    <>
      <PageHeader title={decodeURIComponent(name)} />
      <EmptyState icon="eye" text="This section is not part of the hackathon demo. The A/B tests, Placements and Experiment Referee pages are live." />
    </>
  );
}
