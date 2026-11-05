"use client";

import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";

import { ReportedBadge, StatusBadge } from "@/components/Badges";
import { formatUtc, LANGUAGE_NAMES, REPORTED_LABELS, type CaseDetail } from "@/lib/types";

type Load = { state: "loading" } | { state: "missing" } | { state: "error"; message: string } | { state: "ok"; data: CaseDetail };

const KIND_LABELS: Record<string, string> = {
  email: "Email",
  phone: "Phone",
  email_hash: "Email hash",
  name: "Name",
};

const SIGNAL_LABELS: Record<string, string> = {
  deletion: "Deletion",
  negation: "Refuses deletion",
  keep: "Keep account",
  access: "Access / copy",
  correction: "Correction",
  opt_out: "Marketing opt-out",
  login: "Login help",
};

function Section({ title, count, children }: { title: string; count?: number; children: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-white/10 bg-surface p-5 sm:p-6">
      <h2 className="flex items-baseline gap-2 text-base font-semibold text-ink">
        {title}
        {count !== undefined && <span className="text-sm font-normal text-muted">{count}</span>}
      </h2>
      <div className="mt-4">{children}</div>
    </section>
  );
}

function Empty({ children }: { children: React.ReactNode }) {
  return <p className="rounded-lg border border-dashed border-white/10 px-4 py-6 text-center text-sm text-muted">{children}</p>;
}

function Table({
  head,
  children,
  minWidth = "min-w-[36rem]",
  desktopOnly = [],
}: {
  head: string[];
  children: React.ReactNode;
  minWidth?: string;
  desktopOnly?: string[];
}) {
  return (
    <div className="-mx-5 overflow-x-auto px-5 sm:mx-0 sm:px-0">
      <table className={`w-full ${minWidth} text-left text-sm`}>
        <thead className="text-xs uppercase tracking-wide text-muted">
          <tr>
            {head.map((h) => (
              <th
                key={h}
                scope="col"
                className={`border-b border-white/10 py-2 pr-4 font-medium ${
                  desktopOnly.includes(h) ? "hidden sm:table-cell" : ""
                }`}
              >
                {h}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="text-ink-2">{children}</tbody>
      </table>
    </div>
  );
}

/** "Reported vs our verdict": red when the shop said COMPLETE but data remains. */
function VerdictBanner({ c }: { c: CaseDetail }) {
  const preliminary =
    c.our_status === "INCOMPLETE" &&
    c.steps.length === 0 &&
    c.resources.length === 0 &&
    c.flows.length === 0 &&
    c.restore_risks.length === 0;
  const claimedDone = c.reported_status === "COMPLETE";

  let tone = "border-white/10 bg-surface";
  let headline: string;
  if (c.our_status === "NOT_APPLICABLE") {
    headline = "This request did not ask for deletion, so there is nothing to audit.";
  } else if (claimedDone && c.our_status === "INCOMPLETE") {
    tone = "border-critical/60 bg-critical/15";
    headline = "The shop reported this deletion as complete, but TRACE found it is not.";
  } else if (claimedDone && c.our_status === "COMPLETE") {
    tone = "border-good/50 bg-good/10";
    headline = "The shop reported this deletion as complete, and the evidence confirms it.";
  } else if (c.our_status === "COMPLETE") {
    tone = "border-good/50 bg-good/10";
    headline = `The shop reported “${REPORTED_LABELS[c.reported_status] ?? c.reported_status}”, but the evidence shows the deletion is complete.`;
  } else {
    headline = `The shop reported “${REPORTED_LABELS[c.reported_status] ?? c.reported_status}”, and TRACE agrees the deletion is not complete.`;
  }

  return (
    <div role="status" className={`rounded-xl border p-5 sm:p-6 ${tone}`}>
      <div className="flex flex-wrap items-center gap-x-6 gap-y-3">
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">Shop reported</p>
          <div className="mt-1.5"><ReportedBadge status={c.reported_status} /></div>
        </div>
        <span aria-hidden className="text-muted">→</span>
        <div>
          <p className="text-xs uppercase tracking-wide text-muted">Our verdict</p>
          <div className="mt-1.5"><StatusBadge status={c.our_status} /></div>
        </div>
      </div>
      <p className="mt-4 text-base font-medium text-ink">{headline}</p>
      {preliminary && (
        <p className="mt-1 text-sm text-ink-2">
          Preliminary: the policy engine is not connected yet, so this verdict is a default, not a checked result.
        </p>
      )}
    </div>
  );
}

export default function CasePage() {
  const { id } = useParams<{ id: string }>();
  const [load, setLoad] = useState<Load>({ state: "loading" });

  useEffect(() => {
    let cancelled = false;
    setLoad({ state: "loading" });
    fetch(`/api/cases/${encodeURIComponent(id)}`)
      .then(async (res) => {
        if (res.status === 404) return { state: "missing" } as const;
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return { state: "ok", data: (await res.json()) as CaseDetail } as const;
      })
      .then((l) => !cancelled && setLoad(l))
      .catch((err: Error) => !cancelled && setLoad({ state: "error", message: err.message }));
    return () => {
      cancelled = true;
    };
  }, [id]);

  return (
    <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 sm:py-12">
      <Link href="/cases" className="text-sm text-muted hover:text-ink-2">
        ← All cases
      </Link>

      {load.state === "loading" && (
        <div className="mt-6 space-y-4" aria-busy>
          <div className="h-8 w-48 animate-pulse rounded bg-white/5" />
          <div className="h-32 animate-pulse rounded-xl bg-surface" />
          <div className="h-48 animate-pulse rounded-xl bg-surface" />
        </div>
      )}

      {load.state === "missing" && (
        <div className="mt-6 rounded-xl border border-white/10 bg-surface p-6">
          <h1 className="text-xl font-semibold text-ink">Case not found</h1>
          <p className="mt-2 text-ink-2">
            There is no case called <span className="font-mono">{id}</span>.
          </p>
        </div>
      )}

      {load.state === "error" && (
        <div role="alert" className="mt-6 rounded-lg border border-critical/50 bg-critical/10 px-4 py-3 text-sm text-ink">
          Could not load this case ({load.message}).
        </div>
      )}

      {load.state === "ok" && <CaseView c={load.data} />}
    </main>
  );
}

function CaseView({ c }: { c: CaseDetail }) {
  const current = c.identities.filter((i) => !i.is_historical);
  const historical = c.identities.filter((i) => i.is_historical);

  return (
    <div className="mt-4 space-y-6">
      <header className="flex flex-wrap items-baseline justify-between gap-x-4 gap-y-1">
        <h1 className="font-mono text-2xl font-semibold text-ink sm:text-3xl">{c.case_id}</h1>
        <p className="text-sm text-muted">
          Requested {formatUtc(c.requested_at)} · Audited at {formatUtc(c.audit_at)}
        </p>
      </header>

      <VerdictBanner c={c} />

      <Section title="The request">
        <blockquote
          lang={c.language || undefined}
          className="border-l-2 border-white/15 pl-4 leading-relaxed text-ink"
        >
          {c.request_text}
        </blockquote>
        <dl className="mt-5 grid gap-4 text-sm sm:grid-cols-3">
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Email</dt>
            <dd className="mt-1 font-mono text-ink-2">{c.email}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Language</dt>
            <dd className="mt-1 text-ink-2">{LANGUAGE_NAMES[c.language] ?? (c.language || "—")}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase tracking-wide text-muted">Classifier decision</dt>
            <dd className="mt-1 text-ink-2">
              {c.classification === "IS_DELETION" ? "Asks for deletion" : c.classification === "NOT_APPLICABLE" ? "Not a deletion request" : c.classification || "—"}
              {c.confidence && <span className="text-muted"> · {c.confidence.toLowerCase()} confidence</span>}
            </dd>
          </div>
        </dl>
        {c.reason && (
          <div className="mt-5 rounded-lg bg-white/[0.03] p-4">
            <p className="text-xs uppercase tracking-wide text-muted">Why</p>
            <p className="mt-1 text-ink">{c.reason}</p>
          </div>
        )}
        {c.matched_signals.length > 0 && (
          <div className="mt-4">
            <p className="text-xs uppercase tracking-wide text-muted">Matched signals</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {c.matched_signals.map((s) => {
                const [family, ...rest] = s.split(":");
                return (
                  <li key={s} className="inline-flex items-center gap-1.5 rounded-md border border-white/10 bg-white/[0.04] px-2 py-1 text-xs">
                    <span className="text-muted">{SIGNAL_LABELS[family] ?? family}</span>
                    <span className="text-ink">“{rest.join(":").trim()}”</span>
                  </li>
                );
              })}
            </ul>
          </div>
        )}
      </Section>

      <Section title="Identity" count={c.identities.length}>
        {c.identities.length === 0 ? (
          <Empty>
            {c.our_status === "NOT_APPLICABLE"
              ? "Not looked up: identity is only resolved for requests that ask for deletion."
              : "No identity could be resolved for this email."}
          </Empty>
        ) : (
          <>
            {c.user_id && (
              <p className="mb-3 text-sm text-ink-2">
                Internal user reference <span className="font-mono text-ink">{c.user_id}</span>
              </p>
            )}
            <Table head={["Type", "Value", "When", "Audit ID"]} minWidth="sm:min-w-[36rem]" desktopOnly={["When", "Audit ID"]}>
              {[...current, ...historical].map((i) => {
                const when = i.is_historical ? (
                  <span className="rounded-full border border-dashed border-white/25 px-2 py-0.5 text-xs text-ink-2">Historical</span>
                ) : (
                  <span className="rounded-full bg-white/10 px-2 py-0.5 text-xs text-ink">Current</span>
                );
                const audit = i.audit_id || <span className="text-muted">—</span>;
                return (
                  <tr key={`${i.kind}-${i.value}-${i.is_historical}`} className="border-b border-hairline align-top last:border-0">
                    <td className="py-2.5 pr-4">{KIND_LABELS[i.kind] ?? i.kind}</td>
                    <td className="py-2.5 pr-4">
                      <span className="break-all font-mono text-ink">{i.value}</span>
                      {/* On phones, "When" and the audit id sit under the value */}
                      <div className="mt-1.5 flex flex-wrap items-center gap-2 sm:hidden">
                        {when}
                        {i.audit_id && <span className="font-mono text-xs text-ink-2">{i.audit_id}</span>}
                      </div>
                    </td>
                    <td className="hidden py-2.5 pr-4 sm:table-cell">{when}</td>
                    <td className="hidden py-2.5 pr-4 font-mono text-xs sm:table-cell">{audit}</td>
                  </tr>
                );
              })}
            </Table>
            <p className="mt-3 text-xs text-muted">
              Historical values were replaced by the change in the audit log shown. Values are masked for privacy.
            </p>
          </>
        )}
      </Section>

      <Section title="Evidence found" count={c.evidence_hits.length}>
        {c.evidence_hits.length === 0 ? (
          <Empty>
            {c.our_status === "NOT_APPLICABLE"
              ? "No search: evidence is only searched for requests that ask for deletion."
              : "No evidence captured before the audit time mentions this person."}
          </Empty>
        ) : (
          <Table head={["File", "System", "Resource", "Matched identifier", "Captured at"]}>
            {c.evidence_hits.map((h) => (
              <tr key={`${h.file_id}-${h.resource_id}-${h.matched_identifier}`} className="border-b border-hairline last:border-0">
                <td className="py-2.5 pr-4 font-mono text-ink">{h.file_id}</td>
                <td className="py-2.5 pr-4">{h.system_id}</td>
                <td className="py-2.5 pr-4 font-mono text-xs">{h.resource_id}</td>
                <td className="py-2.5 pr-4 font-mono text-xs">{h.matched_identifier}</td>
                <td className="whitespace-nowrap py-2.5 pr-4 text-xs">{formatUtc(h.captured_at)}</td>
              </tr>
            ))}
          </Table>
        )}
      </Section>

      <Section title="Steps" count={c.steps.length}>
        {c.steps.length === 0 ? (
          <Empty>
            {c.our_status === "NOT_APPLICABLE"
              ? "No steps: requests that don't ask for deletion get an empty plan."
              : "Waiting for the policy engine"}
          </Empty>
        ) : (
          <Table head={["#", "Phase", "System", "Resource", "Operation", "State", "Evidence"]}>
            {c.steps.map((s) => (
              <tr key={s.step_no} className="border-b border-hairline last:border-0">
                <td className="py-2.5 pr-4 tabular-nums text-ink">{s.step_no}</td>
                <td className="py-2.5 pr-4 text-xs">{s.phase}</td>
                <td className="py-2.5 pr-4">{s.system_id}</td>
                <td className="py-2.5 pr-4 font-mono text-xs">{s.resource_id}</td>
                <td className="py-2.5 pr-4 font-mono text-xs text-ink">{s.operation}</td>
                <td className="py-2.5 pr-4 text-xs">{s.state}</td>
                <td className="py-2.5 pr-4 font-mono text-xs">{s.evidence_id || <span className="text-muted">—</span>}</td>
              </tr>
            ))}
          </Table>
        )}
      </Section>
    </div>
  );
}
