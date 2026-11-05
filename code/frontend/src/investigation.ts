import type { CaseResult, Step } from './types';

/** These labels describe supplied checks; they never change the engine's decision. */
export function verificationLabel(result: CaseResult, step: Step) {
  return result.deletion_status === 'COMPLETE' && step.evidence_id
    ? 'Evidence-backed verification at audit cutoff'
    : 'Pending verification - not executed';
}

export function evidenceDetails(result: CaseResult, evidenceId: string) {
  return {
    evidence: result.evidence.find(e => e.id === evidenceId),
    findings: result.findings.filter(f => f.evidence_id === evidenceId),
    steps: result.steps.filter(s => s.evidence_id === evidenceId),
  };
}
