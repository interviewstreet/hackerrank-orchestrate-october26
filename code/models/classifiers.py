"""
Request Classification
Determines if a request authorizes deletion or is something else
"""
from typing import Dict
from utils import LLMClient


class RequestClassifier:
    """Classifies whether a request text authorizes deletion"""
    
    def __init__(self, llm_client: LLMClient):
        self.llm = llm_client
    
    def classify_request(self, request_text: str) -> Dict:
        """
        Determine if request authorizes deletion
        
        Returns:
            {
                "is_deletion": bool,
                "request_type": str,  # "deletion", "access", "export", "correction", "opt_out", "other"
                "confidence": str,  # "high", "medium", "low"
                "reasoning": str
            }
        """
        prompt = f"""Analyze this data subject request and determine if it authorizes DELETION of personal data.

REQUEST TEXT:
{request_text}

INSTRUCTIONS:
- A DELETION request explicitly asks to delete, erase, remove, or close an account with data deletion
- NOT deletion: access requests, data export, correction, marketing opt-out alone, account information inquiry
- The request may be in any language

Respond with JSON:
{{
    "is_deletion": true/false,
    "request_type": "deletion" or "access" or "export" or "correction" or "opt_out" or "other",
    "confidence": "high" or "medium" or "low",
    "reasoning": "brief explanation"
}}"""

        messages = [{"role": "user", "content": prompt}]
        
        try:
            result = self.llm.chat_completion_json(messages, temperature=0.1)
            return result
        except Exception as e:
            print(f"Classification error: {e}")
            # Default to deletion if unclear (safer for audit)
            return {
                "is_deletion": True,
                "request_type": "deletion",
                "confidence": "low",
                "reasoning": f"Error during classification: {str(e)}"
            }
