import { useState } from 'react';
import { Link } from 'react-router-dom';
import Icon from '../components/Icon';
import VerdictText from '../components/VerdictText';
import { ApprovalModal } from '../components/referee/ActionsPanel';
import { ErrorBox, PageHeader, Skeleton, StatusText } from '../components/common';
import { referee } from '../lib/api';
import { daysText, fmtDate, fmtDateTime, money, num } from '../lib/format';
import { useAsync } from '../lib/useAsync';
import type { ActionPreview, Opportunity } from '../lib/types';

const INTRO_KEY = 'referee_intro_dismissed';

export default function RefereePage() {
  const [intro, setIntro] = useState(() => {
    try {
      return !localStorage.getItem(INTRO_KEY);
    } catch {
      return true;
    }
  });
  const [approval, setApproval] = useState<{ testId: string; action: ActionPreview } | null>(null);
  const overview = useAsync(() => referee.overview(), []);
  const opportunities = useAsync(() => referee.opportunities(), []);
  const log = useAsync(() => referee.auditLog(), []);
  const reloadAll = () => {
    overview.reload();
    opportunities.reload();
    log.reload();
  };
  const dismiss = () => {
    try {
      localStorage.setItem(INTRO_KEY, '1');
    } catch {
      /* private mode */
    }
    setIntro(false);
  };
  const rows = overview.data ?? [];
  const waiting = rows.filter((r) => r.verdict && !r.verdict.is_call && r.state === 'live').length;
  const callable = rows.filter((r) => r.verdict?.is_call).length;
  return (
    <>
      <PageHeader title="Experiment Referee" pill={<span className="ad-pill ad-pill--beta" style={{ verticalAlign: 'middle', marginLeft: 8 }}>Beta</span>} right={<button className="ad-btn ad-btn--secondary ad-btn--with-icon" onClick={reloadAll}><Icon name="sync" />Re-evaluate</button>} />

      {intro && (
        <div className="ad-hero ad-hero--grid rf-mb-24">
          <div className="ad-hero__art">
            <div className="ad-stat-card" style={{ width: 300 }}>
              <div className="ad-row" style={{ gap: 12 }}>
                <span className="ad-app-switcher__avatar" style={{ width: 40, height: 40, flexBasis: 40, borderRadius: 10 }}>L</span>
                <div><div className="ad-semibold">Lumen</div><div className="ad-caption-sm">Referee preview</div></div>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px 32px' }}>
                <div><div className="ad-stat-card__value">{rows.length || '-'}</div><div className="ad-stat-card__label">Tests watched</div></div>
                <div><div className="ad-stat-card__value">{overview.data ? waiting : '-'}</div><div className="ad-stat-card__label">Too early to call</div></div>
                <div><div className="ad-stat-card__value">{overview.data ? callable : '-'}</div><div className="ad-stat-card__label">Ready to call</div></div>
                <div><div className="ad-stat-card__value">0</div><div className="ad-stat-card__label">Autonomous writes</div></div>
              </div>
            </div>
          </div>
          <div className="ad-hero__icon-wrap"><span className="ad-hero__icon"><Icon name="flask" /></span></div>
          <div className="ad-hero__content">
            <h1 className="ad-hero__title ad-gradient-text">Stop calling A/B tests before the money is in</h1>
            <p className="ad-hero__desc ad-gradient-text--body">Deterministic sample-size and trial-lag statistics decide, an LLM explains, and every change to a live test waits for your approval.</p>
            <div>
              <div className="ad-hero__checklist-label u-mb-8">What you get</div>
              <ul className="ad-hero__checklist">
                <li><Icon name="check-circle" />See the date a test becomes safe to call, not just today's P2BB</li>
                <li><Icon name="check-circle" />Count open trials as pending revenue instead of zero</li>
                <li><Icon name="check-circle" />Audit past winners against realized revenue and rank the next test</li>
              </ul>
            </div>
            <div className="ad-inline-alert"><Icon name="warning" />Writes to Adapty stay off until an action is approved here</div>
            <div className="ad-hero__cta">
              <div className="ad-hero__cta-frame"><button className="ad-btn ad-btn--primary ad-btn--3d" onClick={dismiss}>Show my verdicts <Icon name="chevron-right" size={16} /></button></div>
              <a className="ad-btn ad-btn--link ad-btn--muted" href="https://adapty.io/docs/ab-tests" target="_blank" rel="noreferrer">Read docs <Icon name="external" size={16} /></a>
            </div>
          </div>
        </div>
      )}

      <h4 className="ad-h4 rf-mb-16">Verdicts</h4>
      <ErrorBox error={overview.error} />
      {overview.loading && !overview.data && <Skeleton width="100%" height={200} className="rf-mb-24" />}
      {overview.data && (
        <div className="ad-table-scroll rf-mb-24">
          <table className="ad-grid">
            <thead>
              <tr>
                <th className="c-name" style={{ minWidth: 300 }}>Test</th>
                <th>Status</th>
                <th>Verdict</th>
                <th style={{ minWidth: 380 }}>Headline</th>
                <th className="is-right">Safe to call</th>
                <th>Recommended action</th>
                <th style={{ width: 48 }} />
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.test_id}>
                  <td><Link className="ad-link" to={`/referee/${r.test_id}`}>{r.title}</Link><div className="ad-caption-sm">{r.placement_title}</div></td>
                  <td><StatusText state={r.state} /></td>
                  <td>{r.verdict ? <VerdictText verdict={r.verdict} compact /> : <span className="ad-text-error">{r.error}</span>}</td>
                  <td style={{ whiteSpace: 'normal' }}>{r.verdict?.headline}{r.audit_grade && <span className={`rf-grade rf-grade--${r.audit_grade}`} style={{ width: 24, height: 24, fontSize: 12, marginLeft: 8 }}>{r.audit_grade}</span>}</td>
                  <td className="is-right">{r.timeline?.decision_date ? <>{fmtDate(r.timeline.decision_date)}<div className="ad-caption-sm">{daysText(r.timeline.days_to_decision)}</div></> : '-'}</td>
                  <td>{r.recommended_action?.title ?? '-'}</td>
                  <td><Link className="ad-icon-btn ad-icon-btn--plain" to={`/referee/${r.test_id}`} aria-label="Open dossier"><Icon name="chevron-right" /></Link></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <h4 className="ad-h4 rf-mb-16">Where to test next</h4>
      <p className="ad-caption rf-mb-16">Idle placements ranked by the money flowing through them. A ready draft jumps the queue.</p>
      <ErrorBox error={opportunities.error} />
      {opportunities.data && (
        <div className="ad-stack ad-stack--8 rf-mb-24">
          {opportunities.data.map((o: Opportunity) => (
            <div key={o.placement_id} className={`rf-action ${o.rank === 1 && !o.has_live_test ? 'is-recommended' : ''}`}>
              <div className="rf-action__row">
                <div className="ad-row" style={{ gap: 12 }}>
                  <span className="ad-tile"><Icon name="pin" /><span className="ad-tile__priority"><span className="ad-tag">#{o.rank}</span></span></span>
                  <div>
                    <div className="ad-h5"><Link className="ad-link" to={`/placements/flows/${o.placement_id}`}>{o.title}</Link> <span className="rf-muted rf-mono">{o.developer_id}</span></div>
                    <div className="ad-caption">{o.suggestion}</div>
                  </div>
                </div>
                <div className="rf-right rf-nowrap">
                  <div>{money(o.revenue)} <span className="rf-muted">lifetime</span></div>
                  <div className="ad-caption-sm">{num(o.views)} views · {money(o.revenue_per_viewer, { exact: true })} per viewer</div>
                </div>
              </div>
              {o.action && o.draft_test_id && (
                <div className="ad-row" style={{ gap: 8 }}>
                  <pre className="rf-command" style={{ flex: 1 }}>{o.action.cli_command}</pre>
                  <button className="ad-btn ad-btn--primary ad-btn--with-icon" onClick={() => setApproval({ testId: o.draft_test_id!, action: o.action! })}><Icon name="play" />Approve and run</button>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      <h4 className="ad-h4 rf-mb-16">Decision log</h4>
      <ErrorBox error={log.error} />
      {log.data && log.data.length === 0 && <p className="ad-caption rf-mb-24">Here will be stored every dry run, approval and refused write.</p>}
      {log.data && log.data.length > 0 && (
        <div className="ad-table-scroll rf-mb-24">
          <table className="ad-grid">
            <thead>
              <tr><th>When</th><th>Event</th><th>Action</th><th>Approved by</th><th>Command</th></tr>
            </thead>
            <tbody>
              {log.data.map((e, i) => (
                <tr key={i}>
                  <td className="rf-nowrap">{fmtDateTime(e.at)}</td>
                  <td><span className={e.event === 'executed' ? 'ad-text-success' : e.event === 'blocked' || e.event === 'failed' ? 'ad-text-error' : 'rf-muted'}>{e.event.replace('_', ' ')}</span><div className="ad-caption-sm">{e.mode}</div></td>
                  <td style={{ whiteSpace: 'normal' }}>{e.action?.title}</td>
                  <td>{e.approver ?? '-'}</td>
                  <td><code className="rf-mono">{e.action?.cli_command ?? '-'}</code></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <ApprovalModal testId={approval?.testId ?? ''} action={approval?.action ?? null} open={!!approval} onClose={() => setApproval(null)} onDone={reloadAll} />
    </>
  );
}
