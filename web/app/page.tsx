"use client";

import Link from "next/link";
import { useEffect, useState } from "react";

import ClaimChart from "@/components/ClaimChart";
import LanguageBars from "@/components/LanguageBars";
import { OUR_STATUSES, STATUS_META, type Summary } from "@/lib/types";

const STEPS = [
  { title: "Classify", text: "Read the request in any of 6 languages and decide if it really asks for deletion." },
  { title: "Resolve identity", text: "Find the person's current and past emails, phones and hashes as of the audit time." },
  { title: "Find evidence", text: "Search databases, logs, documents and screenshots captured before the audit time." },
  { title: "Decide", text: "Apply the deletion policy to every copy, sync and backup, and plan the fixes." },
];

function Panel({ title, subtitle, children }: { title: string; subtitle?: string; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-white/10 bg-surface p-5 sm:p-6">
      <h2 className="text-base font-semibold text-ink">{title}</h2>
      {subtitle && <p className="mt-1 text-sm text-muted">{subtitle}</p>}
      <div className="mt-5">{children}</div>
    </section>
  );
}

export default function Overview() {
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

  const reportedComplete = summary?.reported_status_counts.COMPLETE ?? 0;

  return (
    <main className="mx-auto max-w-6xl px-4 py-10 sm:px-6 sm:py-14">
      <header className="mb-8">
        <p className="text-xs font-medium uppercase tracking-[0.2em] text-muted">Deletion audit</p>
        <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink sm:text-4xl">TRACE: Ghost Data Audit</h1>
        <p className="mt-3 max-w-2xl text-ink-2">
          {summary ? `${summary.total_cases} deletion requests` : "Deletion requests"} checked against the evidence
          that existed at each case&apos;s audit time, instead of trusting what the shop reported.
        </p>
      </header>

      {error && (
        <div role="alert" className="mb-6 rounded-lg border border-critical/50 bg-critical/10 px-4 py-3 text-sm text-ink">
          Could not load the summary ({error}).
        </div>
      )}

      {summary && !summary.policy_engine_connected && (
        <div className="mb-6 rounded-lg border border-white/10 bg-surface px-4 py-3 text-sm text-ink-2">
          <span className="mr-2 rounded bg-white/10 px-1.5 py-0.5 text-xs font-medium text-ink">Preliminary</span>
          The policy engine is not connected yet, so every deletion request is shown as Incomplete until its
          evidence has been checked against the deletion rules.
        </div>
      )}

      {/* Headline number */}
      <section className="mb-6 rounded-xl border border-white/10 bg-surface p-6 sm:p-8" aria-busy={!summary}>
        {summary ? (
          <>
            <p className="text-6xl font-semibold tracking-tight text-ink sm:text-7xl">
              {summary.reported_complete_but_not_complete}
            </p>
            <p className="mt-3 max-w-xl text-lg text-ink-2">
              cases the shop marked <span className="font-medium text-ink">COMPLETE</span> still have personal data
            </p>
            <p className="mt-2 text-sm text-muted">
              out of {reportedComplete} cases the shop reported as complete
            </p>
          </>
        ) : (
          <div className="h-28 animate-pulse rounded bg-white/5" />
        )}
      </section>

      {/* Status cards */}
      <section className="mb-6 grid gap-4 sm:grid-cols-3" aria-label="What TRACE found">
        {OUR_STATUSES.map((status) => {
          const meta = STATUS_META[status];
          return (
            <Link
              key={status}
              href={`/cases?status=${status}`}
              className="group rounded-xl border border-white/10 bg-surface p-5 transition-colors hover:border-white/20"
            >
              <div className="flex items-center gap-2">
                <span aria-hidden className="h-2 w-2 rounded-full" style={{ backgroundColor: meta.color }} />
                <h2 className="text-sm font-medium text-ink-2">{meta.label}</h2>
              </div>
              <p className="mt-4 text-4xl font-semibold text-ink">
                {summary ? (summary.status_counts[status] ?? 0) : (
                  <span className="inline-block h-9 w-16 animate-pulse rounded bg-white/10" />
                )}
              </p>
              <p className="mt-3 text-sm leading-relaxed text-muted">{meta.hint}</p>
              <p className="mt-3 text-xs text-muted group-hover:text-ink-2">View cases →</p>
            </Link>
          );
        })}
      </section>

      <div className="mb-6 grid gap-6 lg:grid-cols-[3fr_2fr]">
        <Panel title="Claim vs reality" subtitle="What the shop reported, split by what TRACE found">
          {summary ? <ClaimChart summary={summary} /> : <div className="h-40 animate-pulse rounded bg-white/5" />}
        </Panel>
        <Panel title="Request languages" subtitle="Requests per language, detected from the request text">
          {summary ? (
            <LanguageBars counts={summary.language_counts} />
          ) : (
            <div className="h-40 animate-pulse rounded bg-white/5" />
          )}
        </Panel>
      </div>

      <section aria-labelledby="how" className="rounded-xl border border-white/10 bg-surface p-5 sm:p-6">
        <h2 id="how" className="text-base font-semibold text-ink">How TRACE works</h2>
        <ol className="mt-5 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          {STEPS.map((step, i) => (
            <li key={step.title} className="relative rounded-lg border border-white/10 bg-white/[0.02] p-4">
              <div className="flex items-center gap-2">
                <span className="grid h-6 w-6 place-items-center rounded-full bg-white/10 text-xs font-semibold text-ink">
                  {i + 1}
                </span>
                <h3 className="text-sm font-semibold text-ink">{step.title}</h3>
                {i < STEPS.length - 1 && (
                  <span aria-hidden className="ml-auto hidden text-muted lg:inline">→</span>
                )}
              </div>
              <p className="mt-2 text-sm leading-relaxed text-muted">{step.text}</p>
            </li>
          ))}
        </ol>
      </section>
    </main>
  );
}
