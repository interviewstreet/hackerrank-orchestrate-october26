import type {
  AuditDataset,
  AuditStep,
  DeletionRequest,
  DeletionRule,
  DeletionStatus,
  EvidenceIndex,
  EvidenceObservation,
  IdentityResolution,
  IdentityResolutionCandidate,
  StepOperation,
  StepPhase,
  StepState,
  SystemActivity,
} from "./types.ts";
import type { EvidenceMatch } from "./evidenceLinker.ts";
import { findEvidenceMatchesForRequest } from "./evidenceLinker.ts";
import { resolveIdentityForRequest } from "./identityResolver.ts";
import { classifyDeletionIntent } from "./intentClassifier.ts";

export interface AuditOutputRow {
  case_id: string;
  deletion_status: DeletionStatus;
  steps_json: string;
}

type PolicyCategory =
  | "USER_PROFILE"
  | "SECONDARY_IDENTIFIER"
  | "SEARCH_INDEX_ENTRY"
  | "CACHE_ENTRY"
  | "SUPPORT_MESSAGE"
  | "SUPPORT_ATTACHMENT"
  | "ANALYTICS_PROFILE"
  | "PRODUCT_TELEMETRY"
  | "USER_EXPORT"
  | "MARKETING_PROFILE"
  | "EMAIL_DELIVERY_LOG"
  | "SECURITY_AUDIT_LOG"
  | "LEGAL_HOLD_RECORD"
  | "BACKUP_ARCHIVE"
  | "ACCOUNT_TOMBSTONE"
  | "DATA_FLOW";

type ObservedState =
  | "ABSENT"
  | "PRESENT"
  | "IDENTIFIABLE"
  | "REDACTED"
  | "ANONYMIZED"
  | "ACTIVE"
  | "DISABLED"
  | "BLOCKED"
  | "UNKNOWN";

interface PolicyResource {
  category: PolicyCategory;
  systemId: string;
  resourceId: string;
  state: ObservedState;
  evidenceId: string;
  observation: EvidenceObservation;
}

interface ResourceAssessment {
  resource: PolicyResource;
  finding?: { operation: StepOperation; state: StepState };
  remediation?: { operation: StepOperation; state: StepState };
  verification?: { operation: StepOperation; state: StepState };
  violatesPolicy: boolean;
  unknown: boolean;
}

const FINDING_ORDER: StepOperation[] = [
  "REPORT_REMAINING_RECORD",
  "REPORT_EXPOSED_PII",
  "REPORT_ACTIVE_DATA_FLOW",
  "REPORT_RESTORE_RISK",
];

const REMEDIATION_ORDER: StepOperation[] = [
  "DISABLE_DATA_FLOW",
  "BLOCK_RESTORE",
  "DELETE_RECORD",
  "REDACT_RECORD",
  "ANONYMIZE_RECORD",
];

const VERIFICATION_ORDER: StepOperation[] = [
  "VERIFY_RECORD_ABSENT",
  "VERIFY_RECORD_PRESENT",
  "VERIFY_RECORD_REDACTED",
  "VERIFY_RECORD_ANONYMIZED",
  "VERIFY_DATA_FLOW_DISABLED",
  "VERIFY_RESTORE_BLOCKED",
];

const PHASE_ORDER: StepPhase[] = ["FINDING", "REMEDIATION", "VERIFICATION"];

function normalized(value: string | undefined): string {
  return (value ?? "").trim().toUpperCase().replace(/[^A-Z0-9]+/g, "_");
}

function fieldValue(
  observation: EvidenceObservation,
  names: string[],
): string | undefined {
  for (const name of names) {
    const exact = observation.fields[name];
    if (exact !== undefined && exact.trim() !== "") return exact.trim();
    const nested = Object.entries(observation.fields).find(
      ([key, value]) =>
        (key.split(".").at(-1) ?? key).replace(/\[\d+\]$/, "") === name &&
        value.trim() !== "",
    )?.[1];
    if (nested) return nested.trim();
  }
  return undefined;
}

function canonicalCategory(
  observation: EvidenceObservation,
): PolicyCategory | undefined {
  const labels = [
    fieldValue(observation, ["record_type"]),
    fieldValue(observation, ["data_category"]),
    fieldValue(observation, ["collection"]),
    fieldValue(observation, ["collection_name"]),
    fieldValue(observation, ["table_name"]),
    fieldValue(observation, ["object_key"]),
    fieldValue(observation, ["file_name"]),
    fieldValue(observation, ["bucket", "storage_path"]),
    observation.data_category,
    observation.source_path,
  ]
    .filter((value): value is string => Boolean(value))
    .map(normalized)
    .join("_");

  const exactCategories: PolicyCategory[] = [
    "ACCOUNT_TOMBSTONE",
    "SECONDARY_IDENTIFIER",
    "SEARCH_INDEX_ENTRY",
    "USER_PROFILE",
    "CACHE_ENTRY",
    "SUPPORT_ATTACHMENT",
    "SUPPORT_MESSAGE",
    "ANALYTICS_PROFILE",
    "PRODUCT_TELEMETRY",
    "USER_EXPORT",
    "MARKETING_PROFILE",
    "EMAIL_DELIVERY_LOG",
    "SECURITY_AUDIT_LOG",
    "LEGAL_HOLD_RECORD",
    "BACKUP_ARCHIVE",
    "DATA_FLOW",
  ];
  for (const category of exactCategories) {
    if (labels.includes(category)) return category;
  }

  const system = normalized(observation.system_id);
  const event = normalized(
    [
      fieldValue(observation, ["event"]),
      fieldValue(observation, ["event_name"]),
      fieldValue(observation, ["event_type"]),
      fieldValue(observation, ["connector_name"]),
    ]
      .filter(Boolean)
      .join("_"),
  );
  const signal = `${labels}_${system}_${event}`;

  if (/DELETED_CUSTOMER_REFERENCES|ACCOUNT_TOMBSTONE|TOMBSTONE/.test(signal)) {
    return "ACCOUNT_TOMBSTONE";
  }
  if (/TICKET_ATTACHMENTS|SUPPORT_ATTACHMENT|ATTACHMENT/.test(signal)) {
    return "SUPPORT_ATTACHMENT";
  }
  if (/LEGAL_HOLD|LEGAL_RETENTION|RETAINED_ORDER_RECORD/.test(signal)) {
    return "LEGAL_HOLD_RECORD";
  }
  if (/SECURITY_AUDIT|AUDIT_RECORD|SECURITY_SERVICE/.test(signal)) {
    return "SECURITY_AUDIT_LOG";
  }
  if (/BACKUP|RESTORE_POLICY|RESTORE_ENTRY/.test(signal)) {
    return "BACKUP_ARCHIVE";
  }
  if (/DATA_FLOW|CONNECTOR|INTEGRATION_SERVICE/.test(signal)) {
    return "DATA_FLOW";
  }
  if (/SEARCH_INDEX|SEARCH_DOCUMENT|INDEX_QUERY|SEARCH_SERVICE/.test(signal)) {
    return "SEARCH_INDEX_ENTRY";
  }
  if (/ANALYTICS_PROFILE|CUSTOMER_ANALYTICS|ANALYTICS_PLATFORM/.test(signal)) {
    return "ANALYTICS_PROFILE";
  }
  if (/PRODUCT_TELEMETRY|TELEMETRY/.test(signal)) return "PRODUCT_TELEMETRY";
  if (/SUPPORT_MESSAGE|SUPPORT_CONVERSATION|SUPPORT_TICKET|SUPPORT_PLATFORM|SUPPORT_REPLICA/.test(signal)) {
    return "SUPPORT_MESSAGE";
  }
  if (/USER_EXPORT|CUSTOMER_EXPORT|EXPORT_JOB|EXPORT_SERVICE/.test(signal)) {
    return "USER_EXPORT";
  }
  if (/MARKETING_PROFILE|MARKETING_PLATFORM/.test(signal)) {
    return "MARKETING_PROFILE";
  }
  if (/EMAIL_DELIVERY|NOTIFICATION_DELIVERY|EMAIL_DELIVERY_SERVICE/.test(signal)) {
    return "EMAIL_DELIVERY_LOG";
  }
  if (/CACHE_ENTRY|CACHE_SERVICE/.test(signal)) return "CACHE_ENTRY";
  if (/SECONDARY_IDENTIFIER/.test(signal)) return "SECONDARY_IDENTIFIER";
  if (/USER_PROFILE|CUSTOMER_PROFILE|ACCOUNT_SERVICE|PROFILE_LOOKUP/.test(signal)) {
    return "USER_PROFILE";
  }
  return undefined;
}

function resourceState(
  observation: EvidenceObservation,
  category: PolicyCategory,
): ObservedState {
  const result = normalized(
    fieldValue(observation, ["result", "reported_result", "status", "state"]),
  );
  const rows = fieldValue(observation, ["rows", "total_hits", "record_count"]);
  const httpStatus = fieldValue(observation, ["http_status", "status_code"]);

  if (category === "DATA_FLOW") {
    const enabled = normalized(fieldValue(observation, ["enabled", "is_enabled"]));
    if (["TRUE", "YES", "1", "ACTIVE", "ENABLED"].includes(enabled)) return "ACTIVE";
    if (["FALSE", "NO", "0", "DISABLED", "STOPPED"].includes(enabled)) return "DISABLED";
    if (["ACTIVE", "ENABLED"].includes(result)) return "ACTIVE";
    if (["DISABLED", "STOPPED", "INACTIVE"].includes(result)) return "DISABLED";
  }

  if (category === "BACKUP_ARCHIVE") {
    const restoreAllowed = normalized(
      fieldValue(observation, ["restore_allowed", "restore_enabled"]),
    );
    if (["TRUE", "YES", "1", "ACTIVE", "ALLOWED"].includes(restoreAllowed)) return "ACTIVE";
    if (["FALSE", "NO", "0", "BLOCKED", "DENIED"].includes(restoreAllowed)) return "BLOCKED";
    if (["ACTIVE", "RESTORABLE", "RESTORE_ALLOWED"].includes(result)) return "ACTIVE";
    if (["BLOCKED", "RESTORE_BLOCKED", "DENIED"].includes(result)) return "BLOCKED";
  }

  if (["NOT_FOUND", "NOTFOUND", "MISS", "ABSENT", "NO_MATCH"].includes(result)) {
    return "ABSENT";
  }
  if (rows !== undefined && /^\s*0\s*$/.test(rows)) return "ABSENT";
  if (httpStatus === "404") return "ABSENT";
  if (result === "REDACTED") return "REDACTED";
  if (result === "ANONYMIZED" || result === "ANONYMISED") return "ANONYMIZED";
  if (result === "IDENTIFIABLE") return "IDENTIFIABLE";
  if (
    category === "SUPPORT_MESSAGE" &&
    identifiersExplicitlyRedacted(observation)
  ) return "REDACTED";
  if (
    ["ANALYTICS_PROFILE", "PRODUCT_TELEMETRY"].includes(category) &&
    analyticsIdentifiersExplicitlyCleared(observation)
  ) return "ANONYMIZED";
  if (
    category === "EMAIL_DELIVERY_LOG" &&
    ["email", "recipient_email"].some((field) => fieldValue(observation, [field]) === "NULL")
  ) return "REDACTED";
  if (result === "BLOCKED" || result === "RESTORE_BLOCKED") return "BLOCKED";
  if (result === "DISABLED" || result === "STOPPED" || result === "INACTIVE") {
    return "DISABLED";
  }
  if (result === "ACTIVE" || result === "ENABLED") return "ACTIVE";
  if (["FOUND", "HIT", "PRESENT"].includes(result)) return "PRESENT";
  if (rows !== undefined && /^\s*[1-9]\d*\s*$/.test(rows)) return "PRESENT";
  if (
    fieldValue(observation, ["resource_id", "record_id", "activity_id"]) &&
    ["SQL", "JSON", "PDF", "IMAGE"].includes(observation.source_format) &&
    category !== "DATA_FLOW" &&
    category !== "BACKUP_ARCHIVE"
  ) {
    return "PRESENT";
  }
  if (hasDirectPersonalIdentifier(observation)) return "PRESENT";
  return "UNKNOWN";
}

function hasValue(value: string | undefined): boolean {
  return Boolean(value && !["NULL", "NONE", "N/A", "REDACTED", "ANONYMIZED"].includes(normalized(value)));
}

function hasDirectPersonalIdentifier(observation: EvidenceObservation): boolean {
  const directIdentifier = /(?:^|_)(?:email|email_address|phone|phone_number|email_hash|name|full_name|display_name|requester_name|owner_name|customer_name|customer_full_name|recipient_name)$/;
  return Object.entries(observation.fields).some(([key, value]) => {
    const leaf = (key.split(".").at(-1) ?? key).replace(/\[\d+\]$/, "");
    return directIdentifier.test(leaf) && hasValue(value);
  });
}

function analyticsIdentifiersExplicitlyCleared(
  observation: EvidenceObservation,
): boolean {
  const requiredGroups = [
    ["email", "email_address", "customer_email"],
    ["phone", "phone_number", "customer_phone"],
    ["email_hash"],
    ["user_id", "customer_id", "customer_reference", "subject_reference"],
  ];

  return requiredGroups.every((aliases) => {
    const values = aliases
      .map((alias) => fieldValue(observation, [alias]))
      .filter((value): value is string => value !== undefined);
    return values.length > 0 && values.every((value) => !hasValue(value));
  });
}

function identifiersExplicitlyRedacted(observation: EvidenceObservation): boolean {
  const directIdentifier = /(?:^|_)(?:email|email_address|phone|phone_number|email_hash|name|full_name|display_name|requester_name|owner_name|customer_name|customer_full_name|recipient_name)$/;
  const entries = Object.entries(observation.fields).filter(([key]) =>
    directIdentifier.test((key.split(".").at(-1) ?? key).replace(/\[\d+\]$/, "")),
  );
  const groups = new Set(
    entries.map(([key]) => {
      const leaf = (key.split(".").at(-1) ?? key).replace(/\[\d+\]$/, "");
      if (/email_hash$/.test(leaf)) return "hash";
      if (/email(?:_address)?$/.test(leaf)) return "email";
      if (/phone(?:_number)?$/.test(leaf)) return "phone";
      return "name";
    }),
  );
  const allCleared = entries.length > 0 && entries.every(([, value]) => !hasValue(value));
  return allCleared && groups.has("email") && groups.has("phone") && groups.has("name");
}

function isAttributable(observation: EvidenceObservation): boolean {
  return ["user_id", "customer_id", "customer_reference", "subject_reference"].some(
    (field) => hasValue(fieldValue(observation, [field])),
  );
}

function compareObservations(
  left: EvidenceObservation,
  right: EvidenceObservation,
): number {
  return (
    Date.parse(left.captured_at) - Date.parse(right.captured_at) ||
    Date.parse(left.observed_at) - Date.parse(right.observed_at)
  );
}

function latestResources(matches: EvidenceMatch[]): PolicyResource[] {
  const selected = new Map<string, PolicyResource>();
  for (const match of matches) {
    const observation = match.observation;
    const category = canonicalCategory(observation);
    if (!category) continue;
    const key = `${category}\u0000${observation.system_id}\u0000${observation.resource_id}`;
    const current = selected.get(key);
    if (current) {
      const timeOrder = compareObservations(current.observation, observation);
      const currentState = resourceState(current.observation, current.category);
      const nextState = resourceState(observation, category);
      const currentSeverity = stateSeverity(currentState);
      const nextSeverity = stateSeverity(nextState);
      if (timeOrder > 0) continue;
      if (timeOrder === 0) {
        if (currentState === "UNKNOWN" && nextState !== "UNKNOWN") {
          // A response/readback at the same instant is more informative than
          // its request/start event, even when the resulting state is ABSENT.
        } else if (currentState !== "UNKNOWN" && nextState === "UNKNOWN") {
          continue;
        } else if (currentSeverity >= nextSeverity) {
          continue;
        }
      }
    }
    selected.set(key, {
      category,
      systemId: observation.system_id,
      resourceId: observation.resource_id,
      state: resourceState(observation, category),
      evidenceId: observation.evidence_id,
      observation,
    });
  }
  return [...selected.values()].sort(
    (left, right) =>
      left.systemId.localeCompare(right.systemId) ||
      left.resourceId.localeCompare(right.resourceId),
  );
}

function stateSeverity(state: ObservedState): number {
  if (["PRESENT", "IDENTIFIABLE", "ACTIVE"].includes(state)) return 3;
  if (state === "UNKNOWN") return 2;
  return 1;
}

const CATEGORY_SYSTEM: Partial<Record<PolicyCategory, string>> = {
  USER_PROFILE: "account_service",
  SECONDARY_IDENTIFIER: "profile_service",
  SEARCH_INDEX_ENTRY: "search_service",
  CACHE_ENTRY: "cache_service",
  SUPPORT_MESSAGE: "support_platform",
  SUPPORT_ATTACHMENT: "support_platform",
  ANALYTICS_PROFILE: "analytics_platform",
  PRODUCT_TELEMETRY: "analytics_platform",
  USER_EXPORT: "export_service",
  MARKETING_PROFILE: "marketing_platform",
  EMAIL_DELIVERY_LOG: "email_delivery_service",
  SECURITY_AUDIT_LOG: "security_service",
  LEGAL_HOLD_RECORD: "legal_service",
  BACKUP_ARCHIVE: "backup_service",
  ACCOUNT_TOMBSTONE: "identity_service",
  DATA_FLOW: "integration_service",
};

function systemForResource(
  observation: EvidenceObservation,
  category: PolicyCategory,
  knownSystems: Set<string>,
): string {
  if (knownSystems.has(observation.system_id)) return observation.system_id;
  const explicit = fieldValue(observation, [
    "system_id",
    "system",
    "source_system",
    "target_system",
    "service",
    "data_store",
  ]);
  if (explicit && knownSystems.has(explicit)) return explicit;
  return CATEGORY_SYSTEM[category] ?? observation.system_id;
}

function withSystemMapping(
  resources: PolicyResource[],
  knownSystems: Set<string>,
): PolicyResource[] {
  return resources.map((resource) => ({
    ...resource,
    systemId: systemForResource(
      resource.observation,
      resource.category,
      knownSystems,
    ),
  }));
}

function activityIdentityMatches(
  candidate: IdentityResolutionCandidate,
  request: DeletionRequest,
  dataset: AuditDataset,
  index: EvidenceIndex,
  knownSystems: Set<string>,
): EvidenceMatch[] {
  const auditAt = Date.parse(request.audit_at);
  const aliases = [
    candidate.user_id,
    ...candidate.identifiers.email,
    ...candidate.identifiers.email_hash,
  ].map((value) => value.trim().toLowerCase()).filter((value) => value.length >= 5);
  if (Number.isNaN(auditAt) || aliases.length === 0) return [];

  const linkedResources = new Map<string, string>();
  for (const event of dataset.activity) {
    if (
      event.event_type.trim().toUpperCase() !== "LINK_RESOURCE_IDENTITY" ||
      Date.parse(event.event_time) > auditAt ||
      !aliases.some((alias) => event.details.toLowerCase().includes(alias))
    ) continue;

    const key = `${event.target_system}\u0000${event.resource_id}`;
    const existing = linkedResources.get(key);
    if (existing && existing !== candidate.user_id) {
      linkedResources.delete(key);
      continue;
    }
    linkedResources.set(key, candidate.user_id);
  }

  const matches: EvidenceMatch[] = [];
  for (const observation of index.observations) {
    const capturedAt = Date.parse(observation.captured_at);
    const observedAt = Date.parse(observation.observed_at);
    if (
      Number.isNaN(capturedAt) || Number.isNaN(observedAt) ||
      capturedAt > auditAt || observedAt > auditAt
    ) continue;
    const key = `${observation.system_id}\u0000${observation.resource_id}`;
    if (linkedResources.get(key) !== candidate.user_id) continue;
    matches.push({
      user_id: candidate.user_id,
      observation,
      matched_fields: ["activity_identity_link"],
    });
  }
  return matches;
}

function nearestProfileDeletionEvent(
  request: DeletionRequest,
  dataset: AuditDataset,
): SystemActivity | undefined {
  const reportedAt = Date.parse(request.reported_at);
  const auditAt = Date.parse(request.audit_at);
  if (Number.isNaN(reportedAt) || Number.isNaN(auditAt)) return undefined;

  const candidates = dataset.activity
    .filter(
      (event) =>
        event.event_type.trim().toUpperCase() === "DELETE_RECORD" &&
        event.target_system.trim().toLowerCase() === "account_service" &&
        Date.parse(event.event_time) <= auditAt,
    )
    .map((event) => ({
      event,
      distance: Math.abs(Date.parse(event.event_time) - reportedAt),
    }))
    .sort((left, right) =>
      left.distance - right.distance ||
      left.event.activity_id.localeCompare(right.event.activity_id),
    );

  const closest = candidates[0];
  const next = candidates[1];
  const maximumDistanceMs = 10 * 60 * 1000;
  const minimumSeparationMs = 20 * 60 * 1000;
  if (!closest || closest.distance > maximumDistanceMs) return undefined;
  if (next && next.distance - closest.distance < minimumSeparationMs) return undefined;
  return closest.event;
}

function activityProfileLocators(
  dataset: AuditDataset,
): Map<string, SystemActivity> {
  const requestLocators = new Map<string, SystemActivity>();
  const claimsByActivity = new Map<string, string[]>();

  for (const request of dataset.deletionRequests) {
    if (classifyDeletionIntent(request.request_text).intent !== "DELETE_REQUEST") continue;
    const event = nearestProfileDeletionEvent(request, dataset);
    if (!event) continue;
    requestLocators.set(request.case_id, event);
    const claimedBy = claimsByActivity.get(event.activity_id) ?? [];
    claimedBy.push(request.case_id);
    claimsByActivity.set(event.activity_id, claimedBy);
  }

  for (const [activityId, caseIds] of claimsByActivity) {
    if (caseIds.length > 1) {
      for (const caseId of caseIds) requestLocators.delete(caseId);
      continue;
    }
    const event = dataset.activity.find((candidate) => candidate.activity_id === activityId);
    if (event && caseIds.length === 1) requestLocators.set(caseIds[0], event);
  }
  return requestLocators;
}

function profileSnapshotMatchesForActivity(
  request: DeletionRequest,
  event: SystemActivity,
  candidateUserId: string,
  index: EvidenceIndex,
  knownSystems: Set<string>,
): EvidenceMatch[] {
  const auditAt = Date.parse(request.audit_at);
  const eventAt = Date.parse(event.event_time);
  if (Number.isNaN(auditAt) || Number.isNaN(eventAt)) return [];
  const artifacts = new Map(index.artifacts.map((artifact) => [artifact.file_id, artifact]));
  const groups = new Map<string, EvidenceObservation[]>();

  for (const observation of index.observations) {
    const artifact = artifacts.get(observation.evidence_id);
    const capturedAt = Date.parse(observation.captured_at);
    const observedAt = Date.parse(observation.observed_at);
    const category = canonicalCategory(observation);
    if (
      observation.source_format !== "SQL" ||
      artifact?.format !== "SQL" ||
      !category ||
      category !== "USER_PROFILE" ||
      systemForResource(observation, category, knownSystems) !== "account_service" ||
      capturedAt < eventAt ||
      capturedAt > auditAt ||
      observedAt > auditAt
    ) {
      continue;
    }
    const tableName = fieldValue(observation, ["table_name", "collection_name"]) ?? "profile_snapshot";
    const key = `${observation.evidence_id}\u0000${tableName}`;
    const rows = groups.get(key) ?? [];
    rows.push(observation);
    groups.set(key, rows);
  }

  const linked: EvidenceMatch[] = [];
  for (const rows of groups.values()) {
    const exemplar = rows[0];
    const artifact = artifacts.get(exemplar.evidence_id);
    if (!artifact) continue;
    const exactResourceRows = rows.filter((row) => row.resource_id === event.resource_id);
    if (exactResourceRows.length > 0) {
      for (const observation of exactResourceRows) {
        linked.push({
          user_id: candidateUserId,
          observation,
          matched_fields: ["unique_report_time_activity_locator"],
        });
      }
      continue;
    }

    const tableName = fieldValue(exemplar, ["table_name", "collection_name"]) ?? "profile_snapshot";
    const observation: EvidenceObservation = {
      ...exemplar,
      evidence_id: artifact.file_id,
      captured_at: artifact.captured_at,
      observed_at: artifact.captured_at,
      system_id: "account_service",
      resource_id: event.resource_id,
      data_category: tableName,
      state: "ABSENT",
      identifiers: {},
      fields: {
        table_name: tableName,
        resource_id: event.resource_id,
        status_code: "404",
      },
      raw_text: `scoped SQL snapshot contained no row for ${event.resource_id}`,
    };
    linked.push({
      user_id: candidateUserId,
      observation,
      matched_fields: ["unique_report_time_activity_locator", "scoped_sql_absence"],
    });
  }
  return linked;
}

function hasUnresolvedNearbyDeletionActivity(
  request: DeletionRequest,
  dataset: AuditDataset,
  matches: EvidenceMatch[],
  knownSystems: Set<string>,
): boolean {
  const reportAt = Date.parse(request.reported_at);
  const auditAt = Date.parse(request.audit_at);
  if (Number.isNaN(reportAt) || Number.isNaN(auditAt)) return true;

  const deletionRequests = dataset.deletionRequests.filter(
    (candidate) => classifyDeletionIntent(candidate.request_text).intent === "DELETE_REQUEST",
  );
  const maximumDistanceMs = 10 * 60 * 1000;
  const minimumSeparationMs = 20 * 60 * 1000;

  for (const event of dataset.activity) {
    const eventAt = Date.parse(event.event_time);
    if (
      event.event_type.trim().toUpperCase() !== "DELETE_RECORD" ||
      eventAt > auditAt ||
      Math.abs(eventAt - reportAt) > maximumDistanceMs
    ) {
      continue;
    }

    const requestDistances = deletionRequests
      .map((candidate) => ({
        caseId: candidate.case_id,
        distance: Math.abs(Date.parse(candidate.reported_at) - eventAt),
      }))
      .sort((left, right) => left.distance - right.distance);
    const closestRequest = requestDistances[0];
    const nextRequest = requestDistances[1];
    if (
      !closestRequest ||
      closestRequest.caseId !== request.case_id ||
      (nextRequest && nextRequest.distance - closestRequest.distance < minimumSeparationMs)
    ) {
      continue;
    }

    const resourceEvidenceFound = matches.some((match) => {
      if (match.observation.resource_id !== event.resource_id) return false;
      const category = canonicalCategory(match.observation);
      return Boolean(
        category &&
        systemForResource(match.observation, category, knownSystems) === event.target_system,
      );
    });
    if (!resourceEvidenceFound) return true;
  }
  return false;
}

function policyActionFor(
  category: PolicyCategory,
  rules: DeletionRule[],
): string | undefined {
  return rules.find((rule) => rule.data_category.trim().toUpperCase() === category)
    ?.required_action.trim().toUpperCase();
}

function assessResource(
  resource: PolicyResource,
  rules: DeletionRule[],
): ResourceAssessment {
  const action = policyActionFor(resource.category, rules);
  const directPii = hasDirectPersonalIdentifier(resource.observation);
  const state = resource.state;
  const result: ResourceAssessment = {
    resource,
    violatesPolicy: false,
    unknown: state === "UNKNOWN",
  };

  if (resource.category === "DATA_FLOW") {
    if (state === "ACTIVE") {
      result.finding = { operation: "REPORT_ACTIVE_DATA_FLOW", state: "ACTIVE" };
      result.remediation = { operation: "DISABLE_DATA_FLOW", state: "DISABLED" };
      result.verification = { operation: "VERIFY_DATA_FLOW_DISABLED", state: "DISABLED" };
      result.violatesPolicy = true;
      result.unknown = false;
    } else if (state === "DISABLED") {
      result.verification = { operation: "VERIFY_DATA_FLOW_DISABLED", state: "DISABLED" };
      result.unknown = false;
    } else {
      result.unknown = true;
    }
    return result;
  }

  if (resource.category === "BACKUP_ARCHIVE") {
    if (state === "ACTIVE") {
      result.finding = { operation: "REPORT_RESTORE_RISK", state: "ACTIVE" };
      result.remediation = { operation: "BLOCK_RESTORE", state: "BLOCKED" };
      result.verification = { operation: "VERIFY_RESTORE_BLOCKED", state: "BLOCKED" };
      result.violatesPolicy = true;
      result.unknown = false;
    } else if (state === "BLOCKED") {
      result.verification = { operation: "VERIFY_RESTORE_BLOCKED", state: "BLOCKED" };
      result.unknown = false;
    } else {
      result.unknown = true;
    }
    return result;
  }

  if (action === "DELETE") {
    if (state === "ABSENT") {
      result.verification = { operation: "VERIFY_RECORD_ABSENT", state: "ABSENT" };
      result.unknown = false;
    } else if (state === "PRESENT" || state === "IDENTIFIABLE") {
      result.finding = { operation: "REPORT_REMAINING_RECORD", state: "PRESENT" };
      result.remediation = { operation: "DELETE_RECORD", state: "ABSENT" };
      result.verification = { operation: "VERIFY_RECORD_ABSENT", state: "ABSENT" };
      result.violatesPolicy = true;
      result.unknown = false;
    }
    return result;
  }

  if (action === "REDACT") {
    result.unknown = true;
    if (state === "REDACTED" && !directPii) {
      result.verification = { operation: "VERIFY_RECORD_REDACTED", state: "REDACTED" };
      result.unknown = false;
    } else if (state === "IDENTIFIABLE" || directPii) {
      result.finding = { operation: "REPORT_EXPOSED_PII", state: "PRESENT" };
      result.remediation = { operation: "REDACT_RECORD", state: "REDACTED" };
      result.verification = { operation: "VERIFY_RECORD_REDACTED", state: "REDACTED" };
      result.violatesPolicy = true;
      result.unknown = false;
    }
    if (
      resource.category === "ACCOUNT_TOMBSTONE" &&
      state === "PRESENT" &&
      !directPii
    ) {
      result.verification = { operation: "VERIFY_RECORD_REDACTED", state: "REDACTED" };
      result.unknown = false;
    }
    return result;
  }

  if (action === "ANONYMIZE") {
    result.unknown = true;
    const attributable = isAttributable(resource.observation) || directPii;
    if (state === "ANONYMIZED" && !directPii) {
      result.verification = {
        operation: "VERIFY_RECORD_ANONYMIZED",
        state: "ANONYMIZED",
      };
      result.unknown = false;
    } else if (state === "IDENTIFIABLE" || directPii || (state === "PRESENT" && attributable)) {
      result.finding = { operation: "REPORT_EXPOSED_PII", state: "PRESENT" };
      result.remediation = { operation: "ANONYMIZE_RECORD", state: "ANONYMIZED" };
      result.verification = {
        operation: "VERIFY_RECORD_ANONYMIZED",
        state: "ANONYMIZED",
      };
      result.violatesPolicy = true;
      result.unknown = false;
    }
    return result;
  }

  if (action === "RETAIN") {
    if (state === "PRESENT" || state === "IDENTIFIABLE") {
      result.verification = { operation: "VERIFY_RECORD_PRESENT", state: "PRESENT" };
      result.unknown = false;
    } else if (state === "ABSENT") {
      result.verification = { operation: "VERIFY_RECORD_PRESENT", state: "PRESENT" };
      result.unknown = true;
    }
    return result;
  }
  return result;
}

function orderIndex(operation: StepOperation, phase: StepPhase): number {
  const order =
    phase === "FINDING"
      ? FINDING_ORDER
      : phase === "REMEDIATION"
        ? REMEDIATION_ORDER
        : VERIFICATION_ORDER;
  return order.indexOf(operation);
}

function buildStep(
  resource: PolicyResource,
  phase: StepPhase,
  operation: StepOperation,
  state: StepState,
  evidenceId: string,
): AuditStep {
  return {
    step_no: 0,
    phase,
    system_id: resource.systemId,
    resource_id: resource.resourceId,
    operation,
    state,
    evidence_id: evidenceId,
  };
}

function dedupeAndOrderSteps(steps: AuditStep[]): AuditStep[] {
  const byResource = new Map<string, AuditStep>();
  for (const step of steps) {
    const key = [
      step.phase,
      step.operation,
      step.system_id,
      step.resource_id,
      step.state,
    ].join("\u0000");
    const existing = byResource.get(key);
    if (!existing || (!existing.evidence_id && step.evidence_id)) {
      byResource.set(key, step);
    }
  }
  return [...byResource.values()]
    .sort(
      (left, right) =>
        PHASE_ORDER.indexOf(left.phase) - PHASE_ORDER.indexOf(right.phase) ||
        orderIndex(left.operation, left.phase) - orderIndex(right.operation, right.phase) ||
        left.system_id.localeCompare(right.system_id) ||
        left.resource_id.localeCompare(right.resource_id),
    )
    .map((step, index) => ({ ...step, step_no: index + 1 }));
}

function stepsForAssessments(
  assessments: ResourceAssessment[],
  complete: boolean,
): AuditStep[] {
  const steps: AuditStep[] = [];
  const incomplete = !complete;
  const add = (
    assessment: ResourceAssessment,
    phase: StepPhase,
    item: ResourceAssessment["finding"],
    evidenceId: string,
  ) => {
    if (!item) return;
    steps.push(
      buildStep(
        assessment.resource,
        phase,
        item.operation,
        item.state,
        evidenceId,
      ),
    );
  };

  for (const assessment of assessments) {
    add(assessment, "FINDING", assessment.finding, assessment.resource.evidenceId);
    add(assessment, "REMEDIATION", assessment.remediation, "");
    if (assessment.verification) {
      add(
        assessment,
        "VERIFICATION",
        assessment.verification,
        incomplete ? "" : assessment.resource.evidenceId,
      );
    }
  }
  return dedupeAndOrderSteps(steps);
}

function evaluateDeletionRequest(
  request: DeletionRequest,
  dataset: AuditDataset,
  evidenceIndex: Parameters<typeof findEvidenceMatchesForRequest>[0],
  knownSystems: Set<string>,
  activityLocator?: SystemActivity,
): AuditOutputRow {
  const intent = classifyDeletionIntent(request.request_text);
  if (intent.intent !== "DELETE_REQUEST") {
    return { case_id: request.case_id, deletion_status: "NOT_APPLICABLE", steps_json: "[]" };
  }

  const resolution: IdentityResolution = resolveIdentityForRequest(
    request.email,
    request.audit_at,
    dataset.identities,
    dataset.identityHistory,
  );
  if (resolution.candidates.length !== 1) {
    return { case_id: request.case_id, deletion_status: "INCOMPLETE", steps_json: "[]" };
  }

  const matches = findEvidenceMatchesForRequest(evidenceIndex, resolution);
  matches.push(
    ...activityIdentityMatches(
      resolution.candidates[0],
      request,
      dataset,
      evidenceIndex,
      knownSystems,
    ),
  );
  const hasDirectProfileMatch = matches.some((match) => {
    const category = canonicalCategory(match.observation);
    return (
      category === "USER_PROFILE" &&
      systemForResource(match.observation, category, knownSystems) === "account_service"
    );
  });
  if (!hasDirectProfileMatch && activityLocator) {
    matches.push(
      ...profileSnapshotMatchesForActivity(
        request,
        activityLocator,
        resolution.candidates[0].user_id,
        evidenceIndex,
        knownSystems,
      ),
    );
  }
  const resources = withSystemMapping(latestResources(matches), knownSystems);
  const assessments = resources.map((resource) => assessResource(resource, dataset.deletionRules));
  const findings = assessments.some((assessment) => assessment.violatesPolicy);
  const unresolvedNearbyActivity = hasUnresolvedNearbyDeletionActivity(
    request,
    dataset,
    matches,
    knownSystems,
  );
  const profileAbsenceProven = assessments.some(
    (assessment) =>
      assessment.resource.category === "USER_PROFILE" &&
      assessment.resource.state === "ABSENT",
  );
  const unknownRelevantState = assessments.some((assessment) => assessment.unknown);
  const complete =
    !findings &&
    profileAbsenceProven &&
    !unknownRelevantState &&
    !unresolvedNearbyActivity;
  const steps = stepsForAssessments(assessments, complete);

  return {
    case_id: request.case_id,
    deletion_status: complete ? "COMPLETE" : "INCOMPLETE",
    steps_json: JSON.stringify(steps),
  };
}

export function generateAuditOutput(
  dataset: AuditDataset,
  evidenceIndex: Parameters<typeof findEvidenceMatchesForRequest>[0],
): AuditOutputRow[] {
  const knownSystems = new Set(
    dataset.activity.flatMap((event) => [event.source_system, event.target_system]),
  );
  const activityLocators = activityProfileLocators(dataset);
  return dataset.deletionRequests
    .map((request) =>
      evaluateDeletionRequest(
        request,
        dataset,
        evidenceIndex,
        knownSystems,
        activityLocators.get(request.case_id),
      ),
    )
    .sort((left, right) => left.case_id.localeCompare(right.case_id));
}
