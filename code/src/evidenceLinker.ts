import type {
  EvidenceIndex,
  EvidenceObservation,
  IdentityResolution,
  IdentityResolutionCandidate,
} from "./types.ts";

export interface EvidenceMatch {
  user_id: string;
  observation: EvidenceObservation;
  matched_fields: string[];
}

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function normalizePhone(value: string): string {
  return value.replace(/\D/g, "");
}

function normalizeName(value: string): string {
  return value.trim().replace(/\s+/g, " ").toLowerCase();
}

function fieldValues(observation: EvidenceObservation): Record<string, string[]> {
  const values: Record<string, Set<string>> = {};
  for (const [key, value] of Object.entries(observation.fields)) {
    const leafKey = key.split(".").at(-1) ?? key;
    (values[leafKey] ??= new Set()).add(value);
  }
  for (const [key, entries] of Object.entries(observation.identifiers)) {
    for (const value of entries) (values[key] ??= new Set()).add(value);
  }
  return Object.fromEntries(
    Object.entries(values).map(([key, entries]) => [key, [...entries]]),
  );
}

function rawTokenPresent(text: string, value: string): boolean {
  const cleaned = value.trim();
  if (!cleaned) return false;
  const escaped = cleaned.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  return new RegExp(`(?<![A-Za-z0-9])${escaped}(?![A-Za-z0-9])`, "i").test(text);
}

function matchesIdentity(
  observation: EvidenceObservation,
  candidate: IdentityResolutionCandidate,
): string[] {
  const fields = fieldValues(observation);
  const matched = new Set<string>();

  const stableReferenceFields = [
    "user_id",
    "customer_id",
    "customer_reference",
    "subject_reference",
    "user_reference",
    "subject_selector",
  ];
  for (const field of stableReferenceFields) {
    if (fields[field]?.some((value) => value.trim() === candidate.user_id)) {
      matched.add(field);
    }
  }

  const groups: Array<{
    type: keyof IdentityResolutionCandidate["identifiers"];
    fieldPattern: RegExp;
    normalize: (value: string) => string;
  }> = [
    {
      type: "email",
      fieldPattern: /email/,
      normalize: normalizeEmail,
    },
    {
      type: "phone",
      fieldPattern: /phone/,
      normalize: normalizePhone,
    },
    {
      type: "email_hash",
      fieldPattern: /hash/,
      normalize: normalizeEmail,
    },
    {
      type: "name",
      fieldPattern: /(?:^|_)(?:name|full_name|display_name|requester_name|owner_name|customer_name|customer_full_name|recipient_name)$/,
      normalize: normalizeName,
    },
  ];

  for (const group of groups) {
    const candidateValues = candidate.identifiers[group.type]
      .map(group.normalize)
      .filter((value) => value.length > 0);
    if (candidateValues.length === 0) continue;

    for (const [field, values] of Object.entries(fields)) {
      if (!group.fieldPattern.test(field)) continue;
      if (values.some((value) => candidateValues.includes(group.normalize(value)))) {
        matched.add(field);
      }
    }
  }

  const allAliases = [
    candidate.user_id,
    ...candidate.identifiers.email,
    ...candidate.identifiers.email_hash,
  ].filter((value) => value.trim().length >= 5);
  for (const alias of allAliases) {
    if (rawTokenPresent(observation.raw_text, alias)) {
      matched.add("raw_text_identifier");
      break;
    }
  }

  return [...matched].sort();
}

function evidenceAvailableAt(
  observation: EvidenceObservation,
  auditAt: string,
): boolean {
  const cutoff = Date.parse(auditAt);
  if (Number.isNaN(cutoff)) throw new Error(`Invalid audit_at timestamp: ${auditAt}`);
  const captured = Date.parse(observation.captured_at);
  const observed = Date.parse(observation.observed_at);
  return (
    !Number.isNaN(captured) &&
    !Number.isNaN(observed) &&
    captured <= cutoff &&
    observed <= cutoff
  );
}

export function findEvidenceMatchesForRequest(
  index: EvidenceIndex,
  resolution: IdentityResolution,
): EvidenceMatch[] {
  const matches: EvidenceMatch[] = [];
  for (const candidate of resolution.candidates) {
    const linkedResources = new Map<string, Set<string>>();
    for (const observation of index.observations) {
      if (!evidenceAvailableAt(observation, resolution.audit_at)) continue;
      const matchedFields = matchesIdentity(observation, candidate);
      if (matchedFields.length === 0) continue;
      const key = [
        observation.evidence_id,
        observation.system_id,
        observation.resource_id,
      ].join("\u0000");
      const fields = linkedResources.get(key) ?? new Set<string>();
      matchedFields.forEach((field) => fields.add(field));
      linkedResources.set(key, fields);
      matches.push({
        user_id: candidate.user_id,
        observation,
        matched_fields: matchedFields,
      });
    }

    for (const observation of index.observations) {
      if (!evidenceAvailableAt(observation, resolution.audit_at)) continue;
      const key = [
        observation.evidence_id,
        observation.system_id,
        observation.resource_id,
      ].join("\u0000");
      const matchedFields = linkedResources.get(key);
      if (!matchedFields) continue;
      if (matches.some(
        (match) =>
          match.user_id === candidate.user_id &&
          match.observation === observation,
      )) {
        continue;
      }
      matches.push({
        user_id: candidate.user_id,
        observation,
        matched_fields: ["linked_resource_observation", ...matchedFields].sort(),
      });
    }
  }
  return matches.sort(
    (left, right) =>
      Date.parse(left.observation.observed_at) -
        Date.parse(right.observation.observed_at) ||
      left.observation.evidence_id.localeCompare(right.observation.evidence_id) ||
      left.observation.resource_id.localeCompare(right.observation.resource_id),
  );
}
