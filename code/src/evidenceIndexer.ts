import { execFileSync } from "node:child_process";
import { DatabaseSync } from "node:sqlite";
import { mkdir, readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { tmpdir } from "node:os";
import { join, relative, resolve, sep } from "node:path";
import tesseract from "tesseract.js";
import type {
  EvidenceArtifact,
  EvidenceFile,
  EvidenceFormat,
  EvidenceIndex,
  EvidenceObservation,
} from "./types.ts";

type Scalar = string | number | boolean;
type ScalarFields = Record<string, string>;
type OcrWorker = Awaited<ReturnType<typeof tesseract.createWorker>>;

let ocrWorkerPromise: Promise<OcrWorker> | undefined;

const IDENTIFIER_FIELDS = new Set([
  "email",
  "email_address",
  "contact_email",
  "customer_email",
  "customer_email_address",
  "owner_email",
  "requester_email",
  "recipient_email",
  "phone",
  "phone_number",
  "contact_phone",
  "customer_phone",
  "owner_phone",
  "requester_phone",
  "recipient_phone",
  "email_hash",
  "name",
  "full_name",
  "display_name",
  "customer_name",
  "customer_full_name",
  "user_id",
  "customer_id",
  "customer_reference",
  "subject_reference",
  "lookup_value",
  "requester_name",
  "owner_name",
  "recipient_name",
]);

const RESOURCE_FIELDS = [
  "resource_id",
  "record_id",
  "id",
  "activity_id",
  "audit_id",
  "ticket_id",
  "attachment_id",
  "document_id",
  "job_id",
  "connector_id",
  "export_id",
  "order_id",
  "order_reference",
  "archive_key",
  "object_key",
  "file_name",
];

const CONTEXT_FIELDS = new Set([
  ...IDENTIFIER_FIELDS,
  ...RESOURCE_FIELDS,
  "collection",
  "collection_name",
  "data_category",
  "category",
  "record_type",
  "system",
  "system_id",
  "source_system",
  "origin_system",
  "data_store",
  "service",
  "event_time",
  "observed_at",
  "captured_at",
  "updated_at",
  "created_at",
  "recorded_at",
  "occurred_at",
  "event_date",
  "effective_at",
  "signed_at",
  "date",
  "timestamp",
  "state",
  "status",
  "result",
  "reported_result",
  "enabled",
  "restore_allowed",
  "deleted",
  "is_deleted",
  "redacted",
  "anonymized",
]);

const SYSTEM_FIELDS = [
  "system_id",
  "system",
  "source_system",
  "origin_system",
  "data_store",
  "service",
];

const CATEGORY_FIELDS = [
  "data_category",
  "category",
  "collection",
  "collection_name",
  "record_type",
];

const TIME_FIELDS = [
  "event_time",
  "occurred_at",
  "observed_at",
  "recorded_at",
  "event_date",
  "effective_at",
  "signed_at",
  "date",
  "timestamp",
  "captured_at",
  "created_at",
  "updated_at",
  "exported_at",
];

const STATE_FIELDS = [
  "state",
  "status",
  "result",
  "reported_result",
  "enabled",
  "restore_allowed",
  "deleted",
  "is_deleted",
  "redacted",
  "anonymized",
];

function scalarString(value: unknown): string | undefined {
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") {
    return String(value);
  }
  return undefined;
}

function normalizeFields(fields: ScalarFields): ScalarFields {
  return Object.fromEntries(
    Object.entries(fields).map(([key, value]) => [key.trim().toLowerCase(), value]),
  );
}

function directScalarFields(value: Record<string, unknown>): ScalarFields {
  const fields: ScalarFields = {};
  for (const [key, fieldValue] of Object.entries(value)) {
    const scalar = scalarString(fieldValue);
    if (scalar !== undefined) fields[key] = scalar;
    else if (fieldValue === null) fields[key] = "NULL";
  }
  return fields;
}

function flattenScalarFields(
  value: unknown,
  prefix = "",
  fields: ScalarFields = {},
): ScalarFields {
  if (Array.isArray(value)) {
    value.forEach((child, index) =>
      flattenScalarFields(child, `${prefix}[${index}]`, fields),
    );
  } else if (value && typeof value === "object") {
    for (const [key, child] of Object.entries(value)) {
      const path = prefix ? `${prefix}.${key}` : key;
      flattenScalarFields(child, path, fields);
    }
  } else {
    const scalar = scalarString(value);
    if (scalar !== undefined && prefix) fields[prefix] = scalar;
    else if (value === null && prefix) fields[prefix] = "NULL";
  }
  return fields;
}

function identifierValues(fields: ScalarFields): Record<string, string[]> {
  const result: Record<string, Set<string>> = {};
  for (const [key, value] of Object.entries(fields)) {
    const leafKey = key.split(".").at(-1) ?? key;
    if (
      !IDENTIFIER_FIELDS.has(leafKey) ||
      value.trim() === "" ||
      ["NULL", "NONE", "N/A", "REDACTED", "ANONYMIZED"].includes(value.trim().toUpperCase())
    ) continue;
    (result[leafKey] ??= new Set()).add(value.trim());
  }
  return Object.fromEntries(
    Object.entries(result).map(([key, values]) => [key, [...values].sort()]),
  );
}

function firstField(fields: ScalarFields, names: string[]): string | undefined {
  for (const name of names) {
    const value = fields[name];
    if (value !== undefined && value.trim() !== "") return value.trim();
    const nested = Object.entries(fields).find(
      ([key, nestedValue]) =>
        (key.split(".").at(-1) ?? key).replace(/\[\d+\]$/, "") === name &&
        nestedValue.trim() !== "",
    )?.[1];
    if (nested) return nested.trim();
  }
  return undefined;
}

function formatForPath(filePath: string): EvidenceFormat {
  const extension = filePath.split(".").at(-1)?.toLowerCase();
  if (extension === "json") return "JSON";
  if (extension === "log") return "LOG";
  if (extension === "sql") return "SQL";
  if (extension === "txt") return "TEXT";
  if (extension === "pdf") return "PDF";
  if (extension === "png" || extension === "jpg" || extension === "jpeg") {
    return "IMAGE";
  }
  return "UNKNOWN";
}

function categoryFromPath(filePath: string): string {
  const fileName = filePath.split(/[\\/]/).at(-1) ?? filePath;
  return fileName.replace(/\.[^.]+$/, "").toLowerCase();
}

function parseTimestamp(
  fields: ScalarFields,
  fallback: string,
  rawText = "",
): string {
  const timestampInText = /^\s*[-*]?\s*(\d{4}-\d{2}-\d{2}[T ][^\s|]+)/.exec(rawText)?.[1];
  const value = firstField(fields, TIME_FIELDS) ?? timestampInText;
  if (!value) return fallback;
  const timestamp = Date.parse(value);
  return Number.isNaN(timestamp) ? fallback : new Date(timestamp).toISOString();
}

function makeObservation(args: {
  evidence: EvidenceFile;
  format: EvidenceFormat;
  path: string;
  fields: ScalarFields;
  rawText: string;
  fallbackSystem?: string;
  fallbackCategory?: string;
}): EvidenceObservation {
  const fields = normalizeFields(args.fields);
  const resourceId = firstField(fields, RESOURCE_FIELDS) ?? `${args.evidence.file_id}:${args.path}`;
  const systemId =
    firstField(fields, SYSTEM_FIELDS) ??
    args.fallbackSystem ??
    args.evidence.origin ??
    "unknown";
  const category =
    firstField(fields, CATEGORY_FIELDS) ?? args.fallbackCategory ?? "unknown";

  return {
    evidence_id: args.evidence.file_id,
    source_path: args.evidence.file_path,
    captured_at: args.evidence.captured_at,
    observed_at: parseTimestamp(fields, args.evidence.captured_at, args.rawText),
    source_format: args.format,
    system_id: systemId,
    resource_id: resourceId,
    data_category: category,
    state: firstField(fields, STATE_FIELDS) ?? "UNKNOWN",
    identifiers: identifierValues(fields),
    fields,
    raw_text: args.rawText,
  };
}

function hasIdentifierOrResource(fields: ScalarFields): boolean {
  return (
    Object.keys(identifierValues(fields)).length > 0 ||
    Boolean(firstField(fields, RESOURCE_FIELDS))
  );
}

function contextFrom(fields: ScalarFields): ScalarFields {
  const context: ScalarFields = {};
  for (const [key, value] of Object.entries(fields)) {
    const leafKey = key.split(".").at(-1) ?? key;
    if (CONTEXT_FIELDS.has(leafKey)) context[leafKey] = value;
  }
  return context;
}

function parseJsonObservations(
  input: unknown,
  evidence: EvidenceFile,
  sourceFormat: EvidenceFormat = "JSON",
): EvidenceObservation[] {
  const observations: EvidenceObservation[] = [];

  const visit = (
    node: unknown,
    path: string,
    inheritedFields: ScalarFields,
    fallbackSystem?: string,
    fallbackCategory?: string,
  ): void => {
    if (Array.isArray(node)) {
      node.forEach((child, index) =>
        visit(child, `${path}[${index}]`, inheritedFields, fallbackSystem, path.slice(2)),
      );
      return;
    }
    if (!node || typeof node !== "object") return;

    const record = node as Record<string, unknown>;
    const ownFields = normalizeFields(directScalarFields(record));
    const localFields = { ...inheritedFields, ...ownFields };
    const nextContext = { ...inheritedFields, ...contextFrom(ownFields) };
    const serviceKey = Object.keys(record).find((key) =>
      /(?:_service|_platform|_system)$/i.test(key),
    );
    const nextSystem =
      firstField(ownFields, SYSTEM_FIELDS) ?? serviceKey ?? fallbackSystem;
    const nextCategory =
      firstField(ownFields, CATEGORY_FIELDS) ?? fallbackCategory;

    if (Object.keys(ownFields).length > 0 && hasIdentifierOrResource(ownFields)) {
      observations.push(
        makeObservation({
          evidence,
          format: sourceFormat,
          path,
          fields: localFields,
          rawText: JSON.stringify(ownFields) ?? "",
          fallbackSystem: nextSystem,
          fallbackCategory: nextCategory,
        }),
      );
    }

    for (const [key, value] of Object.entries(record)) {
      if (!value || typeof value !== "object") continue;
      const childContext = { ...nextContext };
      const childSystem = /(?:_service|_platform|_system)$/i.test(key)
        ? key
        : nextSystem;
      visit(value, `${path}.${key}`, childContext, childSystem, key);
    }
  };

  visit(input, "$", {}, undefined, undefined);
  return observations;
}

function parseKeyValueLine(line: string): ScalarFields {
  const fields: ScalarFields = {};
  const expression = /([A-Za-z][A-Za-z0-9_.-]*)=(?:"([^"]*)"|'([^']*)'|([^\s,|}]+))/g;
  for (const match of line.matchAll(expression)) {
    fields[match[1]] = match[2] ?? match[3] ?? match[4] ?? "";
  }
  return fields;
}

function parsePipeRecord(line: string): ScalarFields | undefined {
  const cells = line.split("|").map((cell) => cell.trim());
  if (cells.length < 5 || Number.isNaN(Date.parse(cells[0].replace(/^[-*]\s*/, "")))) {
    return undefined;
  }
  const timestamp = cells[0].replace(/^[-*]\s*/, "");
  if (!/^[a-z][a-z0-9_]*$/i.test(cells[1]) || !/^[a-z][a-z0-9_-]*$/i.test(cells[2])) {
    return undefined;
  }
  return {
    timestamp,
    system: cells[1],
    resource_id: cells[2],
    record_type: cells[3],
    result: cells[4],
    ...(cells[5] ? { lookup_value: cells[5] } : {}),
  };
}

function parseLineObservations(
  text: string,
  evidence: EvidenceFile,
  format: EvidenceFormat,
): EvidenceObservation[] {
  const observations: EvidenceObservation[] = [];
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    const cleaned = line.trim();
    if (!cleaned) continue;

    if (cleaned.startsWith("{")) {
      try {
        const jsonObservations = parseJsonObservations(
          JSON.parse(cleaned),
          evidence,
          format,
        );
        observations.push(...jsonObservations);
        if (jsonObservations.length > 0) continue;
      } catch {
        // Fall through to key/value parsing for JSON-like log lines.
      }
    }

    const fields = parsePipeRecord(cleaned) ?? parseKeyValueLine(cleaned);
    observations.push(
      makeObservation({
        evidence,
        format,
        path: `line:${index + 1}`,
        fields: { ...fields, _line_text: cleaned },
        rawText: cleaned,
        fallbackCategory: categoryFromPath(evidence.file_path),
      }),
    );
  }
  return observations;
}

function parseDocumentLineObservations(
  text: string,
  evidence: EvidenceFile,
  format: EvidenceFormat,
): EvidenceObservation[] {
  const observations: EvidenceObservation[] = [];
  let currentResourceId: string | undefined;
  for (const [index, line] of text.split(/\r?\n/).entries()) {
    const cleaned = line.trim();
    if (!cleaned) continue;

    const fields = parseKeyValueLine(cleaned);
    const resourceId = /\b(?!user_)[a-z][a-z0-9]*_\d{1,8}\b/i.exec(cleaned)?.[0];
    if (resourceId) currentResourceId = resourceId;
    if (currentResourceId) fields.resource_id ??= currentResourceId;

    const email = /\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b/i.exec(cleaned)?.[0];
    if (email) fields.email ??= email;

    const labelValue = /^\s*([A-Za-z][A-Za-z0-9 ._-]{0,48})\s*:\s*(.*?)\s*$/.exec(
      cleaned,
    );
    if (labelValue && Object.keys(fields).length === 0) {
      const label = labelValue[1]
        .trim()
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, "_")
        .replace(/^_+|_+$/g, "");
      fields[label] = labelValue[2];
    }

    const phone = /(?:\+\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?){2,4}\d{2,4}/.exec(cleaned)?.[0];
    const hasPhoneContext = cleaned.includes("+") || /\b(phone|telephone|mobile|tel)\b/i.test(cleaned);
    if (phone && hasPhoneContext && /\d{8,}/.test(phone.replace(/\D/g, ""))) {
      fields.phone ??= phone.trim();
    }

    observations.push(
      makeObservation({
        evidence,
        format,
        path: `line:${index + 1}`,
        fields: { ...fields, _document_text: cleaned },
        rawText: cleaned,
        fallbackCategory: categoryFromPath(evidence.file_path),
      }),
    );
  }
  return observations;
}

async function getOcrWorker(): Promise<OcrWorker> {
  if (!ocrWorkerPromise) {
    ocrWorkerPromise = (async () => {
      const cachePath = join(tmpdir(), "ghost-data-still-exists-tesseract");
      await mkdir(cachePath, { recursive: true });
      const require = createRequire(import.meta.url);
      const language = require("@tesseract.js-data/eng") as {
        code: string;
        gzip: boolean;
        langPath: string;
      };
      return tesseract.createWorker(language.code, 1, {
        cachePath,
        gzip: language.gzip,
        langPath: language.langPath,
        logger: () => undefined,
      });
    })();
  }
  return ocrWorkerPromise;
}

async function extractMediaText(
  sourcePath: string,
  format: EvidenceFormat,
): Promise<string | undefined> {
  if (format === "IMAGE") {
    const worker = await getOcrWorker();
    const result = await worker.recognize(sourcePath);
    return result.data.text;
  }

  try {
    return execFileSync("pdftotext", ["-layout", sourcePath, "-"], {
      encoding: "utf8",
      maxBuffer: 16 * 1024 * 1024,
      stdio: ["ignore", "pipe", "ignore"],
      timeout: 30_000,
    });
  } catch (error) {
    if (
      error &&
      typeof error === "object" &&
      "code" in error &&
      error.code === "ENOENT"
    ) {
      return undefined;
    }
    throw new Error(
      `Could not extract text from ${format} evidence at ${sourcePath}.`,
      { cause: error },
    );
  }
}

function splitSqlStatements(sql: string): string[] {
  const statements: string[] = [];
  let current = "";
  let quote: "'" | '"' | "`" | "]" | undefined;
  let lineComment = false;
  let blockComment = false;

  for (let index = 0; index < sql.length; index += 1) {
    const character = sql[index];
    const next = sql[index + 1];

    if (lineComment) {
      if (character === "\n") {
        lineComment = false;
        current += "\n";
      }
      continue;
    }
    if (blockComment) {
      if (character === "*" && next === "/") {
        blockComment = false;
        index += 1;
      }
      continue;
    }
    if (quote) {
      current += character;
      if (character === quote) {
        if (next === quote && quote !== "]") {
          current += next;
          index += 1;
        } else {
          quote = undefined;
        }
      }
      continue;
    }

    if (character === "-" && next === "-") {
      lineComment = true;
      index += 1;
    } else if (character === "/" && next === "*") {
      blockComment = true;
      index += 1;
    } else if (character === "'" || character === '"' || character === "`") {
      quote = character;
      current += character;
    } else if (character === "[") {
      quote = "]";
      current += character;
    } else if (character === ";") {
      if (current.trim()) statements.push(current.trim());
      current = "";
    } else {
      current += character;
    }
  }

  if (current.trim()) statements.push(current.trim());
  return statements;
}

function assertSafeSql(sql: string, fileId: string): string[] {
  const statements = splitSqlStatements(sql);
  for (const statement of statements) {
    const allowed = /^(?:PRAGMA\b|BEGIN\b|COMMIT\b|CREATE\s+(?:UNIQUE\s+)?(?:TABLE|INDEX)\b|INSERT\s+INTO\b)/i;
    if (!allowed.test(statement)) {
      throw new Error(
        `Unsupported SQL statement in ${fileId}: ${statement.slice(0, 40)}`,
      );
    }
  }
  return statements;
}

function quoteSqlIdentifier(value: string): string {
  return `"${value.replaceAll('"', '""')}"`;
}

function parseSqlObservations(
  sql: string,
  evidence: EvidenceFile,
): EvidenceObservation[] {
  const statements = assertSafeSql(sql, evidence.file_id);
  const database = new DatabaseSync(":memory:");
  try {
    for (const statement of statements) database.exec(statement);
    const tableRows = database
      .prepare("SELECT name FROM sqlite_master WHERE type = 'table' ORDER BY name")
      .all() as Array<{ name: string }>;
    const observations: EvidenceObservation[] = [];

    for (const { name: tableName } of tableRows) {
      const rows = database
        .prepare(`SELECT * FROM ${quoteSqlIdentifier(tableName)}`)
        .all() as Array<Record<string, Scalar | null>>;
      rows.forEach((row, index) => {
        const fields: ScalarFields = {};
        for (const [key, value] of Object.entries(row)) {
          fields[key] = value === null ? "NULL" : String(value);
        }

        const recordJson = fields.record_json;
        if (recordJson) {
          try {
            const parsed = JSON.parse(recordJson) as unknown;
            if (parsed && typeof parsed === "object" && !Array.isArray(parsed)) {
              Object.assign(fields, flattenScalarFields(parsed));
            }
          } catch {
            // Keep the original record_json field as searchable text.
          }
        }

        if (!hasIdentifierOrResource(normalizeFields(fields))) return;
        observations.push(
          makeObservation({
            evidence,
            format: "SQL",
            path: `${tableName}:${index + 1}`,
            fields: {
              table_name: tableName,
              collection_name: fields.collection_name ?? tableName,
              ...fields,
            },
            rawText: JSON.stringify(row) ?? "",
            fallbackCategory: tableName,
          }),
        );
      });
    }
    return observations;
  } finally {
    database.close();
  }
}

async function parseEvidenceFile(
  repositoryRoot: string,
  evidence: EvidenceFile,
): Promise<{ artifact: EvidenceArtifact; observations: EvidenceObservation[] }> {
  const datasetDirectory = resolve(repositoryRoot, "dataset");
  const evidenceRoot = resolve(datasetDirectory, "evidence");
  const sourcePath = resolve(datasetDirectory, evidence.file_path);
  const pathFromEvidenceRoot = relative(evidenceRoot, sourcePath);
  if (
    pathFromEvidenceRoot === ".." ||
    pathFromEvidenceRoot.startsWith(`..${sep}`) ||
    resolve(evidenceRoot, pathFromEvidenceRoot) !== sourcePath
  ) {
    throw new Error(`Evidence path escapes dataset/evidence: ${evidence.file_path}`);
  }

  const format = formatForPath(evidence.file_path);
  const bytes = await readFile(sourcePath);
  const text =
    format === "PDF" || format === "IMAGE"
      ? await extractMediaText(sourcePath, format)
      : bytes.toString("utf8");
  let observations: EvidenceObservation[] = [];

  if (text === undefined) {
    observations = [];
  } else if (format === "JSON") {
    observations = parseJsonObservations(JSON.parse(text) as unknown, evidence);
  } else if (format === "SQL") {
    observations = parseSqlObservations(text, evidence);
  } else if (format === "LOG" || format === "TEXT") {
    observations = parseLineObservations(text, evidence, format);
  } else if (format === "PDF" || format === "IMAGE") {
    observations = parseDocumentLineObservations(text, evidence, format);
  }

  const unsupportedMedia =
    (format === "PDF" || format === "IMAGE") &&
    (!text || text.trim().length === 0);
  return {
    artifact: {
      file_id: evidence.file_id,
      file_path: evidence.file_path,
      captured_at: evidence.captured_at,
      format,
      parse_status: unsupportedMedia ? "UNSUPPORTED_MEDIA" : "INDEXED",
      observation_count: observations.length,
    },
    observations,
  };
}

export async function loadEvidenceIndex(
  repositoryRoot: string,
  evidenceFiles: EvidenceFile[],
): Promise<EvidenceIndex> {
  try {
    const parsedFiles = await Promise.all(
      evidenceFiles.map((evidence) => parseEvidenceFile(repositoryRoot, evidence)),
    );
    return {
      artifacts: parsedFiles.map((parsed) => parsed.artifact),
      observations: parsedFiles.flatMap((parsed) => parsed.observations),
    };
  } finally {
    if (ocrWorkerPromise) {
      const workerPromise = ocrWorkerPromise;
      ocrWorkerPromise = undefined;
      const worker = await workerPromise;
      await worker.terminate();
    }
  }
}
