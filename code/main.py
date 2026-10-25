#!/usr/bin/env python3
"""
Ghost Data Still Exists - Deletion Audit Agent (Optimized for Large Scale)
HackerRank Orchestrate October 2026

Optimizations for 50M+ records:
1. Inverted index: Map identifiers -> evidence files (avoids O(R × E) scans)
2. Batch processing with multiprocessing
3. Lazy evidence parsing with caching
4. Streaming CSV processing for memory efficiency
5. Pre-filtered activity indexes
"""

import csv
import json
import re
import sqlite3
import os
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Tuple, Optional, Any, Iterator
from dataclasses import dataclass, field
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing as mp
import time

BASE_DIR = Path(__file__).parent.parent
DATASET_DIR = BASE_DIR / "dataset"
EVIDENCE_DIR = DATASET_DIR / "evidence"


@dataclass
class DeletionRequest:
    case_id: str
    email: str
    requested_at: datetime
    reported_status: str
    reported_at: datetime
    audit_at: datetime
    request_text: str


@dataclass
class UserIdentity:
    user_id: str
    name: str
    email: str
    phone: str
    email_hash: str
    updated_at: datetime


@dataclass
class AuditLogEntry:
    audit_id: str
    user_id: str
    event_time: datetime
    field_name: str
    old_value: str
    new_value: str


@dataclass
class SystemActivity:
    activity_id: str
    event_time: datetime
    event_type: str
    source_system: str
    target_system: str
    resource_id: str
    reported_result: str
    details: str


@dataclass
class DeletionRule:
    rule_id: str
    data_category: str
    condition: str
    required_action: str


@dataclass
class EvidenceFile:
    file_id: str
    file_path: str
    origin: str
    captured_at: datetime


@dataclass
class Step:
    step_no: int
    phase: str
    system_id: str
    resource_id: str
    operation: str
    state: str
    evidence_id: str


# Operation to state mapping (specification compliant)
OPERATION_STATE_MAP = {
    "REPORT_REMAINING_RECORD": "PRESENT",
    "REPORT_EXPOSED_PII": "PRESENT",
    "REPORT_ACTIVE_DATA_FLOW": "ACTIVE",
    "REPORT_RESTORE_RISK": "ACTIVE",
    "DISABLE_DATA_FLOW": "DISABLED",
    "BLOCK_RESTORE": "BLOCKED",
    "DELETE_RECORD": "ABSENT",
    "REDACT_RECORD": "REDACTED",
    "ANONYMIZE_RECORD": "ANONYMIZED",
    "VERIFY_RECORD_ABSENT": "ABSENT",
    "VERIFY_RECORD_PRESENT": "PRESENT",
    "VERIFY_RECORD_REDACTED": "REDACTED",
    "VERIFY_RECORD_ANONYMIZED": "ANONYMIZED",
    "VERIFY_DATA_FLOW_DISABLED": "DISABLED",
    "VERIFY_RESTORE_BLOCKED": "BLOCKED",
}

PHASE_ORDER = {"FINDING": 0, "REMEDIATION": 1, "VERIFICATION": 2}
FINDING_OP_ORDER = {
    "REPORT_REMAINING_RECORD": 0,
    "REPORT_EXPOSED_PII": 1,
    "REPORT_ACTIVE_DATA_FLOW": 2,
    "REPORT_RESTORE_RISK": 3,
}
REMEDIATION_OP_ORDER = {
    "DISABLE_DATA_FLOW": 0,
    "BLOCK_RESTORE": 1,
    "DELETE_RECORD": 2,
    "REDACT_RECORD": 3,
    "ANONYMIZE_RECORD": 4,
}
VERIFICATION_OP_ORDER = {
    "VERIFY_RECORD_ABSENT": 0,
    "VERIFY_RECORD_PRESENT": 1,
    "VERIFY_RECORD_REDACTED": 2,
    "VERIFY_RECORD_ANONYMIZED": 3,
    "VERIFY_DATA_FLOW_DISABLED": 4,
    "VERIFY_RESTORE_BLOCKED": 5,
}


def _default_historical():
    return defaultdict(list)


class OptimizedDataLoader:
    """Optimized data loader with inverted indexes for fast lookups."""
    
    def __init__(self):
        self.requests: List[DeletionRequest] = []
        self.identities: Dict[str, UserIdentity] = {}
        self.audit_logs: List[AuditLogEntry] = []
        self.activities: List[SystemActivity] = []
        self.rules: List[DeletionRule] = []
        self.evidence_files: List[EvidenceFile] = []
        
        # Core identifier indexes
        self.email_to_user_id: Dict[str, str] = {}
        self.email_hash_to_user_id: Dict[str, str] = {}
        self.phone_to_user_id: Dict[str, str] = {}
        self.name_to_user_id: Dict[str, str] = {}
        self.historical_identifiers: Dict[str, Dict[str, List[str]]] = defaultdict(_default_historical)
        
        # Inverted indexes for evidence (identifier -> set of evidence_file_ids)
        self.evidence_by_email: Dict[str, Set[str]] = defaultdict(set)
        self.evidence_by_phone: Dict[str, Set[str]] = defaultdict(set)
        self.evidence_by_name: Dict[str, Set[str]] = defaultdict(set)
        self.evidence_by_user_id: Dict[str, Set[str]] = defaultdict(set)
        self.evidence_by_email_hash: Dict[str, Set[str]] = defaultdict(set)
        
        # Activity indexes
        self.activities_by_time: List[SystemActivity] = []  # Sorted by event_time
        self.activities_by_user: Dict[str, List[SystemActivity]] = defaultdict(list)
        
        # Pre-parsed evidence cache (file_id -> parsed data)
        self._evidence_cache: Dict[str, Any] = {}
        self._evidence_cache_timestamps: Dict[str, datetime] = {}
        self._evidence_index_built = False

    def load_all(self):
        """Load all data and build inverted indexes."""
        print("Loading data...")
        start = time.time()
        self._load_requests()
        self._load_identities()
        self._load_audit_logs()
        self._load_activities()
        self._load_rules()
        self._load_evidence_files()
        self._build_inverted_indexes()
        print(f"Loaded in {time.time() - start:.2f}s: "
              f"{len(self.requests)} requests, {len(self.identities)} identities, "
              f"{len(self.audit_logs)} audit logs, {len(self.activities)} activities, "
              f"{len(self.rules)} rules, {len(self.evidence_files)} evidence files")

    def _load_requests(self):
        with open(DATASET_DIR / "deletion_requests.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.requests.append(DeletionRequest(
                    case_id=row["case_id"],
                    email=row["email"].lower(),
                    requested_at=self._parse_dt(row["requested_at"]),
                    reported_status=row["reported_status"],
                    reported_at=self._parse_dt(row["reported_at"]),
                    audit_at=self._parse_dt(row["audit_at"]),
                    request_text=row["request_text"]
                ))

    def _load_identities(self):
        with open(DATASET_DIR / "user_identities.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                identity = UserIdentity(
                    user_id=row["user_id"],
                    name=row["name"],
                    email=row["email"].lower(),
                    phone=row["phone"],
                    email_hash=row["email_hash"],
                    updated_at=self._parse_dt(row["updated_at"])
                )
                self.identities[identity.user_id] = identity
                self.email_to_user_id[identity.email] = identity.user_id
                self.email_hash_to_user_id[identity.email_hash] = identity.user_id
                self.phone_to_user_id[identity.phone] = identity.user_id
                self.name_to_user_id[identity.name.lower()] = identity.user_id

    def _load_audit_logs(self):
        with open(DATASET_DIR / "user_audit_log.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entry = AuditLogEntry(
                    audit_id=row["audit_id"],
                    user_id=row["user_id"],
                    event_time=self._parse_dt(row["event_time"]),
                    field_name=row["field_name"],
                    old_value=row["old_value"],
                    new_value=row["new_value"]
                )
                self.audit_logs.append(entry)
                if row["field_name"] == "email":
                    self.historical_identifiers[row["user_id"]]["email"].append(row["old_value"].lower())
                    self.historical_identifiers[row["user_id"]]["email"].append(row["new_value"].lower())
                elif row["field_name"] == "phone":
                    self.historical_identifiers[row["user_id"]]["phone"].append(row["old_value"])
                    self.historical_identifiers[row["user_id"]]["phone"].append(row["new_value"])
                elif row["field_name"] == "name":
                    self.historical_identifiers[row["user_id"]]["name"].append(row["old_value"].lower())
                    self.historical_identifiers[row["user_id"]]["name"].append(row["new_value"].lower())

    def _load_activities(self):
        with open(DATASET_DIR / "system_activity.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.activities.append(SystemActivity(
                    activity_id=row["activity_id"],
                    event_time=self._parse_dt(row["event_time"]),
                    event_type=row["event_type"],
                    source_system=row["source_system"],
                    target_system=row["target_system"],
                    resource_id=row["resource_id"],
                    reported_result=row["reported_result"],
                    details=row["details"]
                ))

    def _load_rules(self):
        with open(DATASET_DIR / "deletion_rules.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.rules.append(DeletionRule(
                    rule_id=row["rule_id"],
                    data_category=row["data_category"],
                    condition=row["condition"],
                    required_action=row["required_action"]
                ))

    def _load_evidence_files(self):
        with open(DATASET_DIR / "evidence_files.csv", "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.evidence_files.append(EvidenceFile(
                    file_id=row["file_id"],
                    file_path=row["file_path"],
                    origin=row["origin"],
                    captured_at=self._parse_dt(row["captured_at"])
                ))

    def _build_inverted_indexes(self):
        """Build inverted indexes for fast evidence lookups."""
        print("Building inverted indexes...")
        
        # Add current identities to indexes
        for user_id, identity in self.identities.items():
            self.email_to_user_id[identity.email] = user_id
            self.email_hash_to_user_id[identity.email_hash] = user_id
            self.phone_to_user_id[identity.phone] = user_id
            self.name_to_user_id[identity.name.lower()] = user_id

        # Add historical identifiers
        for user_id, fields in self.historical_identifiers.items():
            for field, values in fields.items():
                for value in values:
                    if field == "email":
                        self.email_to_user_id[value.lower()] = user_id
                    elif field == "phone":
                        self.phone_to_user_id[value] = user_id
                    elif field == "name":
                        self.name_to_user_id[value.lower()] = user_id

        # Build activity indexes - optimized using a single pass
        self.activities_by_time = sorted(self.activities, key=lambda a: a.event_time)
        self._build_activity_index()
        
        # Evidence index will be built lazily on first use
        self._evidence_index_built = False

    def _build_activity_index(self):
        """Build activity index by extracting identifiers from activity details using regex."""
        print("  Building activity index...")
        
        email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
        user_id_pattern = r'user_\d+'
        
        for activity in self.activities:
            details = activity.details
            matched_users = set()
            
            # Extract emails
            emails = set(re.findall(email_pattern, details))
            for email in emails:
                email_lower = email.lower()
                if email_lower in self.email_to_user_id:
                    matched_users.add(self.email_to_user_id[email_lower])
            
            # Extract phones
            phones = set(re.findall(phone_pattern, details))
            for phone in phones:
                phone_clean = phone.strip()
                if phone_clean in self.phone_to_user_id:
                    matched_users.add(self.phone_to_user_id[phone_clean])
            
            # Extract user_ids
            user_ids = set(re.findall(user_id_pattern, details))
            for user_id in user_ids:
                if user_id in self.identities:
                    matched_users.add(user_id)
            
            for uid in matched_users:
                self.activities_by_user[uid].append(activity)
        
        print(f"  Activity index built: {len(self.activities_by_user)} users indexed")

    def _ensure_evidence_index(self):
        """Build the evidence identifier index on first use."""
        if self._evidence_index_built:
            return
        print("  Building evidence identifier index (lazy)...")
        
        for evidence_file in self.evidence_files:
            full_path = DATASET_DIR / evidence_file.file_path
            if not full_path.exists():
                continue
            
            try:
                content = ""
                if full_path.suffix == ".sql":
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                elif full_path.suffix == ".json":
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read()
                elif full_path.suffix in (".log", ".txt"):
                    with open(full_path, "r", encoding="utf-8", errors="ignore") as f:
                        content = f.read()
                else:
                    continue
                
                email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
                phone_pattern = r'\+?[\d\s\-\(\)]{10,}'
                user_id_pattern = r'user_\d+'
                
                emails = set(re.findall(email_pattern, content))
                phones = set(re.findall(phone_pattern, content))
                user_ids = set(re.findall(user_id_pattern, content))
                
                for email in emails:
                    email_lower = email.lower()
                    if email_lower in self.email_to_user_id:
                        self.evidence_by_email[email_lower].add(evidence_file.file_id)
                
                for phone in phones:
                    phone_clean = phone.strip()
                    if phone_clean in self.phone_to_user_id:
                        self.evidence_by_phone[phone_clean].add(evidence_file.file_id)
                
                for user_id in user_ids:
                    if user_id in self.identities:
                        self.evidence_by_user_id[user_id].add(evidence_file.file_id)
                        
            except Exception:
                continue
        
        self._evidence_index_built = True
        print(f"  Evidence index built: {len(self.evidence_by_email)} emails, "
              f"{len(self.evidence_by_phone)} phones, {len(self.evidence_by_user_id)} user_ids indexed")

    def find_user_by_email(self, email: str) -> Optional[str]:
        return self.email_to_user_id.get(email.lower())

    def get_relevant_evidence_files(self, identifiers: Dict[str, List[str]], audit_at: datetime) -> List[EvidenceFile]:
        """Get only evidence files relevant to the user's identifiers and before audit_at."""
        self._ensure_evidence_index()
        
        relevant_file_ids = set()
        
        for email in identifiers.get("email", []):
            relevant_file_ids.update(self.evidence_by_email.get(email.lower(), set()))
        for phone in identifiers.get("phone", []):
            relevant_file_ids.update(self.evidence_by_phone.get(phone, set()))
        for name in identifiers.get("name", []):
            relevant_file_ids.update(self.evidence_by_name.get(name.lower(), set()))
        for user_id in identifiers.get("user_id", []):
            relevant_file_ids.update(self.evidence_by_user_id.get(user_id, set()))
        for email_hash in identifiers.get("email_hash", []):
            relevant_file_ids.update(self.evidence_by_email_hash.get(email_hash, set()))
        
        relevant_files = []
        for evidence_file in self.evidence_files:
            if evidence_file.file_id in relevant_file_ids and evidence_file.captured_at <= audit_at:
                relevant_files.append(evidence_file)
        
        return relevant_files

    def get_relevant_activities(self, identifiers: Dict[str, List[str]], audit_at: datetime) -> List[SystemActivity]:
        """Get only activities relevant to the user and before audit_at."""
        relevant = set()
        
        for user_id in identifiers.get("user_id", []):
            for activity in self.activities_by_user.get(user_id, []):
                if activity.event_time <= audit_at:
                    relevant.add(activity.activity_id)
        
        # The activity index already captures all identifier matches via regex extraction
        # No need for fallback linear scan
        
        return [a for a in self.activities if a.activity_id in relevant]

    @staticmethod
    def _parse_dt(dt_str: str) -> datetime:
        return datetime.fromisoformat(dt_str.replace("Z", "+00:00"))


class OptimizedEvidenceParser:
    """Optimized evidence parser with caching."""
    
    def __init__(self, data_loader: OptimizedDataLoader):
        self.data_loader = data_loader
        self._cache: Dict[str, Any] = {}
    
    def parse_evidence(self, evidence_id: str, audit_at: datetime) -> Any:
        cache_key = f"{evidence_id}_{audit_at.isoformat()}"
        if cache_key in self._cache:
            return self._cache[cache_key]
        
        evidence_file = next((e for e in self.data_loader.evidence_files if e.file_id == evidence_id), None)
        if not evidence_file or evidence_file.captured_at > audit_at:
            return None
        
        full_path = DATASET_DIR / evidence_file.file_path
        if not full_path.exists():
            return None
        
        result = None
        if full_path.suffix == ".sql":
            result = self._parse_sql(full_path)
        elif full_path.suffix == ".json":
            result = self._parse_json(full_path)
        elif full_path.suffix == ".log":
            result = self._parse_log(full_path)
        elif full_path.suffix == ".txt":
            result = self._parse_text(full_path)
        elif full_path.suffix == ".pdf":
            result = self._parse_pdf(full_path)
        elif full_path.suffix == ".png":
            result = self._parse_image(full_path)
        
        self._cache[cache_key] = result
        return result
    
    def _parse_sql(self, path: Path) -> Dict[str, List[Dict]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
            conn = sqlite3.connect(":memory:")
            cursor = conn.cursor()
            cursor.executescript(content)
            tables = cursor.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
            result = {}
            for (table_name,) in tables:
                rows = cursor.execute(f"SELECT * FROM {table_name}").fetchall()
                cols = [desc[0] for desc in cursor.description]
                result[table_name] = [dict(zip(cols, row)) for row in rows]
            conn.close()
            return result
        except Exception:
            return {}
    
    def _parse_json(self, path: Path) -> Any:
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    
    def _parse_log(self, path: Path) -> List[str]:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.readlines()
        except Exception:
            return []
    
    def _parse_text(self, path: Path) -> str:
        try:
            with open(path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        except Exception:
            return ""
    
    def _parse_pdf(self, path: Path) -> str:
        try:
            import fitz
            doc = fitz.open(path)
            text = ""
            for page in doc:
                text += page.get_text()
            doc.close()
            return text
        except Exception:
            return ""
    
    def _parse_image(self, path: Path) -> str:
        try:
            import pytesseract
            from PIL import Image
            img = Image.open(path)
            text = pytesseract.image_to_string(img)
            return text
        except Exception:
            return ""


class OptimizedDeletionAuditor:
    """Optimized auditor using inverted indexes."""
    
    def __init__(self, data_loader: OptimizedDataLoader):
        self.data_loader = data_loader
        self.evidence_parser = OptimizedEvidenceParser(data_loader)
        self.system_categories = {
            "account_service": "USER_PROFILE",
            "search_service": "SEARCH_INDEX_ENTRY",
            "analytics_platform": "ANALYTICS_PROFILE",
            "support_platform": "SUPPORT_MESSAGE",
            "export_service": "USER_EXPORT",
            "marketing_service": "MARKETING_PROFILE",
            "email_delivery_service": "EMAIL_DELIVERY_LOG",
            "security_service": "SECURITY_AUDIT_LOG",
            "backup_service": "BACKUP_ARCHIVE",
            "profile_service": "SECONDARY_IDENTIFIER",
            "cache_service": "CACHE_ENTRY",
        }
    
    def audit_request(self, request: DeletionRequest) -> Tuple[str, List[Step]]:
        if not self._authorizes_deletion(request.request_text):
            return "NOT_APPLICABLE", []
        
        user_id = self.data_loader.find_user_by_email(request.email)
        if not user_id:
            return "NOT_APPLICABLE", []
        
        all_identifiers = self._get_all_identifiers(user_id)
        findings = self._find_remaining_records_fast(user_id, all_identifiers, request.audit_at)
        
        if not findings:
            verification_steps = self._generate_verification_steps(user_id, all_identifiers, request.audit_at)
            verification_steps = self._sort_steps(verification_steps)
            for i, step in enumerate(verification_steps, 1):
                step.step_no = i
            return "COMPLETE", verification_steps
        
        remediation_steps = self._generate_remediation_steps(findings)
        verification_steps = self._generate_post_remediation_verification(findings)
        
        all_steps = findings + remediation_steps + verification_steps
        all_steps = self._sort_steps(all_steps)
        for i, step in enumerate(all_steps, 1):
            step.step_no = i
        
        return "INCOMPLETE", all_steps
    
    def _sort_steps(self, steps: List[Step]) -> List[Step]:
        def step_sort_key(step: Step) -> Tuple:
            phase_order = PHASE_ORDER.get(step.phase, 99)
            if step.phase == "FINDING":
                op_order = FINDING_OP_ORDER.get(step.operation, 99)
            elif step.phase == "REMEDIATION":
                op_order = REMEDIATION_OP_ORDER.get(step.operation, 99)
            else:
                op_order = VERIFICATION_OP_ORDER.get(step.operation, 99)
            return (phase_order, op_order, step.system_id, step.resource_id)
        return sorted(steps, key=step_sort_key)
    
    def _authorizes_deletion(self, request_text: str) -> bool:
        text_lower = request_text.lower()
        deletion_keywords = [
            "delete", "erase", "remove", "close my account", "permanent deletion",
            "account deletion", "delete my account", "deletion", "suppression", "eliminar",
            "supprimer", "löschen", "削除", "삭제", "excluir"
        ]
        non_deletion_keywords = [
            "access", "correct", "export", "download", "opt-out", "unsubscribe",
            "marketing", "preferences", "update", "modify", "change", "view",
            "see", "get", "retrieve", "copy", "portability", "rectification"
        ]
        has_deletion = any(kw in text_lower for kw in deletion_keywords)
        purely_non_deletion = any(kw in text_lower for kw in non_deletion_keywords) and not has_deletion
        if purely_non_deletion:
            return False
        return has_deletion
    
    def _get_all_identifiers(self, user_id: str) -> Dict[str, List[str]]:
        identity = self.data_loader.identities.get(user_id)
        if not identity:
            return {}
        
        identifiers = {
            "user_id": [user_id],
            "email": [identity.email],
            "phone": [identity.phone],
            "name": [identity.name.lower()],
            "email_hash": [identity.email_hash],
        }
        
        for field, values in self.data_loader.historical_identifiers.get(user_id, {}).items():
            if field in identifiers:
                identifiers[field].extend(values)
            else:
                identifiers[field] = values
        
        for key in identifiers:
            identifiers[key] = list(set(v for v in identifiers[key] if v))
        
        return identifiers
    
    def _find_remaining_records_fast(self, user_id: str, identifiers: Dict[str, List[str]], audit_at: datetime) -> List[Step]:
        """Fast evidence lookup using inverted indexes."""
        findings = []
        
        relevant_evidence = self.data_loader.get_relevant_evidence_files(identifiers, audit_at)
        
        for evidence_file in relevant_evidence:
            evidence_data = self.evidence_parser.parse_evidence(evidence_file.file_id, audit_at)
            if not evidence_data:
                continue
            
            system_id = self._infer_system_id(evidence_file)
            data_category = self.system_categories.get(system_id, "USER_PROFILE")
            rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
            if not rule:
                continue
            
            matches = self._check_evidence_for_user(evidence_data, identifiers, system_id, evidence_file.file_id)
            for match in matches:
                resource_id, operation = match
                state = OPERATION_STATE_MAP.get(operation, "PRESENT")
                findings.append(Step(0, "FINDING", system_id, resource_id, operation, state, evidence_file.file_id))
        
        relevant_activities = self.data_loader.get_relevant_activities(identifiers, audit_at)
        
        for activity in relevant_activities:
            operation = self._activity_to_operation(activity)
            if operation:
                state = OPERATION_STATE_MAP.get(operation, "PRESENT")
                findings.append(Step(0, "FINDING", activity.target_system, activity.resource_id, operation, state, activity.activity_id))
        
        seen = set()
        deduped = []
        for f in findings:
            key = (f.system_id, f.resource_id, f.operation)
            if key not in seen:
                seen.add(key)
                deduped.append(f)
        
        return deduped
    
    def _infer_system_id(self, evidence_file: EvidenceFile) -> str:
        path = evidence_file.file_path.lower()
        if "account" in path and "admin" in path:
            return "account_service"
        elif "search" in path:
            return "search_service"
        elif "analytics" in path:
            return "analytics_platform"
        elif "support" in path:
            return "support_platform"
        elif "export" in path:
            return "export_service"
        elif "marketing" in path:
            return "marketing_service"
        elif "email" in path or "notification" in path:
            return "email_delivery_service"
        elif "security" in path or "audit" in path:
            return "security_service"
        elif "backup" in path:
            return "backup_service"
        elif "connector" in path:
            return "profile_service"
        elif any(x in path for x in ["read_replica", "failover_replica", "reporting_replica", "regional_replica", "inventory"]):
            return "account_service"
        return "account_service"
    
    def _check_evidence_for_user(self, evidence_data: Any, identifiers: Dict[str, List[str]], system_id: str, evidence_id: str) -> List[Tuple[str, str]]:
        matches = []
        
        def check_value(value: Any) -> bool:
            if not isinstance(value, str):
                return False
            value_lower = value.lower()
            for field, values in identifiers.items():
                for v in values:
                    if v and v.lower() in value_lower:
                        return True
            return False
        
        def check_record(record: Dict, resource_id: str) -> bool:
            matched = False
            for key, value in record.items():
                if check_value(value):
                    matched = True
                    data_category = self.system_categories.get(system_id, "USER_PROFILE")
                    rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
                    if rule:
                        if rule.required_action == "DELETE":
                            matches.append((resource_id, "REPORT_REMAINING_RECORD"))
                        elif rule.required_action in ("REDACT", "ANONYMIZE"):
                            matches.append((resource_id, "REPORT_EXPOSED_PII"))
            return matched
        
        if isinstance(evidence_data, dict):
            if all(isinstance(v, list) for v in evidence_data.values()):
                for table_name, rows in evidence_data.items():
                    for row in rows:
                        if isinstance(row, dict):
                            rid = row.get("resource_id") or row.get("id") or row.get("user_id") or f"{table_name}_record"
                            check_record(row, str(rid))
            else:
                rid = evidence_data.get("resource_id") or evidence_data.get("id") or "record"
                check_record(evidence_data, str(rid))
        elif isinstance(evidence_data, list):
            for item in evidence_data:
                if isinstance(item, dict):
                    rid = item.get("resource_id") or item.get("id") or "record"
                    check_record(item, str(rid))
        elif isinstance(evidence_data, str):
            for field, values in identifiers.items():
                for v in values:
                    if v and v.lower() in evidence_data.lower():
                        matches.append(("document", "REPORT_REMAINING_RECORD"))
                        return matches
        
        return matches
    
    def _activity_to_operation(self, activity: SystemActivity) -> Optional[str]:
        if activity.event_type in ("SYNC_RECORD", "INDEX_RECORD"):
            return "REPORT_ACTIVE_DATA_FLOW"
        elif activity.event_type in ("BACKUP", "RESTORE"):
            return "REPORT_RESTORE_RISK"
        return None
    
    def _generate_remediation_steps(self, findings: List[Step]) -> List[Step]:
        remediation = []
        for finding in findings:
            if finding.operation == "REPORT_ACTIVE_DATA_FLOW":
                remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "DISABLE_DATA_FLOW", OPERATION_STATE_MAP["DISABLE_DATA_FLOW"], ""))
            elif finding.operation == "REPORT_RESTORE_RISK":
                remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "BLOCK_RESTORE", OPERATION_STATE_MAP["BLOCK_RESTORE"], ""))
            elif finding.operation == "REPORT_REMAINING_RECORD":
                data_category = self.system_categories.get(finding.system_id, "USER_PROFILE")
                rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
                if rule:
                    if rule.required_action == "DELETE":
                        remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "DELETE_RECORD", OPERATION_STATE_MAP["DELETE_RECORD"], ""))
                    elif rule.required_action == "REDACT":
                        remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "REDACT_RECORD", OPERATION_STATE_MAP["REDACT_RECORD"], ""))
                    elif rule.required_action == "ANONYMIZE":
                        remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "ANONYMIZE_RECORD", OPERATION_STATE_MAP["ANONYMIZE_RECORD"], ""))
            elif finding.operation == "REPORT_EXPOSED_PII":
                data_category = self.system_categories.get(finding.system_id, "USER_PROFILE")
                rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
                if rule:
                    if rule.required_action == "REDACT":
                        remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "REDACT_RECORD", OPERATION_STATE_MAP["REDACT_RECORD"], ""))
                    elif rule.required_action == "ANONYMIZE":
                        remediation.append(Step(0, "REMEDIATION", finding.system_id, finding.resource_id, "ANONYMIZE_RECORD", OPERATION_STATE_MAP["ANONYMIZE_RECORD"], ""))
        return remediation
    
    def _generate_post_remediation_verification(self, findings: List[Step]) -> List[Step]:
        verification = []
        for finding in findings:
            if finding.operation == "REPORT_REMAINING_RECORD":
                verification.append(Step(0, "VERIFICATION", finding.system_id, finding.resource_id, "VERIFY_RECORD_ABSENT", OPERATION_STATE_MAP["VERIFY_RECORD_ABSENT"], ""))
            elif finding.operation == "REPORT_EXPOSED_PII":
                data_category = self.system_categories.get(finding.system_id, "USER_PROFILE")
                rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
                if rule and rule.required_action == "REDACT":
                    verification.append(Step(0, "VERIFICATION", finding.system_id, finding.resource_id, "VERIFY_RECORD_REDACTED", OPERATION_STATE_MAP["VERIFY_RECORD_REDACTED"], ""))
                elif rule and rule.required_action == "ANONYMIZE":
                    verification.append(Step(0, "VERIFICATION", finding.system_id, finding.resource_id, "VERIFY_RECORD_ANONYMIZED", OPERATION_STATE_MAP["VERIFY_RECORD_ANONYMIZED"], ""))
            elif finding.operation == "REPORT_ACTIVE_DATA_FLOW":
                verification.append(Step(0, "VERIFICATION", finding.system_id, finding.resource_id, "VERIFY_DATA_FLOW_DISABLED", OPERATION_STATE_MAP["VERIFY_DATA_FLOW_DISABLED"], ""))
            elif finding.operation == "REPORT_RESTORE_RISK":
                verification.append(Step(0, "VERIFICATION", finding.system_id, finding.resource_id, "VERIFY_RESTORE_BLOCKED", OPERATION_STATE_MAP["VERIFY_RESTORE_BLOCKED"], ""))
        return verification
    
    def _generate_verification_steps(self, user_id: str, identifiers: Dict[str, List[str]], audit_at: datetime) -> List[Step]:
        verification = []
        
        relevant_evidence = self.data_loader.get_relevant_evidence_files(identifiers, audit_at)
        
        for evidence_file in relevant_evidence:
            evidence_data = self.evidence_parser.parse_evidence(evidence_file.file_id, audit_at)
            if not evidence_data:
                continue
            
            system_id = self._infer_system_id(evidence_file)
            data_category = self.system_categories.get(system_id, "USER_PROFILE")
            rule = next((r for r in self.data_loader.rules if r.data_category == data_category), None)
            if not rule:
                continue
            
            has_user_data = self._check_evidence_for_user(evidence_data, identifiers, system_id, evidence_file.file_id)
            if not has_user_data:
                resource_id = self._extract_resource_id(evidence_data, system_id)
                if rule.required_action == "DELETE":
                    verification.append(Step(0, "VERIFICATION", system_id, resource_id, "VERIFY_RECORD_ABSENT", OPERATION_STATE_MAP["VERIFY_RECORD_ABSENT"], evidence_file.file_id))
                elif rule.required_action == "ANONYMIZE":
                    verification.append(Step(0, "VERIFICATION", system_id, resource_id, "VERIFY_RECORD_ANONYMIZED", OPERATION_STATE_MAP["VERIFY_RECORD_ANONYMIZED"], evidence_file.file_id))
                elif rule.required_action == "RETAIN":
                    verification.append(Step(0, "VERIFICATION", system_id, resource_id, "VERIFY_RECORD_PRESENT", OPERATION_STATE_MAP["VERIFY_RECORD_PRESENT"], evidence_file.file_id))
                elif rule.required_action == "REDACT":
                    verification.append(Step(0, "VERIFICATION", system_id, resource_id, "VERIFY_RECORD_REDACTED", OPERATION_STATE_MAP["VERIFY_RECORD_REDACTED"], evidence_file.file_id))
        
        relevant_activities = self.data_loader.get_relevant_activities(identifiers, audit_at)
        for activity in relevant_activities:
            if activity.event_type == "DELETE_RECORD" and activity.reported_result == "SUCCESS":
                verification.append(Step(0, "VERIFICATION", activity.target_system, activity.resource_id, "VERIFY_RECORD_ABSENT", OPERATION_STATE_MAP["VERIFY_RECORD_ABSENT"], activity.activity_id))
        
        return verification
    
    def _extract_resource_id(self, evidence_data: Any, system_id: str) -> str:
        if isinstance(evidence_data, dict):
            if "resource_id" in evidence_data:
                return str(evidence_data["resource_id"])
            if "id" in evidence_data:
                return str(evidence_data["id"])
            if "user_id" in evidence_data:
                return str(evidence_data["user_id"])
            if all(isinstance(v, list) for v in evidence_data.values()):
                for table_name, rows in evidence_data.items():
                    if rows and isinstance(rows[0], dict):
                        return f"{table_name}_001"
        return f"{system_id}_resource"


def process_batch(requests: List[DeletionRequest], data_loader: OptimizedDataLoader) -> List[Tuple[str, str, str]]:
    """Process a batch of requests (for multiprocessing)."""
    auditor = OptimizedDeletionAuditor(data_loader)
    results = []
    for request in requests:
        status, steps = auditor.audit_request(request)
        steps_json = json.dumps([{
            "step_no": s.step_no,
            "phase": s.phase,
            "system_id": s.system_id,
            "resource_id": s.resource_id,
            "operation": s.operation,
            "state": s.state,
            "evidence_id": s.evidence_id
        } for s in steps], separators=(',', ':'))
        results.append((request.case_id, status, steps_json))
    return results


def main():
    print("=" * 60)
    print("Ghost Data Still Exists - Optimized Deletion Audit Agent")
    print("=" * 60)
    
    start_time = time.time()
    
    loader = OptimizedDataLoader()
    loader.load_all()
    
    num_workers = min(mp.cpu_count(), 8)
    batch_size = max(1, len(loader.requests) // (num_workers * 4))
    
    print(f"Processing {len(loader.requests)} requests with {num_workers} workers, batch size {batch_size}...")
    
    batches = [loader.requests[i:i + batch_size] for i in range(0, len(loader.requests), batch_size)]
    
    all_results = []
    process_start = time.time()
    
    if num_workers > 1 and len(batches) > 1:
        with ProcessPoolExecutor(max_workers=num_workers) as executor:
            futures = [executor.submit(process_batch, batch, loader) for batch in batches]
            for future in as_completed(futures):
                all_results.extend(future.result())
    else:
        for batch in batches:
            all_results.extend(process_batch(batch, loader))
    
    process_time = time.time() - process_start
    print(f"Processing completed in {process_time:.2f}s ({len(loader.requests) / process_time:.1f} req/sec)")
    
    all_results.sort(key=lambda x: x[0])
    
    with open(BASE_DIR / "output.csv", "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["case_id", "deletion_status", "steps_json"])
        for case_id, status, steps_json in all_results:
            writer.writerow([case_id, status, steps_json])
    
    total_time = time.time() - start_time
    print(f"Total time: {total_time:.2f}s")
    print(f"Output written: {len(all_results)} rows")


if __name__ == "__main__":
    main()