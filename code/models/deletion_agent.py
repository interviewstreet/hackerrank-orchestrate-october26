"""
Main Deletion Audit Agent
Orchestrates the entire deletion audit process
"""
import json
from typing import Dict, List
from utils import LLMClient, data_cache
from models.classifiers import RequestClassifier
from models.identity import IdentityResolver
from models.evidence import EvidenceDiscovery
from models.policy import PolicyEngine


class DeletionAuditAgent:
    """Main agent that audits deletion requests"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
        
        # Load data
        self.user_identities = data_cache.get_user_identities()
        self.user_audit_log = data_cache.get_user_audit_log()
        self.system_activity = data_cache.get_system_activity()
        self.deletion_rules = data_cache.get_deletion_rules()
        self.evidence_manifest = data_cache.get_evidence_manifest()
        
        # Initialize sub-agents
        self.classifier = RequestClassifier(llm_client)
        self.identity_resolver = IdentityResolver(self.user_identities, self.user_audit_log)
        self.evidence_discovery = EvidenceDiscovery(
            llm_client,
            self.system_activity,
            self.evidence_manifest
        )
        self.policy_engine = PolicyEngine(llm_client, self.deletion_rules)
        
        print("✓ Deletion Audit Agent initialized")
    
    def audit_case(self, case: Dict) -> Dict:
        """
        Audit a single deletion request case
        
        Returns:
            {
                "case_id": str,
                "deletion_status": "COMPLETE" | "INCOMPLETE" | "NOT_APPLICABLE",
                "steps_json": str (JSON array)
            }
        """
        case_id = case['case_id']
        email = case['email']
        request_text = case['request_text']
        audit_at = case['audit_at']
        
        print(f"\n{'='*80}")
        print(f"Auditing {case_id}: {email}")
        print(f"{'='*80}")
        
        # Step 1: Classify the request
        print("Step 1: Classifying request...")
        classification = self.classifier.classify_request(request_text)
        print(f"  Result: {classification['request_type']} (is_deletion: {classification['is_deletion']})")
        
        if not classification['is_deletion']:
            print(f"  → NOT_APPLICABLE (not a deletion request)")
            return {
                "case_id": case_id,
                "deletion_status": "NOT_APPLICABLE",
                "steps_json": "[]"
            }
        
        # Step 2: Resolve identity
        print("Step 2: Resolving user identity...")
        identity = self.identity_resolver.resolve_identity(email, audit_at)
        
        if not identity:
            print(f"  → User not found for email: {email}")
            # If user not found, consider it complete (already deleted or never existed)
            return {
                "case_id": case_id,
                "deletion_status": "COMPLETE",
                "steps_json": "[]"
            }
        
        print(f"  User ID: {identity['user_id']}")
        print(f"  Match type: {identity['match_type']}")
        print(f"  All emails: {len(identity['all_emails'])}")
        
        # Step 3: Discover evidence
        print("Step 3: Discovering evidence...")
        evidence = self.evidence_discovery.discover_all_evidence(
            identity,
            audit_at,
            analyze_limit=15  # Limit evidence analysis to control costs
        )
        
        print(f"  Activities found: {len(evidence['activities'])}")
        print(f"  Evidence files analyzed: {len(evidence['evidence_files_analyzed'])}")
        print(f"  Findings: {len(evidence['findings'])}")
        
        # Step 4: Apply policy and generate steps
        print("Step 4: Applying deletion policy...")
        policy_result = self.policy_engine.apply_policy(
            evidence['findings'],
            evidence['activities']
        )
        
        status = policy_result['status']
        steps = policy_result.get('steps', [])
        
        print(f"  Status: {status}")
        print(f"  Steps generated: {len(steps)}")
        print(f"  Reasoning: {policy_result.get('reasoning', 'N/A')}")
        
        # Format steps as JSON string
        steps_json = json.dumps(steps)
        
        return {
            "case_id": case_id,
            "deletion_status": status,
            "steps_json": steps_json
        }
    
    def audit_all_cases(self, cases: List[Dict], start_index: int = 0, end_index: int = None) -> List[Dict]:
        """
        Audit multiple cases
        
        Args:
            cases: List of case dictionaries
            start_index: Start from this index (for resuming)
            end_index: Stop at this index (for testing subsets)
        
        Returns:
            List of results
        """
        if end_index is None:
            end_index = len(cases)
        
        results = []
        
        for i in range(start_index, end_index):
            case = cases[i]
            
            try:
                result = self.audit_case(case)
                results.append(result)
                
            except Exception as e:
                print(f"\n❌ ERROR auditing {case['case_id']}: {e}")
                # Add error result
                results.append({
                    "case_id": case['case_id'],
                    "deletion_status": "INCOMPLETE",
                    "steps_json": "[]",
                    "error": str(e)
                })
            
            # Progress indicator
            progress = ((i - start_index + 1) / (end_index - start_index)) * 100
            print(f"\nProgress: {i - start_index + 1}/{end_index - start_index} ({progress:.1f}%)")
        
        return results
