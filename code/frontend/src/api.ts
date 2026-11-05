import { demoCases } from './data';
import type { CaseResult } from './types';
const dataMode = import.meta.env?.VITE_DATA_MODE || 'live';
export const isDemo = dataMode === 'demo';
export const apiBase = (import.meta.env?.VITE_API_BASE_URL || '').replace(/\/$/, '');

const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value);
const strings = (value: unknown, keys: string[]) => object(value) && keys.every(key => typeof value[key] === 'string');
const arrayOf = (value: unknown, check: (item: unknown) => boolean) => Array.isArray(value) && value.every(check);

/** Validate the fields used by all four pages before accepting a live response. */
function validCase(value: unknown): value is CaseResult {
  if (!object(value) || !strings(value, ['case_id', 'deletion_status']) || !value.case_id || !/^(?:case|sample(?:_case)?|mini)_\d{1,12}$/.test(value.case_id as string) ||
      !['COMPLETE', 'INCOMPLETE', 'NOT_APPLICABLE'].includes(value.deletion_status as string)) return false;
  const summary = value.summary;
  if (!object(summary) || !['systems_checked', 'findings_count', 'remediation_count', 'verification_count']
      .every(key => Number.isInteger(summary[key]) && (summary[key] as number) >= 0)) return false;
  if (!arrayOf(value.findings, item => strings(item, ['id', 'title', 'severity', 'system_id', 'resource_id', 'evidence_id', 'description']) &&
      ['HIGH', 'MEDIUM', 'LOW'].includes((item as Record<string, string>).severity))) return false;
  if (!arrayOf(value.steps, item => strings(item, ['phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id']) && object(item) &&
      Number.isInteger(item.step_no) && (item.step_no as number) > 0 && ['FINDING', 'REMEDIATION', 'VERIFICATION'].includes(item.phase as string))) return false;
  if (!arrayOf(value.identities, item => strings(item, ['id', 'label', 'value']) && object(item) && typeof item.historical === 'boolean')) return false;
  if (!arrayOf(value.evidence, item => strings(item, ['id', 'label', 'captured_at']))) return false;
  if (!object(value.graph_data) || !arrayOf(value.graph_data.nodes, item => strings(item, ['id', 'type', 'label', 'status']) && object(item) &&
      ['VERIFIED', 'ISSUE', 'PENDING', 'CONNECTED'].includes(item.status as string) &&
      (item.system_id === undefined || typeof item.system_id === 'string') &&
      (item.evidence_ids === undefined || arrayOf(item.evidence_ids, id => typeof id === 'string'))) ||
      !arrayOf(value.graph_data.edges, item => strings(item, ['id', 'source', 'target', 'relationship', 'status']) && object(item) &&
        ['VERIFIED', 'ISSUE', 'PENDING', 'CONNECTED'].includes(item.status as string))) return false;
  const request = value.request;
  if (request !== undefined && (!object(request) || !strings(request, ['requested_at', 'audit_at', 'reported_status']) ||
      ['email', 'reported_at', 'request_text'].some(key => request[key] !== undefined && typeof request[key] !== 'string'))) return false;
  return true;
}

export async function loadCases(signal?: AbortSignal): Promise<CaseResult[]> {
  if (isDemo) return demoCases;
  if (dataMode !== 'live') throw new Error('Invalid data mode. Use live for backend results or explicitly select demo.');
  let response: Response;
  try {
    response = await fetch(`${apiBase}/api/cases`, { signal });
  } catch (error) {
    if (signal?.aborted) throw error;
    throw new Error('Unable to reach the presentation API. Check that the backend is running and retry.');
  }
  if (!response.ok) throw new Error(`API request failed (${response.status}). Check that the presentation API is running.`);
  let data: unknown;
  try { data = await response.json(); } catch { throw new Error('The API returned invalid JSON. No investigation results were loaded.'); }
  if (!Array.isArray(data) || !data.every(validCase) || new Set(data.map(item => item.case_id)).size !== data.length) {
    throw new Error('The API returned unsupported or duplicate case results. See CONTRACT.md.');
  }
  return data;
}
