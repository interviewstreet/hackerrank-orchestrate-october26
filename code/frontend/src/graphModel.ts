import type { CaseResult, GraphNode } from './types';
export type Position = [number, number, number];
export const nodeColors = { VERIFIED: '#00b897', ISSUE: '#ff435e', PENDING: '#d89b24', CONNECTED: '#46e7ff' };

/** Fixed outer rim plus depth layers; geometry never creates evidence relationships. */
export function globeLayout(nodes: GraphNode[]): Map<string, Position> {
  const sorted = [...nodes].sort((a, b) => a.id.localeCompare(b.id));
  const outer = sorted.filter(n => n.type !== 'IDENTITY');
  const positions = new Map<string, Position>();
  sorted.filter(n => n.type === 'IDENTITY').forEach((n, i) => positions.set(n.id, [i * .25, -.25, 0]));
  const rimCount = Math.min(18, outer.length);
  // Interleave resource types so alert/system nodes do not collect on one side.
  const ordered = [...outer].sort((a, b) => hash(a.id) - hash(b.id) || a.id.localeCompare(b.id));
  ordered.forEach((node, i) => {
    if (i < rimCount) {
      const angle = Math.PI / 2 + i * Math.PI * 2 / rimCount;
      positions.set(node.id, [Math.cos(angle) * 2.42, Math.sin(angle) * 2.28, Math.sin(angle * 3) * .38]);
    } else {
      const index = i - rimCount, count = outer.length - rimCount;
      const y = 1 - 2 * (index + .5) / count, angle = index * 2.39996;
      const r = 2.05, ring = Math.sqrt(1 - y * y);
      positions.set(node.id, [Math.cos(angle) * ring * r, y * r, Math.sin(angle) * ring * r]);
    }
  });
  return positions;
}
function hash(id: string) { return [...id].reduce((value, char) => (Math.imul(value, 31) + char.charCodeAt(0)) >>> 0, 2166136261); }

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
  return { findings, evidence: result.evidence.filter(e => evidenceIds.has(e.id)), evidenceIds: [...evidenceIds], actions: result.steps.filter(s => s.phase === 'REMEDIATION' && resources.has(s.resource_id)), verification: result.steps.filter(s => s.phase === 'VERIFICATION' && resources.has(s.resource_id)) };
}
