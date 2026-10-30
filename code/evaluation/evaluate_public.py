import collections, json, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import main
root=Path(__file__).resolve().parents[2]; d=root/'dataset'; ev=root/'code'/'evaluation'; read=main.read_csv
requests=read(d/'sample_deletion_requests.csv'); gold={x['case_id']:x for x in read(d/'sample_output.csv')}
ident=read(d/'user_identities.csv'); audit=read(d/'user_audit_log.csv'); manifest=read(d/'evidence_files.csv'); rules=read(d/'deletion_rules.csv'); activity=read(d/'system_activity.csv')
status_ok=seq_ok=objects=fields=0; cases=[]; expected_steps=0
def sig(x): return tuple(x.get(k,'') for k in ('phase','system_id','resource_id','operation','state','evidence_id'))
def resource(x): return (x.get('phase',''),x.get('system_id',''),x.get('resource_id',''))
def base(x): return tuple(x.get(k,'') for k in ('phase','system_id','resource_id','operation','state'))
for case in requests:
    status,pred=main.solve_case(case,ident,audit,manifest,rules,activity); expected=json.loads(gold[case['case_id']]['steps_json']); expected_steps+=len(expected)
    status_ok += status==gold[case['case_id']]['deletion_status']; seq_ok += pred==expected
    pc=collections.Counter(map(sig,pred)); ec=collections.Counter(map(sig,expected)); objects += sum((pc&ec).values())
    fields += sum(i<len(pred) and pred[i].get(k)==v.get(k) for i,v in enumerate(expected) for k in ('step_no','phase','system_id','resource_id','operation','state','evidence_id'))
    cases.append({'case_id':case['case_id'],'pred_status':status,'gold_status':gold[case['case_id']]['deletion_status'],'pred':pred,'expected':expected})
wrong=[x['case_id'] for x in cases if x['pred_status']!=x['gold_status']]
missing_extra=[]; core_mismatch=[]; evidence_mismatch=[]; ordering=[]
for x in cases:
    p=x['pred']; e=x['expected']; pc=collections.Counter(map(sig,p)); ec=collections.Counter(map(sig,e)); miss=list((ec-pc).elements()); extra=list((pc-ec).elements())
    if miss or extra: missing_extra.append({'case_id':x['case_id'],'missing':miss,'extra':extra})
    # Pair same phase/system/resource and identify operation/state differences.
    pby=collections.defaultdict(list); eby=collections.defaultdict(list)
    for z in p:pby[resource(z)].append(z)
    for z in e:eby[resource(z)].append(z)
    for key in set(pby)&set(eby):
        for a,b in zip(pby[key],eby[key]):
            changed=[k for k in ('phase','operation','state','system_id','resource_id') if a.get(k)!=b.get(k)]
            if changed: core_mismatch.append({'case_id':x['case_id'],'resource':key,'fields':changed})
    # Evidence ID mismatch where all other sequence semantics agree.
    pbc=collections.Counter(map(base,p)); ebc=collections.Counter(map(base,e))
    if pbc==ebc:
        for key in pbc:
            pe=[z.get('evidence_id','') for z in p if base(z)==key]; ee=[z.get('evidence_id','') for z in e if base(z)==key]
            if pe!=ee: evidence_mismatch.append(x['case_id']); break
    # Compare ordering of semantic step signatures shared by both arrays.
    common=pc&ec
    porder=[sig(z) for z in p for _ in range(common[sig(z)]) if common[sig(z)]>0]
    # Explicit unique shared subsequence avoids duplicate overcount.
    shared=set(common)
    porder=[sig(z) for z in p if sig(z) in shared]; eorder=[sig(z) for z in e if sig(z) in shared]
    if porder!=eorder: ordering.append(x['case_id'])
report={'metrics':{'status_correct':status_ok,'status_total':len(requests),'exact_sequences':seq_ok,'exact_total':len(requests),'exact_step_objects':objects,'expected_step_objects':expected_steps,'exact_step_fields':fields,'expected_step_fields':expected_steps*7},'incorrect_status_cases':wrong,'missing_or_extra_steps':missing_extra,'incorrect_core_fields':core_mismatch,'incorrect_evidence_id_cases':sorted(set(evidence_mismatch)),'ordering_mismatch_cases':sorted(set(ordering))}
(ev/'public_benchmark.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
m=report['metrics']; print(f"status={m['status_correct']}/{m['status_total']} arrays={m['exact_sequences']}/{m['exact_total']} objects={m['exact_step_objects']}/{m['expected_step_objects']} fields={m['exact_step_fields']}/{m['expected_step_fields']}")
