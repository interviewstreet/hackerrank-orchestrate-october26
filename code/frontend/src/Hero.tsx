import { motion, useReducedMotion } from 'motion/react';
import { ArrowDown, ArrowUpRight, Crosshair } from 'lucide-react';
import Graph from './Graph';
import type { CaseResult } from './types';

export default function Hero({ result, cases, onCase, open, focus }: { result: CaseResult; cases: CaseResult[]; onCase: (id: string) => void; open: () => void; focus: string | null }) {
  const reduced = useReducedMotion();
  return <section className="hero" aria-label="Deletion intelligence overview">
    <div className="exposure-field" aria-hidden="true"/><div className="studio-grain" aria-hidden="true"/>
    <div className="hero-meta"><span>ERASIGHT / DATA DELETION INTELLIGENCE</span><span>01 — INVESTIGATION</span></div>
    <div className="hero-copy"><h1>{['See what', 'remains.'].map((line, i) => <motion.span key={line} initial={{ opacity: reduced ? 1 : 0, y: reduced ? 0 : 25 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: .7, delay: i * .1, ease: [.22, 1, .36, 1] }}>{line}</motion.span>)}</h1><div className="hero-support"><span className="target-symbol" aria-hidden="true"><Crosshair size={24} strokeWidth={1}/></span><p>Trace every copy.<br/>Verify every outcome.</p></div><p className="hero-description">Deletion is a promise.<br/>Evidence is the proof.</p><button className="hero-action" onClick={open}>Explore investigation <ArrowUpRight size={19}/></button></div>
    <div className="hero-stage"><Graph result={result} focus={focus} hero/></div>
    <div className="hero-case"><span className="technical-label">ACTIVE CASE</span><select aria-label="Select hero investigation" value={result.case_id} onChange={e => onCase(e.target.value)}>{cases.map(c => <option key={c.case_id}>{c.case_id}</option>)}</select><span className={`hero-audit ${result.deletion_status.toLowerCase()}`}><i/>AUDIT / {result.deletion_status.replaceAll('_', ' ')}</span></div>
    <div className="hero-bottom"><div className="hero-fact"><strong>{String(result.summary.systems_checked).padStart(2, '0')}</strong><span>SYSTEMS<br/>INVESTIGATED</span></div><div className="hero-fact"><strong>{String(result.findings.length).padStart(2, '0')}</strong><span>UNRESOLVED<br/>FINDINGS</span></div><button className="scroll-link" onClick={() => document.getElementById('audit-overview')?.scrollIntoView({ behavior: reduced ? 'instant' : 'smooth', block: 'start' })}>THE AUDIT, IN DETAIL <ArrowDown size={15}/></button></div>
  </section>;
}
