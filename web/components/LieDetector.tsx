"use client";

import { useEffect, useState } from "react";

import type { LieDetectorData } from "@/lib/types";

/**
 * "Lie detector by system": for requests the shop reported COMPLETE, how many
 * still had direct evidence of the person's data in each system, captured
 * after the request. One series (direct proof), ranked; second-hand ledger
 * mentions are shown as text, not as bars.
 */
export default function LieDetector() {
  const [data, setData] = useState<LieDetectorData | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/lie-detector")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<LieDetectorData>;
      })
      .then(setData)
      .catch((err: Error) => setError(err.message));
  }, []);

  const rows = data?.systems.filter((r) => r.proof_cases + r.claim_only_cases > 0) ?? [];
  const max = Math.max(1, ...rows.map((r) => r.proof_cases));

  return (
    <section className="mb-6 rounded-xl border border-white/10 bg-surface p-5 sm:p-6" aria-labelledby="lie-detector">
      <h2 id="lie-detector" className="text-base font-semibold text-ink">
        Systems where data was still found after deletion was reported
      </h2>
      <p className="mt-1 text-sm text-muted">
        {data
          ? `Of the ${data.reported_complete_cases} requests the shop reported as complete: cases with direct evidence of the person's data in each system, captured after the request.`
          : "Of the requests the shop reported as complete."}
      </p>

      {error && (
        <p role="alert" className="mt-4 text-sm text-ink-2">Could not load this chart ({error}).</p>
      )}

      {!data && !error && <div className="mt-5 h-48 animate-pulse rounded bg-white/5" />}

      {data && (
        <>
          <ol className="mt-5 space-y-2.5">
            {rows.map((r, i) => (
              <li
                key={r.system_id}
                className="grid grid-cols-[1.25rem_minmax(0,9.5rem)_1fr] items-center gap-3 text-sm sm:grid-cols-[1.25rem_12rem_1fr]"
                title={`${r.system_id}: ${r.proof_cases} cases with direct evidence${
                  r.claim_only_cases ? `, ${r.claim_only_cases} more with second-hand claims only` : ""
                }`}
              >
                <span className="text-right text-xs tabular-nums text-muted">{i + 1}</span>
                <span className="truncate font-mono text-xs text-ink-2 sm:text-sm">{r.system_id}</span>
                <div className="flex min-w-0 items-center gap-2">
                  <div
                    className="h-4 shrink-0 rounded-r bg-series"
                    style={{ width: `${(r.proof_cases / max) * 70}%`, minWidth: r.proof_cases ? 2 : 0 }}
                  />
                  <span className="whitespace-nowrap tabular-nums text-ink">{r.proof_cases}</span>
                  {r.claim_only_cases > 0 && (
                    <span className="hidden whitespace-nowrap text-xs text-muted sm:inline">
                      +{r.claim_only_cases} claim only
                    </span>
                  )}
                </div>
              </li>
            ))}
          </ol>

          <details className="mt-4 text-sm">
            <summary className="cursor-pointer text-muted hover:text-ink-2">Show as table</summary>
            <div className="mt-3 overflow-x-auto">
              <table className="w-full min-w-[26rem] text-left tabular-nums">
                <thead className="text-xs text-muted">
                  <tr>
                    <th className="py-2 pr-4 font-medium">System</th>
                    <th className="py-2 pr-4 text-right font-medium">Direct evidence</th>
                    <th className="py-2 pr-4 text-right font-medium">Claim only</th>
                    <th className="py-2 text-right font-medium">Share</th>
                  </tr>
                </thead>
                <tbody className="text-ink-2">
                  {rows.map((r) => (
                    <tr key={r.system_id} className="border-t border-hairline">
                      <td className="py-2 pr-4 font-mono text-xs">{r.system_id}</td>
                      <td className="py-2 pr-4 text-right">{r.proof_cases}</td>
                      <td className="py-2 pr-4 text-right">{r.claim_only_cases}</td>
                      <td className="py-2 text-right">{Math.round(r.share_with_proof * 100)}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </details>

          <p className="mt-4 rounded-lg bg-white/[0.03] px-3 py-2 text-xs leading-relaxed text-ink-2">
            Not a verdict. {data.note}
            {!data.policy_engine_connected && " The policy engine is not connected yet."}
          </p>
        </>
      )}
    </section>
  );
}
