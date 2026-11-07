import { daysText, fmtDate, money, num, pValue, pct } from '../../lib/format';
import type { AuditResult } from '../../lib/types';

const STATUS_TEXT = {
  confirmed: ['Winner confirmed by realized revenue', 'ad-text-success'],
  reversed: ['Realized revenue reversed the call', 'ad-text-error'],
  inconclusive: ['Not enough traffic since the stop to judge', 'rf-muted'],
} as const;

export default function AuditPanel({ audit }: { audit: AuditResult }) {
  const realized = audit.realized;
  return (
    <div className="ad-panel">
      <div className="ad-row rf-mb-8" style={{ gap: 12 }}>
        <span className={`rf-grade rf-grade--${audit.grade}`}>{audit.grade}</span>
        <div>
          <h4 className="ad-h4">Retro audit</h4>
          <div className="ad-caption">Evidence at the stop scored {audit.score} of 100</div>
        </div>
      </div>
      <dl className="rf-kv rf-mb-16">
        <dt>Stopped</dt><dd>{fmtDate(audit.stopped_at)} after {daysText(audit.duration_days)}</dd>
        <dt>Declared winner</dt><dd>{audit.declared_winner_title ?? 'none recorded'}</dd>
        <dt>Payers at the stop</dt><dd>{num(audit.evidence.payers_leader)}</dd>
        <dt>Sample at the stop</dt><dd>{num(audit.evidence.min_views_per_arm)}{audit.evidence.required_per_arm ? ` of ${num(audit.evidence.required_per_arm)}` : ''}</dd>
        <dt>p-value</dt><dd>{pValue(audit.evidence.p_value)}</dd>
        <dt>P2BB</dt><dd>{audit.evidence.p2bb_leader === null ? '-' : pct(audit.evidence.p2bb_leader, 1)}</dd>
      </dl>
      <ul className="rf-reasons rf-mb-16">
        {audit.grade_reasons.map((r) => (
          <li key={r}>{r}</li>
        ))}
      </ul>
      {realized && (
        <>
          <h5 className="ad-h5 rf-mb-8">Since the stop</h5>
          <dl className="rf-kv">
            <dt>Winner flow</dt><dd>{money(realized.winner_rpv, { exact: true })} per viewer <span className="rf-muted">({num(realized.winner_flow_views)} views)</span></dd>
            <dt>Alternative flow</dt><dd>{money(realized.alternative_rpv, { exact: true })} per viewer <span className="rf-muted">({num(realized.alternative_flow_views)} views)</span></dd>
          </dl>
          <p className={`ad-body rf-strong ${STATUS_TEXT[realized.status][1]}`} style={{ marginTop: 8 }}>{STATUS_TEXT[realized.status][0]}</p>
          <p className="ad-caption-sm">Source: {realized.source}</p>
        </>
      )}
    </div>
  );
}
