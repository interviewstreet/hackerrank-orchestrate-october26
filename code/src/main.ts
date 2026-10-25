import { readFile, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "csv-parse/sync";
import { resolveIdentityForRequest } from "./identityResolver.ts";
import { loadEvidenceIndex } from "./evidenceIndexer.ts";
import { findEvidenceMatchesForRequest } from "./evidenceLinker.ts";
import { generateAuditOutput } from "./policyEngine.ts";
import type {
  AuditDataset,
  DeletionRequest,
  DeletionRule,
  EvidenceFile,
  IdentityAuditEntry,
  RequestIntentClassification,
  SystemActivity,
  UserIdentity,
} from "./types.ts";
import { classifyDeletionIntent } from "./intentClassifier.ts";

const REQUEST_COLUMNS = [
  "case_id",
  "email",
  "requested_at",
  "reported_status",
  "reported_at",
  "audit_at",
  "request_text",
] as const;

const EXPECTED_REQUEST_COUNT = 518;

function csvField(value: string): string {
  return /[",\r\n]/.test(value) ? `"${value.replaceAll('"', '""')}"` : value;
}

function serializeOutputRows(rows: ReturnType<typeof generateAuditOutput>): string {
  const header = "case_id,deletion_status,steps_json";
  const lines = rows.map((row) =>
    [row.case_id, row.deletion_status, row.steps_json].map(csvField).join(","),
  );
  return `${header}\n${lines.join("\n")}\n`;
}

const IDENTITY_COLUMNS = [
  "user_id",
  "name",
  "email",
  "phone",
  "email_hash",
  "updated_at",
] as const;

const IDENTITY_AUDIT_COLUMNS = [
  "audit_id",
  "user_id",
  "event_time",
  "field_name",
  "old_value",
  "new_value",
] as const;

const ACTIVITY_COLUMNS = [
  "activity_id",
  "event_time",
  "event_type",
  "source_system",
  "target_system",
  "resource_id",
  "reported_result",
  "details",
] as const;

const DELETION_RULE_COLUMNS = [
  "rule_id",
  "data_category",
  "condition",
  "required_action",
] as const;

const EVIDENCE_FILE_COLUMNS = [
  "file_id",
  "file_path",
  "origin",
  "captured_at",
] as const;

function parseCsvTable<T>(
  csvText: string,
  sourceName: string,
  expectedColumns: readonly string[],
): T[] {
  const rows = parse(csvText, {
    bom: true,
    columns: true,
    skip_empty_lines: true,
  }) as Record<string, unknown>[];

  const firstRow = rows[0];
  if (!firstRow) {
    throw new Error(`${sourceName} has a header but no data rows.`);
  }

  const actualColumns = Object.keys(firstRow);
  const columnsMatch =
    actualColumns.length === expectedColumns.length &&
    expectedColumns.every((column, index) => actualColumns[index] === column);

  if (!columnsMatch) {
    throw new Error(
      `Unexpected columns in ${sourceName}: ${actualColumns.join(",")}`,
    );
  }

  for (const [index, row] of rows.entries()) {
    const missingColumn = expectedColumns.find(
      (column) => typeof row[column] !== "string",
    );
    if (missingColumn) {
      throw new Error(
        `${sourceName} row ${index + 2} is missing a string value for ${missingColumn}.`,
      );
    }
  }

  return rows as T[];
}

async function readCsvTable<T>(
  datasetDirectory: string,
  fileName: string,
  expectedColumns: readonly string[],
): Promise<T[]> {
  const csvText = await readFile(resolve(datasetDirectory, fileName), "utf8");
  return parseCsvTable<T>(csvText, fileName, expectedColumns);
}

async function loadAuditDataset(
  repositoryRoot: string,
  requestFileName: string,
): Promise<AuditDataset> {
  const datasetDirectory = resolve(repositoryRoot, "dataset");
  const [deletionRequests, identities, identityHistory, activity, deletionRules, evidenceFiles] =
    await Promise.all([
      readCsvTable<DeletionRequest>(datasetDirectory, requestFileName, REQUEST_COLUMNS),
      readCsvTable<UserIdentity>(datasetDirectory, "user_identities.csv", IDENTITY_COLUMNS),
      readCsvTable<IdentityAuditEntry>(datasetDirectory, "user_audit_log.csv", IDENTITY_AUDIT_COLUMNS),
      readCsvTable<SystemActivity>(datasetDirectory, "system_activity.csv", ACTIVITY_COLUMNS),
      readCsvTable<DeletionRule>(datasetDirectory, "deletion_rules.csv", DELETION_RULE_COLUMNS),
      readCsvTable<EvidenceFile>(datasetDirectory, "evidence_files.csv", EVIDENCE_FILE_COLUMNS),
    ]);

  if (
    requestFileName === "deletion_requests.csv" &&
    deletionRequests.length !== EXPECTED_REQUEST_COUNT
  ) {
    throw new Error(
      `Expected ${EXPECTED_REQUEST_COUNT} deletion requests, found ${deletionRequests.length}.`,
    );
  }

  return {
    deletionRequests,
    identities,
    identityHistory,
    activity,
    deletionRules,
    evidenceFiles,
  };
}

async function main(): Promise<void> {
  const sourceDirectory = dirname(fileURLToPath(import.meta.url));
  const repositoryRoot = resolve(sourceDirectory, "../..");
  const requestFileName = argumentValue("--requests", "deletion_requests.csv");
  const outputFileName = argumentValue("--output", "output.csv");
  const dataset = await loadAuditDataset(repositoryRoot, requestFileName);
  const evidenceIndex = await loadEvidenceIndex(
    repositoryRoot,
    dataset.evidenceFiles,
  );
  const intentCounts = { deletion: 0, other: 0 };
  const identityCounts = { unique: 0, ambiguous: 0, unresolved: 0 };
  const evidenceCounts = { casesWithMatches: 0, matchedObservations: 0 };

  for (const request of dataset.deletionRequests) {
    const intent: RequestIntentClassification = classifyDeletionIntent(
      request.request_text,
    );
    if (intent.intent === "OTHER_REQUEST") {
      intentCounts.other += 1;
      continue;
    }

    intentCounts.deletion += 1;
    const resolution = resolveIdentityForRequest(
      request.email,
      request.audit_at,
      dataset.identities,
      dataset.identityHistory,
    );

    if (resolution.candidates.length === 1) {
      identityCounts.unique += 1;
      const matches = findEvidenceMatchesForRequest(evidenceIndex, resolution);
      if (matches.length > 0) evidenceCounts.casesWithMatches += 1;
      evidenceCounts.matchedObservations += matches.length;
    } else if (resolution.candidates.length > 1) {
      identityCounts.ambiguous += 1;
    } else {
      identityCounts.unresolved += 1;
    }
  }

  console.log(
    [
      `Loaded ${dataset.deletionRequests.length} deletion requests`,
      `${dataset.identities.length} current identities`,
      `${dataset.identityHistory.length} identity history entries`,
      `${dataset.activity.length} activity events`,
      `${dataset.deletionRules.length} deletion rules`,
      `${dataset.evidenceFiles.length} evidence manifest entries.`,
    ].join("; "),
  );
  console.log(
    `Request intent: ${intentCounts.deletion} deletion, ${intentCounts.other} other.`,
  );
  console.log(
    `Identity matches: ${identityCounts.unique} unique, ${identityCounts.ambiguous} ambiguous, ${identityCounts.unresolved} unresolved.`,
  );
  const unsupportedMediaCount = evidenceIndex.artifacts.filter(
    (artifact) => artifact.parse_status === "UNSUPPORTED_MEDIA",
  ).length;
  console.log(
    `Evidence index: ${evidenceIndex.artifacts.length} files, ${evidenceIndex.observations.length} observations; ${unsupportedMediaCount} PDF/image files still need text extraction.`,
  );
  console.log(
    `Evidence links by identity and audit_at: ${evidenceCounts.casesWithMatches} cases with matches, ${evidenceCounts.matchedObservations} matched observations.`,
  );

  const outputRows = generateAuditOutput(dataset, evidenceIndex);
  if (
    requestFileName === "deletion_requests.csv" &&
    outputRows.length !== EXPECTED_REQUEST_COUNT
  ) {
    throw new Error(
      `Expected ${EXPECTED_REQUEST_COUNT} output rows, generated ${outputRows.length}.`,
    );
  }
  const outputPath = resolve(repositoryRoot, outputFileName);
  await writeFile(outputPath, serializeOutputRows(outputRows), "utf8");
  const statusCounts = { COMPLETE: 0, INCOMPLETE: 0, NOT_APPLICABLE: 0 };
  for (const row of outputRows) statusCounts[row.deletion_status] += 1;
  console.log(
    `Wrote ${outputPath}: ${outputRows.length} cases (${statusCounts.COMPLETE} complete, ${statusCounts.INCOMPLETE} incomplete, ${statusCounts.NOT_APPLICABLE} not applicable).`,
  );
}

function argumentValue(name: string, fallback: string): string {
  const index = process.argv.indexOf(name);
  if (index < 0) return fallback;
  const value = process.argv[index + 1];
  if (!value || value.startsWith("--")) {
    throw new Error(`Expected a value after ${name}.`);
  }
  return value;
}

main().catch((error: unknown) => {
  const message = error instanceof Error ? error.message : String(error);
  console.error(`Audit agent could not start: ${message}`);
  process.exitCode = 1;
});
