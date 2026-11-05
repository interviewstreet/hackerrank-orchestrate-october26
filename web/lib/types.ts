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

export type CaseDetail = CaseListItem & {
  request_text: string;
  confidence: string;
  matched_signals: string[];
  reason: string;
  requested_at: string;
  audit_at: string;
  user_id: string | null;
  identities: Identity[];
  evidence_hits: EvidenceHit[];
  resources: unknown[];
  flows: unknown[];
  restore_risks: unknown[];
  timeline: unknown[];
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

/** "2026-09-26T10:38:56Z" -> "2026-09-26 10:38 UTC" (no locale, no timezone shift). */
export function formatUtc(iso: string): string {
  const m = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2})/.exec(iso ?? "");
  return m ? `${m[1]} ${m[2]} UTC` : iso || "—";
}
