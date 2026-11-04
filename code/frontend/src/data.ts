import type { CaseResult, GraphNode } from './types';

// Fictional presentation fixtures, never predictions for challenge cases.
function makeCase(index: number, complete: boolean): CaseResult {
  const case_id = `DEMO-${String(index).padStart(3, '0')}`;
  const systems = ['Account service', 'Search index', 'Support desk', 'Analytics', 'Regional replica', 'Backup vault'];
  const nodes: GraphNode[] = [{ id: 'subject', type: 'IDENTITY', label: 'Customer identity', status: 'VERIFIED' }, { id: 'old-email', type: 'IDENTIFIER', label: 'Historical email', status: 'CONNECTED' }];
  const edges: CaseResult['graph_data']['edges'] = [{ id: 'historical', source: 'subject', target: 'old-email', relationship: 'PREVIOUS_IDENTIFIER', status: 'CONNECTED' }];
  systems.forEach((label, s) => {
    const status = !complete && [1, 4, 5].includes(s) ? 'ISSUE' : 'VERIFIED';
    nodes.push({ id: `system-${s}`, type: s === 5 ? 'BACKUP' : 'SYSTEM', label, status, system_id: label.toLowerCase().replaceAll(' ', '_') });
    edges.push({ id: `subject-${s}`, source: 'subject', target: `system-${s}`, relationship: 'INVESTIGATED_IN', status });
    for (let r = 0; r < 5; r++) {
      const id = `record-${s}-${r}`;
      nodes.push({ id, type: r === 4 ? 'EVIDENCE' : 'RECORD', label: r === 4 ? `Snapshot ${s + 1}` : `${label.split(' ')[0]} record ${r + 1}`, status: r === 0 ? status : 'CONNECTED', system_id: label.toLowerCase().replaceAll(' ', '_'), evidence_ids: [`demo-evidence-${s}`] });
      edges.push({ id: `edge-${id}`, source: `system-${s}`, target: id, relationship: r === 4 ? 'SUPPORTED_BY' : 'CONTAINS', status: r === 0 ? status : 'CONNECTED' });
    }
  });
  const findings: CaseResult['findings'] = complete ? [] : [
    { id: 'f1', title: 'Personal data remains in search', severity: 'HIGH', system_id: 'search_index', resource_id: 'record-1-0', evidence_id: 'demo-evidence-1', description: 'A historical identifier is still exposed in the search snapshot at the audit cutoff.' },
    { id: 'f2', title: 'Replica synchronization is active', severity: 'HIGH', system_id: 'regional_replica', resource_id: 'record-4-0', evidence_id: 'demo-evidence-4', description: 'The synchronization path can recreate prohibited records. Disable it before removing dependent copies.' },
    { id: 'f3', title: 'Restore exclusion is missing', severity: 'MEDIUM', system_id: 'backup_vault', resource_id: 'record-5-0', evidence_id: 'demo-evidence-5', description: 'The backup requires a subject exclusion before a future restore can be considered safe.' },
  ];
  const steps: CaseResult['steps'] = complete ? systems.map((system, i) => ({ step_no: i + 1, phase: 'VERIFICATION', system_id: system.toLowerCase().replaceAll(' ', '_'), resource_id: `record-${i}-0`, operation: i === 5 ? 'VERIFY_RESTORE_BLOCKED' : 'VERIFY_RECORD_ABSENT', state: i === 5 ? 'BLOCKED' : 'ABSENT', evidence_id: `demo-evidence-${i}` })) : [
    ...findings.map((f, i) => ({ step_no: i + 1, phase: 'FINDING' as const, system_id: f.system_id, resource_id: f.resource_id, operation: ['REPORT_REMAINING_RECORD', 'REPORT_ACTIVE_DATA_FLOW', 'REPORT_RESTORE_RISK'][i], state: i === 0 ? 'PRESENT' : 'ACTIVE', evidence_id: f.evidence_id })),
    ...[ ['regional_replica', 'record-4-0', 'DISABLE_DATA_FLOW', 'DISABLED'], ['backup_vault', 'record-5-0', 'BLOCK_RESTORE', 'BLOCKED'], ['search_index', 'record-1-0', 'DELETE_RECORD', 'ABSENT'] ].map(([system_id, resource_id, operation, state], i) => ({ step_no: i + 4, phase: 'REMEDIATION' as const, system_id, resource_id, operation, state, evidence_id: '' })),
    ...[ ['regional_replica', 'record-4-0', 'VERIFY_DATA_FLOW_DISABLED', 'DISABLED'], ['backup_vault', 'record-5-0', 'VERIFY_RESTORE_BLOCKED', 'BLOCKED'], ['search_index', 'record-1-0', 'VERIFY_RECORD_ABSENT', 'ABSENT'] ].map(([system_id, resource_id, operation, state], i) => ({ step_no: i + 7, phase: 'VERIFICATION' as const, system_id, resource_id, operation, state, evidence_id: '' })),
  ];
  return { case_id, deletion_status: complete ? 'COMPLETE' : 'INCOMPLETE', summary: { systems_checked: systems.length, findings_count: findings.length, remediation_count: steps.filter(s => s.phase === 'REMEDIATION').length, verification_count: steps.filter(s => s.phase === 'VERIFICATION').length }, identities: [{ id: 'subject', label: 'Current email', value: 'a••••@example.test', historical: false }, { id: 'old-email', label: 'Historical email', value: 'a••••@old.example.test', historical: true }], findings, steps, evidence: systems.map((label, i) => ({ id: `demo-evidence-${i}`, label: `${label} snapshot`, captured_at: '2026-07-19T10:00:00Z' })), graph_data: { nodes, edges }, request: { email: 'a••••@example.test', requested_at: '2026-07-16T08:00:00Z', audit_at: '2026-07-19T13:00:00Z', reported_status: 'COMPLETE', request_text: 'Please delete my account and associated personal data, including historical copies.' } };
}
export const demoCases = [makeCase(1, false), makeCase(2, true), makeCase(3, false), makeCase(4, true), makeCase(5, true), makeCase(6, false)];
export function metrics(cases: CaseResult[]) {
  const complete = cases.filter(c => c.deletion_status === 'COMPLETE').length;
  const applicable = cases.filter(c => c.deletion_status !== 'NOT_APPLICABLE').length;
  return { total: cases.length, complete, incomplete: cases.filter(c => c.deletion_status === 'INCOMPLETE').length, findings: cases.reduce((sum, c) => sum + c.findings.length, 0), success: applicable ? Math.round(complete / applicable * 100) : null };
}
