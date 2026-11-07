// Copy rules from the Adapty style guide: $1,528 for totals, two decimals for per-user values,
// percentages with two decimals (one for coarse rates), dates like 7 Nov 2026, empty values as "-".

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];

export const EMPTY = '-';

export function money(value: number | null | undefined, opts: { exact?: boolean } = {}): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  if (opts.exact || Math.abs(value) < 100) return `$${value.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  return `$${Math.round(value).toLocaleString('en-US')}`;
}

export function num(value: number | null | undefined, digits = 0): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return value.toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

/** value already expressed in percent (12.28 -> "12.28%") */
export function pct(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${value.toFixed(digits)}%`;
}

/** value is a ratio (0.1228 -> "12.28%") */
export function ratio(value: number | null | undefined, digits = 2): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  return `${(value * 100).toFixed(digits)}%`;
}

export function pValue(value: number | null | undefined): string {
  if (value === null || value === undefined || Number.isNaN(value)) return EMPTY;
  if (value < 0.001) return '<0.001';
  return value.toFixed(3);
}

export function fmtDate(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return EMPTY;
  return `${d.getUTCDate()} ${MONTHS[d.getUTCMonth()]} ${d.getUTCFullYear()}`;
}

export function fmtDateTime(iso: string | null | undefined): string {
  if (!iso) return EMPTY;
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return EMPTY;
  const hh = String(d.getUTCHours()).padStart(2, '0');
  const mm = String(d.getUTCMinutes()).padStart(2, '0');
  return `${fmtDate(iso)}, ${hh}:${mm} UTC`;
}

export function daysText(days: number | null | undefined): string {
  if (days === null || days === undefined || !Number.isFinite(days)) return EMPTY;
  if (days < 1 / 24) return 'under an hour';
  if (days < 1) return `${Math.round(days * 24)} hours`;
  if (days < 10) return `${days.toFixed(1)} days`;
  return `${Math.round(days)} days`;
}

/** "(10 hours)" style duration between two instants */
export function durationBetween(from: string | null | undefined, to: string | null | undefined): string {
  if (!from) return EMPTY;
  const start = new Date(from).getTime();
  const end = to ? new Date(to).getTime() : Date.now();
  if (Number.isNaN(start) || Number.isNaN(end)) return EMPTY;
  const minutes = Math.max(0, Math.round((end - start) / 60000));
  if (minutes < 60) return `${minutes} minutes`;
  const hours = Math.round(minutes / 60);
  if (hours < 48) return `${hours} hours`;
  return `${Math.round(hours / 24)} days`;
}

export function titleCase(state: string): string {
  return state ? state[0].toUpperCase() + state.slice(1) : state;
}

export function relativeLift(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return EMPTY;
  const sign = value > 0 ? '+' : '';
  return `${sign}${(value * 100).toFixed(1)}%`;
}
