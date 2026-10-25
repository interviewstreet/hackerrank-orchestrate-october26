#!/usr/bin/env python3
"""Ghost Data Still Exists - Deletion Audit Agent."""

import csv
import json
import re
import sqlite3
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent
DATASET_DIR = REPO_ROOT / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"

DELETION_REQUESTS_FILE = DATASET_DIR / "deletion_requests.csv"
USER_IDENTITIES_FILE = DATASET_DIR / "user_identities.csv"
USER_AUDIT_LOG_FILE = DATASET_DIR / "user_audit_log.csv"
SYSTEM_ACTIVITY_FILE = DATASET_DIR / "system_activity.csv"
DELETION_RULES_FILE = DATASET_DIR / "deletion_rules.csv"
EVIDENCE_FILES_FILE = DATASET_DIR / "evidence_files.csv"
OUTPUT_FILE = REPO_ROOT / "output.csv"


class DeletionRequest:
    def __init__(self, case_id, email, requested_at, reported_status, reported_at, audit_at, request_text):
        self.case_id = case_id
        self.email = email.lower()
        self.requested_at = datetime.fromisoformat(requested_at.replace('Z', '+00:00'))
        self.reported_status = reported_status
        self.reported_at = datetime.fromisoformat(reported_at.replace('Z', '+00:00'))
        self.audit_at = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        self.request_text = request_text


class UserIdentity:
    def __init__(self, user_id, name, email, phone, email_hash, updated_at):
        self.user_id = user_id
        self.name = name
        self.email = email.lower()
        self.phone = phone
        self.email_hash = email_hash
        self.updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))


class AuditLogEntry:
    def __init__(self, audit_id, user_id, event_time, field_name, old_value, new_value):
        self.audit_id = audit_id
        self.user_id = user_id
        self.event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
        self.field_name = field_name
        self.old_value = old_value
        self.new_value = new_value


class SystemActivity:
    def __init__(self, activity_id, event_time, event_type, source_system, target_system, resource_id, reported_result, details):
        self.activity_id = activity_id
        self.event_time = datetime.fromisoformat(event_time.replace('Z', '+00:00'))
        self.event_type = event_type
        self.source_system = source_system
        self.target_system = target_system
        self.resource_id = resource_id
        self.reported_result = reported_result
        self.details = details


class DeletionRule:
    def __init__(self, rule_id, data_category, condition, required_action):
        self.rule_id = rule_id
        self.data_category = data_category
        self.condition = condition
        self.required_action = required_action


class EvidenceFile:
    def __init__(self, file_id, file_path, origin, captured_at):
        self.file_id = file_id
        self.file_path = file_path
        self.origin = origin
        self.captured_at = datetime.fromisoformat(captured_at.replace('Z', '+00:00'))


class AuditStep:
    def __init__(self, step_no, phase, system_id, resource_id, operation, state, evidence_id=""):
        self.step_no = step_no
        self.phase = phase
        self.system_id = system_id
        self.resource_id = resource_id
        self.operation = operation
        self.state = state
        self.evidence_id = evidence_id

    def to_dict(self):
        return {
            "step_no": self.step_no,
            "phase": self.phase,
            "system_id": self.system_id,
            "resource_id": self.resource_id,
            "operation": self.operation,
            "state": self.state,
            "evidence_id": self.evidence_id
        }


def read_csv_with_encoding(filepath):
    for encoding in ['utf-8', 'cp1252', 'latin-1']:
        try:
            with open(filepath, 'r', encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
        return f.read()


def load_deletion_requests():
    requests = []
    content = read_csv_with_encoding(DELETION_REQUESTS_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        requests.append(DeletionRequest(**row))
    return requests


def load_user_identities():
    identities = {}
    content = read_csv_with_encoding(USER_IDENTITIES_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        identity = UserIdentity(**row)
        identities[identity.email] = identity
    return identities


def load_user_audit_log():
    entries = []
    content = read_csv_with_encoding(USER_AUDIT_LOG_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        entries.append(AuditLogEntry(**row))
    return entries


def load_system_activity():
    activities = []
    content = read_csv_with_encoding(SYSTEM_ACTIVITY_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        activities.append(SystemActivity(**row))
    return activities


def load_deletion_rules():
    rules = []
    content = read_csv_with_encoding(DELETION_RULES_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        rules.append(DeletionRule(**row))
    return rules


def load_evidence_files():
    evidence = {}
    content = read_csv_with_encoding(EVIDENCE_FILES_FILE)
    reader = csv.DictReader(content.splitlines())
    for row in reader:
        evidence[row['file_id']] = EvidenceFile(**row)
    return evidence


def is_deletion_request(request_text):
    text = request_text.lower()
    deletion_keywords = [
        'delete', 'erase', 'remove', 'close my account', 'permanent deletion',
        'account deletion', 'personal data deletion', 'suppression', 'right to be forgotten',
        'supprimer', 'eliminar', 'löschen', '削除', '삭제', 'excluir', 'удалить',
        '完全な削除', 'suppression définitive', 'permanente löschung',
        'close this account', 'close the account', 'permanent account deletion',
        'treat this message as a request for permanent account deletion',
        'would like it closed', 'want to close', 'asking you to remove my account',
        'close my account and process', 'please delete my account',
        'i would like the account associated with this address to be erased',
        'i am asking you to remove my account'
    ]
    non_deletion_keywords = [
        'access', 'correct', 'export', 'opt-out', 'marketing', 'unsubscribe',
        'download', 'portability', 'rectification', 'restriction'
    ]
    for kw in non_deletion_keywords:
        if kw in text:
            return False
    for kw in deletion_keywords:
        if kw in text:
            return True
    return False


def resolve_user_identities(email, user_identities, audit_log, audit_at):
    email = email.lower()
    current = user_identities.get(email)
    if not current:
        for entry in audit_log:
            if entry.field_name == 'email' and entry.new_value.lower() == email:
                current = user_identities.get(entry.user_id)
                if current:
                    break
            elif entry.field_name == 'email' and entry.old_value.lower() == email:
                current = user_identities.get(entry.user_id)
                if current:
                    break
    if not current:
        return {"user_id": None, "identifiers": {}}
    identifiers = {
        "user_id": current.user_id,
        "emails": {current.email},
        "names": {current.name},
        "phones": {current.phone},
        "email_hashes": {current.email_hash}
    }
    for entry in audit_log:
        if entry.user_id == current.user_id and entry.event_time <= audit_at:
            if entry.field_name == 'email':
                identifiers["emails"].add(entry.old_value.lower())
                identifiers["emails"].add(entry.new_value.lower())
            elif entry.field_name == 'name':
                identifiers["names"].add(entry.old_value)
                identifiers["names"].add(entry.new_value)
            elif entry.field_name == 'phone':
                identifiers["phones"].add(entry.old_value)
                identifiers["phones"].add(entry.new_value)
            elif entry.field_name == 'email_hash':
                identifiers["email_hashes"].add(entry.old_value)
                identifiers["email_hashes"].add(entry.new_value)
    return {"user_id": current.user_id, "identifiers": identifiers}


def parse_sql_evidence(file_path):
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        conn = sqlite3.connect(':memory:')
        conn.execute("PRAGMA journal_mode=MEMORY")
        conn.executescript(sql_content)
        cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in cursor.fetchall()]
        for table in tables:
            cursor = conn.execute("SELECT * FROM %s" % table)
            columns = [desc[0] for desc in cursor.description]
            for row in cursor.fetchall():
                record = dict(zip(columns, row))
                record['_table'] = table
                record['_source_file'] = str(file_path)
                records.append(record)
        conn.close()
    except Exception as e:
        print("Warning: Failed to parse SQL evidence %s: %s" % (file_path, e))
    return records


def parse_json_evidence(file_path):
    records = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        if 'snapshots' in data:
            for snapshot in data['snapshots']:
                data_store = snapshot.get('data_store', '')
                collection = snapshot.get('collection', '')
                captured_at = snapshot.get('captured_at', '')
                for record in snapshot.get('records', []):
                    record['_data_store'] = data_store
                    record['_collection'] = collection
                    record['_captured_at'] = captured_at
                    record['_source_file'] = str(file_path)
                    records.append(record)
        elif 'records' in data and isinstance(data.get('records'), list):
            for record in data['records']:
                record['_source_file'] = str(file_path)
                records.append(record)
        else:
            record = dict(data)
            record['_source_file'] = str(file_path)
            records.append(record)
    except Exception as e:
        print("Warning: Failed to parse JSON evidence %s: %s" % (file_path, e))
    return records


def parse_txt_evidence(file_path):
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith('#') or line.startswith('-') or line.startswith('CUSTOMER') or line.startswith('Snapshot') or line.startswith('Account and'):
                    continue
                parts = [p.strip() for p in line.split('|')]
                if len(parts) >= 6:
                    entry = {
                        '_source_file': str(file_path),
                        '_timestamp': parts[0],
                        '_system': parts[1],
                        '_resource_id': parts[2],
                        '_category': parts[3],
                        '_status': parts[4],
                        '_email': parts[5].lower() if len(parts) > 5 else '',
                        '_raw': line
                    }
                    entries.append(entry)
    except Exception as e:
        print("Warning: Failed to parse TXT evidence %s: %s" % (file_path, e))
    return entries


def parse_log_evidence(file_path):
    entries = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                entry = {'_source_file': str(file_path), '_raw': line}
                ts_match = re.match(r'(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)', line)
                if ts_match:
                    entry['_timestamp'] = ts_match.group(1)
                svc_match = re.search(r'service=(\S+)', line)
                if svc_match:
                    entry['_service'] = svc_match.group(1)
                res_match = re.search(r'resource_id=(\S+)', line)
                if res_match:
                    entry['_resource_id'] = res_match.group(1)
                evt_match = re.search(r'event=(\S+)', line)
                if evt_match:
                    entry['_event'] = evt_match.group(1)
                matched_match = re.search(r'matched_value="([^"]+)"', line)
                if matched_match:
                    entry['_matched_value'] = matched_match.group(1)
                corr_match = re.search(r'correlation_key="([^"]+)"', line)
                if corr_match:
                    entry['_correlation_key'] = corr_match.group(1)
                subj_match = re.search(r'subject_ref="([^"]+)"', line)
                if subj_match:
                    entry['_subject_ref'] = subj_match.group(1)
                lookup_match = re.search(r'lookup_key="([^"]+)"', line)
                if lookup_match:
                    entry['_lookup_key'] = lookup_match.group(1)
                subj_key_match = re.search(r'subject_key="([^"]+)"', line)
                if subj_key_match:
                    entry['_subject_key'] = subj_key_match.group(1)
                entries.append(entry)
    except Exception as e:
        print("Warning: Failed to parse log evidence %s: %s" % (file_path, e))
    return entries


def load_all_evidence(evidence_files, audit_at):
    all_records = []
    for file_id, evidence_file in evidence_files.items():
        if evidence_file.captured_at > audit_at:
            continue
        file_path = DATASET_DIR / evidence_file.file_path
        if not file_path.exists():
            continue
        ext = file_path.suffix.lower()
        if ext == '.sql':
            records = parse_sql_evidence(file_path)
        elif ext == '.json':
            records = parse_json_evidence(file_path)
        elif ext == '.log':
            records = parse_log_evidence(file_path)
        elif ext == '.txt':
            records = parse_txt_evidence(file_path)
        else:
            continue
        for record in records:
            record['_evidence_id'] = file_id
            record['_evidence_captured_at'] = evidence_file.captured_at
            all_records.append(record)
    return all_records


def match_record_to_user(record, identifiers):
    user_id = identifiers.get("user_id", "")
    emails = identifiers.get("emails", set())
    names = identifiers.get("names", set())
    phones = identifiers.get("phones", set())
    email_hashes = identifiers.get("email_hashes", set())

    for key in ['user_id', 'customer_reference', 'subject_reference', 'subject_ref']:
        val = record.get(key)
        if val and str(val) == user_id:
            return True
    for key in ['email', 'owner_email', 'lookup_key', 'correlation_key', 'subject_key', 'matched_value', '_email']:
        val = record.get(key)
        if val and str(val).lower() in emails:
            return True
    for key in ['full_name', 'display_name', 'name']:
        val = record.get(key)
        if val and str(val) in names:
            return True
    for key in ['phone']:
        val = record.get(key)
        if val and str(val) in phones:
            return True
    for key in ['email_hash']:
        val = record.get(key)
        if val and str(val) in email_hashes:
            return True

    record_json = record.get('record_json', '')
    if record_json:
        try:
            parsed = json.loads(record_json)
            for key in ['user_id', 'customer_reference', 'subject_reference', 'email', 'phone', 'email_hash', 'full_name', 'display_name', 'owner_email']:
                val = parsed.get(key)
                if val:
                    if key in ['email', 'owner_email'] and str(val).lower() in emails:
                        return True
                    if key == 'user_id' and str(val) == user_id:
                        return True
                    if key in ['full_name', 'display_name'] and str(val) in names:
                        return True
                    if key == 'phone' and str(val) in phones:
                        return True
                    if key == 'email_hash' and str(val) in email_hashes:
                        return True
                    if key in ['customer_reference', 'subject_reference'] and str(val) == user_id:
                        return True
        except:
            pass

    raw = record.get('_raw', '')
    if raw:
        for email in emails:
            if email in raw:
                return True
        for phone in phones:
            if phone in raw:
                return True
        for name in names:
            if name in raw:
                return True

    document = record.get('document', '')
    if document:
        try:
            if isinstance(document, str):
                parsed = json.loads(document)
            else:
                parsed = document
            for key in ['email', 'customer_reference', 'display_name']:
                val = parsed.get(key)
                if val:
                    if key == 'email' and str(val).lower() in emails:
                        return True
                    if key == 'customer_reference' and str(val) == user_id:
                        return True
                    if key == 'display_name' and str(val) in names:
                        return True
        except:
            pass

    return False


def get_record_system_and_type(record):
    system_id = ""
    resource_id = ""
    data_category = ""

    origin_system = record.get('origin_system', '')
    collection_name = record.get('collection_name', '')
    if origin_system:
        system_id = origin_system
        if collection_name == 'customer_profiles':
            data_category = 'USER_PROFILE'
        elif collection_name == 'customer_analytics_reports':
            data_category = 'ANALYTICS_PROFILE'
        elif collection_name == 'security_audit_records':
            data_category = 'SECURITY_AUDIT_LOG'
        elif collection_name == 'backup_restore_entries':
            data_category = 'BACKUP_ARCHIVE'
        elif collection_name == 'customer_search_documents':
            data_category = 'SEARCH_INDEX_ENTRY'
        elif collection_name == 'customer_exports':
            data_category = 'USER_EXPORT'
        elif collection_name == 'connector_subscriptions':
            data_category = 'SECONDARY_IDENTIFIER'
        elif collection_name == 'support_records':
            data_category = 'SUPPORT_MESSAGE'
        elif collection_name == 'snapshot_scope':
            data_category = 'CACHE_ENTRY'

    data_store = record.get('_data_store', '')
    if data_store and not system_id:
        if data_store == 'account_service':
            system_id = 'account_service'
            data_category = 'USER_PROFILE'
        elif data_store == 'analytics_platform':
            system_id = 'analytics_platform'
            data_category = 'ANALYTICS_PROFILE'
        elif data_store == 'search_service':
            system_id = 'search_service'
            data_category = 'SEARCH_INDEX_ENTRY'
        elif data_store == 'backup_service':
            system_id = 'backup_service'
            data_category = 'BACKUP_ARCHIVE'
        elif data_store == 'export_service':
            system_id = 'export_service'
            data_category = 'USER_EXPORT'
        elif data_store == 'integration_service':
            system_id = 'integration_service'
            data_category = 'SECONDARY_IDENTIFIER'
        elif data_store == 'security_service':
            system_id = 'security_service'
            data_category = 'SECURITY_AUDIT_LOG'

    txt_system = record.get('_system', '')
    txt_category = record.get('_category', '')
    if txt_system and not system_id:
        system_id = txt_system
        if txt_category == 'USER_PROFILE':
            data_category = 'USER_PROFILE'
        elif txt_category == 'ANALYTICS_PROFILE':
            data_category = 'ANALYTICS_PROFILE'
        elif txt_category == 'SECURITY_AUDIT_LOG':
            data_category = 'SECURITY_AUDIT_LOG'
        elif txt_category == 'BACKUP_ARCHIVE':
            data_category = 'BACKUP_ARCHIVE'
        elif txt_category == 'SEARCH_INDEX_ENTRY':
            data_category = 'SEARCH_INDEX_ENTRY'
        elif txt_category == 'USER_EXPORT':
            data_category = 'USER_EXPORT'
        elif txt_category == 'DATA_FLOW':
            data_category = 'SECONDARY_IDENTIFIER'
        elif txt_category == 'SUPPORT_MESSAGE' or txt_category == 'SUPPORT_ATTACHMENT':
            data_category = 'SUPPORT_MESSAGE'

    table = record.get('_table', '')
    if table and not system_id:
        if 'customer_profiles' in table:
            system_id = 'account_service'
            data_category = 'USER_PROFILE'
        elif 'analytics' in table.lower():
            system_id = 'analytics_platform'
            data_category = 'ANALYTICS_PROFILE'
        elif 'audit' in table.lower():
            system_id = 'security_service'
            data_category = 'SECURITY_AUDIT_LOG'
        elif 'backup' in table.lower():
            system_id = 'backup_service'
            data_category = 'BACKUP_ARCHIVE'
        elif 'search' in table.lower():
            system_id = 'search_service'
            data_category = 'SEARCH_INDEX_ENTRY'
        elif 'export' in table.lower():
            system_id = 'export_service'
            data_category = 'USER_EXPORT'
        elif 'data_flow' in table.lower() or 'connector' in table.lower():
            system_id = 'integration_service'
            data_category = 'SECONDARY_IDENTIFIER'
        elif 'support' in table.lower():
            system_id = 'support_platform'
            data_category = 'SUPPORT_MESSAGE'
        elif 'cache' in table.lower():
            system_id = 'cache_service'
            data_category = 'CACHE_ENTRY'

    if record.get('system') == 'account_service' and record.get('record_type') == 'USER_PROFILE':
        system_id = 'account_service'
        data_category = 'USER_PROFILE'

    for key in ['resource_id', 'record_id', '_resource_id']:
        val = record.get(key)
        if val:
            resource_id = str(val)
            break

    if not system_id and record.get('_service'):
        svc = record['_service']
        if svc == 'account_service':
            system_id = 'account_service'
            data_category = 'USER_PROFILE'
        elif svc == 'search_service':
            system_id = 'search_service'
            data_category = 'SEARCH_INDEX_ENTRY'
        elif svc == 'support_platform':
            system_id = 'support_platform'
            data_category = 'SUPPORT_MESSAGE'
        elif svc == 'security_service':
            system_id = 'security_service'
            data_category = 'SECURITY_AUDIT_LOG'

    return system_id, resource_id, data_category


def get_rule_for_category(data_category, rules):
    for rule in rules:
        if rule.data_category == data_category:
            return rule
    return None


def find_account_resource_id(identifiers, evidence_records):
    """Find the account resource_id for a user from evidence records."""
    user_id = identifiers.get("user_id", "")
    emails = identifiers.get("emails", set())
    names = identifiers.get("names", set())

    for record in evidence_records:
        system_id, resource_id, data_category = get_record_system_and_type(record)
        if system_id == 'account_service' and data_category == 'USER_PROFILE' and resource_id:
            if match_record_to_user(record, identifiers):
                return resource_id
    return None


def process_case(request, user_identities, audit_log, system_activity, rules, evidence_files):
    if not is_deletion_request(request.request_text):
        return "NOT_APPLICABLE", []
    user_info = resolve_user_identities(request.email, user_identities, audit_log, request.audit_at)
    if not user_info["user_id"]:
        return "NOT_APPLICABLE", []
    evidence_records = load_all_evidence(evidence_files, request.audit_at)
    identifiers = user_info["identifiers"]
    user_id = identifiers["user_id"]

    # Find account resource_id from evidence
    account_resource_id = find_account_resource_id(identifiers, evidence_records)
    if not account_resource_id:
        # Fallback: construct from user_id
        account_resource_id = 'account_%s' % user_id.split('_')[-1] if user_id else 'unknown'

    findings = []
    for record in evidence_records:
        if match_record_to_user(record, identifiers):
            system_id, resource_id, data_category = get_record_system_and_type(record)
            evidence_id = record.get('_evidence_id', '')
            is_present = True
            account_status = record.get('account_status', '')
            result = record.get('result', '')
            rows = record.get('rows', None)
            status = record.get('_status', '')
            record_json = record.get('record_json', '')
            if record_json:
                try:
                    parsed = json.loads(record_json)
                    if not account_status:
                        account_status = parsed.get('account_status', '')
                    if not result:
                        result = parsed.get('result', '')
                except:
                    pass
            if account_status == 'DELETED' or account_status == 'deleted':
                is_present = False
            if result == 'NOT_FOUND':
                is_present = False
            if rows == 0:
                is_present = False
            if status == 'NOT_FOUND':
                is_present = False
            if is_present and resource_id:
                findings.append({
                    'system_id': system_id,
                    'resource_id': resource_id,
                    'data_category': data_category,
                    'evidence_id': evidence_id,
                    'record': record
                })
    for activity in system_activity:
        if activity.event_time > request.audit_at:
            continue
        activity_text = ("%s %s %s %s" % (str(activity.details), str(activity.resource_id), str(activity.source_system), str(activity.target_system))).lower()
        user_match = False
        for email in identifiers["emails"]:
            if email in activity_text:
                user_match = True
                break
        for phone in identifiers["phones"]:
            if phone in activity_text:
                user_match = True
                break
        if user_id and user_id in activity_text:
            user_match = True
        if user_match:
            if activity.event_type == 'SYNC_RECORD' and activity.reported_result == 'SUCCESS':
                findings.append({
                    'system_id': activity.source_system,
                    'resource_id': activity.resource_id,
                    'data_category': 'SECONDARY_IDENTIFIER',
                    'evidence_id': '',
                    'record': {'_event_type': activity.event_type, '_reported_result': activity.reported_result},
                    '_is_data_flow': True
                })
            elif activity.event_type == 'CHECK_RESTORE_ACCESS' and activity.reported_result == 'SUCCESS':
                findings.append({
                    'system_id': activity.target_system,
                    'resource_id': activity.resource_id,
                    'data_category': 'BACKUP_ARCHIVE',
                    'evidence_id': '',
                    'record': {'_event_type': activity.event_type, '_reported_result': activity.reported_result},
                    '_is_restore_risk': True
                })
    seen = set()
    unique_findings = []
    for f in findings:
        key = (f['system_id'], f['resource_id'], f.get('_is_data_flow', False), f.get('_is_restore_risk', False))
        if key not in seen:
            seen.add(key)
            unique_findings.append(f)
    steps = []
    step_no = 1
    remaining_records = [f for f in unique_findings if not f.get('_is_data_flow') and not f.get('_is_restore_risk')]
    data_flows = [f for f in unique_findings if f.get('_is_data_flow')]
    restore_risks = [f for f in unique_findings if f.get('_is_restore_risk')]
    remaining_records.sort(key=lambda f: (f['system_id'], f['resource_id']))
    data_flows.sort(key=lambda f: (f['system_id'], f['resource_id']))
    restore_risks.sort(key=lambda f: (f['system_id'], f['resource_id']))
    for f in remaining_records:
        rule = get_rule_for_category(f['data_category'], rules)
        if rule and rule.required_action == 'DELETE':
            steps.append(AuditStep(step_no, 'FINDING', f['system_id'], f['resource_id'], 'REPORT_REMAINING_RECORD', 'PRESENT', f['evidence_id']))
        elif rule and rule.required_action == 'REDACT':
            steps.append(AuditStep(step_no, 'FINDING', f['system_id'], f['resource_id'], 'REPORT_EXPOSED_PII', 'PRESENT', f['evidence_id']))
        else:
            steps.append(AuditStep(step_no, 'FINDING', f['system_id'], f['resource_id'], 'REPORT_REMAINING_RECORD', 'PRESENT', f['evidence_id']))
        step_no += 1
    for f in data_flows:
        steps.append(AuditStep(step_no, 'FINDING', f['system_id'], f['resource_id'], 'REPORT_ACTIVE_DATA_FLOW', 'ACTIVE', f['evidence_id']))
        step_no += 1
    for f in restore_risks:
        steps.append(AuditStep(step_no, 'FINDING', f['system_id'], f['resource_id'], 'REPORT_RESTORE_RISK', 'ACTIVE', f['evidence_id']))
        step_no += 1
    remaining_records.sort(key=lambda f: (f['system_id'], f['resource_id']))
    data_flows.sort(key=lambda f: (f['system_id'], f['resource_id']))
    restore_risks.sort(key=lambda f: (f['system_id'], f['resource_id']))
    for f in remaining_records:
        rule = get_rule_for_category(f['data_category'], rules)
        if rule and rule.required_action == 'DELETE':
            steps.append(AuditStep(step_no, 'REMEDIATION', f['system_id'], f['resource_id'], 'DELETE_RECORD', 'ABSENT', ''))
        elif rule and rule.required_action == 'REDACT':
            steps.append(AuditStep(step_no, 'REMEDIATION', f['system_id'], f['resource_id'], 'REDACT_RECORD', 'REDACTED', ''))
        elif rule and rule.required_action == 'ANONYMIZE':
            steps.append(AuditStep(step_no, 'REMEDIATION', f['system_id'], f['resource_id'], 'ANONYMIZE_RECORD', 'ANONYMIZED', ''))
        step_no += 1
    for f in data_flows:
        steps.append(AuditStep(step_no, 'REMEDIATION', f['system_id'], f['resource_id'], 'DISABLE_DATA_FLOW', 'DISABLED', ''))
        step_no += 1
    for f in restore_risks:
        steps.append(AuditStep(step_no, 'REMEDIATION', f['system_id'], f['resource_id'], 'BLOCK_RESTORE', 'BLOCKED', ''))
        step_no += 1
    steps.append(AuditStep(step_no, 'VERIFICATION', 'account_service', account_resource_id, 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
    step_no += 1
    remaining_records.sort(key=lambda f: (f['system_id'], f['resource_id']))
    for f in remaining_records:
        rule = get_rule_for_category(f['data_category'], rules)
        if rule and rule.required_action == 'DELETE':
            steps.append(AuditStep(step_no, 'VERIFICATION', f['system_id'], f['resource_id'], 'VERIFY_RECORD_ABSENT', 'ABSENT', ''))
        elif rule and rule.required_action == 'REDACT':
            steps.append(AuditStep(step_no, 'VERIFICATION', f['system_id'], f['resource_id'], 'VERIFY_RECORD_REDACTED', 'REDACTED', ''))
        elif rule and rule.required_action == 'ANONYMIZE':
            steps.append(AuditStep(step_no, 'VERIFICATION', f['system_id'], f['resource_id'], 'VERIFY_RECORD_ANONYMIZED', 'ANONYMIZED', ''))
        step_no += 1
    for record in evidence_records:
        if match_record_to_user(record, identifiers):
            system_id, resource_id, data_category = get_record_system_and_type(record)
            if data_category == 'SECURITY_AUDIT_LOG':
                steps.append(AuditStep(step_no, 'VERIFICATION', system_id, resource_id, 'VERIFY_RECORD_PRESENT', 'PRESENT', ''))
                step_no += 1
    for f in data_flows:
        steps.append(AuditStep(step_no, 'VERIFICATION', f['system_id'], f['resource_id'], 'VERIFY_DATA_FLOW_DISABLED', 'DISABLED', ''))
        step_no += 1
    for f in restore_risks:
        steps.append(AuditStep(step_no, 'VERIFICATION', f['system_id'], f['resource_id'], 'VERIFY_RESTORE_BLOCKED', 'BLOCKED', ''))
        step_no += 1
    if not unique_findings:
        deletion_status = "COMPLETE"
        verify_steps = [s for s in steps if s.phase == 'VERIFICATION']
        steps = verify_steps
        cited_evidence = set()
        for record in evidence_records:
            if match_record_to_user(record, identifiers):
                eid = record.get('_evidence_id', '')
                if eid:
                    cited_evidence.add(eid)
        if not cited_evidence:
            for record in evidence_records:
                system_id, _, _ = get_record_system_and_type(record)
                if system_id == 'account_service':
                    eid = record.get('_evidence_id', '')
                    if eid:
                        cited_evidence.add(eid)
        if cited_evidence:
            default_evidence = sorted(cited_evidence, key=lambda e: evidence_files[e].captured_at)[-1]
        else:
            default_evidence = ''
        for s in steps:
            if not s.evidence_id:
                s.evidence_id = default_evidence
        for i, s in enumerate(steps):
            s.step_no = i + 1
    else:
        deletion_status = "INCOMPLETE"
    return deletion_status, steps


def main():
    print("Loading dataset...")
    deletion_requests = load_deletion_requests()
    user_identities = load_user_identities()
    audit_log = load_user_audit_log()
    system_activity = load_system_activity()
    rules = load_deletion_rules()
    evidence_files = load_evidence_files()
    print("Loaded %d deletion requests" % len(deletion_requests))
    print("Loaded %d user identities" % len(user_identities))
    print("Loaded %d audit log entries" % len(audit_log))
    print("Loaded %d system activities" % len(system_activity))
    print("Loaded %d deletion rules" % len(rules))
    print("Loaded %d evidence files" % len(evidence_files))
    results = []
    for request in deletion_requests:
        print("Processing %s..." % request.case_id)
        status, steps = process_case(request, user_identities, audit_log, system_activity, rules, evidence_files)
        steps_json = json.dumps([step.to_dict() for step in steps], separators=(',', ':'))
        results.append({
            "case_id": request.case_id,
            "deletion_status": status,
            "steps_json": steps_json
        })
    results.sort(key=lambda x: x["case_id"])
    with open(OUTPUT_FILE, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=["case_id", "deletion_status", "steps_json"])
        writer.writeheader()
        writer.writerows(results)
    print("Written %d results to %s" % (len(results), OUTPUT_FILE))


if __name__ == "__main__":
    main()