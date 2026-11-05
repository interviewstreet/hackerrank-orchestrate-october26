"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import LineageMap, { type NodeTime } from "@/components/LineageMap";
import { eventBasis, formatUtc, type Basis, type Lineage, type TimelineEvent } from "@/lib/types";

const STEP_MS = 700; // Play speed: one moment per step

const BASIS_STYLE: Record<Basis, string> = {
  proof: "border-white/30 bg-white/10 text-ink",
  claim: "border-dashed border-white/25 text-ink-2",
  record: "border-transparent bg-white/[0.04] text-muted",
};

function describe(e: TimelineEvent): string {
  const where = [e.system_id, e.resource_id].filter(Boolean).join(" · ");
  switch (e.event) {
    case "IDENTITY_CHANGE":
      return `Identity changed: ${e.resource_id} (${e.evidence_id})`;
    case "DELETION_REQUESTED":
      return "Deletion requested";
    case "AUDIT":
      return "Audit time: the answer is decided here";
    case "EVIDENCE_PROOF":
      return `${e.evidence_id} shows ${where}: ${e.state_after}`;
    case "EVIDENCE_CLAIM":
      return `${e.evidence_id} (second-hand ledger) reports ${where}: ${e.state_after}`;
    case "ABSENCE_PROOF":
      return `${e.evidence_id} snapshot has no ${where}`;
    default: {
      const what = e.event.toLowerCase().replace(/_record$/, "").replace(/_/g, " ");
      return `${what} ${where}${e.state_after ? ` · reported ${e.state_after}` : ""}${
        e.evidence_id ? ` (${e.evidence_id})` : ""
      }`;
    }
  }
}

/** Latest proof (else latest second-hand claim) about each node, up to `at`. */
function nodeStates(lineage: Lineage, events: TimelineEvent[], at: string): Record<string, NodeTime> {
  const latest = new Map<string, { proof?: TimelineEvent; claim?: TimelineEvent }>();
  for (const e of events) {
    if (e.time > at || !e.resource_id) continue;
    const basis = eventBasis(e);
    const isState = e.state_after === "PRESENT" || e.state_after === "ABSENT";
    if (!isState || basis === "record" || e.evidence_id.startsWith("activity_")) continue;
    const key = `${e.system_id}|${e.resource_id}`.toLowerCase();
    const slot = latest.get(key) ?? {};
    if (basis === "proof") slot.proof = e;
    else slot.claim = e;
    latest.set(key, slot);
  }
  const out: Record<string, NodeTime> = {};
  for (const n of lineage.nodes) {
    const slot = latest.get(`${n.system_id}|${n.resource_id}`.toLowerCase());
    const e = slot?.proof ?? slot?.claim;
    out[n.id] = e
      ? {
          state: e.state_after === "PRESENT" ? "present" : "absent",
          basis: slot?.proof ? "proof" : "claim",
          evidence_id: e.evidence_id,
        }
      : { state: "none", basis: null, evidence_id: "" };
  }
  return out;
}

export default function LineageExplorer({
  lineage,
  timeline,
  auditAt,
}: {
  lineage: Lineage;
  timeline: TimelineEvent[];
  auditAt: string;
}) {
  // Slider stops: every distinct moment, earliest -> audit_at
  const events = useMemo(
    () => [...timeline].filter((e) => !auditAt || e.time <= auditAt).sort((a, b) => a.time.localeCompare(b.time)),
    [timeline, auditAt],
  );
  const moments = useMemo(() => {
    const times = Array.from(new Set(events.map((e) => e.time)));
    if (auditAt && !times.includes(auditAt)) times.push(auditAt);
    return times.sort();
  }, [events, auditAt]);

  const last = Math.max(0, moments.length - 1);
  const [index, setIndex] = useState(last);
  const [playing, setPlaying] = useState(false);
  const timer = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => setIndex(last), [last]);

  useEffect(() => {
    if (!playing) return;
    timer.current = setInterval(() => {
      setIndex((i) => {
        if (i >= last) {
          setPlaying(false);
          return last;
        }
        return i + 1;
      });
    }, STEP_MS);
    return () => {
      if (timer.current) clearInterval(timer.current);
    };
  }, [playing, last]);

  const at = moments[index] ?? auditAt;
  const states = useMemo(() => nodeStates(lineage, events, at), [lineage, events, at]);
  const shown = events.filter((e) => e.time <= at);
  const withProof = lineage.nodes.filter((n) => states[n.id]?.state === "present" && states[n.id]?.basis === "proof");
  const withClaim = lineage.nodes.filter((n) => states[n.id]?.state === "present" && states[n.id]?.basis === "claim");
  const systemsOf = (ns: typeof lineage.nodes) => Array.from(new Set(ns.map((n) => n.system_id)));

  // Keep the newest event in view as the slider moves
  const list = useRef<HTMLOListElement | null>(null);
  useEffect(() => {
    if (list.current) list.current.scrollTop = list.current.scrollHeight;
  }, [at]);

  const play = () => {
    if (index >= last) setIndex(0);
    setPlaying((p) => !p);
  };

  if (lineage.nodes.length === 0 || moments.length === 0) {
    return <LineageMap lineage={lineage} />;
  }

  return (
    <div>
      <LineageMap lineage={lineage} timeState={states} at={at} />

      <div className="mt-6 rounded-lg border border-white/10 bg-white/[0.02] p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <p className="text-xs uppercase tracking-wide text-muted">Time travel</p>
          <p className="text-sm tabular-nums text-ink" aria-live="polite">
            {formatUtc(at)}
            {at === auditAt && <span className="ml-2 text-xs text-muted">audit time</span>}
          </p>
        </div>

        <div className="mt-3 flex items-center gap-3">
          <button
            type="button"
            onClick={play}
            aria-label={playing ? "Pause" : "Play the timeline"}
            className="grid h-9 w-9 shrink-0 place-items-center rounded-full border border-white/15 bg-white/[0.06] text-ink hover:bg-white/10"
          >
            {playing ? (
              <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden><rect x="1" y="1" width="3.5" height="10" fill="currentColor" /><rect x="7.5" y="1" width="3.5" height="10" fill="currentColor" /></svg>
            ) : (
              <svg width="12" height="12" viewBox="0 0 12 12" aria-hidden><path d="M2 1 L11 6 L2 11 Z" fill="currentColor" /></svg>
            )}
          </button>
          <div className="relative flex-1">
            <input
              type="range"
              min={0}
              max={last}
              step={1}
              value={index}
              onChange={(e) => {
                setPlaying(false);
                setIndex(Number(e.target.value));
              }}
              aria-label="Move through the case's timeline"
              aria-valuetext={formatUtc(at)}
              className="w-full accent-[#f0efec]"
            />
          </div>
        </div>
        <div className="mt-1 flex justify-between text-[11px] text-muted">
          <span>{formatUtc(moments[0])}</span>
          <span>{formatUtc(auditAt || moments[last])}</span>
        </div>

        <p className="mt-3 text-sm text-ink-2">
          At this moment: proof of the person&apos;s data in{" "}
          <span className="font-medium text-ink">{systemsOf(withProof).length}</span> system
          {systemsOf(withProof).length === 1 ? "" : "s"}
          {withProof.length > 0 && <span className="text-muted"> ({systemsOf(withProof).join(", ")})</span>}
          {withClaim.length > 0 && (
            <>
              ; claimed in <span className="font-medium text-ink">{systemsOf(withClaim).length}</span> more
              <span className="text-muted"> ({systemsOf(withClaim).join(", ")})</span>
            </>
          )}
          .
        </p>

        <ol ref={list} className="mt-3 max-h-72 space-y-1.5 overflow-y-auto pr-1 text-xs" aria-label="Events up to this moment">
          {shown.map((e, i) => {
            const basis = eventBasis(e);
            const isNow = e.time === at;
            return (
              <li key={`${e.time}-${e.evidence_id}-${e.resource_id}-${i}`} className={`flex gap-2 ${isNow ? "" : "opacity-70"}`}>
                <span className="w-[8.75rem] shrink-0 whitespace-nowrap tabular-nums text-muted">{formatUtc(e.time)}</span>
                <span className={`h-fit shrink-0 rounded border px-1.5 py-px text-[10px] uppercase tracking-wide ${BASIS_STYLE[basis]}`}>
                  {basis}
                </span>
                <span className="min-w-0 break-words text-ink-2">{describe(e)}</span>
              </li>
            );
          })}
        </ol>
        <p className="mt-3 text-[11px] text-muted">
          A box lights up when the latest proof up to that moment shows the data (dashed when only a second-hand claim
          says so). Claims come from the shop&apos;s logs and ledgers, proof from direct evidence.
        </p>
      </div>
    </div>
  );
}
