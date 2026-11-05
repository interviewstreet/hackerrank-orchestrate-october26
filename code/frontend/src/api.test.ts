import { test } from 'node:test';
import assert from 'node:assert/strict';
import { loadCases, isDemo } from './api';
import { demoCases, metrics } from './data';
import { connectedPath, globeLayout, nodeDetails } from './graphModel';

const result = () => ({ ...structuredClone(demoCases[0]), case_id: 'case_1' });
const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status });

test('live API feeds overview metrics, investigation steps, evidence graph and analytics unchanged', async () => {
  assert.equal(isDemo, false);
  const original = globalThis.fetch;
  const supplied = result();
  const controller = new AbortController();
  globalThis.fetch = async (url, options) => {
    assert.equal(url, '/api/cases');
    assert.equal(options?.signal, controller.signal);
    return json([supplied]);
  };
  try {
    const cases = await loadCases(controller.signal);
    assert.deepEqual(cases, [supplied]);
    assert.deepEqual(cases[0].steps, supplied.steps);
    assert.deepEqual(metrics(cases), { total: 1, complete: 0, incomplete: 1, findings: 3, success: 0 });
    const graph = cases[0].graph_data;
    assert.equal(globeLayout(graph.nodes).size, graph.nodes.length);
    const node = graph.nodes.find(n => n.id === 'record-1-0')!;
    assert.equal(nodeDetails(cases[0], node).evidence[0].id, supplied.findings[0].evidence_id);
    assert.ok(connectedPath(cases[0], node.id).nodeIds.has('subject'));
    assert.deepEqual(cases.flatMap(c => c.evidence), supplied.evidence);
  } finally { globalThis.fetch = original; }
});

test('empty live responses stay empty rather than loading fixtures', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => json([]);
  try { assert.deepEqual(await loadCases(), []); } finally { globalThis.fetch = original; }
});

test('API failures never return mock data or expose upstream response content', async () => {
  const original = globalThis.fetch;
  try {
    globalThis.fetch = async () => { throw new Error('private connection details'); };
    await assert.rejects(loadCases(), /Unable to reach the presentation API/);
    globalThis.fetch = async () => json({ error: 'private server details' }, 503);
    await assert.rejects(loadCases(), /API request failed \(503\)/);
    globalThis.fetch = async () => new Response('private invalid payload');
    await assert.rejects(loadCases(), /invalid JSON/);
  } finally { globalThis.fetch = original; }
});

for (const [name, mutate] of [
  ['missing summary counts', (r: any) => { r.summary = {}; }],
  ['null finding', (r: any) => { r.findings = [null]; }],
  ['invalid step', (r: any) => { r.steps[0].phase = 'EXECUTED'; }],
  ['null evidence', (r: any) => { r.evidence = [null]; }],
  ['invalid graph node', (r: any) => { r.graph_data.nodes[0].status = 'invented'; }],
  ['invalid graph edge', (r: any) => { r.graph_data.edges = [null]; }],
  ['invalid request metadata', (r: any) => { r.request.audit_at = null; }],
  ['demo response in live mode', (r: any) => { r.case_id = 'DEMO-001'; }],
] as const) test(`invalid live response is rejected: ${name}`, async () => {
  const original = globalThis.fetch;
  const supplied = result(); mutate(supplied);
  globalThis.fetch = async () => json([supplied]);
  try { await assert.rejects(loadCases(), /unsupported or duplicate/); } finally { globalThis.fetch = original; }
});

test('duplicate case IDs are rejected', async () => {
  const original = globalThis.fetch;
  globalThis.fetch = async () => json([result(), result()]);
  try { await assert.rejects(loadCases(), /duplicate/); } finally { globalThis.fetch = original; }
});

test('aborted loads remain aborted rather than returning fixtures', async () => {
  const original = globalThis.fetch;
  const controller = new AbortController(); controller.abort();
  globalThis.fetch = async () => { throw new DOMException('Aborted', 'AbortError'); };
  try { await assert.rejects(loadCases(controller.signal), { name: 'AbortError' }); } finally { globalThis.fetch = original; }
});
