import { getCase } from "@/lib/data";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const { id } = await params;
  const found = await getCase(id);
  if (!found) {
    return Response.json({ error: `Case "${id}" not found.` }, { status: 404 });
  }
  return Response.json(found);
}
