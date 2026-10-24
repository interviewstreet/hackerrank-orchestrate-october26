"""Deletion completeness decision engine."""
from __future__ import annotations
from code.policy import get_required_action
EXPECTED={'DELETE':{'ABSENT','DELETED'},'REDACT':{'REDACTED'},'ANONYMIZE':{'ANONYMIZED'},'RETAIN':{'PRESENT','ACTIVE','TOMBSTONE'}}
def _context(hit):
 r=hit.get('record',{}); state=hit.get('state','').upper()
 return {'has_shared_context':bool(r.get('shared_context',True)),'within_retention_period':bool(r.get('within_retention_period',True)),'legal_hold_active':bool(r.get('legal_hold_active',True)),'restore_can_be_blocked':bool(r.get('restore_can_be_blocked',True)),'only_stable_id_needed':state in {'REDACTED','TOMBSTONE','ANONYMIZED'},'attachment_belongs_only_to_subject':bool(r.get('attachment_belongs_only_to_subject',True)),'record_still_attributable':state not in {'ANONYMIZED','ABSENT'},'log_contains_email':bool(r.get('email') or hit.get('identifiers_found'))}
def decide(case,user_identity,evidence_index,system_activity_events,deletion_rules,classify_fn):
 intent=classify_fn(case['request_text'],case['case_id'])
 if intent=='NOT_APPLICABLE':return {'status':'NOT_APPLICABLE','findings':[],'resources':[],'compliant_resources':[]}
 if user_identity is None:return {'status':'INCOMPLETE','findings':[{'type':'identity_unresolved','system_id':'identity_service','resource_id':case.get('email',''),'evidence_id':''}],'resources':[],'compliant_resources':[]}
 findings=[]; compliant=[]; resources=[]
 for resource_id,hits in evidence_index.items():
  hit=hits[-1]; action=get_required_action(hit['data_category'],_context(hit),deletion_rules); state=hit.get('state','').upper()
  resource={**hit,'required_action':action,'resource_id':resource_id};resources.append(resource)
  if state in EXPECTED[action]: compliant.append(resource)
  else: findings.append({**resource,'type':'non_compliant_resource'})
 deletion_times=[e.get('event_time','') for e in system_activity_events if 'DELETE' in e.get('event_type','').upper()]
 after=max(deletion_times) if deletion_times else ''
 for event in system_activity_events:
  kind=event.get('event_type','').upper()
  if kind in {'SYNC_RECORD','INDEX_RECORD','CREATE_EXPORT','RESTORE_BACKUP'} and event.get('event_time','')>after and event.get('reported_result','').upper() not in {'DISABLED','FAILED','BLOCKED'}:
   findings.append({'type':'restore_risk' if kind=='RESTORE_BACKUP' else 'active_data_flow','system_id':event.get('target_system') or event.get('source_system','unknown'),'resource_id':event.get('resource_id',''),'evidence_id':event.get('activity_id',''),'state':'ACTIVE'})
 for resource in resources:
  if resource['data_category']=='BACKUP_ARCHIVE' and resource.get('record',{}).get('restore_allowed') is True:
   findings.append({**resource,'type':'restore_risk'})
 return {'status':'COMPLETE' if not findings and len(compliant)==len(evidence_index) else 'INCOMPLETE','findings':findings,'resources':resources,'compliant_resources':compliant}
