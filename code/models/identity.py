"""
Identity Resolution
Resolves current and historical user identifiers
"""
from typing import Dict, List, Set, Optional
from datetime import datetime


class IdentityResolver:
    """Resolves user identities across current and historical records"""
    
    def __init__(self, user_identities: List[Dict], user_audit_log: List[Dict]):
        self.user_identities = user_identities
        self.user_audit_log = user_audit_log
        
        # Build lookup indexes
        self._build_indexes()
    
    def _build_indexes(self):
        """Build indexes for fast lookups"""
        # Email to user_id mapping
        self.email_to_user = {}
        for user in self.user_identities:
            email = user['email'].lower()
            self.email_to_user[email] = user
        
        # Historical emails from audit log
        self.historical_emails = {}  # user_id -> set of old emails
        for audit in self.user_audit_log:
            if audit['field_name'] == 'email':
                user_id = audit['user_id']
                old_email = audit['old_value'].lower()
                
                if user_id not in self.historical_emails:
                    self.historical_emails[user_id] = set()
                self.historical_emails[user_id].add(old_email)
    
    def resolve_identity(self, email: str, audit_at: str) -> Optional[Dict]:
        """
        Resolve user identity from email at a specific point in time
        
        Returns:
            {
                "user_id": str,
                "current_email": str,
                "current_name": str,
                "current_phone": str,
                "current_email_hash": str,
                "all_emails": [list of current and historical emails],
                "all_phones": [list of current and historical phones],
                "match_type": "current" or "historical"
            }
            or None if not found
        """
        email_lower = email.lower()
        
        # Try current email match first
        if email_lower in self.email_to_user:
            user = self.email_to_user[email_lower]
            return self._build_identity_record(user, "current", audit_at)
        
        # Try historical email match
        for user_id, hist_emails in self.historical_emails.items():
            if email_lower in hist_emails:
                # Find current user record
                user = next((u for u in self.user_identities if u['user_id'] == user_id), None)
                if user:
                    return self._build_identity_record(user, "historical", audit_at)
        
        return None
    
    def _build_identity_record(self, user: Dict, match_type: str, audit_at: str) -> Dict:
        """Build complete identity record with current and historical data"""
        user_id = user['user_id']
        
        # Get all historical values for this user
        all_emails = {user['email'].lower()}
        all_phones = {user['phone']}
        all_names = {user['name']}
        
        # Add historical values from audit log (only before audit_at)
        audit_at_dt = datetime.fromisoformat(audit_at.replace('Z', '+00:00'))
        
        for audit in self.user_audit_log:
            if audit['user_id'] != user_id:
                continue
            
            # Only include changes before audit_at
            event_time = datetime.fromisoformat(audit['event_time'].replace('Z', '+00:00'))
            if event_time > audit_at_dt:
                continue
            
            field = audit['field_name']
            old_value = audit['old_value']
            
            if field == 'email':
                all_emails.add(old_value.lower())
            elif field == 'phone':
                all_phones.add(old_value)
            elif field == 'name':
                all_names.add(old_value)
        
        return {
            "user_id": user_id,
            "current_email": user['email'],
            "current_name": user['name'],
            "current_phone": user['phone'],
            "current_email_hash": user['email_hash'],
            "all_emails": sorted(list(all_emails)),
            "all_phones": sorted(list(all_phones)),
            "all_names": sorted(list(all_names)),
            "match_type": match_type
        }
    
    def get_all_identifiers(self, identity: Dict) -> Set[str]:
        """Get all identifiers (emails, phones, user_id, email_hash) for searching"""
        identifiers = set()
        
        identifiers.add(identity['user_id'])
        identifiers.add(identity['current_email_hash'])
        
        for email in identity['all_emails']:
            identifiers.add(email)
            identifiers.add(email.lower())
        
        for phone in identity['all_phones']:
            identifiers.add(phone)
            # Add normalized phone (remove spaces, dashes, etc.)
            normalized = phone.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
            identifiers.add(normalized)
        
        for name in identity['all_names']:
            identifiers.add(name)
            identifiers.add(name.lower())
        
        return identifiers
