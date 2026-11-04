import { demoCases } from './data';
import type { CaseResult } from './types';
export const isDemo = import.meta.env.VITE_DATA_MODE !== 'live';
export const apiBase = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000').replace(/\/$/, '');
async function request(path: string, signal?: AbortSignal): Promise<unknown> {
  const response = await fetch(`${apiBase}${path}`, { signal });
  if (!response.ok) throw new Error(`API request failed (${response.status}). Check that the presentation API is running.`);
  return response.json();
}
export async function loadCases(signal?: AbortSignal): Promise<CaseResult[]> {
  if (isDemo) return demoCases;
  const data = await request('/api/cases', signal);
  if (!Array.isArray(data)) throw new Error('Expected a case-result array from /api/cases.');
  for (const item of data) {
    if (!item || typeof item.case_id !== 'string' || !['COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE'].includes(item.deletion_status) || !Array.isArray(item.findings) || !Array.isArray(item.steps) || !Array.isArray(item.identities) || !Array.isArray(item.evidence) || !Array.isArray(item.graph_data?.nodes) || !Array.isArray(item.graph_data?.edges) || !item.summary) throw new Error('The API returned an unsupported case result. See CONTRACT.md.');
  }
  return data as CaseResult[];
}
