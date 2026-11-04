# Design decisions

The screen answers: which deletion claims still need evidence-backed remediation? Its signature is a resource network linking historical identifiers, system copies, evidence captures, and restore risks. Selection connects a finding to its graph neighborhood. The overview puts that network beside the findings that require action.

Dealt style: True-black flat, seed 1032678506. The PRD explicitly requests a dark navy/charcoal shell, so the palette maps the dealt ground/surface hierarchy to navy (#0c111b, #111925, #182231); this overrides the skill's neutral-only dark preference. Status colors are green #58b79c, red #e47c82, amber #d5ac60, and evidence blue #728aa7. No gradients, glow or decorative charts. The system Segoe UI Variable/Segoe UI face suits the Windows local workspace without an external font dependency.

Layout: 226px sidebar and 67px search header; equal 28px workspace gutters; a divided metric strip, evidence network, findings rail, and recent-case table. The sidebar folds below 1000px; panels stack below 720px. Text stays left aligned; numeric columns align right. Status words accompany every status color.

All counts derive from the six fictional cases in `src/data.ts`; fixtures are labeled in the persistent workspace notice. Demo cases are not challenge evidence or predictions. No invented percentage changes, notifications, delivery statuses, or operation execution results are shown.
