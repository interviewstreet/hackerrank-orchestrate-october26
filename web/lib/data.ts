// Server-side only: imported by the API routes, never by client components.
import { promises as fs } from "node:fs";
import path from "node:path";

// web/data/ is written by `python3 code/export_web_data.py`.
// It is outside public/, so it is only reachable through the API routes.
const DATA_DIR = path.join(process.cwd(), "data");

import { OUR_STATUSES, type CaseListItem, type LieDetectorData, type Status, type Summary } from "./types";

export const STATUSES = OUR_STATUSES;
export type { CaseListItem, Status, Summary };

// Only ids like "case_43": the id becomes a file name, so nothing else is allowed.
const CASE_ID_RE = /^[A-Za-z0-9_-]{1,64}$/;

async function readJson<T>(relative: string): Promise<T> {
  const text = await fs.readFile(path.join(DATA_DIR, relative), "utf8");
  return JSON.parse(text) as T;
}

export function getSummary(): Promise<Summary> {
  return readJson<Summary>("summary.json");
}

export function getLieDetector(): Promise<LieDetectorData> {
  return readJson<LieDetectorData>("lie_detector.json");
}

export function getCaseList(): Promise<CaseListItem[]> {
  return readJson<CaseListItem[]>("cases.json");
}

/** One case's full JSON, or null if the id is invalid or unknown. */
export async function getCase(id: string): Promise<Record<string, unknown> | null> {
  if (!CASE_ID_RE.test(id)) return null;
  try {
    return await readJson<Record<string, unknown>>(path.join("cases", `${id}.json`));
  } catch (err) {
    if ((err as NodeJS.ErrnoException).code === "ENOENT") return null;
    throw err;
  }
}
