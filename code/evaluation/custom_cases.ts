import assert from "node:assert/strict";
import { classifyDeletionIntent } from "../src/intentClassifier.ts";
import { resolveIdentityForRequest } from "../src/identityResolver.ts";
import type { IdentityAuditEntry, UserIdentity } from "../src/types.ts";

const cases = [
  {
    name: "export request with an explicitly negated deletion",
    run: () => {
      const result = classifyDeletionIntent(
        "I do not want you to delete my account; please export my data.",
      );
      assert.equal(result.intent, "OTHER_REQUEST");
    },
  },
  {
    name: "Spanish account and personal-data deletion request",
    run: () => {
      const result = classifyDeletionIntent(
        "Por favor, elimina mi cuenta y todos mis datos personales.",
      );
      assert.equal(result.intent, "DELETE_REQUEST");
    },
  },
  {
    name: "historical email resolves before cutoff and later email is excluded",
    run: () => {
      const identities: UserIdentity[] = [
        {
          user_id: "user_eval_01",
          name: "Example Subject",
          email: "current@example.test",
          phone: "+10000000001",
          email_hash: "hash-current",
          updated_at: "2026-01-20T10:00:00Z",
        },
      ];
      const history: IdentityAuditEntry[] = [
        {
          audit_id: "audit_eval_01",
          user_id: "user_eval_01",
          event_time: "2026-01-20T10:00:00Z",
          field_name: "email",
          old_value: "old@example.test",
          new_value: "current@example.test",
        },
        {
          audit_id: "audit_eval_02",
          user_id: "user_eval_01",
          event_time: "2026-02-20T10:00:00Z",
          field_name: "email",
          old_value: "current@example.test",
          new_value: "later@example.test",
        },
      ];
      const historical = resolveIdentityForRequest(
        "old@example.test",
        "2026-02-01T00:00:00Z",
        identities,
        history,
      );
      assert.equal(historical.candidates.length, 1);
      assert.ok(historical.candidates[0].identifiers.email.includes("old@example.test"));
      assert.ok(!historical.candidates[0].identifiers.email.includes("later@example.test"));

      const futureOnly = resolveIdentityForRequest(
        "later@example.test",
        "2026-02-01T00:00:00Z",
        identities,
        history,
      );
      assert.equal(futureOnly.candidates.length, 0);
    },
  },
];

for (const evaluationCase of cases) {
  evaluationCase.run();
  console.log(`PASS ${evaluationCase.name}`);
}

console.log(`Passed ${cases.length} participant-created evaluation cases.`);
