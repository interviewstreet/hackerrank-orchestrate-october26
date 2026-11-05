import { test } from 'node:test';
import assert from 'node:assert/strict';
import { demoCases } from './data';
import { evidenceDetails, verificationLabel } from './investigation';
import { nodeDetails } from './graphModel';

test('evidence review follows exact citations without mixing cases or inferring records', () => {
  const result = structuredClone(demoCases[0]);
  const before = structuredClone(result);
  const details = evidenceDetails(result, 'demo-evidence-1');
  assert.equal(details.evidence?.id, 'demo-evidence-1');
  assert.deepEqual(details.findings.map(f => f.resource_id), ['record-1-0']);
  assert.ok(details.steps.every(s => s.evidence_id === 'demo-evidence-1'));
  assert.deepEqual(evidenceDetails(result, 'unknown'), { evidence: undefined, findings: [], steps: [] });
  assert.deepEqual(result, before);
});

test('graph inspection includes supplied verification in engine order', () => {
  const result = demoCases[0];
  const node = result.graph_data.nodes.find(n => n.id === 'record-1-0')!;
  const details = nodeDetails(result, node);
  assert.deepEqual(details.verification, result.steps.filter(s => s.phase === 'VERIFICATION' && s.resource_id === node.id));
  assert.equal(details.verification.length, 1);
  assert.equal(details.verification[0].operation, 'VERIFY_RECORD_ABSENT');
  assert.equal(verificationLabel(result, details.verification[0]), 'Pending verification - not executed');
});

test('completed checks need a complete backend result and an evidence citation', () => {
  const complete = structuredClone(demoCases[1]);
  assert.equal(verificationLabel(complete, complete.steps[0]), 'Evidence-backed verification at audit cutoff');
  complete.steps[0].evidence_id = '';
  assert.equal(verificationLabel(complete, complete.steps[0]), 'Pending verification - not executed');
  complete.steps[0].evidence_id = 'evidence_1';
  complete.deletion_status = 'INCOMPLETE';
  assert.equal(verificationLabel(complete, complete.steps[0]), 'Pending verification - not executed');
});
