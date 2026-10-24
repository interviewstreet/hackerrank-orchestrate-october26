"""Command-line entry point for the deletion-audit pipeline."""
from __future__ import annotations
import argparse,csv,json,sys
from pathlib import Path
if __package__ in (None,''):
 sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from code.classify import classify_request
from code.decision import decide
from code.evidence import build_evidence_index
from code.identity import resolve_identity
from code.ingest import load_all
from code.planner import plan_steps
from code.temporal import filter_events
from code.validate import validate_output
class MemoryCache:
 def __init__(self):self.data={}
 def make_key(self,a,b):return a+b
 def get(self,k):return self.data.get(k)
 def set(self,k,v):self.data[k]=v
def process_case(case,data,repo_root,cache_override=None):
 identity=resolve_identity(case['email'],case['requested_at'],data)
 evidence=build_evidence_index(repo_root,data['evidence_manifest'],identity,case['audit_at'])
 events=filter_events(data['system_activity'],identity,case['audit_at'])
 classifier=lambda text,cid:classify_request(text,cid,cache_override) if cache_override else classify_request(text,cid)
 result=decide(case,identity,evidence,events,data['deletion_rules'],classifier)
 steps=plan_steps(result,identity,evidence)
 return {'case_id':case['case_id'],'deletion_status':result['status'],'steps_json':json.dumps(steps,ensure_ascii=False,separators=(',',':'))}
def run_pipeline(repo_root,cases=None,no_cache=False,sample=False):
 data=load_all(repo_root); source=data['sample_requests'] if sample else data['deletion_requests']
 wanted=set(cases or [])
 selected=[c for c in source if not wanted or c['case_id'] in wanted]
 # Explicit sample IDs are useful for smoke tests but are not part of the 518-row run.
 if wanted and not sample:
  found={c['case_id'] for c in selected}
  selected.extend(c for c in data['sample_requests'] if c['case_id'] in wanted-found)
 transient=MemoryCache() if no_cache else None
 return sorted((process_case(c,data,repo_root,transient) for c in selected),key=lambda r:r['case_id'])
def main(argv=None):
 parser=argparse.ArgumentParser();parser.add_argument('--cases',help='comma-separated case IDs');parser.add_argument('--no-cache',action='store_true');args=parser.parse_args(argv)
 root=Path(__file__).resolve().parents[1]; case_ids=[x.strip() for x in args.cases.split(',')] if args.cases else None
 rows=run_pipeline(root,case_ids,args.no_cache)
 with (root/'output.csv').open('w',encoding='utf-8',newline='') as h:
  writer=csv.DictWriter(h,fieldnames=['case_id','deletion_status','steps_json'],lineterminator='\n');writer.writeheader();writer.writerows(rows)
 errors=validate_output(rows)
 for error in errors:print(f'VALIDATION ERROR: {error}')
 print(f'Total cases processed: {len(rows)}');print(f'Validation error count: {len(errors)}')
 return 1 if errors else 0
if __name__=='__main__':raise SystemExit(main())
