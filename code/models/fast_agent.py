"""
Fast Deletion Audit Agent
Optimized for speed with hybrid rule-based + LLM approach
"""
import json
import re
from typing import Dict, List
from utils import LLMClient, data_cache
from models.classifiers import RequestClassifier
from models.identity import IdentityResolver
from models.evidence_fast import FastEvidenceDiscovery


class FastDeletionAgent:
    """Faster agent using rule-based logic where possible"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        
        # Load data
        self.user_identities = data_cache.get_user_identities()
        self.user_audit_log = data_cache.get_user_audit_log()
        self.system_activity = data_cache.get_system_activity()
        self.deletion_rules = data_cache.get_deletion_rules()
        self.evidence_manifest = data_cache.get_evidence_manifest()
        
        # Initialize
        self.classifier = RequestClassifier(llm_client)
        self.identity_resolver = IdentityResolver(self.user_identities, self.user_audit_log)
        self.evidence_discovery = FastEvidenceDiscovery(
            self.system_activity,
            self.evidence_manifest
        )
        
        print("✓ Fast Deletion Agent initialized")
    
    def quick_classify(self, request_text: str) -> bool:
        """Quick rule-based classification before using LLM"""
        text_lower = request_text.lower()
        
        # Deletion keywords
        deletion_keywords = [
            'delet', 'erase', 'remove', 'close', 'cancel',
            'elimina', 'suprimir',  # Spanish
            'exclu', 'apagar',  # Portuguese
            '削除', '消去',  # Japanese
            '삭제',  # Korean
        ]
        
        # Non-deletion keywords
        non_deletion_keywords = [
            'access', 'export', 'download', 'copy', 'view',
            'correct', 'update', 'change', 'modify',
            'opt-out', 'unsubscribe', 'stop email'
        ]
        
        has_deletion = any(kw in text_lower for kw in deletion_keywords)
        has_non_deletion = any(kw in text_lower for kw in non_deletion_keywords)
        
        if has_deletion and not has_non_deletion:
            return True  # Likely deletion
        elif has_non_deletion and not has_deletion:
            return False  # Likely not deletion
        else:
            return None  # Unclear, need LLM
    
    def generate_simple_steps(
        self,
        status: str,
        user_id: str,
        deletion_activities: List[Dict],
        findings: List[Dict]
    ) -> List[Dict]:
        """Generate steps using simple rules"""
        steps = []
        step_no = 1
        
        if status == "COMPLETE":
            # Just verification steps
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": "account_service",
                "resource_id": f"account_{user_id.split('_')[1]}",
                "operation": "VERIFY_RECORD_ABSENT",
                "state": "ABSENT",
                "evidence_id": deletion_activities[0]['activity_id'] if deletion_activities else ""
            })
        else:
            # Incomplete - add findings and remediation
            for finding in findings[:5]:  # Limit findings
                steps.append({
                    "step_no": step_no,
                    "phase": "FINDING",
                    "system_id": finding.get('system_id', 'account_service'),
                    "resource_id": f"{finding.get('resource_type', 'account')}_001",
                    "operation": "REPORT_REMAINING_RECORD",
                    "state": "PRESENT",
                    "evidence_id": ""
                })
                step_no += 1
            
            # Add remediation
            for finding in findings[:5]:
                steps.append({
                    "step_no": step_no,
                    "phase": "REMEDIATION",
                    "system_id": finding.get('system_id', 'account_service'),
                    "resource_id": f"{finding.get('resource_type', 'account')}_001",
                    "operation": "DELETE_RECORD",
                    "state": "ABSENT",
                    "evidence_id": ""
                })
                step_no += 1
            
            # Add verification
            steps.append({
                "step_no": step_no,
                "phase": "VERIFICATION",
                "system_id": "account_service",
                "resource_id": f"account_{user_id.split('_')[1]}",
                "operation": "VERIFY_RECORD_ABSENT",
                "state": "ABSENT",
                "evidence_id": ""
            })
        
        return steps
    
    def audit_case(self, case: Dict) -> Dict:
        """Audit a case quickly"""
        case_id = case['case_id']
        email = case['email']
        request_text = case['request_text']
        audit_at = case['audit_at']
        
        print(f"\nAuditing {case_id}")
        
        # Quick classification
        is_deletion = self.quick_classify(request_text)
        
        if is_deletion is None:
            # Use LLM for unclear cases
            classification = self.classifier.classify_request(request_text)
            is_deletion = classification['is_deletion']
        
        if not is_deletion:
            return {
                "case_id": case_id,
                "deletion_status": "NOT_APPLICABLE",
                "steps_json": "[]"
            }
        
        # Resolve identity
        identity = self.identity_resolver.resolve_identity(email, audit_at)
        
        if not identity:
            return {
                "case_id": case_id,
                "deletion_status": "COMPLETE",
                "steps_json": "[]"
            }
        
        user_id = identity['user_id']
        
        # Fast evidence discovery
        evidence = self.evidence_discovery.discover_fast(identity, audit_at)
        
        deletion_activities = evidence['deletion_activities']
        findings = evidence['findings']
        
        # Determine status
        if deletion_activities and not findings:
            status = "COMPLETE"
        elif findings:
            status = "INCOMPLETE"
        else:
            # Unclear - default to INCOMPLETE for safety
            status = "INCOMPLETE"
        
        # Generate steps
        steps = self.generate_simple_steps(
            status,
            user_id,
            deletion_activities,
            findings
        )
        
        return {
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": json.dumps(steps)
        }
    
    def audit_all_cases(self, cases: List[Dict], start_index: int = 0, end_index: int = None) -> List[Dict]:
        """Audit multiple cases"""
        if end_index is None:
            end_index = len(cases)
        
        results = []
        
        for i in range(start_index, end_index):
            case = cases[i]
            
            try:
                result = self.audit_case(case)
                results.append(result)
                
                if (i - start_index + 1) % 10 == 0:
                    print(f"Progress: {i - start_index + 1}/{end_index - start_index}")
                    
            except Exception as e:
                print(f"ERROR {case['case_id']}: {e}")
                results.append({
                    "case_id": case['case_id'],
                    "deletion_status": "INCOMPLETE",
                    "steps_json": "[]"
                })
        
        return results
