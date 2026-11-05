import { OUR_STATUSES, REPORTED_LABELS, REPORTED_STATUSES, STATUS_META, type Summary } from "@/lib/types";

/**
 * "Claim vs reality": one horizontal stacked bar per status the shop reported,
 * split by what TRACE found. All bars share one scale, so lengths compare.
 * Hover or focus a segment for its exact count; the table view has every value.
 */
export default function ClaimChart({ summary }: { summary: Summary }) {
  const rows = REPORTED_STATUSES.map((reported) => {
    const cells = summary.reported_vs_ours[reported] ?? {};
    const segments = OUR_STATUSES.map((ours) => ({ ours, count: cells[ours] ?? 0 })).filter(
      (s) => s.count > 0,
    );
    const total = segments.reduce((n, s) => n + s.count, 0);
    return { reported, segments, total };
  });
  const max = Math.max(1, ...rows.map((r) => r.total));

  return (
    <div>
      {/* Legend: always present for more than one series */}
      <ul className="mb-5 flex flex-wrap gap-x-5 gap-y-2 text-sm text-ink-2" aria-label="Legend">
        {OUR_STATUSES.map((s) => (
          <li key={s} className="flex items-center gap-2">
            <span aria-hidden className="h-2.5 w-2.5 rounded-sm" style={{ backgroundColor: STATUS_META[s].color }} />
            TRACE found: {STATUS_META[s].label}
          </li>
        ))}
      </ul>

      <div className="space-y-4" role="list">
        {rows.map((row) => (
          <div key={row.reported} role="listitem" className="grid gap-1.5 sm:grid-cols-[10rem_1fr] sm:items-center sm:gap-4">
            <div className="text-sm text-ink-2">
              <span className="text-muted">Shop said </span>
              {REPORTED_LABELS[row.reported]}
            </div>
            <div className="flex items-center gap-3">
              <div className="flex h-7 min-w-0 flex-1 items-stretch">
                <div className="flex h-full gap-[2px]" style={{ width: `${(row.total / max) * 100}%` }}>
                  {row.segments.map((seg, i) => {
                    const last = i === row.segments.length - 1;
                    const share = (seg.count / max) * 100;
                    const label = `Shop said ${REPORTED_LABELS[row.reported]}, TRACE found ${
                      STATUS_META[seg.ours].label
                    }: ${seg.count} case${seg.count === 1 ? "" : "s"}`;
                    return (
                      <div
                        key={seg.ours}
                        tabIndex={0}
                        aria-label={label}
                        className={`group relative h-full outline-none focus-visible:ring-2 focus-visible:ring-white/60 ${
                          last ? "rounded-r" : ""
                        }`}
                        style={{ flexGrow: seg.count, flexBasis: 0, backgroundColor: STATUS_META[seg.ours].color }}
                      >
                        {share >= 9 && (
                          <span className="absolute inset-0 flex items-center px-2 text-xs font-medium text-white">
                            {seg.count}
                          </span>
                        )}
                        <span
                          role="tooltip"
                          className="pointer-events-none absolute bottom-full left-1/2 z-10 mb-2 hidden -translate-x-1/2 whitespace-nowrap rounded-md border border-white/10 bg-surface-2 px-2.5 py-1.5 text-xs text-ink shadow-lg group-hover:block group-focus:block"
                        >
                          {label}
                        </span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <span className="w-10 shrink-0 text-right text-sm tabular-nums text-ink">{row.total}</span>
            </div>
          </div>
        ))}
      </div>

      <details className="mt-5 text-sm">
        <summary className="cursor-pointer text-muted hover:text-ink-2">Show as table</summary>
        <div className="mt-3 overflow-x-auto">
          <table className="w-full min-w-[28rem] text-left tabular-nums">
            <thead className="text-xs text-muted">
              <tr>
                <th className="py-2 pr-4 font-medium">Shop said</th>
                {OUR_STATUSES.map((s) => (
                  <th key={s} className="py-2 pr-4 text-right font-medium">
                    Found: {STATUS_META[s].label}
                  </th>
                ))}
                <th className="py-2 text-right font-medium">Total</th>
              </tr>
            </thead>
            <tbody className="text-ink-2">
              {rows.map((row) => (
                <tr key={row.reported} className="border-t border-hairline">
                  <td className="py-2 pr-4">{REPORTED_LABELS[row.reported]}</td>
                  {OUR_STATUSES.map((s) => (
                    <td key={s} className="py-2 pr-4 text-right">
                      {summary.reported_vs_ours[row.reported]?.[s] ?? 0}
                    </td>
                  ))}
                  <td className="py-2 text-right text-ink">{row.total}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </div>
  );
}
