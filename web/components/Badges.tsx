import { REPORTED_LABELS, STATUS_META } from "@/lib/types";

/** Our verdict: coloured dot + text label (colour is never the only cue). */
export function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status];
  return (
    <span className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border border-white/10 bg-white/[0.04] px-2.5 py-0.5 text-xs font-medium text-ink">
      <span
        aria-hidden
        className="h-2 w-2 shrink-0 rounded-full"
        style={{ backgroundColor: meta?.color ?? "#898781" }}
      />
      {meta?.label ?? status}
    </span>
  );
}

/** What the shop's workflow claimed: a neutral, dashed "claim" badge. */
export function ReportedBadge({ status }: { status: string }) {
  return (
    <span className="inline-flex items-center whitespace-nowrap rounded-full border border-dashed border-white/20 px-2.5 py-0.5 text-xs text-ink-2">
      {REPORTED_LABELS[status] ?? status}
    </span>
  );
}
