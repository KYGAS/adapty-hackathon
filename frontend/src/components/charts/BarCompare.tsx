import { useTooltip } from './tooltip';
import { SERIES } from '../VariantTable';

export interface Bar {
  key: string;
  label: string;
  sublabel?: string;
  value: number;
  format: (v: number) => string;
}

/** Thin vertical bars, one per variant, direct value labels, hover tooltip. */
export default function BarCompare({ bars, height = 120 }: { bars: Bar[]; height?: number }) {
  const tooltip = useTooltip();
  const width = 420;
  const padX = 24;
  const top = 20;
  const bottom = 28;
  const max = Math.max(0.0001, ...bars.map((b) => b.value)) * 1.1;
  const slot = (width - padX * 2) / Math.max(1, bars.length);
  const barW = Math.min(48, slot * 0.5);
  const y = (v: number) => top + (1 - v / max) * (height - top - bottom);
  return (
    <div>
      <svg className="rf-chart" viewBox={`0 0 ${width} ${height}`} role="img" aria-label="Metric by variant">
        <line className="rf-axis" x1={padX} x2={width - padX} y1={height - bottom} y2={height - bottom} />
        {bars.map((b, i) => {
          const cx = padX + slot * i + slot / 2;
          const h = Math.max(0, height - bottom - y(b.value));
          const color = SERIES[i % SERIES.length];
          return (
            <g key={b.key} onMouseMove={(e) => tooltip.show(e, <><b>{b.label}{b.sublabel ? ` · ${b.sublabel}` : ''}</b>{b.format(b.value)}</>)} onMouseLeave={tooltip.hide}>
              <rect x={cx - slot / 2} y={top - 10} width={slot} height={height - top + 10} fill="transparent" />
              <rect x={cx - barW / 2} y={y(b.value)} width={barW} height={h} fill={color} rx={4} ry={4} />
              <rect x={cx - barW / 2} y={height - bottom - Math.min(4, h)} width={barW} height={Math.min(4, h)} fill={color} />
              <text x={cx} y={y(b.value) - 6} textAnchor="middle" fontWeight={500}>{b.format(b.value)}</text>
              <text x={cx} y={height - 10} textAnchor="middle" className="rf-muted-text">{b.label}</text>
            </g>
          );
        })}
      </svg>
      {tooltip.element}
    </div>
  );
}
