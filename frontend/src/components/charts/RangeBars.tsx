import { useTooltip } from './tooltip';
import { SERIES } from '../VariantTable';
import { money } from '../../lib/format';
import type { ArmStats } from '../../lib/types';

/**
 * Revenue per viewer today (hollow marker) and where it lands once the open trials resolve
 * (thin range low to high, filled marker at the expected value). One row per arm, direct labels.
 */
export default function RangeBars({ arms }: { arms: ArmStats[] }) {
  const tooltip = useTooltip();
  const width = 640;
  const rowH = 44;
  const left = 150;
  const right = 60;
  const top = 12;
  const height = top + arms.length * rowH + 28;
  const values = arms.flatMap((a) => [a.revenue_per_viewer, a.projected_rpv_low, a.projected_rpv_high]);
  const max = Math.max(0.01, ...values) * 1.08;
  const x = (v: number) => left + (v / max) * (width - left - right);
  const ticks = [0, max / 4, max / 2, (3 * max) / 4, max].map((v) => Math.round(v * 100) / 100);
  return (
    <div>
      <svg className="rf-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Revenue per viewer today and after open trials, per arm">
        {ticks.map((t) => (
          <g key={t}>
            <line className="rf-grid" x1={x(t)} x2={x(t)} y1={top} y2={height - 24} />
            <text className="rf-muted-text" x={x(t)} y={height - 8} textAnchor="middle">{money(t)}</text>
          </g>
        ))}
        {arms.map((a, i) => {
          const y = top + i * rowH + rowH / 2;
          const color = SERIES[i % SERIES.length];
          const content = (
            <>
              <b>{a.title} · {a.flow_name}</b>
              Today {money(a.revenue_per_viewer, { exact: true })} per viewer
              <br />
              After open trials: {money(a.projected_rpv_low, { exact: true })} to {money(a.projected_rpv_high, { exact: true })}, expected {money(a.projected_rpv_expected, { exact: true })}
              <br />
              {a.trials_pending} open trials
            </>
          );
          return (
            <g key={a.flow_id} onMouseMove={(e) => tooltip.show(e, content)} onMouseLeave={tooltip.hide}>
              <rect x={0} y={y - rowH / 2} width={width} height={rowH} fill="transparent" />
              <text x={0} y={y + 4} fontWeight={600}>{a.title}</text>
              <text className="rf-muted-text" x={18} y={y + 4}>{a.flow_name.length > 20 ? `${a.flow_name.slice(0, 19)}...` : a.flow_name}</text>
              <line x1={x(a.projected_rpv_low)} x2={x(a.projected_rpv_high)} y1={y} y2={y} stroke={color} strokeWidth={2} strokeLinecap="round" />
              <circle cx={x(a.projected_rpv_expected)} cy={y} r={5} fill={color} stroke="var(--white)" strokeWidth={2} />
              <circle cx={x(a.revenue_per_viewer)} cy={y} r={4.5} fill="var(--white)" stroke={color} strokeWidth={2} />
              <text className="rf-muted-text" x={x(a.projected_rpv_high) + 8} y={y + 4}>{money(a.projected_rpv_high, { exact: true })}</text>
            </g>
          );
        })}
      </svg>
      <div className="rf-legend">
        <span style={{ ['--swatch' as string]: 'var(--white)', outline: 'none' }}>◯ today</span>
        <span style={{ ['--swatch' as string]: 'var(--black-600)' }}>projected low to high, dot = expected</span>
      </div>
      {tooltip.element}
    </div>
  );
}
