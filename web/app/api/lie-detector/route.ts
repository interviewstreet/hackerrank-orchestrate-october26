import { getLieDetector } from "@/lib/data";

export const dynamic = "force-dynamic";

/** GET /api/lie-detector: per system, reported-COMPLETE cases that still had evidence of data. */
export async function GET() {
  return Response.json(await getLieDetector());
}
