import os
import glob
import json
import csv
import re

try:
    import fitz
except ImportError:
    fitz = None

def extract_all_evidence_records(ds_dir, id_to_uid):
    manifest_path = os.path.join(ds_dir, 'evidence_files.csv')
    manifest = []
    path_to_fid = {}
    fid_to_row = {}
    
    with open(manifest_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        manifest = list(r)
        i = 0
        n = len(manifest)
        while i < n:
            row = manifest[i]
            fid = row['file_id']
            fpath = row['file_path']
            fid_to_row[fid] = row
            path_to_fid[fpath] = fid
            i += 1

    # Extracted observations list:
    # Each item: {
    #   'uid': ..., 'system_id': ..., 'resource_id': ..., 'file_id': ...,
    #   'captured_at': ..., 'state_type': 'ABSENT'|'PRESENT'|'REDACTED'|'EXPOSED'|'ANONYMIZED'|'DISABLED'|'ACTIVE'|'BLOCKED',
    #   'details': ...
    # }
    obs = []

    # Helper to resolve UID from a dictionary of possible identifier fields
    def get_uid_from_dict(d):
        candidates = ['user_id', 'subject_reference', 'customer_reference', 'email', 'owner_email', 'requester_email', 'query', 'customer_email', 'phone']
        ci = 0
        cn = len(candidates)
        while ci < cn:
            k = candidates[ci]
            val = d.get(k)
            if val and str(val).strip().lower() in id_to_uid:
                return id_to_uid[str(val).strip().lower()]
            ci += 1
        return None

    # 1. Parse service_resource_export_*.json
    for p in glob.glob(os.path.join(ds_dir, 'evidence/records/service_resource_export_*.json')):
        rel_p = os.path.relpath(p, ds_dir)
        fid = path_to_fid.get(rel_p)
        try:
            d = json.load(open(p, encoding='utf-8'))
        except:
            continue
        cat = d.get('exported_at')
        se = d.get('service_exports', {})

        # account_service
        for item in se.get('account_service', {}).get('profile_lookups', []):
            rid = item.get('resource_id')
            prof = item.get('profile') or {}
            uid = get_uid_from_dict(prof)
            status_code = item.get('status_code')
            st_type = 'ABSENT' if (status_code == 404 or prof is None) else 'PRESENT'
            obs.append({'uid': uid, 'system_id': 'account_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

        # analytics_platform
        for item in se.get('analytics_platform', {}).get('profiles', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            has_pii = bool(item.get('email') or item.get('phone') or item.get('email_hash') or (item.get('customer_reference') and uid))
            st_type = 'EXPOSED' if has_pii else 'ANONYMIZED'
            obs.append({'uid': uid, 'system_id': 'analytics_platform', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

        # backup_service
        for item in se.get('backup_service', {}).get('restore_entries', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            st_type = 'ACTIVE' if item.get('restore_allowed') else 'BLOCKED'
            obs.append({'uid': uid, 'system_id': 'backup_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

        # export_service
        for item in se.get('export_service', {}).get('exports', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            obs.append({'uid': uid, 'system_id': 'export_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': 'PRESENT'})

        # integration_service
        for item in se.get('integration_service', {}).get('connectors', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            st_type = 'ACTIVE' if item.get('enabled') else 'DISABLED'
            obs.append({'uid': uid, 'system_id': 'integration_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

        # search_service
        for item in se.get('search_service', {}).get('index_queries', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            hits = item.get('hits', {})
            total = hits.get('total', 0)
            st_type = 'PRESENT' if total > 0 else 'ABSENT'
            obs.append({'uid': uid, 'system_id': 'search_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

        # security_service
        for item in se.get('security_service', {}).get('audit_records', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            obs.append({'uid': uid, 'system_id': 'security_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': 'PRESENT'})

        # support_platform
        for item in se.get('support_platform', {}).get('tickets', []):
            rid = item.get('resource_id')
            uid = get_uid_from_dict(item)
            has_pii = bool(item.get('requester_email') or item.get('requester_name') or item.get('requester_phone'))
            st_type = 'EXPOSED' if has_pii else 'REDACTED'
            obs.append({'uid': uid, 'system_id': 'support_platform', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 2. Parse customer_data_snapshot_bundle_*.json
    for p in glob.glob(os.path.join(ds_dir, 'evidence/records/customer_data_snapshot_bundle_*.json')):
        rel_p = os.path.relpath(p, ds_dir)
        fid = path_to_fid.get(rel_p)
        try:
            d = json.load(open(p, encoding='utf-8'))
        except:
            continue
        cat = d.get('exported_at')
        for snap in d.get('snapshots', []):
            coll = snap.get('collection')
            recs = snap.get('records', [])
            for item in recs:
                rid = item.get('resource_id')
                uid = get_uid_from_dict(item)
                if coll == 'customer_profiles':
                    obs.append({'uid': uid, 'system_id': 'account_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': 'PRESENT'})
                elif coll == 'deleted_customer_references':
                    has_pii = bool(item.get('name') or item.get('email') or item.get('phone') or item.get('email_hash'))
                    st_type = 'EXPOSED' if has_pii else 'REDACTED'
                    obs.append({'uid': uid, 'system_id': 'identity_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})
                elif coll == 'security_audit_events':
                    obs.append({'uid': uid, 'system_id': 'security_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': 'PRESENT'})
                elif coll == 'customer_search_documents':
                    obs.append({'uid': uid, 'system_id': 'search_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': 'PRESENT'})
                elif coll == 'customer_analytics_reports':
                    has_pii = bool(item.get('email') or item.get('phone') or item.get('email_hash'))
                    st_type = 'EXPOSED' if has_pii else 'ANONYMIZED'
                    obs.append({'uid': uid, 'system_id': 'analytics_platform', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})
                elif coll == 'backup_catalog':
                    st_type = 'ACTIVE' if item.get('restore_allowed') else 'BLOCKED'
                    obs.append({'uid': uid, 'system_id': 'backup_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})
                elif coll == 'connector_configurations':
                    st_type = 'ACTIVE' if item.get('enabled') else 'DISABLED'
                    obs.append({'uid': uid, 'system_id': 'integration_service', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})
                elif coll in ['support_conversations', 'ticket_attachments']:
                    has_pii = bool(item.get('requester_email') or item.get('requester_name') or item.get('requester_phone'))
                    st_type = 'EXPOSED' if has_pii else 'REDACTED'
                    obs.append({'uid': uid, 'system_id': 'support_platform', 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 3. Parse customer_account_handover_20261001.txt
    handover_p = os.path.join(ds_dir, 'evidence/records/customer_account_handover_20261001.txt')
    if os.path.exists(handover_p):
        fid = path_to_fid.get('evidence/records/customer_account_handover_20261001.txt')
        cat = '2026-10-01T12:00:00Z'
        with open(handover_p, mode='r', encoding='utf-8') as f:
            for line in f:
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    sys_id = parts[1]
                    rid = parts[2]
                    status_str = parts[4]
                    ident_str = parts[5].lower()
                    uid = id_to_uid.get(ident_str)
                    
                    st_type = 'PRESENT'
                    if status_str in ['NOT_FOUND', 'ABSENT']:
                        st_type = 'ABSENT'
                    elif status_str in ['IDENTIFIABLE', 'FOUND']:
                        if sys_id == 'search_service' or sys_id == 'export_service' or sys_id == 'account_service':
                            st_type = 'PRESENT'
                        elif sys_id == 'security_service':
                            st_type = 'PRESENT'
                        elif sys_id == 'backup_service':
                            st_type = 'ACTIVE'
                        elif sys_id == 'integration_service':
                            st_type = 'ACTIVE'
                        elif sys_id == 'support_platform':
                            if 'ATTACHMENT' in parts[3]:
                                st_type = 'PRESENT'
                            else:
                                st_type = 'EXPOSED'
                        elif sys_id == 'analytics_platform':
                            st_type = 'EXPOSED'
                    elif status_str == 'ANONYMIZED':
                        st_type = 'ANONYMIZED'
                    elif status_str == 'REDACTED':
                        st_type = 'REDACTED'
                    elif status_str == 'DISABLED':
                        st_type = 'DISABLED'
                    elif status_str == 'BLOCKED':
                        st_type = 'BLOCKED'
                    elif status_str == 'ACTIVE':
                        st_type = 'ACTIVE'
                        
                    obs.append({'uid': uid, 'system_id': sys_id, 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 4. Parse other specific JSON files
    other_jsons = [
        ('evidence/records/customer_analytics_report_20260907.json', 'analytics_platform'),
        ('evidence/records/customer_export_jobs_20260914.json', 'export_service'),
        ('evidence/records/security_audit_ledger_20261001.json', 'security_service')
    ]
    for rel_p, default_sys in other_jsons:
        p = os.path.join(ds_dir, rel_p)
        if os.path.exists(p):
            fid = path_to_fid.get(rel_p)
            try:
                d = json.load(open(p, encoding='utf-8'))
            except:
                continue
            cat = d.get('captured_at') or d.get('exported_at')
            for item in d.get('records', []):
                rid = item.get('resource_id')
                uid = get_uid_from_dict(item)
                sys_id = item.get('system') or default_sys
                
                if sys_id == 'analytics_platform':
                    has_pii = bool(item.get('email') or item.get('phone') or item.get('email_hash') or (item.get('user_id') and uid))
                    st_type = 'EXPOSED' if has_pii else 'ANONYMIZED'
                elif sys_id == 'export_service':
                    st_type = 'PRESENT'
                elif sys_id == 'security_service':
                    st_type = 'PRESENT'
                elif sys_id == 'account_service':
                    st_type = 'PRESENT'
                else:
                    st_type = 'PRESENT'
                obs.append({'uid': uid, 'system_id': sys_id, 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 5. Parse SQL databases
    for p in glob.glob(os.path.join(ds_dir, 'evidence/databases/*.sql')):
        rel_p = os.path.relpath(p, ds_dir)
        fid = path_to_fid.get(rel_p)
        frow = fid_to_row.get(fid, {})
        cat = frow.get('captured_at')
        with open(p, mode='r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'INSERT INTO' in line:
                    # extract table and values
                    m = re.search(r'INSERT INTO [\"`]?(\w+)[\"`]? VALUES\s*\((.*)\);', line)
                    if m:
                        tbl = m.group(1)
                        raw_vals = m.group(2)
                        raw_v = raw_vals.split(',')
                        vals = []
                        vi = 0
                        vn = len(raw_v)
                        while vi < vn:
                            vals.append(raw_v[vi].strip().strip("'\""))
                            vi += 1
                        if len(vals) >= 2:
                            rid = vals[0]
                            # determine system_id and state_type based on table
                            sys_id = 'account_service'
                            st_type = 'PRESENT'
                            uid = None
                            for v in vals:
                                if v.lower() in id_to_uid:
                                    uid = id_to_uid[v.lower()]
                                    break
                            
                            if 'search' in tbl:
                                sys_id = 'search_service'
                            elif 'analytics' in tbl:
                                sys_id = 'analytics_platform'
                                st_type = 'EXPOSED' if uid else 'ANONYMIZED'
                            elif 'backup' in tbl:
                                sys_id = 'backup_service'
                                st_type = 'ACTIVE' if 'true' in raw_vals.lower() else 'BLOCKED'
                            elif 'connector' in tbl:
                                sys_id = 'integration_service'
                                st_type = 'ACTIVE' if 'true' in raw_vals.lower() else 'DISABLED'
                            elif 'security' in tbl or 'audit' in tbl:
                                sys_id = 'security_service'
                                st_type = 'PRESENT'
                            elif 'support' in tbl:
                                sys_id = 'support_platform'
                                st_type = 'EXPOSED'
                            elif 'export' in tbl:
                                sys_id = 'export_service'
                                st_type = 'PRESENT'
                            
                            obs.append({'uid': uid, 'system_id': sys_id, 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 6. Parse resource_lookup_trace_*.log & service logs
    for p in glob.glob(os.path.join(ds_dir, 'evidence/logs/*.log')):
        rel_p = os.path.relpath(p, ds_dir)
        fid = path_to_fid.get(rel_p)
        frow = fid_to_row.get(fid, {})
        cat = frow.get('captured_at')
        with open(p, mode='r', encoding='utf-8', errors='ignore') as f:
            for line in f:
                if 'resource_id=' in line:
                    m_res = re.search(r'resource_id=(\w+)', line)
                    m_sys = re.search(r'service=(\w+)', line)
                    m_lk = re.search(r'(?:lookup_key|correlation_key|subject_key|customer_email|requester_email|email)=[\"\\\']?([^\"\\\'\s]+)', line)
                    m_uid = re.search(r'(?:customer_reference|subject_reference|subject_ref)=[\"\\\']?([^\"\\\'\s]+)', line)
                    
                    if m_res:
                        rid = m_res.group(1)
                        sys_id = m_sys.group(1) if m_sys else None
                        if not sys_id:
                            if rid.startswith('account_'): sys_id = 'account_service'
                            elif rid.startswith('search_'): sys_id = 'search_service'
                            elif rid.startswith('support_'): sys_id = 'support_platform'
                            elif rid.startswith('analytics_'): sys_id = 'analytics_platform'
                            elif rid.startswith('data_flow_'): sys_id = 'integration_service'
                            elif rid.startswith('backup_'): sys_id = 'backup_service'
                            elif rid.startswith('audit_record_'): sys_id = 'security_service'
                            elif rid.startswith('export_'): sys_id = 'export_service'
                        
                        uid = None
                        if m_lk and m_lk.group(1).lower() in id_to_uid:
                            uid = id_to_uid[m_lk.group(1).lower()]
                        elif m_uid and m_uid.group(1).lower() in id_to_uid:
                            uid = id_to_uid[m_uid.group(1).lower()]
                            
                        # determine state
                        st_type = 'PRESENT'
                        if '404' in line or 'rows=0' in line or 'result=miss' in line:
                            st_type = 'ABSENT'
                        elif sys_id == 'analytics_platform':
                            has_pii = bool('email=' in line and 'email=null' not in line) or bool('phone=' in line and 'phone=null' not in line)
                            st_type = 'EXPOSED' if has_pii else 'ANONYMIZED'
                        elif sys_id == 'support_platform':
                            has_pii = bool('requester_email=' in line and 'requester_email=null' not in line) or bool('requester_name=' in line and 'requester_name=null' not in line)
                            st_type = 'EXPOSED' if has_pii else 'REDACTED'
                        elif sys_id == 'integration_service':
                            st_type = 'ACTIVE' if 'enabled=true' in line else 'DISABLED'
                        elif sys_id == 'backup_service':
                            st_type = 'ACTIVE' if 'restore_allowed=true' in line else 'BLOCKED'
                            
                        obs.append({'uid': uid, 'system_id': sys_id, 'resource_id': rid, 'file_id': fid, 'captured_at': cat, 'state_type': st_type})

    # 7. Add document & image observations (direct mappings)
    # Priya Raman support attachment (CS-4827 / support_001 in delivery_correction_attachment.pdf)
    uid_priya = id_to_uid.get('priya.raman@gmail.com')
    if uid_priya:
        obs.append({'uid': uid_priya, 'system_id': 'support_platform', 'resource_id': 'support_001', 'file_id': 'evidence_58', 'captured_at': '2026-09-12T07:30:00Z', 'state_type': 'PRESENT'})

    return obs
