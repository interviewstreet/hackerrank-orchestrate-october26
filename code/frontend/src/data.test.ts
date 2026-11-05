import { test } from 'node:test';
import assert from 'node:assert/strict';
import { demoCases, metrics } from './data';
import { connectedPath, globeLayout, nodeDetails } from './graphModel';
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
test('globe layout preserves supplied nodes and is independent of input order', () => {
  const nodes = demoCases[0].graph_data.nodes;
  const first = globeLayout(nodes), reversed = globeLayout([...nodes].reverse());
  assert.equal(first.size, nodes.length);
  for (const node of nodes) {
    assert.deepEqual(first.get(node.id), reversed.get(node.id));
    assert.ok(first.get(node.id)!.every(Number.isFinite));
  }
  assert.deepEqual(first.get('subject'), [0, -.25, 0]);
  assert.equal(globeLayout([]).size, 0);
});
test('highlight paths include real ancestors and terminate on cycles', () => {
  const result = structuredClone(demoCases[0]);
  result.graph_data.edges.push({ id: 'cycle', source: 'record-1-0', target: 'system-1', relationship: 'REFERENCES', status: 'CONNECTED' });
  result.graph_data.edges.push({ id: 'dangling', source: 'missing', target: 'record-1-0', relationship: 'INVALID', status: 'CONNECTED' });
  const path = connectedPath(result, 'record-1-0');
  assert.ok(path.nodeIds.has('subject'));
  assert.ok(path.nodeIds.has('system-1'));
  assert.ok(path.nodeIds.has('record-1-0'));
  assert.ok(!path.nodeIds.has('missing'));
  assert.ok(!path.nodeIds.has('record-5-0'));
  assert.ok(!path.edgeIds.has('dangling'));
  assert.equal(connectedPath(result, 'unknown').nodeIds.size, 0);
});
test('alert inspection binds evidence and remediation to the selected resource', () => {
  const result = demoCases[0];
  const node = result.graph_data.nodes.find(n => n.id === 'record-1-0')!;
  const details = nodeDetails(result, node);
  assert.deepEqual(details.evidenceIds, ['demo-evidence-1']);
  assert.deepEqual(details.findings.map(f => f.id), ['f1']);
  assert.deepEqual(details.actions.map(s => s.operation), ['DELETE_RECORD']);
  const compliant = demoCases[1];
  assert.equal(nodeDetails(compliant, compliant.graph_data.nodes[0]).actions.length, 0);
});

test('spherical depth layout preserves every node without mutating evidence', () => {
  const graph = structuredClone(demoCases[0].graph_data);
  const before = JSON.stringify(graph);
  const positions = globeLayout(graph.nodes);
  const radii = graph.nodes.filter(n => n.type !== 'IDENTITY').map(n => Math.hypot(...positions.get(n.id)!));
  assert.equal(positions.size, graph.nodes.length);
  assert.ok(Math.max(...radii) - Math.min(...radii) > .2);
  assert.ok(radii.every(r => r >= 2 && r <= 2.5));
  assert.equal(JSON.stringify(graph), before);
});
