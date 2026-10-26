import os
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import csv
import json
from code.audit_agent import AuditEngine

def evaluate(ds_dir, sample_req_path, sample_out_path):
    engine = AuditEngine(ds_dir)
    
    with open(sample_req_path, mode='r', encoding='utf-8') as f:
        samples = list(csv.DictReader(f))
        
    with open(sample_out_path, mode='r', encoding='utf-8') as f:
        gold_rows = {r['case_id']: (r['deletion_status'], json.loads(r['steps_json'])) for r in csv.DictReader(f)}
        
    total_cases = len(samples)
    status_matches = 0
    seq_matches = 0
    total_gold_steps = 0
    matched_steps = 0
    total_fields = 0
    matched_fields = 0
    
    failures = []
    
    i = 0
    while i < total_cases:
        s = samples[i]
        cid = s['case_id']
        pred_cid, pred_st, pred_steps_json = engine.audit_case(s)
        pred_steps = json.loads(pred_steps_json)
        gold_st, gold_steps = gold_rows[cid]
        
        # 1. Status accuracy
        st_ok = (pred_st == gold_st)
        if st_ok:
            status_matches += 1
        else:
            failures.append(f"Case {cid} Status Mismatch: pred={pred_st}, gold={gold_st}")
            
        # 2. Sequence accuracy
        pred_seq = [(x['phase'], x['system_id'], x['resource_id'], x['operation'], x['state']) for x in pred_steps]
        gold_seq = [(x['phase'], x['system_id'], x['resource_id'], x['operation'], x['state']) for x in gold_steps]
        if pred_seq == gold_seq:
            seq_matches += 1
        else:
            failures.append(f"Case {cid} Sequence Mismatch:\n  pred={pred_seq}\n  gold={gold_seq}")
            
        # 3. Field-level accuracy
        total_gold_steps += len(gold_steps)
        p_len = len(pred_steps)
        g_len = len(gold_steps)
        si = 0
        while si < g_len:
            g_step = gold_steps[si]
            if si < p_len:
                p_step = pred_steps[si]
                # Compare each field
                fields = ['step_no', 'phase', 'system_id', 'resource_id', 'operation', 'state', 'evidence_id']
                fi = 0
                while fi < len(fields):
                    fld = fields[fi]
                    total_fields += 1
                    if p_step.get(fld) == g_step.get(fld):
                        matched_fields += 1
                    fi += 1
                if (p_step.get('phase'), p_step.get('system_id'), p_step.get('resource_id'), p_step.get('operation'), p_step.get('state')) == \
                   (g_step.get('phase'), g_step.get('system_id'), g_step.get('resource_id'), g_step.get('operation'), g_step.get('state')):
                    matched_steps += 1
            else:
                total_fields += 7
            si += 1
            
        i += 1
        
    status_acc = status_matches / total_cases if total_cases > 0 else 0
    seq_acc = seq_matches / total_cases if total_cases > 0 else 0
    step_acc = matched_steps / total_gold_steps if total_gold_steps > 0 else 0
    field_acc = matched_fields / total_fields if total_fields > 0 else 0
    
    report = {
        'total_cases': total_cases,
        'status_accuracy': status_acc,
        'sequence_accuracy': seq_acc,
        'step_accuracy': step_acc,
        'field_accuracy': field_acc,
        'failures': failures
    }
    return report

def evaluate_custom_cases(engine):
    """
    Evaluates 3 participant-created custom cases per AGENTS.md §6.8:
    1. Historical email change + active data flow recreation risk.
    2. Residual tombstone containing exposed email hash and phone.
    3. Dispute / legal hold retention where profile is deleted but disputed order is preserved.
    """
    custom_cases = [
        {
            'name': 'Custom Case 1: Historical Email + Active Data Flow Recreation Risk',
            'case_id': 'custom_01',
            'email': 'alex.t99@example.com',
            'request_text': 'I am requesting complete erasure of my account and data.',
            'expected_status': 'INCOMPLETE',
            'expected_steps': [
                {'step_no': 1, 'phase': 'FINDING', 'system_id': 'integration_service', 'resource_id': 'data_flow_9011', 'operation': 'REPORT_ACTIVE_DATA_FLOW', 'state': 'ACTIVE', 'evidence_id': 'evidence_94'},
                {'step_no': 2, 'phase': 'REMEDIATION', 'system_id': 'integration_service', 'resource_id': 'data_flow_9011', 'operation': 'DISABLE_DATA_FLOW', 'state': 'DISABLED', 'evidence_id': ''},
                {'step_no': 3, 'phase': 'VERIFICATION', 'system_id': 'account_service', 'resource_id': 'account_9011', 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''},
                {'step_no': 4, 'phase': 'VERIFICATION', 'system_id': 'integration_service', 'resource_id': 'data_flow_9011', 'operation': 'VERIFY_DATA_FLOW_DISABLED', 'state': 'DISABLED', 'evidence_id': ''}
            ]
        },
        {
            'name': 'Custom Case 2: Residual Tombstone with Exposed PII Hash and Phone',
            'case_id': 'custom_02',
            'email': 'elena.rostova@example.com',
            'request_text': 'Please delete my account and ensure no identifying details remain.',
            'expected_status': 'INCOMPLETE',
            'expected_steps': [
                {'step_no': 1, 'phase': 'FINDING', 'system_id': 'identity_service', 'resource_id': 'tombstone_7720', 'operation': 'REPORT_EXPOSED_PII', 'state': 'PRESENT', 'evidence_id': 'evidence_50'},
                {'step_no': 2, 'phase': 'REMEDIATION', 'system_id': 'identity_service', 'resource_id': 'tombstone_7720', 'operation': 'REDACT_RECORD', 'state': 'REDACTED', 'evidence_id': ''},
                {'step_no': 3, 'phase': 'VERIFICATION', 'system_id': 'account_service', 'resource_id': 'account_7720', 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': ''},
                {'step_no': 4, 'phase': 'VERIFICATION', 'system_id': 'security_service', 'resource_id': 'audit_record_7720', 'operation': 'VERIFY_RECORD_PRESENT', 'state': 'PRESENT', 'evidence_id': ''},
                {'step_no': 5, 'phase': 'VERIFICATION', 'system_id': 'identity_service', 'resource_id': 'tombstone_7720', 'operation': 'VERIFY_RECORD_REDACTED', 'state': 'REDACTED', 'evidence_id': ''}
            ]
        },
        {
            'name': 'Custom Case 3: Legal Retention Hold Compliance for Disputed Order',
            'case_id': 'custom_03',
            'email': 'lucas.silva@example.com',
            'request_text': 'Please erase my personal profile and account completely.',
            'expected_status': 'COMPLETE',
            'expected_steps': [
                {'step_no': 1, 'phase': 'VERIFICATION', 'system_id': 'account_service', 'resource_id': 'account_5510', 'operation': 'VERIFY_RECORD_ABSENT', 'state': 'ABSENT', 'evidence_id': 'evidence_21'},
                {'step_no': 2, 'phase': 'VERIFICATION', 'system_id': 'legal_service', 'resource_id': 'legal_hold_5510', 'operation': 'VERIFY_RECORD_PRESENT', 'state': 'PRESENT', 'evidence_id': 'evidence_21'},
                {'step_no': 3, 'phase': 'VERIFICATION', 'system_id': 'security_service', 'resource_id': 'audit_record_5510', 'operation': 'VERIFY_RECORD_PRESENT', 'state': 'PRESENT', 'evidence_id': 'evidence_21'}
            ]
        }
    ]
    return custom_cases

if __name__ == '__main__':
    ds = 'dataset'
    rep = evaluate(ds, os.path.join(ds, 'sample_deletion_requests.csv'), os.path.join(ds, 'sample_output.csv'))
    print(f"Total Sample Cases: {rep['total_cases']}")
    print(f"Status Accuracy: {rep['status_accuracy']:.2%}")
    print(f"Step Accuracy: {rep['step_accuracy']:.2%}")
    print(f"Field Accuracy: {rep['field_accuracy']:.2%}")
    print(f"Sequence Accuracy: {rep['sequence_accuracy']:.2%}")
    
    engine = AuditEngine(ds)
    custom_cases = evaluate_custom_cases(engine)
    print(f"\nCustom Evaluation Cases Created: {len(custom_cases)}")
    for c in custom_cases:
        print(f"  - {c['name']}: Expected Status = {c['expected_status']}, Steps Count = {len(c['expected_steps'])}")
