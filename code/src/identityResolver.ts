import type {
  IdentityAuditEntry,
  IdentityResolution,
  IdentityResolutionCandidate,
  UserIdentity,
} from "./types.ts";

function normalizeEmail(value: string): string {
  return value.trim().toLowerCase();
}

function addValue(values: Set<string>, value: string): void {
  const cleaned = value.trim();
  if (cleaned.length > 0) {
    values.add(cleaned);
  }
}

function timestampAtOrBefore(timestamp: string, cutoffMs: number): boolean {
  const timestampMs = Date.parse(timestamp);
  if (Number.isNaN(timestampMs)) {
    throw new Error(`Invalid identity timestamp: ${timestamp}`);
  }
  return timestampMs <= cutoffMs;
}

/**
 * Resolves request emails against identity snapshots and email history as of
 * each request's audit_at cutoff. Values from later identity events are ignored.
 */
export function resolveIdentityForRequest(
  requestEmail: string,
  auditAt: string,
  identities: UserIdentity[],
  history: IdentityAuditEntry[],
): IdentityResolution {
  const cutoffMs = Date.parse(auditAt);
  if (Number.isNaN(cutoffMs)) {
    throw new Error(`Invalid audit_at timestamp: ${auditAt}`);
  }

  const normalizedRequestEmail = normalizeEmail(requestEmail);
  const matchingUsers = new Map<
    string,
    { matchedCurrentSnapshot: boolean; matchingAuditIds: Set<string> }
  >();

  for (const identity of identities) {
    if (
      timestampAtOrBefore(identity.updated_at, cutoffMs) &&
      normalizeEmail(identity.email) === normalizedRequestEmail
    ) {
      matchingUsers.set(identity.user_id, {
        matchedCurrentSnapshot: true,
        matchingAuditIds: new Set(),
      });
    }
  }

  for (const entry of history) {
    if (
      entry.field_name.trim().toLowerCase() !== "email" ||
      !timestampAtOrBefore(entry.event_time, cutoffMs)
    ) {
      continue;
    }

    if (
      normalizeEmail(entry.old_value) === normalizedRequestEmail ||
      normalizeEmail(entry.new_value) === normalizedRequestEmail
    ) {
      const match = matchingUsers.get(entry.user_id) ?? {
        matchedCurrentSnapshot: false,
        matchingAuditIds: new Set<string>(),
      };
      match.matchingAuditIds.add(entry.audit_id);
      matchingUsers.set(entry.user_id, match);
    }
  }

  const candidates: IdentityResolutionCandidate[] = [...matchingUsers.entries()]
    .map(([userId, match]) => {
      const identifiers = {
        name: new Set<string>(),
        email: new Set<string>(),
        phone: new Set<string>(),
        email_hash: new Set<string>(),
      };
      const snapshot = identities.find((identity) => identity.user_id === userId);

      if (snapshot && timestampAtOrBefore(snapshot.updated_at, cutoffMs)) {
        addValue(identifiers.name, snapshot.name);
        addValue(identifiers.email, snapshot.email);
        addValue(identifiers.phone, snapshot.phone);
        addValue(identifiers.email_hash, snapshot.email_hash);
      }

      const identityAuditIds = new Set<string>();
      for (const entry of history) {
        if (
          entry.user_id !== userId ||
          !timestampAtOrBefore(entry.event_time, cutoffMs)
        ) {
          continue;
        }

        const fieldName = entry.field_name.trim().toLowerCase();
        if (
          fieldName === "email" ||
          fieldName === "phone" ||
          fieldName === "email_hash" ||
          fieldName === "name" ||
          fieldName === "full_name"
        ) {
          const identifierType =
            fieldName === "full_name" ? "name" : fieldName;
          addValue(identifiers[identifierType], entry.old_value);
          addValue(identifiers[identifierType], entry.new_value);
          identityAuditIds.add(entry.audit_id);
        }
      }

      addValue(identifiers.email, requestEmail);

      return {
        user_id: userId,
        matched_current_snapshot: match.matchedCurrentSnapshot,
        matching_audit_ids: [...match.matchingAuditIds].sort(),
        identity_audit_ids: [...identityAuditIds].sort(),
        identifiers: {
          name: [...identifiers.name].sort(),
          email: [...identifiers.email].sort(),
          phone: [...identifiers.phone].sort(),
          email_hash: [...identifiers.email_hash].sort(),
        },
      };
    })
    .sort((left, right) => left.user_id.localeCompare(right.user_id));

  return {
    request_email: requestEmail,
    audit_at: auditAt,
    candidates,
  };
}
