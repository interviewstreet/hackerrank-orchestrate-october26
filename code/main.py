import os
import sys
import csv
import json
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from code.audit_agent import AuditEngine

def run_audit(ds_dir, req_path, out_path):
    start_time = time.time()
    print(f"Initializing AuditEngine with dataset at: {ds_dir}")
    engine = AuditEngine(ds_dir)
    init_time = time.time() - start_time
    print(f"AuditEngine initialized in {init_time:.2f} seconds.")

    print(f"Reading deletion requests from: {req_path}")
    with open(req_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        requests = list(r)
        
    n = len(requests)
    print(f"Processing {n} evaluation requests...")

    status_counts = {'COMPLETE': 0, 'INCOMPLETE': 0, 'NOT_APPLICABLE': 0}
    output_rows = []

    i = 0
    while i < n:
        row = requests[i]
        cid, status, steps_json = engine.audit_case(row)
        status_counts[status] = status_counts.get(status, 0) + 1
        output_rows.append({
            'case_id': cid,
            'deletion_status': status,
            'steps_json': steps_json
        })
        i += 1

    # Sort output rows by case_id numerically/alphabetically
    output_rows.sort(key=lambda x: (
        int(x['case_id'].split('_')[1]) if '_' in x['case_id'] and x['case_id'].split('_')[1].isdigit() else 0,
        x['case_id']
    ))

    print(f"Writing {len(output_rows)} audited predictions to: {out_path}")
    with open(out_path, mode='w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['case_id', 'deletion_status', 'steps_json'])
        writer.writeheader()
        writer.writerows(output_rows)

    total_time = time.time() - start_time
    print(f"Successfully generated {out_path} in {total_time:.2f} seconds.")
    print("Summary of decisions:")
    for st, count in sorted(status_counts.items()):
        print(f"  {st}: {count} ({count/n:.2%})")

if __name__ == '__main__':
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ds_dir = os.path.join(repo_root, 'dataset')
    req_path = os.path.join(ds_dir, 'deletion_requests.csv')
    out_path = os.path.join(repo_root, 'output.csv')
    run_audit(ds_dir, req_path, out_path)
