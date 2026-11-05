"use client";

import { useMemo, useState } from "react";

import { formatUtc, type Lineage, type LineageEdge, type LineageNode } from "@/lib/types";

// Layout (SVG user units = px at 100%)
const COL_W = 212;
const COL_GAP = 76;
const NODE_H = 68;
const ROW_GAP = 16;
const HEAD_H = 34;
const PAD = 8;

// Ink + mark colours (dataviz dark palette; status steps for P3 overlays)
const C = {
  surface: "#1a1a19",
  node: "#232321",
  nodeSelected: "#2d2d2a",
  border: "rgba(255,255,255,0.16)",
  ink: "#f0efec",
  ink2: "#c3c2b7",
  muted: "#898781",
  claim: "#898781",
  flow: "#d03b3b", // critical: an active flow can recreate data
  restore: "#ec835a", // serious: a backup can bring data back
};

type Placed = LineageNode & { x: number; y: number };

/** A box's state at the slider's moment (time-travel mode). */
export type NodeTime = {
  state: "present" | "absent" | "none";
  basis: "proof" | "claim" | null;
  evidence_id: string;
};

const TIME_TEXT: Record<string, string> = {
  "present-proof": "● data present · proof",
  "present-claim": "◌ data present · claim",
  "absent-proof": "absent · proof",
  "absent-claim": "absent · claim",
  none: "no evidence yet",
};

const trunc = (s: string, n: number) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

function edgeColor(e: LineageEdge, nodes: Map<string, Placed>) {
  const src = nodes.get(e.from);
  if (src?.active_flow?.active_at_audit) return C.flow;
  if (src?.restore_risk?.active_at_audit) return C.restore;
  return C.claim;
}

function edgePath(a: Placed, b: Placed): string {
  const ay = a.y + NODE_H / 2;
  const by = b.y + NODE_H / 2;
  if (b.x > a.x) {
    const x1 = a.x + COL_W, x2 = b.x - 6, mid = (x1 + x2) / 2;
    return `M${x1},${ay} C${mid},${ay} ${mid},${by} ${x2},${by}`;
  }
  if (b.x < a.x) {
    const x1 = a.x, x2 = b.x + COL_W + 6, mid = (x1 + x2) / 2;
    return `M${x1},${ay} C${mid},${ay} ${mid},${by} ${x2},${by}`;
  }
  // same column: loop out to the right
  const x = a.x + COL_W, bulge = x + 44;
  return `M${x},${ay} C${bulge},${ay} ${bulge},${by} ${x + 6},${by}`;
}

export default function LineageMap({
  lineage,
  timeState,
  at,
}: {
  lineage: Lineage;
  /** time-travel mode: state of each node id at the slider's moment */
  timeState?: Record<string, NodeTime>;
  /** ISO time of the slider; arrows reported later are faded */
  at?: string;
}) {
  const [selected, setSelected] = useState<string | null>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  const { placed, byId, width, height } = useMemo(() => {
    const placed: Placed[] = [];
    let rows = 0;
    lineage.groups.forEach((g, col) => {
      const inCol = lineage.nodes.filter((n) => n.group === g.id);
      inCol.forEach((n, row) => {
        placed.push({ ...n, x: PAD + col * (COL_W + COL_GAP), y: HEAD_H + row * (NODE_H + ROW_GAP) });
      });
      rows = Math.max(rows, inCol.length);
    });
    return {
      placed,
      byId: new Map(placed.map((p) => [p.id, p])),
      width: PAD * 2 + lineage.groups.length * COL_W + (lineage.groups.length - 1) * COL_GAP + 40,
      height: HEAD_H + Math.max(1, rows) * (NODE_H + ROW_GAP) + PAD,
    };
  }, [lineage]);

  if (lineage.nodes.length === 0) {
    return (
      <p className="rounded-lg border border-dashed border-white/10 px-4 py-8 text-center text-sm text-muted">
        No copies found
      </p>
    );
  }

  const activeId = hovered ?? selected;
  const active = activeId ? byId.get(activeId) : undefined;
  const linked = new Set(
    activeId ? lineage.edges.filter((e) => e.from === activeId || e.to === activeId).map((e) => e.activity_id) : [],
  );

  return (
    <div>
      <Legend />

      <p className="mt-4 text-xs text-muted md:hidden">Swipe sideways to see all three columns →</p>
      <div className="-mx-5 mt-2 overflow-x-auto px-5 sm:mx-0 sm:px-0 md:mt-4">
        <svg
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="group"
          aria-label="Data lineage map: systems holding this person's data, in columns"
          className="block"
        >
          <defs>
            {(["claim", "flow", "restore"] as const).map((k) => (
              <marker key={k} id={`arrow-${k}`} viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
                <path d="M0,0 L10,5 L0,10 z" fill={C[k]} />
              </marker>
            ))}
          </defs>

          {/* Column headers */}
          {lineage.groups.map((g, col) => {
            const count = lineage.nodes.filter((n) => n.group === g.id).length;
            const x = PAD + col * (COL_W + COL_GAP);
            return (
              <g key={g.id}>
                <text x={x} y={16} fill={C.muted} fontSize={11} letterSpacing="0.08em">
                  {g.label.toUpperCase()}
                </text>
                {count === 0 && (
                  <text x={x} y={HEAD_H + 24} fill={C.muted} fontSize={12}>
                    none found
                  </text>
                )}
              </g>
            );
          })}

          {/* Edges under the nodes */}
          {lineage.edges.map((e) => {
            const a = byId.get(e.from);
            const b = byId.get(e.to);
            if (!a || !b) return null;
            const color = edgeColor(e, byId);
            const kind = color === C.flow ? "flow" : color === C.restore ? "restore" : "claim";
            const future = !!at && e.event_time > at;
            const dim = future || (activeId && !linked.has(e.activity_id));
            return (
              <path
                key={e.activity_id}
                d={edgePath(a, b)}
                fill="none"
                stroke={color}
                strokeWidth={2}
                strokeDasharray={kind === "claim" ? "5 4" : undefined}
                markerEnd={`url(#arrow-${kind})`}
                opacity={future ? 0.12 : dim ? 0.25 : 1}
              >
                <title>{`${e.label} (${e.reported_result}, reported claim) · ${e.activity_id}`}</title>
              </path>
            );
          })}

          {/* Nodes */}
          {placed.map((n) => {
            const isActive = n.id === activeId;
            const flow = n.active_flow?.active_at_audit;
            const restore = n.restore_risk?.active_at_audit;
            const t = timeState?.[n.id];
            const present = t?.state === "present";
            const ring = flow
              ? C.flow
              : restore
                ? C.restore
                : present
                  ? C.ink
                  : isActive
                    ? "rgba(255,255,255,0.55)"
                    : C.border;
            const third = t
              ? `${TIME_TEXT[t.state === "none" ? "none" : `${t.state}-${t.basis}`]}${t.evidence_id ? ` · ${t.evidence_id}` : ""}`
              : n.source === "evidence"
                ? trunc(n.file_ids.join(", "), 30)
                : "named in activity log only";
            const opacity = !t || present ? 1 : t.state === "absent" ? 0.55 : 0.35;
            return (
              <g
                key={n.id}
                transform={`translate(${n.x},${n.y})`}
                role="button"
                tabIndex={0}
                aria-pressed={selected === n.id}
                aria-label={`${n.system_id}, ${n.resource_id}${n.replica_or_table ? `, ${n.replica_or_table}` : ""}`}
                onMouseEnter={() => setHovered(n.id)}
                onMouseLeave={() => setHovered(null)}
                onFocus={() => setHovered(n.id)}
                onBlur={() => setHovered(null)}
                onClick={() => setSelected((s) => (s === n.id ? null : n.id))}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") {
                    ev.preventDefault();
                    setSelected((s) => (s === n.id ? null : n.id));
                  }
                }}
                className="cursor-pointer outline-none"
                opacity={opacity}
                style={{ transition: "opacity 250ms" }}
              >
                <rect
                  width={COL_W}
                  height={NODE_H}
                  rx={8}
                  fill={isActive ? C.nodeSelected : C.node}
                  stroke={ring}
                  strokeWidth={flow || restore || present ? 2 : 1}
                  strokeDasharray={
                    present && t?.basis === "claim" ? "5 3" : n.source === "activity" ? "4 3" : undefined
                  }
                />
                <text x={12} y={21} fill={C.ink} fontSize={13} fontWeight={600}>
                  {trunc(n.system_id, 26)}
                </text>
                <text x={12} y={39} fill={C.ink2} fontSize={11.5} fontFamily="ui-monospace, SFMono-Regular, Menlo, monospace">
                  {trunc(n.resource_id + (n.replica_or_table ? ` · ${n.replica_or_table}` : ""), 30)}
                </text>
                <text
                  x={12}
                  y={56}
                  fill={present ? C.ink : C.muted}
                  fontSize={11}
                  fontFamily={!t && n.source === "evidence" ? "ui-monospace, SFMono-Regular, Menlo, monospace" : undefined}
                >
                  {trunc(third, 34)}
                </text>
                {n.claims.length > 0 && (
                  <g transform={`translate(${COL_W - 16},14)`}>
                    <circle r={5} fill="none" stroke={C.ink2} strokeWidth={1.5} />
                    <text x={0} y={3.5} fill={C.ink2} fontSize={8} textAnchor="middle" fontWeight={700}>
                      {n.claims.length}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
        </svg>
      </div>

      <Details node={active} edges={lineage.edges} byId={byId} pinned={!!selected && !hovered} />
    </div>
  );
}

function Legend() {
  const item = "flex items-center gap-2";
  return (
    <ul className="flex flex-wrap gap-x-5 gap-y-2 text-xs text-ink-2" aria-label="Map legend">
      <li className={item}>
        <span aria-hidden className="h-3 w-5 rounded-sm border border-white/30 bg-surface-2" /> Found in evidence
      </li>
      <li className={item}>
        <span aria-hidden className="h-3 w-5 rounded-sm border border-dashed border-white/40" /> Only named in activity log
      </li>
      <li className={item}>
        <svg aria-hidden width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke={C.claim} strokeWidth="2" strokeDasharray="5 4" /></svg>
        Reported activity (claims)
      </li>
      <li className={item}>
        <svg aria-hidden width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke={C.flow} strokeWidth="2" /></svg>
        Active flow (policy engine)
      </li>
      <li className={item}>
        <svg aria-hidden width="26" height="8"><line x1="0" y1="4" x2="26" y2="4" stroke={C.restore} strokeWidth="2" /></svg>
        Restore risk (policy engine)
      </li>
      <li className={item}>
        <svg aria-hidden width="12" height="12"><circle cx="6" cy="6" r="5" fill="none" stroke={C.ink2} strokeWidth="1.5" /></svg>
        Flow / backup claims
      </li>
    </ul>
  );
}

function Details({
  node,
  edges,
  byId,
  pinned,
}: {
  node: Placed | undefined;
  edges: LineageEdge[];
  byId: Map<string, Placed>;
  pinned: boolean;
}) {
  if (!node) {
    return <p className="mt-3 text-xs text-muted">Hover or tap a box to see its details.</p>;
  }
  const related = edges.filter((e) => e.from === node.id || e.to === node.id);
  const name = (id: string) => {
    const n = byId.get(id);
    return n ? `${n.system_id} · ${n.resource_id}` : id;
  };
  const group = { primary: "Primary system", copy: "Copy", backup: "Backup / archive" }[node.group];

  return (
    <div className="mt-4 rounded-lg border border-white/10 bg-white/[0.03] p-4 text-sm" aria-live="polite">
      <div className="flex flex-wrap items-baseline justify-between gap-2">
        <p className="font-semibold text-ink">
          {node.system_id} <span className="font-mono font-normal text-ink-2">{node.resource_id}</span>
        </p>
        <span className="text-xs text-muted">{group}{pinned ? " · selected" : ""}</span>
      </div>
      <dl className="mt-3 grid gap-x-6 gap-y-2 sm:grid-cols-2">
        {node.replica_or_table && <Row k="Copy" v={node.replica_or_table} mono />}
        <Row k="Seen in" v={node.source === "evidence" ? node.file_ids.join(", ") : "Activity log only (no evidence file)"} mono={node.source === "evidence"} />
        {node.origins.length > 0 && <Row k="Evidence origin" v={node.origins.join(", ")} />}
        {node.first_captured_at && (
          <Row
            k="Captured"
            v={node.first_captured_at === node.last_captured_at ? formatUtc(node.first_captured_at) : `${formatUtc(node.first_captured_at)} – ${formatUtc(node.last_captured_at)}`}
          />
        )}
        {node.matched_identifiers.length > 0 && <Row k="Matched" v={node.matched_identifiers.join(", ")} mono />}
        {node.active_flow && (
          <Row k="Policy engine" v={`${node.active_flow.kind} flow ${node.active_flow.active_at_audit ? "ACTIVE" : "inactive"} at audit time (${node.active_flow.evidence_id})`} />
        )}
        {node.restore_risk && (
          <Row k="Policy engine" v={`restore ${node.restore_risk.active_at_audit ? "NOT blocked" : "blocked"} at audit time (${node.restore_risk.evidence_id})`} />
        )}
      </dl>
      {(node.claims.length > 0 || related.length > 0) && (
        <div className="mt-3 border-t border-white/10 pt-3">
          <p className="text-xs uppercase tracking-wide text-muted">Reported activity (claims, not proof)</p>
          <ul className="mt-2 space-y-1.5 text-xs text-ink-2">
            {related.map((e) => (
              <li key={e.activity_id}>
                <span className="font-mono text-ink">{e.activity_id}</span> · {formatUtc(e.event_time)} · {e.label}{" "}
                {name(e.from)} → {name(e.to)} · reported {e.reported_result}
                <span className="block text-muted">{e.details}</span>
              </li>
            ))}
            {node.claims.map((c) => (
              <li key={c.activity_id}>
                <span className="font-mono text-ink">{c.activity_id}</span> · {formatUtc(c.event_time)} · {c.label} · reported{" "}
                {c.reported_result}
                <span className="block text-muted">{c.details}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

function Row({ k, v, mono }: { k: string; v: string; mono?: boolean }) {
  return (
    <div className="min-w-0">
      <dt className="text-xs text-muted">{k}</dt>
      <dd className={`break-words text-ink-2 ${mono ? "font-mono text-xs" : ""}`}>{v}</dd>
    </div>
  );
}
