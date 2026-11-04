import { Component, lazy, Suspense, useEffect, useMemo, useRef, useState, type ReactNode } from 'react';
import { AnimatePresence, motion, useReducedMotion } from 'motion/react';
import { ArrowUpRight, Crosshair, Filter, Minus, Pause, Play, Plus, RotateCcw, RotateCw, Search, X } from 'lucide-react';
import type { CaseResult } from './types';
import { connectedPath, globeLayout, nodeColors, nodeDetails } from './graphModel';

const GlobeScene = lazy(() => import('./GlobeScene'));
const readable = (value: string) => value.toLowerCase().replaceAll('_', ' ');
class SceneBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}
function supportsWebGL() {
  try { const context = document.createElement('canvas').getContext('webgl2'); if (!context) return false; context.getExtension('WEBGL_lose_context')?.loseContext(); return true; } catch { return false; }
}
function GraphFallback({ result, select, visible }: { result: CaseResult; select: (id: string) => void; visible: Set<string> }) {
  const positions = useMemo(() => globeLayout(result.graph_data.nodes), [result]);
  return <div className="graph-fallback"><svg viewBox="-3 -3 6 6" role="img" aria-label="Static projection of the supplied evidence graph">{result.graph_data.edges.map(e => { const a = positions.get(e.source), b = positions.get(e.target); return a && b ? <line key={e.id} x1={a[0]} y1={-a[1]} x2={b[0]} y2={-b[1]} stroke="#168bff" strokeWidth=".012" opacity={visible.has(e.source) && visible.has(e.target) ? .5 : .08}/> : null; })}{result.graph_data.nodes.map(n => { const p = positions.get(n.id)!; return <g key={n.id} style={{ cursor: 'pointer' }} onClick={() => select(n.id)} opacity={visible.has(n.id) ? 1 : .15}><circle cx={p[0]} cy={-p[1]} r={n.type === 'IDENTITY' ? .16 : n.status === 'ISSUE' ? .09 : .055} fill={nodeColors[n.status]}/><title>{n.label} / {n.status}</title></g>; })}</svg><p>3D is unavailable on this device. Use the graph or node list to inspect evidence.</p></div>;
}
export default function Graph({ result, focus, expanded = false, hero = false }: { result: CaseResult; focus: string | null; expanded?: boolean; hero?: boolean }) {
  const reduced = useReducedMotion();
  const [webgl] = useState(supportsWebGL);
  const [contextLost, setContextLost] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [alertsOnly, setAlertsOnly] = useState(false);
  const [type, setType] = useState('ALL');
  const [system, setSystem] = useState('ALL');
  const [paused, setPaused] = useState(false);
  const [inView, setInView] = useState(true);
  const [pageVisible, setPageVisible] = useState(true);
  const [command, setCommand] = useState({ action: 'reset', sequence: 0 });
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => { setSelectedId(null); setHoveredId(null); setQuery(''); setAlertsOnly(false); setType('ALL'); setSystem('ALL'); setCommand(c => ({ action: 'reset', sequence: c.sequence + 1 })); }, [result]);
  useEffect(() => { setSelectedId(focus && result.graph_data.nodes.some(n => n.id === focus) ? focus : null); }, [focus, result]);
  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => setInView(entry.isIntersecting), { threshold: .05 });
    if (container.current) observer.observe(container.current);
    const change = () => setPageVisible(document.visibilityState === 'visible');
    document.addEventListener('visibilitychange', change);
    return () => { observer.disconnect(); document.removeEventListener('visibilitychange', change); };
  }, []);
  const selected = result.graph_data.nodes.find(n => n.id === selectedId);
  const visible = useMemo(() => new Set(result.graph_data.nodes.filter(n => (!query || `${n.label} ${n.id}`.toLowerCase().includes(query.toLowerCase())) && (!alertsOnly || n.status === 'ISSUE') && (type === 'ALL' || n.type === type) && (system === 'ALL' || n.system_id === system)).map(n => n.id)), [result, query, alertsOnly, type, system]);
  const path = useMemo(() => connectedPath(result, hoveredId || selectedId), [result, hoveredId, selectedId]);
  const details = selected ? nodeDetails(result, selected) : null;
  const animate = !paused && !reduced && inView && pageVisible;
  useEffect(() => {
    const heroElement = container.current?.closest<HTMLElement>('.hero');
    if (heroElement) heroElement.dataset.motionPaused = String(!animate);
    return () => { if (heroElement) delete heroElement.dataset.motionPaused; };
  }, [animate]);
  function sendCommand(action: string) { if (action === 'reset') { setSelectedId(null); setHoveredId(null); setQuery(''); setAlertsOnly(false); setType('ALL'); setSystem('ALL'); } setCommand(c => ({ action, sequence: c.sequence + 1 })); }
  function select(id: string) { setSelectedId(id); setHoveredId(null); }
  const fallback = <GraphFallback result={result} select={select} visible={visible}/>;
  return <div ref={container} className={`globe-workspace ${hero ? 'hero-globe' : ''} ${expanded ? 'expanded' : ''} ${animate ? 'is-animated' : ''}`}>
    <div className="globe-canvas" aria-label={`3D evidence globe for ${result.case_id}: ${result.graph_data.nodes.length} nodes. Keyboard controls and node list follow.`}>
      {webgl && !contextLost ? <SceneBoundary fallback={fallback}><Suspense fallback={<div className="globe-loading">Assembling evidence network…</div>}><GlobeScene result={result} selectedId={selectedId} hoveredId={hoveredId} visible={visible} path={path} animate={animate} reduced={!!reduced} command={command} onSelect={select} onHover={setHoveredId} onContextLost={() => setContextLost(true)}/></Suspense></SceneBoundary> : fallback}
    </div>
    {!result.graph_data.nodes.length && <div className="globe-loading">No graph data supplied for this case.</div>}
    <div className="globe-caption"><span className="cross-mark">+</span><span>Identity at the center<br/><b>{result.graph_data.nodes.length} nodes / {result.graph_data.edges.length} relationships</b></span></div>
    <div className="globe-controls" aria-label="Evidence globe controls"><button aria-label="Rotate globe" title="Rotate globe" onClick={() => sendCommand('rotate')}><RotateCw size={16}/></button><button aria-label="Zoom in" title="Zoom in" onClick={() => sendCommand('in')}><Plus size={17}/></button><button aria-label="Zoom out" title="Zoom out" onClick={() => sendCommand('out')}><Minus size={17}/></button><button aria-label="Reset globe" title="Reset globe" onClick={() => sendCommand('reset')}><RotateCcw size={15}/></button><span className="control-divider"/><button aria-label={paused ? 'Resume animation' : 'Pause animation'} title={reduced ? 'Motion disabled by device preference' : paused ? 'Resume animation' : 'Pause animation'} disabled={!!reduced} aria-pressed={paused || !!reduced} onClick={() => setPaused(!paused)}>{paused || reduced ? <Play size={15}/> : <Pause size={15}/>}</button><button aria-label="Filter alert nodes" aria-pressed={alertsOnly} className={alertsOnly ? 'active' : ''} onClick={() => { setAlertsOnly(!alertsOnly); setSelectedId(null); }}><Filter size={14}/><span>Alerts</span></button></div>
    <details className="graph-browser"><summary><Search size={13}/><span>Find a node</span><ArrowUpRight size={13}/></summary><div className="graph-browser-content"><p className="scaffold-note">Faint light scaffold is decorative, not evidence. Only supplied relationships are counted or highlighted.</p><label className="input"><Search size={14}/><input aria-label="Search graph nodes" placeholder="Search systems or resources" value={query} onChange={e => { setQuery(e.target.value); setSelectedId(null); }}/></label><div className="graph-filter-row"><select aria-label="Filter node type" value={type} onChange={e => setType(e.target.value)}><option value="ALL">All types</option>{[...new Set(result.graph_data.nodes.map(n => n.type))].map(t => <option key={t}>{t}</option>)}</select><select aria-label="Filter graph system" value={system} onChange={e => setSystem(e.target.value)}><option value="ALL">All systems</option>{[...new Set(result.graph_data.nodes.flatMap(n => n.system_id ? [n.system_id] : []))].map(s => <option key={s}>{s}</option>)}</select></div><div className="graph-node-list">{result.graph_data.nodes.filter(n => visible.has(n.id)).map(n => <button key={n.id} aria-pressed={selectedId === n.id} onClick={() => select(n.id)}><i style={{ background: nodeColors[n.status] }}/><span>{n.label}<small>{readable(n.status)}</small></span><Crosshair size={13}/></button>)}{!visible.size && <p>No nodes match these filters.</p>}</div></div></details>
    <AnimatePresence>{selected && details && <motion.aside key={selected.id} className="globe-node-detail" initial={{ opacity: 0, x: reduced ? 0 : 14 }} animate={{ opacity: 1, x: 0 }} exit={{ opacity: 0 }} transition={{ duration: reduced ? 0 : .2 }} aria-label="Selected node details"><div className="node-detail-top"><span className={`node-state ${selected.status.toLowerCase()}`}><i/>{readable(selected.status)}</span><button aria-label="Close node details" onClick={() => setSelectedId(null)}><X size={16}/></button></div><h3>{selected.label}</h3><p className="node-meta">{readable(selected.type)} / {result.case_id}</p>{selected.system_id && <p className="node-system">{readable(selected.system_id)}</p>}{details.findings.map(f => <div className="node-finding" key={f.id}><strong>{f.title}</strong><p>{f.description}</p></div>)}<h4>Supporting evidence</h4>{details.evidenceIds.length ? details.evidenceIds.map(id => <div key={id} className="node-evidence"><code>{id}</code><small>{details.evidence.find(e => e.id === id)?.label || 'Reference supplied; metadata unavailable'}</small></div>) : <p>No direct reference supplied for this node.</p>}<h4>Recommended action</h4>{details.actions.length ? details.actions.map(s => <p className="node-action" key={s.step_no}>{s.step_no}. {readable(s.operation)}<small>Recommended · not executed</small></p>) : <p>No remediation step supplied for this node.</p>}<details><summary>Connected records</summary>{result.graph_data.edges.filter(e => e.source === selected.id || e.target === selected.id).map(e => <p key={e.id}>{result.graph_data.nodes.find(n => n.id === (e.source === selected.id ? e.target : e.source))?.label}<small>{readable(e.relationship)}</small></p>)}</details></motion.aside>}</AnimatePresence>
    <div className="globe-legend"><span><i className="issue"/>Residual / risk</span><span><i className="verified"/>Verified</span><span><i/>Evidence</span><small>Supplied relationships only</small></div>
  </div>;
}
