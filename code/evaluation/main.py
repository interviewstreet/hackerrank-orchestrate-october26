import csv
import json
import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUTPUT_CSV_PATH = os.path.join(REPO_ROOT, 'output.csv')
DATASET_DIR = os.path.join(REPO_ROOT, 'dataset')

ALLOWED_PHASES = {'FINDING', 'REMEDIATION', 'VERIFICATION'}

ALLOWED_OPS = {
    'FINDING': {
        'REPORT_REMAINING_RECORD': 'PRESENT',
        'REPORT_EXPOSED_PII': 'PRESENT',
        'REPORT_ACTIVE_DATA_FLOW': 'ACTIVE',
        'REPORT_RESTORE_RISK': 'ACTIVE'
    },
    'REMEDIATION': {
        'DISABLE_DATA_FLOW': 'DISABLED',
        'BLOCK_RESTORE': 'BLOCKED',
        'DELETE_RECORD': 'ABSENT',
        'REDACT_RECORD': 'REDACTED',
        'ANONYMIZE_RECORD': 'ANONYMIZED'
    },
    'VERIFICATION': {
        'VERIFY_RECORD_ABSENT': 'ABSENT',
        'VERIFY_RECORD_PRESENT': 'PRESENT',
        'VERIFY_RECORD_REDACTED': 'REDACTED',
        'VERIFY_RECORD_ANONYMIZED': 'ANONYMIZED',
        'VERIFY_DATA_FLOW_DISABLED': 'DISABLED',
        'VERIFY_RESTORE_BLOCKED': 'BLOCKED'
    }
}

ALLOWED_SYSTEMS = {
    'account_service',
    'search_service',
    'support_platform',
    'export_service',
    'analytics_platform',
    'security_service',
    'backup_service',
    'integration_service',
    'identity_service'
}

def validate_output():
    print("=== Running Validation on output.csv ===", flush=True)

    if not os.path.exists(OUTPUT_CSV_PATH):
        print(f"FAIL: Output file not found at {OUTPUT_CSV_PATH}", flush=True)
        return False

    with open(OUTPUT_CSV_PATH, 'r', encoding='utf-8') as f:
        reader = csv.reader(f)
        try:
            header = next(reader)
        except StopIteration:
            print("FAIL: output.csv is empty.", flush=True)
            return False

        if header != ['case_id', 'deletion_status', 'steps_json']:
            print(f"FAIL: Header mismatch. Got {header}, expected ['case_id', 'deletion_status', 'steps_json']", flush=True)
            return False

        rows = list(reader)

    print(f"Header OK. Total data rows: {len(rows)}", flush=True)

    if len(rows) != 518:
        print(f"FAIL: Expected 518 rows, got {len(rows)}", flush=True)
        return False

    with open(os.path.join(DATASET_DIR, 'deletion_requests.csv'), 'r', encoding='utf-8') as f:
        eval_requests = list(csv.DictReader(f))
    expected_case_ids = [r['case_id'] for r in eval_requests]

    actual_case_ids = [r[0] for r in rows]
    if actual_case_ids != expected_case_ids:
        print("FAIL: Case ID ordering mismatch.", flush=True)
        print(f"  Expected first 3: {expected_case_ids[:3]}, actual first 3: {actual_case_ids[:3]}", flush=True)
        return False

    with open(os.path.join(DATASET_DIR, 'evidence_files.csv'), 'r', encoding='utf-8') as f:
        evidence_manifest = {r['file_id']: r for r in csv.DictReader(f)}

    errors = []
    status_counts = {'COMPLETE': 0, 'INCOMPLETE': 0, 'NOT_APPLICABLE': 0}

    for idx, row in enumerate(rows):
        cid, status, steps_raw = row[0], row[1], row[2]

        if status not in status_counts:
            errors.append(f"Row {idx+1} ({cid}): Invalid deletion_status '{status}'")
            continue
        status_counts[status] += 1

        try:
            steps = json.loads(steps_raw)
        except Exception as e:
            errors.append(f"Row {idx+1} ({cid}): Invalid JSON in steps_json: {e}")
            continue

        if not isinstance(steps, list):
            errors.append(f"Row {idx+1} ({cid}): steps_json is not a JSON list")
            continue

        if status == 'NOT_APPLICABLE':
            if len(steps) != 0:
                errors.append(f"Row {idx+1} ({cid}): NOT_APPLICABLE must have empty steps_json, got {len(steps)} steps")
            continue

        if len(steps) == 0:
            errors.append(f"Row {idx+1} ({cid}): {status} request has empty steps_json")
            continue

        phase_order = {'FINDING': 1, 'REMEDIATION': 2, 'VERIFICATION': 3}
        last_phase_rank = 1
        expected_step_no = 1

        for s_idx, step in enumerate(steps):
            if not isinstance(step, dict):
                errors.append(f"Row {idx+1} ({cid}) step {s_idx+1}: Step is not a dict")
                break

            req_keys = {'step_no', 'phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id'}
            if set(step.keys()) != req_keys:
                errors.append(f"Row {idx+1} ({cid}) step {s_idx+1}: Invalid keys {set(step.keys())}")

            step_no = step.get('step_no')
            phase = step.get('phase')
            sys_id = step.get('system_id')
            res_id = step.get('resource_id')
            op = step.get('operation')
            st = step.get('state')
            eid = step.get('evidence_id')

            if step_no != expected_step_no:
                errors.append(f"Row {idx+1} ({cid}): Non-consecutive step_no {step_no}, expected {expected_step_no}")
            expected_step_no += 1

            if phase not in ALLOWED_PHASES:
                errors.append(f"Row {idx+1} ({cid}): Invalid phase '{phase}'")
                continue

            phase_rank = phase_order[phase]
            if phase_rank < last_phase_rank:
                errors.append(f"Row {idx+1} ({cid}): Phase ordering violation ('{phase}' after rank {last_phase_rank})")
            last_phase_rank = phase_rank

            if sys_id not in ALLOWED_SYSTEMS:
                errors.append(f"Row {idx+1} ({cid}): Invalid system_id '{sys_id}'")

            if op not in ALLOWED_OPS.get(phase, {}):
                errors.append(f"Row {idx+1} ({cid}): Invalid operation '{op}' for phase '{phase}'")
            else:
                expected_st = ALLOWED_OPS[phase][op]
                if st != expected_st:
                    errors.append(f"Row {idx+1} ({cid}): Invalid state '{st}' for operation '{op}' (expected '{expected_st}')")

            if phase == 'FINDING':
                if not eid or eid not in evidence_manifest:
                    errors.append(f"Row {idx+1} ({cid}): Finding step requires valid evidence_id, got '{eid}'")
            elif phase == 'REMEDIATION':
                if eid != "":
                    errors.append(f"Row {idx+1} ({cid}): Proposed remediation step must have empty evidence_id, got '{eid}'")
            elif phase == 'VERIFICATION':
                if status == 'COMPLETE':
                    if not eid or eid not in evidence_manifest:
                        errors.append(f"Row {idx+1} ({cid}): COMPLETE verification step requires valid evidence_id, got '{eid}'")
                elif status == 'INCOMPLETE':
                    if eid != "":
                        errors.append(f"Row {idx+1} ({cid}): INCOMPLETE future verification step must have empty evidence_id, got '{eid}'")

    print(f"Status Breakdown: {status_counts}", flush=True)
    if errors:
        print(f"FAIL: Found {len(errors)} validation errors:", flush=True)
        for err in errors[:10]:
            print(f"  {err}", flush=True)
        return False
    else:
        print("SUCCESS: All 518 rows passed all structural, schema, ordering, and evidence checks!", flush=True)
        return True

if __name__ == '__main__':
    ok = validate_output()
    if not ok:
        sys.exit(1)
