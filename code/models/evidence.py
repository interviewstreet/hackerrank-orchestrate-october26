"""
Evidence Discovery and Analysis
Searches for user data across all evidence sources
"""
from typing import Dict, List, Set, Optional
from datetime import datetime
from utils import LLMClient, load_evidence_file


class EvidenceDiscovery:
    """Discovers and analyzes evidence of user data"""
    
    def __init__(
        self,
        llm_client: LLMClient,
        system_activity: List[Dict],
        evidence_manifest: List[Dict]
    ):
        self.llm = llm_client
        self.system_activity = system_activity
        self.evidence_manifest = evidence_manifest
    
    def search_system_activity(
        self,
        user_identifiers: Set[str],
        audit_at: str
    ) -> List[Dict]:
        """
        Search system activity logs for events related to the user
        Only returns activities before audit_at timestamp
        """
        audit_at_dt = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        relevant_activities = []
        
        for activity in self.system_activity:
            # Check timestamp
            event_time = datetime.fromisoformat(activity['event_time'].replace('Z', '+00:00'))
            if event_time > audit_at_dt:
                continue
            
            # Check if activity mentions any user identifier
            activity_str = str(activity).lower()
            for identifier in user_identifiers:
                if str(identifier).lower() in activity_str:
                    relevant_activities.append(activity)
                    break
        
        return relevant_activities
    
    def get_relevant_evidence_files(
        self,
        user_identifiers: Set[str],
        audit_at: str
    ) -> List[Dict]:
        """
        Get list of evidence files that might contain user data
        Only returns files captured before audit_at
        """
        audit_at_dt = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        relevant_files = []
        
        for file_info in self.evidence_manifest:
            # Check capture time
            captured_at = datetime.fromisoformat(file_info['captured_at'].replace('Z', '+00:00'))
            if captured_at > audit_at_dt:
                continue
            
            relevant_files.append(file_info)
        
        return relevant_files
    
    def analyze_evidence_with_llm(
        self,
        evidence_content: str,
        evidence_type: str,
        file_id: str,
        user_identifiers: Set[str],
        user_id: str
    ) -> Dict:
        """
        Use LLM to analyze evidence and extract findings
        
        Returns:
            {
                "contains_user_data": bool,
                "findings": [
                    {
                        "system_id": str,
                        "resource_id": str,
                        "data_category": str,
                        "state": str,
                        "has_pii": bool,
                        "description": str
                    }
                ]
            }
        """
        # Truncate evidence if too long
        max_length = 10000
        if len(evidence_content) > max_length:
            evidence_content = evidence_content[:max_length] + f"\n... [truncated, total length: {len(evidence_content)}]"
        
        # Create identifier list string
        identifier_list = "\n".join([f"- {id}" for id in sorted(list(user_identifiers))[:20]])
        
        prompt = f"""Analyze this evidence file and identify any records or references to the user.

EVIDENCE FILE: {file_id}
EVIDENCE TYPE: {evidence_type}
USER_ID: {user_id}

USER IDENTIFIERS TO SEARCH FOR:
{identifier_list}

EVIDENCE CONTENT:
{evidence_content}

TASK:
1. Search for ANY mention of the user's identifiers
2. Identify specific records (accounts, search entries, analytics profiles, support tickets, exports, etc.)
3. For each record found, determine:
   - system_id (e.g., "account_service", "search_service", "analytics_platform", "support_platform", "export_service")
   - resource_id (e.g., "account_123", "search_456", "analytics_789")
   - data_category (e.g., "USER_PROFILE", "SEARCH_INDEX_ENTRY", "ANALYTICS_PROFILE", "SUPPORT_MESSAGE", "USER_EXPORT")
   - state ("PRESENT" if exists, "ABSENT" if deleted/not found)
   - has_pii (true if contains name/email/phone/email_hash)

Respond with JSON:
{{
    "contains_user_data": true/false,
    "findings": [
        {{
            "system_id": "account_service",
            "resource_id": "account_123",
            "data_category": "USER_PROFILE",
            "state": "PRESENT",
            "has_pii": true,
            "description": "brief description of what was found"
        }}
    ]
}}

If no user data found, return {{"contains_user_data": false, "findings": []}}"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            result = self.llm.chat_completion_json(messages, temperature=0.1)
            return result
        except Exception as e:
            print(f"Evidence analysis error for {file_id}: {e}")
            return {
                "contains_user_data": False,
                "findings": [],
                "error": str(e)
            }
    
    def discover_all_evidence(
        self,
        user_identity: Dict,
        audit_at: str,
        analyze_limit: int = 20
    ) -> Dict:
        """
        Discover all evidence related to the user
        
        Returns:
            {
                "activities": [...],
                "evidence_files_analyzed": [...],
                "findings": [...]
            }
        """
        user_identifiers = self._get_searchable_identifiers(user_identity)
        user_id = user_identity['user_id']
        
        # Search system activity
        activities = self.search_system_activity(user_identifiers, audit_at)
        
        # Get relevant evidence files
        evidence_files = self.get_relevant_evidence_files(user_identifiers, audit_at)
        
        # Analyze evidence files (limit to avoid too many API calls)
        all_findings = []
        analyzed_files = []
        
        for i, file_info in enumerate(evidence_files[:analyze_limit]):
            file_id = file_info['file_id']
            file_type, content = load_evidence_file(file_id, self.evidence_manifest)
            
            if file_type == "not_found":
                continue
            
            # Convert content to string for analysis
            if file_type == "sql":
                content_str = str(content)
            elif file_type == "json":
                import json
                content_str = json.dumps(content, indent=2)
            else:
                content_str = str(content)
            
            # Analyze with LLM
            analysis = self.analyze_evidence_with_llm(
                content_str,
                file_type,
                file_id,
                user_identifiers,
                user_id
            )
            
            if analysis.get("contains_user_data"):
                all_findings.extend(analysis.get("findings", []))
                analyzed_files.append({
                    "file_id": file_id,
                    "file_type": file_type,
                    "findings_count": len(analysis.get("findings", []))
                })
        
        return {
            "activities": activities,
            "evidence_files_analyzed": analyzed_files,
            "findings": all_findings
        }
    
    def _get_searchable_identifiers(self, identity: Dict) -> Set[str]:
        """Extract searchable identifiers from identity"""
        identifiers = set()
        
        identifiers.add(identity['user_id'])
        identifiers.add(identity['current_email'])
        identifiers.add(identity['current_email_hash'])
        identifiers.add(identity['current_phone'])
        identifiers.add(identity['current_name'])
        
        for email in identity.get('all_emails', []):
            identifiers.add(email)
        
        for phone in identity.get('all_phones', []):
            identifiers.add(phone)
        
        for name in identity.get('all_names', []):
            identifiers.add(name)
        
        return identifiers
