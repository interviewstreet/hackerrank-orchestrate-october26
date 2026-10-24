"""Deterministic remediation-plan construction."""
from __future__ import annotations
OPERATION_STATE={
'FINDING':{'REPORT_REMAINING_RECORD':'PRESENT','REPORT_EXPOSED_PII':'PRESENT','REPORT_ACTIVE_DATA_FLOW':'ACTIVE','REPORT_RESTORE_RISK':'ACTIVE'},
'REMEDIATION':{'DISABLE_DATA_FLOW':'DISABLED','BLOCK_RESTORE':'BLOCKED','DELETE_RECORD':'ABSENT','REDACT_RECORD':'REDACTED','ANONYMIZE_RECORD':'ANONYMIZED'},
'VERIFICATION':{'VERIFY_RECORD_ABSENT':'ABSENT','VERIFY_RECORD_PRESENT':'PRESENT','VERIFY_RECORD_REDACTED':'REDACTED','VERIFY_RECORD_ANONYMIZED':'ANONYMIZED','VERIFY_DATA_FLOW_DISABLED':'DISABLED','VERIFY_RESTORE_BLOCKED':'BLOCKED'}}
PHASE_ORDER={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
OP_ORDER={op:i for phase in ('FINDING','REMEDIATION','VERIFICATION') for i,op in enumerate(OPERATION_STATE[phase])}
VERIFY={'DELETE':'VERIFY_RECORD_ABSENT','REDACT':'VERIFY_RECORD_REDACTED','ANONYMIZE':'VERIFY_RECORD_ANONYMIZED','RETAIN':'VERIFY_RECORD_PRESENT'}
REMEDIATE={'DELETE':'DELETE_RECORD','REDACT':'REDACT_RECORD','ANONYMIZE':'ANONYMIZE_RECORD'}
def _step(phase,system,resource,operation,evidence=''):
 return {'step_no':0,'phase':phase,'system_id':system or 'unknown','resource_id':resource or 'unknown','operation':operation,'state':OPERATION_STATE[phase][operation],'evidence_id':evidence or ''}
def plan_steps(decision_result,user_identity,evidence_index):
 del user_identity,evidence_index
 status=decision_result['status']
 if status=='NOT_APPLICABLE':return []
 steps=[]
 if status=='COMPLETE':
  for r in decision_result.get('compliant_resources',[]): steps.append(_step('VERIFICATION',r.get('system_id'),r.get('resource_id'),VERIFY[r['required_action']],r.get('file_id') or r.get('evidence_id')))
 else:
  for f in decision_result.get('findings',[]):
   typ=f.get('type'); action=f.get('required_action','DELETE')
   finding={'active_data_flow':'REPORT_ACTIVE_DATA_FLOW','restore_risk':'REPORT_RESTORE_RISK','identity_unresolved':'REPORT_REMAINING_RECORD'}.get(typ,'REPORT_REMAINING_RECORD' if action=='DELETE' else 'REPORT_EXPOSED_PII')
   steps.append(_step('FINDING',f.get('system_id'),f.get('resource_id'),finding,f.get('file_id') or f.get('evidence_id')))
   if typ=='active_data_flow': rem,ver='DISABLE_DATA_FLOW','VERIFY_DATA_FLOW_DISABLED'
   elif typ=='restore_risk': rem,ver='BLOCK_RESTORE','VERIFY_RESTORE_BLOCKED'
   elif typ=='identity_unresolved': continue
   else:
    rem=REMEDIATE.get(action)
    if not rem:continue
    ver=VERIFY[action]
   steps.extend([_step('REMEDIATION',f.get('system_id'),f.get('resource_id'),rem),_step('VERIFICATION',f.get('system_id'),f.get('resource_id'),ver)])
 steps.sort(key=lambda s:(PHASE_ORDER[s['phase']],OP_ORDER[s['operation']],s['system_id'],s['resource_id']))
 for i,s in enumerate(steps,1):s['step_no']=i
 return steps
