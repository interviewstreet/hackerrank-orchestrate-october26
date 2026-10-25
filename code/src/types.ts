export type DeletionStatus = "COMPLETE" | "INCOMPLETE" | "NOT_APPLICABLE";

export type ReportedWorkflowStatus =
  | "COMPLETE"
  | "PARTIALLY_COMPLETE"
  | "NOT_STARTED";

export type RequestIntent = "DELETE_REQUEST" | "OTHER_REQUEST";

export type RequestIntentReason =
  | "EXPLICIT_DELETION"
  | "VERIFY_PRIOR_DELETION"
  | "NO_CLEAR_DELETION_AUTHORIZATION";

export interface RequestIntentClassification {
  intent: RequestIntent;
  reason: RequestIntentReason;
}

export type StepPhase = "FINDING" | "REMEDIATION" | "VERIFICATION";

export type StepOperation =
  | "REPORT_REMAINING_RECORD"
  | "REPORT_EXPOSED_PII"
  | "REPORT_ACTIVE_DATA_FLOW"
  | "REPORT_RESTORE_RISK"
  | "DISABLE_DATA_FLOW"
  | "BLOCK_RESTORE"
  | "DELETE_RECORD"
  | "REDACT_RECORD"
  | "ANONYMIZE_RECORD"
  | "VERIFY_RECORD_ABSENT"
  | "VERIFY_RECORD_PRESENT"
  | "VERIFY_RECORD_REDACTED"
  | "VERIFY_RECORD_ANONYMIZED"
  | "VERIFY_DATA_FLOW_DISABLED"
  | "VERIFY_RESTORE_BLOCKED";

export type StepState =
  | "PRESENT"
  | "ACTIVE"
  | "DISABLED"
  | "BLOCKED"
  | "ABSENT"
  | "REDACTED"
  | "ANONYMIZED";

export interface DeletionRequest {
  case_id: string;
  email: string;
  requested_at: string;
  reported_status: ReportedWorkflowStatus;
  reported_at: string;
  audit_at: string;
  request_text: string;
}

export interface UserIdentity {
  user_id: string;
  name: string;
  email: string;
  phone: string;
  email_hash: string;
  updated_at: string;
}

export interface IdentityAuditEntry {
  audit_id: string;
  user_id: string;
  event_time: string;
  field_name: string;
  old_value: string;
  new_value: string;
}

export interface SystemActivity {
  activity_id: string;
  event_time: string;
  event_type: string;
  source_system: string;
  target_system: string;
  resource_id: string;
  reported_result: string;
  details: string;
}

export interface DeletionRule {
  rule_id: string;
  data_category: string;
  condition: string;
  required_action: string;
}

export interface EvidenceFile {
  file_id: string;
  file_path: string;
  origin: string;
  captured_at: string;
}

export type EvidenceFormat = "JSON" | "LOG" | "SQL" | "TEXT" | "PDF" | "IMAGE" | "UNKNOWN";

export interface EvidenceArtifact {
  file_id: string;
  file_path: string;
  captured_at: string;
  format: EvidenceFormat;
  parse_status: "INDEXED" | "UNSUPPORTED_MEDIA";
  observation_count: number;
}

export interface EvidenceObservation {
  evidence_id: string;
  source_path: string;
  captured_at: string;
  observed_at: string;
  source_format: EvidenceFormat;
  system_id: string;
  resource_id: string;
  data_category: string;
  state: string;
  identifiers: Record<string, string[]>;
  fields: Record<string, string>;
  raw_text: string;
}

export interface EvidenceIndex {
  artifacts: EvidenceArtifact[];
  observations: EvidenceObservation[];
}

export interface AuditDataset {
  deletionRequests: DeletionRequest[];
  identities: UserIdentity[];
  identityHistory: IdentityAuditEntry[];
  activity: SystemActivity[];
  deletionRules: DeletionRule[];
  evidenceFiles: EvidenceFile[];
}

export interface IdentityResolutionCandidate {
  user_id: string;
  matched_current_snapshot: boolean;
  matching_audit_ids: string[];
  identity_audit_ids: string[];
  identifiers: {
    name: string[];
    email: string[];
    phone: string[];
    email_hash: string[];
  };
}

export interface IdentityResolution {
  request_email: string;
  audit_at: string;
  candidates: IdentityResolutionCandidate[];
}

export interface AuditStep {
  step_no: number;
  phase: StepPhase;
  system_id: string;
  resource_id: string;
  operation: StepOperation;
  state: StepState;
  evidence_id: string;
}
