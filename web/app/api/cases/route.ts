import type { NextRequest } from "next/server";

import { getCaseList, STATUSES, type Status } from "@/lib/data";

export const dynamic = "force-dynamic";

/**
 * GET /api/cases?status=INCOMPLETE&q=case_4
 *   status  optional, one of COMPLETE / INCOMPLETE / NOT_APPLICABLE (any case)
 *   q       optional, case-insensitive text search in case_id and masked email
 */
export async function GET(request: NextRequest) {
  const params = request.nextUrl.searchParams;
  const status = params.get("status")?.trim().toUpperCase() || null;
  const q = params.get("q")?.trim().toLowerCase() || null;

  if (status && !STATUSES.includes(status as Status)) {
    return Response.json(
      { error: `Unknown status "${status}". Use one of: ${STATUSES.join(", ")}.` },
      { status: 400 },
    );
  }

  let cases = await getCaseList();
  if (status) cases = cases.filter((c) => c.our_status === status);
  if (q) {
    cases = cases.filter(
      (c) => c.case_id.toLowerCase().includes(q) || c.email.toLowerCase().includes(q),
    );
  }
  return Response.json({ count: cases.length, cases });
}
