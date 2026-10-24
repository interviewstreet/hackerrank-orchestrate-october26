"""Public-sample regression runner."""
from __future__ import annotations
import json,sys
from pathlib import Path
if __package__ in (None,''):sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from code.ingest import load_all
from code.main import run_pipeline
FIELDS=('phase','operation','state','system_id','resource_id','evidence_id')
def run_evaluation(repo_root):
 data=load_all(repo_root); actual={r['case_id']:r for r in run_pipeline(repo_root,sample=True)}; truth=data['sample_output']
 status_correct=0;correct_steps=0;total_steps=0;sequence_correct=0;breakdown=[]
 for case_id in sorted(truth):
  expected=truth[case_id];got=actual.get(case_id,{}); es=json.loads(expected['steps_json']); gs=json.loads(got.get('steps_json','[]'))
  status_ok=got.get('deletion_status')==expected['deletion_status'];status_correct+=status_ok
  total_steps+=len(es); positional=0
  mismatches=[]
  if not status_ok:mismatches.append(f"status expected={expected['deletion_status']} actual={got.get('deletion_status')}")
  if len(es)!=len(gs):mismatches.append(f'step_count expected={len(es)} actual={len(gs)}')
  for i,(e,g) in enumerate(zip(es,gs),1):
   bad=[f for f in FIELDS if e.get(f)!=g.get(f)]
   if not bad:positional+=1
   else:mismatches.append(f"step {i} fields={','.join(bad)}")
  correct_steps+=positional
  seq_ok=status_ok and len(es)==len(gs) and positional==len(es);sequence_correct+=seq_ok
  breakdown.append((case_id,'PASS' if seq_ok else 'FAIL',mismatches))
 print('=== Sample Evaluation Report ===')
 print(f'Case-level status accuracy: {status_correct} of {len(truth)} correct ({status_correct/len(truth):.1%})')
 print(f'Step-level accuracy: {correct_steps} / {total_steps} ({correct_steps/total_steps:.1%})' if total_steps else 'Step-level accuracy: 0 / 0')
 print(f'Sequence accuracy: {sequence_correct} of {len(truth)} cases ({sequence_correct/len(truth):.1%})')
 print('--- Per-case breakdown ---')
 for cid,result,mismatches in breakdown:print(f"{cid}: {result}"+(f" | {'; '.join(mismatches)}" if mismatches else ''))
 return {'status_correct':status_correct,'step_correct':correct_steps,'total_steps':total_steps,'sequence_correct':sequence_correct}
def main():run_evaluation(Path(__file__).resolve().parents[1])
if __name__=='__main__':main()
