"""
Fast Evidence Discovery
Optimized version with text search before LLM analysis
"""
from typing import Dict, List, Set
from datetime import datetime
from utils import load_evidence_file


class FastEvidenceDiscovery:
    """Faster evidence discovery with text-based prefiltering"""
    
    def __init__(self, system_activity: List[Dict], evidence_manifest: List[Dict]):
        self.system_activity = system_activity
        self.evidence_manifest = evidence_manifest
    
    def search_system_activity(
        self,
        user_identifiers: Set[str],
        audit_at: str
    ) -> Dict:
        """
        Search system activity for deletion-related events
        Returns categorized activities
        """
        audit_at_dt = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        
        deletion_activities = []
        other_activities = []
        
        for activity in self.system_activity:
            event_time = datetime.fromisoformat(activity['event_time'].replace('Z', '+00:00'))
            if event_time > audit_at_dt:
                continue
            
            activity_str = str(activity).lower()
            
            # Check if related to user
            is_relevant = False
            for identifier in user_identifiers:
                if str(identifier).lower() in activity_str:
                    is_relevant = True
                    break
            
            if not is_relevant:
                continue
            
            # Categorize by event type
            event_type = activity.get('event_type', '').upper()
            if 'DELETE' in event_type or 'ANONYMIZE' in event_type or 'REDACT' in event_type:
                deletion_activities.append(activity)
            else:
                other_activities.append(activity)
        
        return {
            'deletion_activities': deletion_activities,
            'other_activities': other_activities[:10]  # Limit other activities
        }
    
    def simple_text_search(
        self,
        content_str: str,
        user_identifiers: Set[str]
    ) -> Dict:
        """
        Simple text-based search without LLM
        Returns basic findings
        """
        content_lower = content_str.lower()
        found_identifiers = set()
        
        for identifier in user_identifiers:
            if str(identifier).lower() in content_lower:
                found_identifiers.add(identifier)
        
        if not found_identifiers:
            return {"found": False, "identifiers": []}
        
        # Try to extract system/resource info from context
        findings = []
        
        # Common patterns
        if 'account' in content_lower:
            findings.append({
                "system_id": "account_service",
                "resource_type": "account",
                "identifiers_found": list(found_identifiers)
            })
        
        if 'search' in content_lower:
            findings.append({
                "system_id": "search_service",
                "resource_type": "search",
                "identifiers_found": list(found_identifiers)
            })
        
        if 'analytics' in content_lower:
            findings.append({
                "system_id": "analytics_platform",
                "resource_type": "analytics",
                "identifiers_found": list(found_identifiers)
            })
        
        if 'support' in content_lower:
            findings.append({
                "system_id": "support_platform",
                "resource_type": "support",
                "identifiers_found": list(found_identifiers)
            })
        
        return {
            "found": True,
            "identifiers": list(found_identifiers),
            "findings": findings if findings else [{"system_id": "unknown", "resource_type": "unknown", "identifiers_found": list(found_identifiers)}]
        }
    
    def discover_fast(
        self,
        user_identity: Dict,
        audit_at: str
    ) -> Dict:
        """
        Fast evidence discovery using text search
        """
        user_identifiers = self._get_searchable_identifiers(user_identity)
        
        # Search activities
        activities = self.search_system_activity(user_identifiers, audit_at)
        
        # Quick text search in recent evidence files
        audit_at_dt = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        
        relevant_evidence = []
        all_findings = []
        
        # Only check the 5 most recent evidence files
        recent_files = [
            f for f in self.evidence_manifest
            if datetime.fromisoformat(f['captured_at'].replace('Z', '+00:00')) <= audit_at_dt
        ]
        recent_files.sort(key=lambda x: x['captured_at'], reverse=True)
        
        for file_info in recent_files[:5]:
            file_id = file_info['file_id']
            file_type, content = load_evidence_file(file_id, self.evidence_manifest)
            
            if file_type == "not_found":
                continue
            
            # Convert to string
            if file_type == "sql":
                content_str = str(content)[:5000]  # Limit size
            elif file_type == "json":
                import json
                content_str = json.dumps(content)[:5000]
            else:
                content_str = str(content)[:5000]
            
            # Simple text search
            search_result = self.simple_text_search(content_str, user_identifiers)
            
            if search_result["found"]:
                relevant_evidence.append({
                    "file_id": file_id,
                    "file_type": file_type,
                    "identifiers_found": search_result["identifiers"]
                })
                all_findings.extend(search_result.get("findings", []))
        
        return {
            "deletion_activities": activities['deletion_activities'],
            "other_activities": activities['other_activities'],
            "evidence_files": relevant_evidence,
            "findings": all_findings
        }
    
    def _get_searchable_identifiers(self, identity: Dict) -> Set[str]:
        """Extract searchable identifiers"""
        identifiers = set()
        identifiers.add(identity['user_id'])
        identifiers.add(identity['current_email'].lower())
        identifiers.add(identity['current_phone'])
        
        for email in identity.get('all_emails', [])[:3]:  # Limit to 3
            identifiers.add(email.lower())
        
        return identifiers
