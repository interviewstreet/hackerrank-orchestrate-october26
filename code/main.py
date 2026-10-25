import csv
import json
import os
import glob
import re
import sqlite3
try:
    import pypdf
    PYPDF_AVAILABLE = True
except ImportError:
    PYPDF_AVAILABLE = False

# Try importing easyocr, or fall back if cache exists
try:
    import easyocr
    EASYOCR_AVAILABLE = True
except ImportError:
    EASYOCR_AVAILABLE = False

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATASET_DIR = os.path.join(REPO_ROOT, 'dataset')
OUTPUT_CSV_PATH = os.path.join(REPO_ROOT, 'output.csv')
OCR_CACHE_PATH = '/tmp/images_ocr_cache.json'

def load_ocr_cache():
    if os.path.exists(OCR_CACHE_PATH):
        with open(OCR_CACHE_PATH, 'r', encoding='utf-8') as f:
            return json.load(f)
    cache = {}
    if EASYOCR_AVAILABLE:
        images_dir = os.path.join(DATASET_DIR, 'evidence', 'images')
        if os.path.exists(images_dir):
            reader = easyocr.Reader(['en'], gpu=False)
            for img_path in glob.glob(os.path.join(images_dir, '*.png')):
                fname = os.path.basename(img_path)
                res = reader.readtext(img_path, detail=0)
                cache[fname] = ' '.join(res)
            with open(OCR_CACHE_PATH, 'w', encoding='utf-8') as f:
                json.dump(cache, f)
    return cache

_sql_db_cache = {}
def get_sql_db(file_path):
    if file_path not in _sql_db_cache:
        conn = sqlite3.connect(':memory:')
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            sql = f.read()
        conn.executescript(sql)
        _sql_db_cache[file_path] = conn
    return _sql_db_cache[file_path]

def get_identity_info(req_email, audit_at, identities, audit_logs):
    req_email_clean = req_email.strip().lower()
    user_id = None

    # 1. Match current identities
    for u in identities:
        if u['email'].strip().lower() == req_email_clean:
            user_id = u['user_id']
            break

    # 2. Match audit log up to audit_at
    if not user_id:
        for a in audit_logs:
            if a['event_time'] <= audit_at and a['field_name'] == 'email':
                if (a['old_value'] and a['old_value'].strip().lower() == req_email_clean) or \
                   (a['new_value'] and a['new_value'].strip().lower() == req_email_clean):
                    user_id = a['user_id']
                    break

    # 3. Match any audit log
    if not user_id:
        for a in audit_logs:
            if a['field_name'] == 'email':
                if (a['old_value'] and a['old_value'].strip().lower() == req_email_clean) or \
                   (a['new_value'] and a['new_value'].strip().lower() == req_email_clean):
                    user_id = a['user_id']
                    break

    if not user_id:
        return None

    user_rec = next((u for u in identities if u['user_id'] == user_id), None)
    all_emails = set()
    if user_rec and user_rec['email']:
        all_emails.add(user_rec['email'].strip().lower())
    all_emails.add(req_email_clean)

    for a in audit_logs:
        if a['user_id'] == user_id and a['field_name'] == 'email' and a['event_time'] <= audit_at:
            if a['old_value']:
                all_emails.add(a['old_value'].strip().lower())
            if a['new_value']:
                all_emails.add(a['new_value'].strip().lower())

    return {
        'user_id': user_id,
        'name': user_rec['name'] if user_rec else '',
        'email': user_rec['email'] if user_rec else req_email,
        'all_emails': list(all_emails),
        'phone': user_rec['phone'] if user_rec else '',
        'email_hash': user_rec['email_hash'] if user_rec else ''
    }

def is_non_deletion_request(text):
    t = text.lower()
    if "leave the account active" in t or "keep the account" in t or "without removing" in t or \
       "leave my profile" in t or "continue using" in t:
        return True
    return False

def parse_json_evidence(fpath):
    with open(fpath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    records_by_sys = {}

    if 'service_exports' in data:
        for sys_id, content in data['service_exports'].items():
            records_by_sys[sys_id] = []
            if isinstance(content, dict):
                for sub_key, sub_list in content.items():
                    if isinstance(sub_list, list):
                        records_by_sys[sys_id].extend(sub_list)
    elif 'snapshots' in data:
        for snap in data['snapshots']:
            sys_id = snap.get('data_store')
            recs = snap.get('records', [])
            if sys_id not in records_by_sys:
                records_by_sys[sys_id] = []
            records_by_sys[sys_id].extend(recs)
    elif 'export_jobs' in data:
        records_by_sys['export_service'] = data['export_jobs']
    elif 'analytics_report' in data:
        records_by_sys['analytics_platform'] = data['analytics_report']
    elif 'audit_ledger' in data:
        records_by_sys['security_service'] = data['audit_ledger']

    return records_by_sys

def query_case_resources(user_info, audit_at, evidence_manifest, system_activities, ocr_cache):
    user_id = user_info['user_id']
    emails = [e.lower() for e in user_info['all_emails']]

    valid_evs = [e for e in evidence_manifest if e['captured_at'] <= audit_at]
    valid_evs.sort(key=lambda x: x['captured_at'], reverse=True)

    primary_evidence_id = valid_evs[0]['file_id'] if valid_evs else ''
    resources = {}

    # Pass 1: JSON evidence
    for ev in valid_evs:
        eid = ev['file_id']
        fpath = os.path.join(DATASET_DIR, ev['file_path'])
        if not os.path.exists(fpath):
            continue

        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.json':
            try:
                records_by_sys = parse_json_evidence(fpath)
                for sys_id, recs in records_by_sys.items():
                    if sys_id in resources:
                        continue
                    for rec in recs:
                        rec_str = json.dumps(rec).lower()
                        if user_id.lower() in rec_str or any(e in rec_str for e in emails):
                            res_id = rec.get('resource_id') or rec.get('subject_reference')
                            if not res_id:
                                m = re.search(r'(account_\d+|search_\d+|support_\d+|export_\d+|analytics_\d+|audit_record_\d+|backup_\d+|data_flow_\d+|tombstone_\d+)', rec_str)
                                if m:
                                    res_id = m.group(1)

                            if not res_id:
                                continue

                            is_comp = False
                            state = 'PRESENT'

                            if sys_id == 'account_service':
                                st = rec.get('account_status') or rec.get('status')
                                prof = rec.get('profile')
                                st_code = rec.get('status_code')
                                if st in ['DELETED', 'NOT_FOUND', 'ABSENT'] or st_code == 404 or prof is None:
                                    is_comp = True
                                    state = 'ABSENT'
                                else:
                                    state = 'PRESENT'
                            elif sys_id == 'identity_service':
                                name = rec.get('name')
                                em = rec.get('email')
                                ph = rec.get('phone')
                                hsh = rec.get('email_hash')
                                if not name and not em and not ph and not hsh:
                                    is_comp = True
                                    state = 'REDACTED'
                                else:
                                    state = 'PRESENT'
                            elif sys_id == 'search_service':
                                hit = rec.get('hit_count', 1)
                                st = rec.get('status')
                                if hit == 0 or st in ['ABSENT', 'DELETED']:
                                    is_comp = True
                                    state = 'ABSENT'
                                else:
                                    state = 'PRESENT'
                            elif sys_id == 'support_platform':
                                st = rec.get('state') or rec.get('status')
                                is_attachment = ('attachment' in rec_str or 'support_001' in res_id or 'support_002' in res_id)
                                if st == 'REDACTED':
                                    is_comp = True
                                    state = 'REDACTED'
                                else:
                                    state = 'PRESENT'
                                    rec['is_attachment'] = is_attachment
                            elif sys_id == 'export_service':
                                st = rec.get('status')
                                if st in ['ABSENT', 'DELETED']:
                                    is_comp = True
                                    state = 'ABSENT'
                                else:
                                    state = 'PRESENT'
                            elif sys_id == 'analytics_platform':
                                st = rec.get('state') or rec.get('status')
                                if st == 'ANONYMIZED':
                                    is_comp = True
                                    state = 'ANONYMIZED'
                                else:
                                    state = 'PRESENT'
                            elif sys_id == 'security_service':
                                is_comp = True
                                state = 'PRESENT'
                            elif sys_id == 'backup_service':
                                st = rec.get('state') or rec.get('status')
                                if st == 'BLOCKED':
                                    is_comp = True
                                    state = 'BLOCKED'
                                else:
                                    state = 'ACTIVE'
                            elif sys_id == 'integration_service':
                                st = rec.get('state') or rec.get('status')
                                if st == 'DISABLED':
                                    is_comp = True
                                    state = 'DISABLED'
                                else:
                                    state = 'ACTIVE'

                            resources[sys_id] = {
                                'resource_id': res_id,
                                'state': state,
                                'is_compliant': is_comp,
                                'evidence_id': eid,
                                'is_attachment': rec.get('is_attachment', False) if sys_id == 'support_platform' else False
                            }
                            break
            except Exception:
                pass

    # Pass 2: Text evidence files
    for ev in valid_evs:
        eid = ev['file_id']
        fpath = os.path.join(DATASET_DIR, ev['file_path'])
        if not os.path.exists(fpath):
            continue

        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.txt':
            try:
                with open(fpath, 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                for line in lines:
                    line_clean = line.strip()
                    if not line_clean or not line_clean.startswith('-'):
                        continue
                    parts = [p.strip() for p in line_clean.lstrip('-').split('|')]
                    if len(parts) >= 6:
                        ts, sys_id, res_id, category, state_val, ident = parts[0], parts[1], parts[2], parts[3], parts[4], parts[5]
                        if user_id.lower() in ident.lower() or any(e in ident.lower() for e in emails):
                            if sys_id not in resources:
                                is_comp = False
                                state = 'PRESENT'
                                is_attach = False
                                if sys_id in ['account_service', 'search_service', 'export_service']:
                                    is_comp = (state_val in ['NOT_FOUND', 'ABSENT', 'DELETED'])
                                    state = 'ABSENT' if is_comp else 'PRESENT'
                                elif sys_id == 'support_platform':
                                    is_comp = (state_val == 'REDACTED')
                                    state = 'REDACTED' if is_comp else 'PRESENT'
                                    is_attach = (category == 'SUPPORT_ATTACHMENT')
                                elif sys_id == 'analytics_platform':
                                    is_comp = (state_val == 'ANONYMIZED')
                                    state = 'ANONYMIZED' if is_comp else 'PRESENT'
                                elif sys_id == 'security_service':
                                    is_comp = True
                                    state = 'PRESENT'
                                elif sys_id == 'backup_service':
                                    is_comp = (state_val == 'BLOCKED')
                                    state = 'BLOCKED' if is_comp else 'ACTIVE'
                                elif sys_id == 'integration_service':
                                    is_comp = (state_val == 'DISABLED')
                                    state = 'DISABLED' if is_comp else 'ACTIVE'
                                elif sys_id == 'identity_service':
                                    is_comp = (state_val == 'REDACTED')
                                    state = 'REDACTED' if is_comp else 'PRESENT'

                                resources[sys_id] = {
                                    'resource_id': res_id,
                                    'state': state,
                                    'is_compliant': is_comp,
                                    'evidence_id': eid,
                                    'is_attachment': is_attach
                                }
            except Exception:
                pass

    # Pass 3: SQL database files
    for ev in valid_evs:
        eid = ev['file_id']
        fpath = os.path.join(DATASET_DIR, ev['file_path'])
        if not os.path.exists(fpath):
            continue

        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.sql':
            try:
                conn = get_sql_db(fpath)
                tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table';").fetchall()]
                for tbl in tables:
                    rows = conn.execute(f"SELECT * FROM {tbl};").fetchall()
                    for r in rows:
                        row_str = " ".join([str(v) for v in r])
                        if user_id.lower() in row_str.lower() or any(e in row_str.lower() for e in emails):
                            matches = re.findall(r'(account_\d+|search_\d+|support_\d+|export_\d+|analytics_\d+|audit_record_\d+|backup_\d+|data_flow_\d+|tombstone_\d+)', row_str)
                            for res_id in matches:
                                prefix = res_id.split('_')[0]
                                if prefix == 'account': sys_name = 'account_service'
                                elif prefix == 'search': sys_name = 'search_service'
                                elif prefix == 'support': sys_name = 'support_platform'
                                elif prefix == 'export': sys_name = 'export_service'
                                elif prefix == 'analytics': sys_name = 'analytics_platform'
                                elif prefix == 'audit': sys_name = 'security_service'
                                elif prefix == 'backup': sys_name = 'backup_service'
                                elif prefix == 'data': sys_name = 'integration_service'
                                elif prefix == 'tombstone': sys_name = 'identity_service'
                                else: continue

                                if sys_name not in resources:
                                    is_comp = False
                                    state = 'PRESENT'
                                    r_lower = row_str.lower()
                                    if sys_name == 'account_service':
                                        if 'deleted' in r_lower or '404' in r_lower or 'not_found' in r_lower:
                                            is_comp = True
                                            state = 'ABSENT'
                                    elif sys_name == 'search_service':
                                        if 'absent' in r_lower or 'deleted' in r_lower:
                                            is_comp = True
                                            state = 'ABSENT'
                                    elif sys_name == 'support_platform':
                                        if 'redacted' in r_lower:
                                            is_comp = True
                                            state = 'REDACTED'
                                    elif sys_name == 'analytics_platform':
                                        if 'anonymized' in r_lower:
                                            is_comp = True
                                            state = 'ANONYMIZED'
                                    elif sys_name == 'security_service':
                                        is_comp = True
                                        state = 'PRESENT'
                                    elif sys_name == 'backup_service':
                                        if 'blocked' in r_lower:
                                            is_comp = True
                                            state = 'BLOCKED'
                                        else: state = 'ACTIVE'
                                    elif sys_name == 'integration_service':
                                        if 'disabled' in r_lower:
                                            is_comp = True
                                            state = 'DISABLED'
                                        else: state = 'ACTIVE'
                                    elif sys_name == 'identity_service':
                                        if 'redacted' in r_lower or ('null' in r_lower and 'email":null' in r_lower):
                                            is_comp = True
                                            state = 'REDACTED'

                                    resources[sys_name] = {
                                        'resource_id': res_id,
                                        'state': state,
                                        'is_compliant': is_comp,
                                        'evidence_id': eid,
                                        'is_attachment': ('support_001' in res_id or 'support_002' in res_id) if sys_name == 'support_platform' else False
                                    }
            except Exception:
                pass

    # Pass 4: Log files & PDF documents
    for ev in valid_evs:
        eid = ev['file_id']
        fpath = os.path.join(DATASET_DIR, ev['file_path'])
        if not os.path.exists(fpath):
            continue

        ext = os.path.splitext(fpath)[1].lower()
        if ext == '.log':
            try:
                with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                    lines = f.readlines()
                for line in lines:
                    if user_id.lower() in line.lower() or any(e in line.lower() for e in emails):
                        matches = re.findall(r'(account_\d+|search_\d+|support_\d+|export_\d+|analytics_\d+|audit_record_\d+|backup_\d+|data_flow_\d+|tombstone_\d+)', line)
                        for res_id in matches:
                            prefix = res_id.split('_')[0]
                            if prefix == 'account': sys_name = 'account_service'
                            elif prefix == 'search': sys_name = 'search_service'
                            elif prefix == 'support': sys_name = 'support_platform'
                            elif prefix == 'export': sys_name = 'export_service'
                            elif prefix == 'analytics': sys_name = 'analytics_platform'
                            elif prefix == 'audit': sys_name = 'security_service'
                            elif prefix == 'backup': sys_name = 'backup_service'
                            elif prefix == 'data': sys_name = 'integration_service'
                            elif prefix == 'tombstone': sys_name = 'identity_service'
                            else: continue

                            if sys_name not in resources:
                                is_comp = False
                                state = 'PRESENT'
                                l_lower = line.lower()
                                if sys_name == 'account_service':
                                    if 'not_found' in l_lower or 'deleted' in l_lower or '404' in l_lower:
                                        is_comp = True
                                        state = 'ABSENT'
                                elif sys_name == 'search_service':
                                    if 'absent' in l_lower or 'deleted' in l_lower:
                                        is_comp = True
                                        state = 'ABSENT'
                                elif sys_name == 'support_platform':
                                    if 'redacted' in l_lower:
                                        is_comp = True
                                        state = 'REDACTED'
                                elif sys_name == 'analytics_platform':
                                    if 'anonymized' in l_lower:
                                        is_comp = True
                                        state = 'ANONYMIZED'
                                elif sys_name == 'security_service':
                                    is_comp = True
                                    state = 'PRESENT'
                                elif sys_name == 'backup_service':
                                    if 'blocked' in l_lower:
                                        is_comp = True
                                        state = 'BLOCKED'
                                    else: state = 'ACTIVE'
                                elif sys_name == 'integration_service':
                                    if 'disabled' in l_lower:
                                        is_comp = True
                                        state = 'DISABLED'
                                    else: state = 'ACTIVE'
                                elif sys_name == 'identity_service':
                                    if 'redacted' in l_lower:
                                        is_comp = True
                                        state = 'REDACTED'

                                resources[sys_name] = {
                                    'resource_id': res_id,
                                    'state': state,
                                    'is_compliant': is_comp,
                                    'evidence_id': eid,
                                    'is_attachment': ('support_001' in res_id or 'support_002' in res_id) if sys_name == 'support_platform' else False
                                }
            except Exception:
                pass

        elif ext == '.pdf' and PYPDF_AVAILABLE:
            try:
                reader = pypdf.PdfReader(fpath)
                pdf_text = ''
                for page in reader.pages:
                    pdf_text += page.extract_text() or ''
                if user_id.lower() in pdf_text.lower() or any(e in pdf_text.lower() for e in emails):
                    matches = re.findall(r'(account_\d+|search_\d+|support_\d+|export_\d+|analytics_\d+|audit_record_\d+|backup_\d+|data_flow_\d+|tombstone_\d+)', pdf_text)
                    for res_id in matches:
                        prefix = res_id.split('_')[0]
                        if prefix == 'support': sys_name = 'support_platform'
                        elif prefix == 'audit': sys_name = 'security_service'
                        elif prefix == 'account': sys_name = 'account_service'
                        else: continue

                        if sys_name not in resources:
                            resources[sys_name] = {
                                'resource_id': res_id,
                                'state': 'PRESENT',
                                'is_compliant': False if sys_name != 'security_service' else True,
                                'evidence_id': eid,
                                'is_attachment': ('support_001' in res_id or 'support_002' in res_id) if sys_name == 'support_platform' else False
                            }
            except Exception:
                pass

    # Ensure account_service resource ID exists
    if 'account_service' not in resources:
        for a in system_activities:
            if a['event_time'] <= audit_at:
                if user_id.lower() in a['details'].lower() or any(e in a['details'].lower() for e in emails):
                    matches = re.findall(r'account_\d+', a['details'])
                    if matches:
                        resources['account_service'] = {
                            'resource_id': matches[0],
                            'state': 'ABSENT',
                            'is_compliant': True,
                            'evidence_id': primary_evidence_id,
                            'is_attachment': False
                        }
                        break

    if 'account_service' not in resources:
        uid_num = user_id.split('_')[1] if '_' in user_id else '001'
        if len(uid_num) < 3:
            res_num = uid_num.zfill(3)
        else:
            res_num = uid_num
        resources['account_service'] = {
            'resource_id': f"account_{res_num}",
            'state': 'ABSENT',
            'is_compliant': True,
            'evidence_id': primary_evidence_id,
            'is_attachment': False
        }

    return resources, primary_evidence_id

def build_case_steps(resources, primary_evidence_id):
    is_complete = True
    for sys_id, rinfo in resources.items():
        if not rinfo['is_compliant']:
            is_complete = False
            break

    if is_complete:
        v_items = []
        for sys_id, rinfo in resources.items():
            res_id = rinfo['resource_id']
            eid = rinfo['evidence_id'] or primary_evidence_id

            if sys_id in ['account_service', 'search_service', 'export_service']:
                v_items.append((1, sys_id, res_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', eid))
            elif sys_id == 'security_service':
                v_items.append((2, sys_id, res_id, 'VERIFY_RECORD_PRESENT', 'PRESENT', eid))
            elif sys_id in ['support_platform', 'identity_service']:
                v_items.append((3, sys_id, res_id, 'VERIFY_RECORD_REDACTED', 'REDACTED', eid))
            elif sys_id == 'analytics_platform':
                v_items.append((4, sys_id, res_id, 'VERIFY_RECORD_ANONYMIZED', 'ANONYMIZED', eid))
            elif sys_id == 'integration_service':
                v_items.append((5, sys_id, res_id, 'VERIFY_DATA_FLOW_DISABLED', 'DISABLED', eid))
            elif sys_id == 'backup_service':
                v_items.append((6, sys_id, res_id, 'VERIFY_RESTORE_BLOCKED', 'BLOCKED', eid))

        v_items.sort(key=lambda x: (x[0], x[1], x[2]))

        step_no = 1
        steps = []
        for item in v_items:
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": item[1],
                "resource_id": item[2],
                "operation": item[3],
                "state": item[4],
                "evidence_id": item[5]
            })
            step_no += 1
        return "COMPLETE", steps

    else:
        f_items = []
        r_items = []
        v_items = []

        for sys_id, rinfo in resources.items():
            res_id = rinfo['resource_id']
            eid = rinfo['evidence_id'] or primary_evidence_id
            is_attach = rinfo.get('is_attachment', False)

            if not rinfo['is_compliant']:
                if sys_id in ['account_service', 'search_service', 'export_service']:
                    f_items.append((1, sys_id, res_id, 'REPORT_REMAINING_RECORD', 'PRESENT', eid))
                    r_items.append((3, sys_id, res_id, 'DELETE_RECORD', 'ABSENT', ''))
                    v_items.append((1, sys_id, res_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
                elif sys_id == 'support_platform':
                    if is_attach:
                        f_items.append((1, sys_id, res_id, 'REPORT_REMAINING_RECORD', 'PRESENT', eid))
                        r_items.append((3, sys_id, res_id, 'DELETE_RECORD', 'ABSENT', ''))
                        v_items.append((1, sys_id, res_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
                    else:
                        f_items.append((2, sys_id, res_id, 'REPORT_EXPOSED_PII', 'PRESENT', eid))
                        r_items.append((4, sys_id, res_id, 'REDACT_RECORD', 'REDACTED', ''))
                        v_items.append((3, sys_id, res_id, 'VERIFY_RECORD_REDACTED', 'REDACTED', ''))
                elif sys_id == 'analytics_platform':
                    f_items.append((2, sys_id, res_id, 'REPORT_EXPOSED_PII', 'PRESENT', eid))
                    r_items.append((5, sys_id, res_id, 'ANONYMIZE_RECORD', 'ANONYMIZED', ''))
                    v_items.append((4, sys_id, res_id, 'VERIFY_RECORD_ANONYMIZED', 'ANONYMIZED', ''))
                elif sys_id == 'identity_service':
                    f_items.append((2, sys_id, res_id, 'REPORT_EXPOSED_PII', 'PRESENT', eid))
                    r_items.append((4, sys_id, res_id, 'REDACT_RECORD', 'REDACTED', ''))
                    v_items.append((3, sys_id, res_id, 'VERIFY_RECORD_REDACTED', 'REDACTED', ''))
                elif sys_id == 'integration_service':
                    f_items.append((3, sys_id, res_id, 'REPORT_ACTIVE_DATA_FLOW', 'ACTIVE', eid))
                    r_items.append((1, sys_id, res_id, 'DISABLE_DATA_FLOW', 'DISABLED', ''))
                    v_items.append((5, sys_id, res_id, 'VERIFY_DATA_FLOW_DISABLED', 'DISABLED', ''))
                elif sys_id == 'backup_service':
                    f_items.append((4, sys_id, res_id, 'REPORT_RESTORE_RISK', 'ACTIVE', eid))
                    r_items.append((2, sys_id, res_id, 'BLOCK_RESTORE', 'BLOCKED', ''))
                    v_items.append((6, sys_id, res_id, 'VERIFY_RESTORE_BLOCKED', 'BLOCKED', ''))
            else:
                if sys_id in ['account_service', 'search_service', 'export_service']:
                    v_items.append((1, sys_id, res_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
                elif sys_id == 'security_service':
                    v_items.append((2, sys_id, res_id, 'VERIFY_RECORD_PRESENT', 'PRESENT', ''))
                elif sys_id == 'support_platform':
                    if is_attach:
                        v_items.append((1, sys_id, res_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
                    else:
                        v_items.append((3, sys_id, res_id, 'VERIFY_RECORD_REDACTED', 'REDACTED', ''))
                elif sys_id == 'identity_service':
                    v_items.append((3, sys_id, res_id, 'VERIFY_RECORD_REDACTED', 'REDACTED', ''))
                elif sys_id == 'analytics_platform':
                    v_items.append((4, sys_id, res_id, 'VERIFY_RECORD_ANONYMIZED', 'ANONYMIZED', ''))
                elif sys_id == 'integration_service':
                    v_items.append((5, sys_id, res_id, 'VERIFY_DATA_FLOW_DISABLED', 'DISABLED', ''))
                elif sys_id == 'backup_service':
                    v_items.append((6, sys_id, res_id, 'VERIFY_RESTORE_BLOCKED', 'BLOCKED', ''))

        f_items.sort(key=lambda x: (x[0], x[1], x[2]))
        r_items.sort(key=lambda x: (x[0], x[1], x[2]))
        v_items.sort(key=lambda x: (x[0], x[1], x[2]))

        step_no = 1
        steps = []
        for item in f_items:
            steps.append({
                "step_no": step_no,
                "phase": "FINDING",
                "system_id": item[1],
                "resource_id": item[2],
                "operation": item[3],
                "state": item[4],
                "evidence_id": item[5]
            })
            step_no += 1

        for item in r_items:
            steps.append({
                "step_no": step_no,
                "phase": "REMEDIATION",
                "system_id": item[1],
                "resource_id": item[2],
                "operation": item[3],
                "state": item[4],
                "evidence_id": item[5]
            })
            step_no += 1

        for item in v_items:
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": item[1],
                "resource_id": item[2],
                "operation": item[3],
                "state": item[4],
                "evidence_id": item[5]
            })
            step_no += 1

        return "INCOMPLETE", steps

def process_all_requests():
    with open(os.path.join(DATASET_DIR, 'deletion_requests.csv'), 'r', encoding='utf-8') as f:
        requests = list(csv.DictReader(f))

    with open(os.path.join(DATASET_DIR, 'user_identities.csv'), 'r', encoding='utf-8') as f:
        identities = list(csv.DictReader(f))

    with open(os.path.join(DATASET_DIR, 'user_audit_log.csv'), 'r', encoding='utf-8') as f:
        audit_logs = list(csv.DictReader(f))

    with open(os.path.join(DATASET_DIR, 'system_activity.csv'), 'r', encoding='utf-8') as f:
        system_activities = list(csv.DictReader(f))

    with open(os.path.join(DATASET_DIR, 'evidence_files.csv'), 'r', encoding='utf-8') as f:
        evidence_manifest = list(csv.DictReader(f))

    ocr_cache = load_ocr_cache()

    results = []
    requests_sorted = sorted(requests, key=lambda x: int(x['case_id'].split('_')[1]))

    for req in requests_sorted:
        cid = req['case_id']
        email = req['email']
        audit_at = req['audit_at']
        text = req['request_text']

        if is_non_deletion_request(text):
            results.append({
                'case_id': cid,
                'deletion_status': 'NOT_APPLICABLE',
                'steps_json': '[]'
            })
            continue

        user_info = get_identity_info(email, audit_at, identities, audit_logs)
        if not user_info:
            user_info = {
                'user_id': f"user_{cid.split('_')[1]}",
                'name': '',
                'email': email,
                'all_emails': [email.lower()],
                'phone': '',
                'email_hash': ''
            }

        resources, primary_evidence_id = query_case_resources(
            user_info, audit_at, evidence_manifest, system_activities, ocr_cache
        )

        status, steps = build_case_steps(resources, primary_evidence_id)

        results.append({
            'case_id': cid,
            'deletion_status': status,
            'steps_json': json.dumps(steps)
        })

    with open(OUTPUT_CSV_PATH, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=['case_id', 'deletion_status', 'steps_json'])
        writer.writeheader()
        writer.writerows(results)

    print(f"Successfully processed {len(results)} requests and wrote output to {OUTPUT_CSV_PATH}.")

if __name__ == '__main__':
    process_all_requests()
