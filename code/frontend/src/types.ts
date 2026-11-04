export type DeletionStatus = 'COMPLETE' | 'INCOMPLETE' | 'NOT_APPLICABLE';
export type NodeStatus = 'VERIFIED' | 'ISSUE' | 'PENDING' | 'CONNECTED';
export interface GraphNode { id: string; type: string; label: string; status: NodeStatus; system_id?: string; evidence_ids?: string[] }
export interface GraphEdge { id: string; source: string; target: string; relationship: string; status: NodeStatus }
export interface Step { step_no: number; phase: 'FINDING' | 'REMEDIATION' | 'VERIFICATION'; system_id: string; resource_id: string; operation: string; state: string; evidence_id: string }
export interface Finding { id: string; title: string; severity: 'HIGH' | 'MEDIUM' | 'LOW'; system_id: string; resource_id: string; evidence_id: string; description: string }
export interface CaseResult {
  case_id: string; deletion_status: DeletionStatus;
  summary: { systems_checked: number; findings_count: number; remediation_count: number; verification_count: number };
  identities: { id: string; label: string; value: string; historical: boolean }[];
  findings: Finding[]; steps: Step[];
  evidence: { id: string; label: string; captured_at: string }[];
  graph_data: { nodes: GraphNode[]; edges: GraphEdge[] };
  request?: { email: string; requested_at: string; audit_at: string; reported_status: string; request_text: string };
}
