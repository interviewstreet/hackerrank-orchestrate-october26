// Types and display labels shared by the API routes and the pages.
// Safe to import from client components (no Node APIs here).

export const OUR_STATUSES = ["COMPLETE", "INCOMPLETE", "NOT_APPLICABLE"] as const;
export type Status = (typeof OUR_STATUSES)[number];

export const REPORTED_STATUSES = ["COMPLETE", "PARTIALLY_COMPLETE", "NOT_STARTED"] as const;

export const LANGUAGES = ["en", "es", "pt", "fr", "ja", "ko"] as const;
export const LANGUAGE_NAMES: Record<string, string> = {
  en: "English",
  es: "Spanish",
  pt: "Portuguese",
  fr: "French",
  ja: "Japanese",
  ko: "Korean",
  unknown: "Unknown",
};

export type Summary = {
  total_cases: number;
  status_counts: Record<string, number>;
  reported_status_counts: Record<string, number>;
  reported_vs_ours: Record<string, Record<string, number>>;
  reported_complete_but_not_complete: number;
  classification_counts: Record<string, number>;
  language_counts: Record<string, number>;
  policy_engine_connected: boolean;
};

export type CaseListItem = {
  case_id: string;
  email: string; // masked by the export
  reported_status: string;
  our_status: string;
  classification: string;
  language: string;
};

export type Identity = {
  kind: string;
  value: string;
  is_historical: boolean;
  audit_id: string;
};

export type EvidenceHit = {
  file_id: string;
  system_id: string;
  resource_id: string;
  matched_identifier: string;
  captured_at: string;
};

export type Step = {
  step_no: number;
  phase: string;
  system_id: string;
  resource_id: string;
  operation: string;
  state: string;
  evidence_id: string;
};

export type TrailEntry = {
  value: string; // masked email
  is_current: boolean;
  is_request: boolean;
  replaced_by: { audit_id: string; changed_at: string } | null;
};

export type LineageClaim = {
  activity_id: string;
  event_time: string;
  label: string;
  reported_result: string;
  details: string;
};

export type LineageNode = {
  id: string;
  system_id: string;
  resource_id: string;
  replica_or_table: string;
  source: "evidence" | "activity";
  group: "primary" | "copy" | "backup";
  file_ids: string[];
  origins: string[];
  matched_identifiers: string[];
  first_captured_at: string;
  last_captured_at: string;
  claims: LineageClaim[];
  active_flow: { kind: string; active_at_audit: boolean; evidence_id: string } | null;
  restore_risk: { active_at_audit: boolean; evidence_id: string } | null;
};

export type LineageEdge = LineageClaim & { from: string; to: string; kind: "claim" };

export type Lineage = {
  groups: { id: LineageNode["group"]; label: string }[];
  nodes: LineageNode[];
  edges: LineageEdge[];
  edge_note: string;
};

export type TimelineEvent = {
  time: string;
  system_id: string;
  resource_id: string;
  event: string;
  state_after: string;
  evidence_id: string;
};

export type Basis = "proof" | "claim" | "record";

/**
 * Proof = direct evidence of state (snapshot, SQL row, read-back, document).
 * Claim = something a system reported (activity rows, second-hand ledgers).
 * Record = audit-log identity changes, the request, the audit time.
 * Works for TRACE's derived timeline and for P3's timeline (by evidence id).
 */
export function eventBasis(e: TimelineEvent): Basis {
  if (e.event === "EVIDENCE_PROOF" || e.event === "ABSENCE_PROOF") return "proof";
  if (e.event === "EVIDENCE_CLAIM" || e.evidence_id.startsWith("activity_")) return "claim";
  if (e.evidence_id.startsWith("evidence_")) return "proof";
  return "record";
}

export type LieDetectorRow = {
  system_id: string;
  proof_cases: number;
  claim_only_cases: number;
  share_with_proof: number;
};

export type LieDetectorData = {
  reported_complete_cases: number;
  systems: LieDetectorRow[];
  basis: string;
  note: string;
  policy_engine_connected: boolean;
};

export type CaseDetail = CaseListItem & {
  request_text: string;
  confidence: string;
  matched_signals: string[];
  reason: string;
  requested_at: string;
  audit_at: string;
  user_id: string | null;
  identities: Identity[];
  identity_trail: TrailEntry[];
  evidence_hits: EvidenceHit[];
  lineage: Lineage;
  resources: unknown[];
  flows: unknown[];
  restore_risks: unknown[];
  timeline: TimelineEvent[];
  steps: Step[];
};

// Status colours (dataviz status palette, dark surface). Colour is never the
// only cue: every use is paired with the text label.
export const STATUS_META: Record<string, { label: string; color: string; hint: string }> = {
  COMPLETE: {
    label: "Complete",
    color: "#0ca30c",
    hint: "Every copy has the required treatment and nothing can recreate it.",
  },
  INCOMPLETE: {
    label: "Incomplete",
    color: "#d03b3b",
    hint: "Personal data remains, or a sync or restore can bring it back.",
  },
  NOT_APPLICABLE: {
    label: "Not applicable",
    color: "#898781",
    hint: "The request did not ask for deletion.",
  },
};

export const REPORTED_LABELS: Record<string, string> = {
  COMPLETE: "Complete",
  PARTIALLY_COMPLETE: "Partially complete",
  NOT_STARTED: "Not started",
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** "2026-05-28T19:48:13Z" -> "28 May 2026" (UTC date, no locale). */
export function formatDay(iso: string): string {
  const m = /^(\d{4})-(\d{2})-(\d{2})/.exec(iso ?? "");
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]} ${m[1]}` : iso || "—";
}

/** "2026-09-26T10:38:56Z" -> "2026-09-26 10:38 UTC" (no locale, no timezone shift). */
export function formatUtc(iso: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/.exec(iso ?? "");
  return m ? `${m[1]} ${m[2]} UTC` : iso || "—";
}
