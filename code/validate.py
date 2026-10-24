"""Submission contract validation."""
from __future__ import annotations
import json
from code.planner import OPERATION_STATE
STATUSES={'COMPLETE','INCOMPLETE','NOT_APPLICABLE'}; PHASES={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
def validate_output(rows:list)->list[str]:
 errors=[]
 for index,row in enumerate(rows,1):
  prefix=f"row {index} ({row.get('case_id','')}):"
  if not row.get('case_id'):errors.append(f'{prefix} missing case_id')
  status=row.get('deletion_status')
  if status not in STATUSES:errors.append(f'{prefix} invalid deletion_status')
  try:steps=json.loads(row.get('steps_json',''))
  except (json.JSONDecodeError,TypeError):errors.append(f'{prefix} steps_json is not valid JSON');continue
  if not isinstance(steps,list):errors.append(f'{prefix} steps_json must be an array');continue
  if status=='NOT_APPLICABLE' and steps:errors.append(f'{prefix} NOT_APPLICABLE steps_json must be []')
  last=-1
  fields={'step_no','phase','system_id','resource_id','operation','state','evidence_id'}
  for pos,step in enumerate(steps,1):
   if not isinstance(step,dict):errors.append(f'{prefix} step {pos} is not an object');continue
   if set(step)!=fields:errors.append(f'{prefix} step {pos} must have exactly 7 fields')
   if not isinstance(step.get('step_no'),int) or step.get('step_no')!=pos:errors.append(f'{prefix} step_no gap at step {pos}')
   phase=step.get('phase');order=PHASES.get(phase,-1)
   if order<last:errors.append(f'{prefix} wrong phase order at step {pos}')
   last=max(last,order)
   if OPERATION_STATE.get(phase,{}).get(step.get('operation'))!=step.get('state'):errors.append(f'{prefix} invalid operation+state pair at step {pos}')
   evidence=step.get('evidence_id')
   if phase=='REMEDIATION' and evidence!='':errors.append(f'{prefix} non-empty evidence_id on REMEDIATION step {pos}')
   if (phase=='FINDING' or (status=='COMPLETE' and phase=='VERIFICATION')) and not evidence:errors.append(f'{prefix} evidence_id required at step {pos}')
 return errors
def validate_row_count(rows:list,expected=518)->list[str]:
 errors=[]
 if len(rows)!=expected:errors.append(f'expected {expected} rows, got {len(rows)}')
 ids=[r.get('case_id','') for r in rows]
 if ids!=sorted(ids):errors.append('rows are not sorted by case_id')
 return errors
