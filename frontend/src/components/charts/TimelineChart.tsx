import { useTooltip } from './tooltip';
import { fmtDate, fmtDateTime } from '../../lib/format';
import type { Timeline } from '../../lib/types';

interface Marker {
  key: string;
  label: string;
  at: string;
  color: string;
  detail: string;
}

/** Start to horizon on one axis; the gates the referee waits for sit on it as 8px markers with direct labels. */
export default function TimelineChart({ timeline }: { timeline: Timeline }) {
  const tooltip = useTooltip();
  const start = timeline.started_at ? new Date(timeline.started_at).getTime() : new Date(timeline.now).getTime();
  const now = new Date(timeline.now).getTime();
  const markers: Marker[] = [];
  const push = (key: string, label: string, at: string | null, color: string, detail: string) => {
    if (at) markers.push({ key, label, at, color, detail });
  };
  push('runtime', 'First full week', timeline.min_runtime_date, 'var(--black-400)', 'Minimum runtime: weekday and weekend behaviour both covered.');
  push('maturity', 'Trials mature', timeline.maturity_date, 'var(--orange-400)', 'Last open trial resolved, plus one grace day.');
  push('sample', 'Sample reached', timeline.sample_date, 'var(--purplePrimary)', 'Smallest arm reaches the planned viewers at the current traffic.');
  push('decision', 'Safe to call', timeline.decision_date, 'var(--green-500)', 'Every gate open: the referee can call the test.');
  push('horizon', `Goal horizon (${timeline.horizon_days} days)`, timeline.horizon_date, 'var(--black-600)', 'Measurement window named in the test goal.');
  const times = [start, now, ...markers.map((m) => new Date(m.at).getTime())];
  const end = Math.max(...times);
  const span = Math.max(end - start, 86400000);
  const width = 640;
  const left = 16;
  const right = 16;
  const axisY = 58;
  const x = (t: number) => left + ((t - start) / span) * (width - left - right);
  const nowX = x(now);
  const sorted = [...markers].sort((a, b) => new Date(a.at).getTime() - new Date(b.at).getTime());
  return (
    <div>
      <svg className="rf-chart" viewBox={`0 0 ${width} 120`} role="img" aria-label="Decision timeline">
        <rect x={left} y={axisY - 6} width={Math.max(0, nowX - left)} height={12} fill="var(--black-50)" rx={3} />
        <line className="rf-axis" x1={left} x2={width - right} y1={axisY} y2={axisY} strokeWidth={2} />
        <g>
          <line x1={x(start)} x2={x(start)} y1={axisY - 10} y2={axisY + 10} stroke="var(--black-800)" strokeWidth={2} />
          <text x={x(start)} y={axisY + 28} textAnchor="start" className="rf-muted-text">Started {fmtDate(timeline.started_at)}</text>
        </g>
        <g onMouseMove={(e) => tooltip.show(e, <><b>Today</b>{fmtDateTime(timeline.now)}</>)} onMouseLeave={tooltip.hide}>
          <line x1={nowX} x2={nowX} y1={axisY - 38} y2={axisY + 14} stroke="var(--black-800)" strokeWidth={1} strokeDasharray="3 3" />
          <text x={nowX} y={axisY - 44} textAnchor="middle" fontWeight={600}>Today</text>
        </g>
        {sorted.map((m, i) => {
          const mx = x(new Date(m.at).getTime());
          const above = i % 2 === 0;
          const ly = above ? axisY - 16 : axisY + 44;
          return (
            <g key={m.key} onMouseMove={(e) => tooltip.show(e, <><b>{m.label}</b>{fmtDate(m.at)}<br />{m.detail}</>)} onMouseLeave={tooltip.hide}>
              <circle cx={mx} cy={axisY} r={5} fill={m.color} stroke="var(--white)" strokeWidth={2} />
              <text x={mx} y={ly} textAnchor="middle" className="rf-muted-text">{m.label}</text>
              <text x={mx} y={ly + (above ? -12 : 12)} textAnchor="middle" fontWeight={500}>{fmtDate(m.at)}</text>
            </g>
          );
        })}
      </svg>
      {tooltip.element}
    </div>
  );
}
