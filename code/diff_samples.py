import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import json
from code.audit_agent import AuditEngine

def run_diff():
    ds_dir = 'dataset'
    engine = AuditEngine(ds_dir)
    
    with open(os.path.join(ds_dir, 'sample_deletion_requests.csv'), mode='r', encoding='utf-8') as f:
        samples = list(csv.DictReader(f))
        
    with open(os.path.join(ds_dir, 'sample_output.csv'), mode='r', encoding='utf-8') as f:
        gold_rows = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
        
    mismatched = []
    
    for s in samples:
        cid = s['case_id']
        pred_cid, pred_st, pred_steps_json = engine.audit_case(s)
        pred_steps = json.loads(pred_steps_json)
        gold_st, gold_steps = gold_rows[cid]
        
        pred_seq = [(x['phase'], x['system_id'], x['resource_id'], x['operation'], x['state']) for x in pred_steps]
        gold_seq = [(x['phase'], x['system_id'], x['resource_id'], x['operation'], x['state']) for x in gold_steps]
        
        if pred_seq != gold_seq or pred_steps != gold_steps:
            mismatched.append((s, pred_st, pred_steps, gold_st, gold_steps))
            
    print(f"Total Mismatched Cases: {len(mismatched)} / {len(samples)}\n" + "="*80)
    
    for s, pred_st, pred_steps, gold_st, gold_steps in mismatched:
        cid = s['case_id']
        email = s['email']
        print(f"\n>>> CASE: {cid} | Email: {email} | Status: Pred={pred_st}, Gold={gold_st}")
        print(f"    ReqAt: {s['requested_at']} | RepAt: {s['reported_at']} | AuditAt: {s['audit_at']}")
        
        pred_map = {(x['phase'], x['system_id'], x['resource_id'], x['operation']): x for x in pred_steps}
        gold_map = {(x['phase'], x['system_id'], x['resource_id'], x['operation']): x for x in gold_steps}
        
        missing = [x for k, x in gold_map.items() if k not in pred_map]
        extra = [x for k, x in pred_map.items() if k not in gold_map]
        
        field_diffs = []
        for k in gold_map:
            if k in pred_map:
                p_item = pred_map[k]
                g_item = gold_map[k]
                diffs = {}
                for fld in ['state', 'evidence_id']:
                    if p_item.get(fld) != g_item.get(fld):
                        diffs[fld] = {'pred': p_item.get(fld), 'gold': g_item.get(fld)}
                if diffs:
                    field_diffs.append((k, diffs))
                    
        # Check ordering if sets are equal
        pred_keys = [(x['phase'], x['system_id'], x['resource_id'], x['operation']) for x in pred_steps]
        gold_keys = [(x['phase'], x['system_id'], x['resource_id'], x['operation']) for x in gold_steps]
        
        if missing:
            print("  [MISSING STEPS in Pred]:")
            for m in missing:
                print(f"    - phase={m['phase']}, sys={m['system_id']}, res={m['resource_id']}, op={m['operation']}, st={m['state']}, ev={m.get('evidence_id')}")
        if extra:
            print("  [EXTRA STEPS in Pred]:")
            for e in extra:
                print(f"    + phase={e['phase']}, sys={e['system_id']}, res={e['resource_id']}, op={e['operation']}, st={e['state']}, ev={e.get('evidence_id')}")
        if field_diffs:
            print("  [FIELD MISMATCHES]:")
            for k, diff in field_diffs:
                print(f"    ~ key={k}: diffs={diff}")
        if set(pred_keys) == set(gold_keys) and pred_keys != gold_keys:
            print("  [ORDERING MISMATCH]:")
            print(f"    Pred order: {[x[1:3] for x in pred_keys]}")
            print(f"    Gold order: {[x[1:3] for x in gold_keys]}")

if __name__ == '__main__':
    run_diff()
