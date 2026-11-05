import { LANGUAGE_NAMES, LANGUAGES } from "@/lib/types";

/** Requests per language: one series, one hue, sorted, value at each bar tip. */
export default function LanguageBars({ counts }: { counts: Record<string, number> }) {
  const rows = LANGUAGES.map((lang) => ({ lang, count: counts[lang] ?? 0 })).sort(
    (a, b) => b.count - a.count || LANGUAGES.indexOf(a.lang) - LANGUAGES.indexOf(b.lang),
  );
  const max = Math.max(1, ...rows.map((r) => r.count));
  const total = rows.reduce((n, r) => n + r.count, 0);

  return (
    <ul className="space-y-2.5">
      {rows.map((r) => (
        <li key={r.lang} className="grid grid-cols-[6.5rem_1fr] items-center gap-3 text-sm">
          <span className="text-ink-2">{LANGUAGE_NAMES[r.lang]}</span>
          <div
            className="flex items-center gap-2"
            title={`${LANGUAGE_NAMES[r.lang]}: ${r.count} of ${total} requests`}
          >
            <div
              className="h-4 rounded-r bg-series"
              style={{ width: `${(r.count / max) * 85}%`, minWidth: r.count > 0 ? "2px" : 0 }}
            />
            <span className="tabular-nums text-ink">{r.count}</span>
          </div>
        </li>
      ))}
    </ul>
  );
}
