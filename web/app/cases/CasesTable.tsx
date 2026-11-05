"use client";

import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useMemo, useState } from "react";

import { ReportedBadge, StatusBadge } from "@/components/Badges";
import {
  LANGUAGE_NAMES,
  LANGUAGES,
  OUR_STATUSES,
  REPORTED_LABELS,
  REPORTED_STATUSES,
  STATUS_META,
  type CaseListItem,
} from "@/lib/types";

type Filters = { q: string; status: string; reported: string; lang: string };
const KEYS: (keyof Filters)[] = ["q", "status", "reported", "lang"];

const selectClass =
  "h-10 rounded-lg border border-white/10 bg-surface px-3 text-sm text-ink outline-none focus:border-white/30";

export default function CasesTable() {
  const router = useRouter();
  const pathname = usePathname();
  const params = useSearchParams();

  const [cases, setCases] = useState<CaseListItem[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(() => ({
    q: params.get("q") ?? "",
    status: params.get("status") ?? "",
    reported: params.get("reported") ?? "",
    lang: params.get("lang") ?? "",
  }));

  // All 518 rows come from the API once; filtering is then instant in the browser.
  useEffect(() => {
    fetch("/api/cases")
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json() as Promise<{ cases: CaseListItem[] }>;
      })
      .then((data) => setCases(data.cases))
      .catch((err: Error) => setError(err.message));
  }, []);

  // Keep the filters in the URL so a filtered view can be shared or reloaded
  useEffect(() => {
    const next = new URLSearchParams();
    for (const k of KEYS) if (filters[k]) next.set(k, filters[k]);
    const qs = next.toString();
    if (qs !== params.toString()) router.replace(qs ? `${pathname}?${qs}` : pathname, { scroll: false });
  }, [filters, params, pathname, router]);

  const rows = useMemo(() => {
    if (!cases) return [];
    const q = filters.q.trim().toLowerCase();
    return cases.filter(
      (c) =>
        (!filters.status || c.our_status === filters.status) &&
        (!filters.reported || c.reported_status === filters.reported) &&
        (!filters.lang || c.language === filters.lang) &&
        (!q || c.case_id.toLowerCase().includes(q) || c.email.toLowerCase().includes(q)),
    );
  }, [cases, filters]);

  const set = (k: keyof Filters) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setFilters((f) => ({ ...f, [k]: e.target.value }));
  const anyFilter = KEYS.some((k) => filters[k]);

  return (
    <div>
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-[1fr_auto_auto_auto_auto]">
        <label className="sm:col-span-2 lg:col-span-1">
          <span className="sr-only">Search by case or email</span>
          <input
            type="search"
            value={filters.q}
            onChange={set("q")}
            placeholder="Search case ID or email…"
            className="h-10 w-full rounded-lg border border-white/10 bg-surface px-3 text-sm text-ink placeholder:text-muted outline-none focus:border-white/30"
          />
        </label>
        <label>
          <span className="sr-only">Our verdict</span>
          <select value={filters.status} onChange={set("status")} className={`${selectClass} w-full`}>
            <option value="">All verdicts</option>
            {OUR_STATUSES.map((s) => (
              <option key={s} value={s}>
                {STATUS_META[s].label}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Shop reported</span>
          <select value={filters.reported} onChange={set("reported")} className={`${selectClass} w-full`}>
            <option value="">Any shop report</option>
            {REPORTED_STATUSES.map((s) => (
              <option key={s} value={s}>
                Shop: {REPORTED_LABELS[s]}
              </option>
            ))}
          </select>
        </label>
        <label>
          <span className="sr-only">Language</span>
          <select value={filters.lang} onChange={set("lang")} className={`${selectClass} w-full`}>
            <option value="">All languages</option>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {LANGUAGE_NAMES[l]}
              </option>
            ))}
          </select>
        </label>
        <button
          type="button"
          onClick={() => setFilters({ q: "", status: "", reported: "", lang: "" })}
          disabled={!anyFilter}
          className="h-10 rounded-lg border border-white/10 px-3 text-sm text-ink-2 hover:bg-white/5 disabled:opacity-40"
        >
          Clear
        </button>
      </div>

      <p className="mb-3 text-sm text-muted" aria-live="polite">
        {cases ? `Showing ${rows.length} of ${cases.length} cases` : "Loading cases…"}
      </p>

      {error ? (
        <div role="alert" className="rounded-lg border border-critical/50 bg-critical/10 px-4 py-3 text-sm text-ink">
          Could not load the cases ({error}).
        </div>
      ) : (
        <div className="overflow-x-auto rounded-xl border border-white/10 bg-surface">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-white/10 text-xs uppercase tracking-wide text-muted">
              <tr>
                <th scope="col" className="px-4 py-3 font-medium">Case</th>
                <th scope="col" className="hidden px-4 py-3 font-medium sm:table-cell">Email</th>
                <th scope="col" className="px-4 py-3 font-medium">Shop reported</th>
                <th scope="col" className="px-4 py-3 font-medium">Our verdict</th>
                <th scope="col" className="hidden px-4 py-3 font-medium md:table-cell">Language</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr
                  key={c.case_id}
                  onClick={() => router.push(`/cases/${c.case_id}`)}
                  className="cursor-pointer border-b border-hairline last:border-0 hover:bg-white/[0.04]"
                >
                  <td className="whitespace-nowrap px-4 py-3">
                    <Link
                      href={`/cases/${c.case_id}`}
                      onClick={(e) => e.stopPropagation()}
                      className="font-mono text-ink hover:underline"
                    >
                      {c.case_id}
                    </Link>
                    <div className="mt-0.5 font-mono text-xs text-muted sm:hidden">{c.email}</div>
                  </td>
                  <td className="hidden px-4 py-3 font-mono text-ink-2 sm:table-cell">{c.email}</td>
                  <td className="px-4 py-3">
                    <ReportedBadge status={c.reported_status} />
                  </td>
                  <td className="px-4 py-3">
                    <StatusBadge status={c.our_status} />
                  </td>
                  <td className="hidden px-4 py-3 text-ink-2 md:table-cell">
                    {LANGUAGE_NAMES[c.language] ?? c.language}
                  </td>
                </tr>
              ))}
              {cases && rows.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-10 text-center text-muted">
                    No cases match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
