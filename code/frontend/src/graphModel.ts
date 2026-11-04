import type { CaseResult, GraphNode } from './types';
export type Position = [number, number, number];
export const nodeColors = { VERIFIED: '#247f68', ISSUE: '#f0442a', PENDING: '#b36a12', CONNECTED: '#53575b' };

/** Stable spherical layout; layout positions carry no analytical meaning. */
export function globeLayout(nodes: GraphNode[]): Map<string, Position> {
  const sorted = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
  const outer = sorted.filter(n => n.type !== 'IDENTITY');
  const positions = new Map<string, Position>();
  sorted.filter(n => n.type === 'IDENTITY').forEach((n, i) => positions.set(n.id, [i * 0.25, 0, 0]));
  outer.forEach((node, index) => {
    const y = 1 - 2 * (index + 0.5) / outer.length;
    const angle = index * Math.PI * (3 - Math.sqrt(5)) + 0.5;
    const radius = ['SYSTEM', 'BACKUP'].includes(node.type) ? 2.0 : 2.43;
    const ring = Math.sqrt(1 - y * y);
    positions.set(node.id, [Math.cos(angle) * ring * radius, y * radius, Math.sin(angle) * ring * radius]);
  });
  return positions;
}

/** Only supplied edges participate in highlighted paths, including cyclic graphs. */
export function connectedPath(result: CaseResult, selectedId: string | null) {
  const nodeIds = new Set<string>(), edgeIds = new Set<string>();
  if (!selectedId || !result.graph_data.nodes.some(n => n.id === selectedId)) return { nodeIds, edgeIds };
  nodeIds.add(selectedId);
  const known = new Set(result.graph_data.nodes.map(n => n.id));
  const edges = result.graph_data.edges.filter(e => known.has(e.source) && known.has(e.target));
  for (const edge of edges) {
    if (edge.source === selectedId || edge.target === selectedId) { nodeIds.add(edge.source); nodeIds.add(edge.target); edgeIds.add(edge.id); }
  }
  const visited = new Set([selectedId]), queue = [selectedId];
  for (let i = 0; i < queue.length; i++) {
    for (const edge of edges.filter(e => e.target === queue[i])) {
      nodeIds.add(edge.source); edgeIds.add(edge.id);
      if (!visited.has(edge.source)) { visited.add(edge.source); queue.push(edge.source); }
    }
  }
  return { nodeIds, edgeIds };
}

export function nodeDetails(result: CaseResult, node: GraphNode) {
  const findings = result.findings.filter(f => f.resource_id === node.id || (['SYSTEM', 'BACKUP'].includes(node.type) && f.system_id === node.system_id));
  const evidenceIds = new Set([...(node.evidence_ids || []), ...findings.map(f => f.evidence_id)].filter(Boolean));
  const resources = new Set([node.id, ...findings.map(f => f.resource_id)]);
  return { findings, evidence: result.evidence.filter(e => evidenceIds.has(e.id)), evidenceIds: [...evidenceIds], actions: result.steps.filter(s => s.phase === 'REMEDIATION' && resources.has(s.resource_id)) };
}
