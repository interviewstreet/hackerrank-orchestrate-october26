"use client";

import { useEffect, useState } from "react";

type Summary = {
  total_cases: number;
  status_counts: Record<string, number>;
};

const CARDS = [
  {
    status: "COMPLETE",
    label: "Complete",
    hint: "Every copy has the required treatment and nothing can recreate it.",
    accent: "bg-emerald-400",
    text: "text-emerald-300",
  },
  {
    status: "INCOMPLETE",
    label: "Incomplete",
    hint: "Personal data remains, or a sync or restore can bring it back.",
    accent: "bg-amber-400",
    text: "text-amber-300",
  },
  {
    status: "NOT_APPLICABLE",
    label: "Not applicable",
    hint: "The request did not ask for deletion.",
    accent: "bg-slate-400",
    text: "text-slate-300",
  },
] as const;

export default function Home() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch("/api/summary")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<Summary>;
      })
      .then(setSummary)
      .catch((err: Error) => setError(err.message));
  }, []);

  return (
    <main className="mx-auto max-w-5xl px-4 py-12 sm:px-6 sm:py-20">
      <header className="mb-10">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-slate-500">
          Deletion audit
        </p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          TRACE: Ghost Data Audit
        </h1>
        <p className="mt-3 max-w-2xl text-slate-400">
          {summary
            ? `${summary.total_cases} deletion requests checked against the evidence at each case's audit time.`
            : "Deletion requests checked against the evidence at each case's audit time."}
        </p>
      </header>

      {error ? (
        <div className="rounded-lg border border-red-900/60 bg-red-950/40 px-4 py-3 text-sm text-red-300">
          Could not load the summary ({error}).
        </div>
      ) : (
        <section className="grid gap-4 sm:grid-cols-3" aria-busy={!summary}>
          {CARDS.map((card) => (
            <div
              key={card.status}
              className="relative overflow-hidden rounded-xl border border-white/10 bg-white/[0.03] p-5"
            >
              <span className={`absolute inset-x-0 top-0 h-0.5 ${card.accent}`} />
              <div className="flex items-center gap-2">
                <span className={`h-2 w-2 rounded-full ${card.accent}`} />
                <h2 className={`text-sm font-medium ${card.text}`}>{card.label}</h2>
              </div>
              <p className="mt-4 text-4xl font-semibold tabular-nums text-white">
                {summary ? (summary.status_counts[card.status] ?? 0) : (
                  <span className="inline-block h-9 w-16 animate-pulse rounded bg-white/10" />
                )}
              </p>
              <p className="mt-3 text-sm leading-relaxed text-slate-500">{card.hint}</p>
            </div>
          ))}
        </section>
      )}
    </main>
  );
}
