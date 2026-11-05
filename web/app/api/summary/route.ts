import { getSummary } from "@/lib/data";

// Read the file on every request (not baked in at build time)
export const dynamic = "force-dynamic";

export async function GET() {
  return Response.json(await getSummary());
}
