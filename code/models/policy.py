"""
Policy Compliance and Remediation Planning
Applies deletion rules and generates remediation steps
"""
from typing import Dict, List, Optional
from utils import LLMClient


class PolicyEngine:
    """Applies deletion policy rules and generates remediation plans"""
    
    def __init__(self, llm_client: LLMClient, deletion_rules: List[Dict]):
        self.llm = llm_client
        self.deletion_rules = deletion_rules
        
        # Build rule lookup
        self.rules_by_category = {}
        for rule in deletion_rules:
            category = rule['data_category']
            self.rules_by_category[category] = rule
    
    def apply_policy(
        self,
        findings: List[Dict],
        activities: List[Dict]
    ) -> Dict:
        """
        Apply deletion policy to findings and generate steps
        
        Returns:
            {
                "status": "COMPLETE" or "INCOMPLETE",
                "findings_steps": [...],
                "remediation_steps": [...],
                "verification_steps": [...]
            }
        """
        # Use LLM to analyze findings and activities in context
        findings_str = self._format_findings(findings)
        activities_str = self._format_activities(activities)
        rules_str = self._format_rules()
        
        prompt = f"""You are auditing whether a user deletion was completed according to policy.

DELETION POLICY RULES:
{rules_str}

FINDINGS (Records/Data Found):
{findings_str}

SYSTEM ACTIVITIES (Deletion operations performed):
{activities_str}

TASK:
1. Determine if deletion is COMPLETE or INCOMPLETE
   - COMPLETE: All records properly deleted/redacted/anonymized per policy, no active risks
   - INCOMPLETE: Any records remain that should be deleted, OR records have PII that should be redacted

2. For INCOMPLETE cases, generate:
   - FINDING steps: Report each remaining record or exposed PII
   - REMEDIATION steps: Actions to fix each issue (in dependency order)
   - VERIFICATION steps: Checks to confirm remediation worked

3. For COMPLETE cases, generate:
   - VERIFICATION steps only: Prove the current compliant state

STEP FORMAT:
{{
    "step_no": 1,
    "phase": "FINDING" or "REMEDIATION" or "VERIFICATION",
    "system_id": "account_service",
    "resource_id": "account_123",
    "operation": "REPORT_REMAINING_RECORD",
    "state": "PRESENT",
    "evidence_id": "evidence_01"
}}

ALLOWED OPERATIONS:
FINDING phase:
- REPORT_REMAINING_RECORD (state: PRESENT)
- REPORT_EXPOSED_PII (state: PRESENT)
- REPORT_ACTIVE_DATA_FLOW (state: ACTIVE)
- REPORT_RESTORE_RISK (state: ACTIVE)

REMEDIATION phase:
- DELETE_RECORD (state: ABSENT)
- REDACT_RECORD (state: REDACTED)
- ANONYMIZE_RECORD (state: ANONYMIZED)
- DISABLE_DATA_FLOW (state: DISABLED)
- BLOCK_RESTORE (state: BLOCKED)

VERIFICATION phase:
- VERIFY_RECORD_ABSENT (state: ABSENT)
- VERIFY_RECORD_PRESENT (state: PRESENT) [for retained records]
- VERIFY_RECORD_REDACTED (state: REDACTED)
- VERIFY_RECORD_ANONYMIZED (state: ANONYMIZED)
- VERIFY_DATA_FLOW_DISABLED (state: DISABLED)
- VERIFY_RESTORE_BLOCKED (state: BLOCKED)

IMPORTANT RULES:
- For findings and COMPLETE verification: use actual evidence_id from findings
- For future remediation/verification: use empty evidence_id ("")
- Order: FINDING, then REMEDIATION, then VERIFICATION
- Within phase: order by operation type, then system_id, then resource_id
- Step numbers start at 1 and increment consecutively
- Disable data flows before deleting dependent records
- Always verify security audit logs are retained (VERIFY_RECORD_PRESENT)

Respond with JSON:
{{
    "status": "COMPLETE" or "INCOMPLETE",
    "reasoning": "brief explanation",
    "steps": [array of step objects as defined above]
}}"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            result = self.llm.chat_completion_json(messages, temperature=0.1)
            
            # Ensure steps are properly numbered
            steps = result.get("steps", [])
            for i, step in enumerate(steps):
                step["step_no"] = i + 1
            
            return result
        except Exception as e:
            print(f"Policy application error: {e}")
            # Default to INCOMPLETE with error
            return {
                "status": "INCOMPLETE",
                "reasoning": f"Error during policy analysis: {str(e)}",
                "steps": []
            }
    
    def _format_findings(self, findings: List[Dict]) -> str:
        """Format findings for the prompt"""
        if not findings:
            return "No records found containing user data."
        
        lines = []
        for i, finding in enumerate(findings[:50], 1):  # Limit to 50 findings
            lines.append(f"{i}. System: {finding.get('system_id', 'unknown')}")
            lines.append(f"   Resource: {finding.get('resource_id', 'unknown')}")
            lines.append(f"   Category: {finding.get('data_category', 'unknown')}")
            lines.append(f"   State: {finding.get('state', 'unknown')}")
            lines.append(f"   Has PII: {finding.get('has_pii', False)}")
            lines.append(f"   Description: {finding.get('description', '')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_activities(self, activities: List[Dict]) -> str:
        """Format system activities for the prompt"""
        if not activities:
            return "No deletion activities found."
        
        lines = []
        for i, activity in enumerate(activities[:30], 1):  # Limit to 30 activities
            lines.append(f"{i}. Event: {activity.get('event_type', 'unknown')}")
            lines.append(f"   Time: {activity.get('event_time', 'unknown')}")
            lines.append(f"   Source: {activity.get('source_system', 'unknown')}")
            lines.append(f"   Target: {activity.get('target_system', 'unknown')}")
            lines.append(f"   Resource: {activity.get('resource_id', 'unknown')}")
            lines.append(f"   Result: {activity.get('reported_result', 'unknown')}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_rules(self) -> str:
        """Format deletion rules for the prompt"""
        lines = []
        for rule in self.deletion_rules:
            lines.append(f"- {rule['data_category']}: {rule['required_action']}")
            if rule['condition'] != 'Always':
                lines.append(f"  Condition: {rule['condition']}")
        
        return "\n".join(lines)
