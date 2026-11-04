import { test } from 'node:test';
import assert from 'node:assert/strict';
import { demoCases, metrics } from './data';
test('fixture summaries reconcile and graph edges resolve', () => {
  for (const result of demoCases) {
    assert.match(result.case_id, /^DEMO-/);
    assert.equal(result.summary.findings_count, result.findings.length);
    assert.equal(result.summary.remediation_count, result.steps.filter(s => s.phase === 'REMEDIATION').length);
    assert.equal(result.summary.verification_count, result.steps.filter(s => s.phase === 'VERIFICATION').length);
    const ids = new Set(result.graph_data.nodes.map(n => n.id));
    for (const edge of result.graph_data.edges) { assert.ok(ids.has(edge.source)); assert.ok(ids.has(edge.target)); }
    for (const finding of result.findings) { assert.ok(ids.has(finding.resource_id)); assert.ok(result.evidence.some(e => e.id === finding.evidence_id)); }
    result.steps.forEach((step, index) => assert.equal(step.step_no, index + 1));
  }
});
test('overview totals and empty-state denominator', () => {
  assert.deepEqual(metrics(demoCases), { total: 6, complete: 3, incomplete: 3, findings: 9, success: 50 });
  assert.deepEqual(metrics([]), { total: 0, complete: 0, incomplete: 0, findings: 0, success: null });
});
