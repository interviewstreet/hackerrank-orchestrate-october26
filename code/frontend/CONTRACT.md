# Member One presentation contract

This frontend consumes Member Two's shared `CaseResult` structure. The exact TypeScript fields are in `src/types.ts`. The engine, deletion-policy logic, email sender and challenge CSV writer remain Member Two's responsibility.

For the first frontend milestone, `GET /api/cases` returns an array of full case results, including `graph_data: { nodes, edges }`. The shared contract did not specify whether this route returns summaries or full results; this is a proposed transport convention to confirm at integration. If the backend returns summaries, adapt `src/api.ts` to fetch `GET /api/cases/{case_id}` before rendering a detail. Do not duplicate engine logic.

Required shared fields: `case_id`, `deletion_status`, `summary`, `identities`, `findings`, `steps`, `evidence`, `graph_data`. The presentation fields inside identities, findings, evidence, and graph nodes are provisional because the supplied shared contract left those arrays untyped. Optional `request` adds `email`, `requested_at`, `audit_at`, `reported_status`, and `request_text`. Missing request metadata is shown as not supplied. Supply already masked identifiers for display; raw identifiers should not be sent unnecessarily.

The graph renders only supplied nodes and edges whose endpoints exist. Node statuses are `VERIFIED`, `ISSUE`, `PENDING`, `CONNECTED`; these are visual classifications, not challenge output statuses. There is no engine inference in the graph component. Finding `resource_id` should match a graph node ID for path highlighting. `evidence_ids` on nodes refer to `evidence[].id`.

`summary` describes the authoritative investigation. Overview metrics derive from the actual loaded cases. `COMPLETE`, `INCOMPLETE`, and `NOT_APPLICABLE` preserve the challenge enumeration. Verification success here means the percentage of applicable cases whose audit status is COMPLETE, not a fabricated step execution rate.

Set Vite's API URL once in `.env.local`. The FastAPI presentation service must permit the local origin `http://127.0.0.1:5173` (and `http://localhost:5173` if used). Failed live requests surface errors and never silently fall back to fixtures.

Slack and email are visibly unavailable until their server endpoints exist. No webhook or provider key belongs in Vite configuration. The frontend currently sends no notifications, approvals, email, or deletion actions. Email endpoint paths, authorization, approval models, revisions, and delivery statuses must be agreed with Member Two before wiring those controls. Remediation and future verification are recommendations, not executed operations.

Demo fixtures are fictional and isolated in `src/data.ts`; their `DEMO-*` IDs do not map to dataset cases. They must never be used to write root `output.csv`.
