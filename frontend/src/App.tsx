import { useEffect, useState } from 'react';
import { Navigate, Route, Routes, useLocation } from 'react-router-dom';
import Shell from './components/Shell';
import ABTestMetricsPage from './pages/ABTestMetricsPage';
import ABTestsListPage from './pages/ABTestsListPage';
import PlacementDetailPage from './pages/PlacementDetailPage';
import PlacementsPage from './pages/PlacementsPage';
import RefereePage from './pages/RefereePage';
import RefereeTestPage from './pages/RefereeTestPage';
import StubPage from './pages/StubPage';
import { loadHealth } from './lib/api';
import type { Health } from './lib/types';

/** A new page starts at the top, as in the dashboard; hash links within a page keep their position. */
function ScrollToTop() {
  const { pathname } = useLocation();
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [pathname]);
  return null;
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    loadHealth()
      .then(setHealth)
      .catch(() => setHealth(null))
      .finally(() => setReady(true));
  }, []);
  return (
    <Shell health={health}>
      <ScrollToTop />
      {!ready ? null : (
        <Routes>
          <Route path="/" element={<Navigate to="/ab-tests/flows" replace />} />
          <Route path="/ab-tests" element={<Navigate to="/ab-tests/flows" replace />} />
          <Route path="/ab-tests/flows" element={<ABTestsListPage />} />
          <Route path="/ab-tests/flows/:id/metrics" element={<ABTestMetricsPage />} />
          <Route path="/ab-tests/flows/:id" element={<ABTestMetricsPage />} />
          <Route path="/placements" element={<Navigate to="/placements/flows" replace />} />
          <Route path="/placements/flows" element={<PlacementsPage />} />
          <Route path="/placements/flows/:id" element={<PlacementDetailPage />} />
          <Route path="/referee" element={<RefereePage />} />
          <Route path="/referee/:id" element={<RefereeTestPage />} />
          <Route path="/stub/:name" element={<StubPage />} />
          <Route path="*" element={<Navigate to="/ab-tests/flows" replace />} />
        </Routes>
      )}
    </Shell>
  );
}
