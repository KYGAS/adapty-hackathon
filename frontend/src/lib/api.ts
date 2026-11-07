import type {
  AdaptyFlow,
  AdaptyFlowMetrics,
  AdaptyMetricsRow,
  AdaptyMetricsTotal,
  AdaptyPlacement,
  AdaptySegment,
  AdaptyTestDetail,
  AdaptyTestListed,
  AuditLogEntry,
  Dossier,
  ExecuteResult,
  Health,
  Narration,
  Opportunity,
  OverviewRow,
  Page,
} from './types';

export class ApiError extends Error {
  status: number;
  body: unknown;
  constructor(status: number, body: unknown) {
    super(typeof body === 'string' ? body : (body as { detail?: unknown })?.detail?.toString() || `HTTP ${status}`);
    this.status = status;
    this.body = body;
  }
}

const DEFAULT_APP_ID = '9c35cea9-1655-4af3-9f05-ac16f383e91d';
let appId = DEFAULT_APP_ID;
let health: Health | null = null;

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const res = await fetch(url, { ...init, headers: { accept: 'application/json', 'content-type': 'application/json', ...(init?.headers || {}) } });
  const text = await res.text();
  let body: unknown = text;
  try {
    body = text ? JSON.parse(text) : null;
  } catch {
    /* keep text */
  }
  if (!res.ok) throw new ApiError(res.status, body);
  return body as T;
}

const q = (params: Record<string, string | number | undefined | null>) =>
  Object.entries(params)
    .filter(([, v]) => v !== undefined && v !== null && v !== '')
    .map(([k, v]) => `${encodeURIComponent(k)}=${encodeURIComponent(String(v))}`)
    .join('&');

export async function loadHealth(): Promise<Health> {
  health = await request<Health>('/api/health');
  appId = health.app_id || DEFAULT_APP_ID;
  return health;
}

export const getHealth = () => health;
export const getAppId = () => appId;

// Every call below hits the real developer API route shape through the backend proxy (/adapty/...).
export const adapty = {
  listTests: (states?: string[]) =>
    request<Page<AdaptyTestListed>>(`/adapty/apps/${appId}/ab-tests/?${q({ type: 'flow', 'filter[state]': states?.join(',') })}`),
  getTest: (id: string) => request<AdaptyTestDetail>(`/adapty/apps/${appId}/ab-tests/${id}/`),
  metricsRows: (ids: string[]) =>
    request<{ data: AdaptyMetricsRow[] }>(`/adapty/apps/${appId}/ab-tests/metrics/?${q({ type: 'flow', 'filter[ab_test_id]': ids.join(',') })}`),
  metricsTotal: (id: string) => request<{ data: AdaptyMetricsTotal }>(`/adapty/apps/${appId}/ab-tests/${id}/metrics/total/?type=flow`),
  metricsTree: (id: string, body: Record<string, unknown> = {}) =>
    request<{ data: AdaptyMetricsRow }>(`/adapty/apps/${appId}/ab-tests/${id}/metrics/?type=flow`, { method: 'POST', body: JSON.stringify(body) }),
  listPlacements: () => request<Page<AdaptyPlacement>>(`/adapty/apps/${appId}/placements/?page[size]=100`),
  getPlacement: (id: string) => request<AdaptyPlacement>(`/adapty/apps/${appId}/placements/${id}/`),
  listFlows: () => request<Page<AdaptyFlow>>(`/adapty/apps/${appId}/flows/?page[size]=100`),
  flowMetrics: (ids: string[]) => request<{ data: AdaptyFlowMetrics[] }>(`/adapty/apps/${appId}/flows/metrics/?${q({ 'filter[flow_id]': ids.join(',') })}`),
  listSegments: () => request<Page<AdaptySegment>>(`/adapty/apps/${appId}/segments/?page[size]=100`),
};

export interface AssumptionParams {
  mde?: number;
  alpha?: number;
  power?: number;
  max_wait?: number;
  min_runtime?: number;
}

const assumptionQuery = (params: AssumptionParams) => q(params as Record<string, number | undefined>);

export const referee = {
  overview: (params: AssumptionParams = {}) => request<OverviewRow[]>(`/api/referee/tests?${assumptionQuery(params)}`),
  dossier: (id: string, params: AssumptionParams = {}) => request<Dossier>(`/api/referee/tests/${id}/dossier?${assumptionQuery(params)}`),
  memo: (id: string, provider?: string) =>
    request<Narration>(`/api/referee/tests/${id}/memo`, { method: 'POST', body: JSON.stringify({ provider: provider || null }) }),
  opportunities: () => request<Opportunity[]>('/api/referee/opportunities'),
  execute: (body: { test_id: string; action_id: string; approved: boolean; approver: string; note?: string }) =>
    request<ExecuteResult>('/api/referee/actions/execute', { method: 'POST', body: JSON.stringify(body) }),
  auditLog: () => request<AuditLogEntry[]>('/api/referee/audit-log'),
};
