from __future__ import annotations
import base64, csv, hashlib, json, re, sqlite3, sys, zlib
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "dataset"
OUT = ROOT / "output.csv"


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))

def dt(value):
    if not value: return None
    try: return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError: return None

def norm(x): return str(x).strip().casefold() if x is not None else ""
def extract_pdf_text(path):
    data=path.read_bytes(); output=[]
    for match in re.finditer(rb'(?<![0-9])([0-9]+)\s+[0-9]+\s+obj(.*?)endobj',data,re.S):
        body=match.group(2); sm=re.search(rb'stream\r?\n(.*?)endstream',body,re.S)
        if not sm: continue
        raw=sm.group(1); filt=re.search(rb'/Filter\s*(\[[^]]+\]|/\w+)',body)
        if not filt: continue
        filters=filt.group(1)
        try:
            if b'ASCII85Decode' in filters: raw=base64.a85decode(raw,adobe=True)
            if b'FlateDecode' in filters: raw=zlib.decompress(raw)
        except Exception: continue
        if b'BT' not in raw or b'Tj' not in raw: continue
        for token in re.findall(rb'\(((?:\\.|[^\\)])*)\)\s*Tj',raw):
            token=re.sub(rb'\\([()\\])',rb'\1',token)
            token=re.sub(rb'\\([nrt])',lambda m:{b'n':b' ',b'r':b' ',b't':b' '}.get(m.group(1),b' '),token)
            token=re.sub(rb'\\[0-7]{1,3}',b' ',token)
            text=token.decode('latin-1','ignore').strip()
            if text:output.append(text)
    return ' '.join(output)

def nested_records(value, path=()):
    if isinstance(value, dict):
        if any(k in value for k in ("resource_id", "id")):
            yield path, value
        for k,v in value.items(): yield from nested_records(v, path+(str(k),))
    elif isinstance(value, list):
        for v in value: yield from nested_records(v,path)

def sys_for(path, rec):
    # Prefer the explicit service namespace; generic terms such as "profile"
    # otherwise misclassify analytics profiles and tombstones as accounts.
    systems=('identity_service','account_service','search_service','analytics_platform','support_platform','security_service','integration_service','backup_service','export_service','marketing_platform','notification_service')
    for system in systems:
        if system in path: return system
    rid=str(rec.get('resource_id') or rec.get('id') or '').lower()
    if rid.startswith('tombstone_'): return 'identity_service'
    prefixes=(('account_','account_service'),('search_','search_service'),('analytics_','analytics_platform'),('support_','support_platform'),('audit_record_','security_service'),('data_flow_','integration_service'),('backup_','backup_service'),('export_','export_service'))
    for prefix,system in prefixes:
        if rid.startswith(prefix): return system
    if rid.startswith('audit_record_'): return 'security_service'
    hint=" ".join(path).lower(); keys=" ".join(map(str,rec.keys())).lower()
    pairs=[('deleted_customer','identity_service'),('tombstone','identity_service'),('security','security_service'),('audit','security_service'),('search','search_service'),('index','search_service'),('analytics','analytics_platform'),('support','support_platform'),('ticket','support_platform'),('connector','integration_service'),('integration','integration_service'),('backup','backup_service'),('restore','backup_service'),('export','export_service'),('marketing','marketing_platform'),('email_delivery','notification_service'),('account','account_service')]
    for token,system in pairs:
        if token in hint or token in keys:return system
    return ''

def ids_for_case(case, identities, audits):
    em=norm(case['email']); users=set(); vals={em}
    for audit in audits:
        if norm(audit.get('field_name'))=='email' and em in (norm(audit.get('old_value')),norm(audit.get('new_value'))): users.add(audit['user_id'])
    for u in identities:
        if norm(u.get('email'))==em: users.add(u['user_id'])
    for u in users:
        vals.add(norm(u))
        for row in identities:
            if row['user_id']==u:
                for k in ('email','name','phone','email_hash'):
                    if row.get(k): vals.add(norm(row[k]))
        for audit in audits:
            if audit.get('user_id')==u and audit.get('field_name','').lower() in ('email','name','phone','email_hash'):
                for k in ('old_value','new_value'):
                    if audit.get(k): vals.add(norm(audit[k]))
    # Readbacks may expose a SHA-256 correlation key instead of an email.
    for value in tuple(vals):
        if '@' in value: vals.add(hashlib.sha256(value.encode('utf-8')).hexdigest())
    return users, vals
_EVIDENCE_INDEX = None
def evidence_records(manifest, cutoff):
    global _EVIDENCE_INDEX
    if _EVIDENCE_INDEX is None:
        indexed=[]
        for m in manifest:
            cap=dt(m['captured_at']); p=DATA/m['file_path']
            if not cap or not p.exists(): continue
            fid=m['file_id']; suffix=p.suffix.lower()
            if suffix=='.json':
                try: data=json.loads(p.read_text(encoding='utf-8-sig'))
                except Exception: continue
                for path,rec in nested_records(data):
                    sys=sys_for(path,rec)
                    if sys: indexed.append((fid,sys,rec,path,cap))
            elif suffix=='.sql':
                con=sqlite3.connect(':memory:')
                try:
                    con.executescript(p.read_text(encoding='utf-8-sig'))
                    for table, in con.execute("select name from sqlite_master where type='table'"):
                        cols=[x[1] for x in con.execute(f'pragma table_info("{table}")')]
                        mapping={'customer_profiles':'account_service','customer_profiles_failover_replica':'account_service','customer_profiles_primary':'account_service','customer_search_documents':'search_service','search_documents_primary':'search_service','customer_analytics_profiles':'analytics_platform','support_records':'support_platform','customer_exports':'export_service','connector_subscriptions':'integration_service','backup_restore_entries':'backup_service','security_audit_records':'security_service','deleted_customer_references':'identity_service'}
                        sys=mapping.get(table)
                        if sys:
                            for row in con.execute(f'select * from "{table}"'): indexed.append((fid,sys,dict(zip(cols,row)),(table,),cap))
                        elif 'record_json' in cols and 'origin_system' in cols:
                            for row in con.execute(f'select * from "{table}"'):
                                d=dict(zip(cols,row))
                                try: record=json.loads(d.get('record_json') or '{}')
                                except Exception: continue
                                indexed.append((fid,d.get('origin_system',''),record,(d.get('collection_name',''),),cap))
                except Exception: pass
                finally: con.close()
            elif suffix=='.pdf':
                text=extract_pdf_text(p)
                if text: indexed.append((fid,'',{'_line':text,'_pdf':True},(),cap))
            elif suffix in ('.log','.txt'):
                for line in p.read_text(encoding='utf-8-sig',errors='ignore').splitlines(): indexed.append((fid,'',{'_line':line},(),cap))
        _EVIDENCE_INDEX=indexed
    return [(fid,sys,rec,path) for fid,sys,rec,path,cap in _EVIDENCE_INDEX if cap<=cutoff]
def classify(sys, rec, path, users, ids, linked_resources=()):
    raw={norm(v) for v in rec.values() if isinstance(v,(str,int,float)) and v is not None}
    raw.update(norm(k)+"="+norm(v) for k,v in rec.items() if isinstance(v,(str,int,float)) and v is not None)
    matched=bool(raw & ids) or str(rec.get('resource_id') or rec.get('id') or '') in linked_resources
    # Text/log evidence may be key-value or pipe-delimited handover records.
    if '_line' in rec:
        line=norm(rec['_line'])
        if re.search(r'event=[a-z0-9_]+_started\b',line): return None
        matched=any(v and re.search(r'(?<![A-Za-z0-9_])'+re.escape(v)+r'(?![A-Za-z0-9_])',line) for v in ids)
        eqrid=re.search(r'resource_id=([A-Za-z0-9_-]+)',line)
        parts=[x.strip() for x in line.split('|')]
        pipe_record=len(parts)>=5 and re.fullmatch(r'[a-z_]+',parts[1] or '') and re.fullmatch(r'(?:[a-z]+_)+[a-z0-9]+',parts[2] or '')
        idrid=re.search(r'\b(account|search|analytics|support|audit_record|data_flow|backup|export|tombstone)_\d+\b',line)
        rid=(eqrid.group(1) if eqrid else (parts[2] if pipe_record else (idrid.group(0) if idrid else '')))
        if rid in linked_resources: matched=True
        if not matched or not rid:return None
        if pipe_record:
            sys=parts[1]; category=parts[3].upper(); status=parts[4].upper()
            if status in ('NOT_FOUND','ABSENT','404'):state='absent'
            elif sys=='security_service' or category=='SECURITY_AUDIT_LOG':state='retained'
            elif sys=='identity_service' or category=='ACCOUNT_TOMBSTONE':state='exposed' if status in ('IDENTIFIABLE','FOUND','PRESENT') else 'redacted'
            elif sys=='analytics_platform' or category in ('ANALYTICS_PROFILE','PRODUCT_TELEMETRY'):state='exposed' if status in ('IDENTIFIABLE','PRESENT','FOUND') else 'anonymized'
            elif sys=='integration_service' or category=='DATA_FLOW':state='active' if status=='ACTIVE' else 'disabled'
            elif sys=='backup_service' or category=='BACKUP_ARCHIVE':state='restore' if status in ('ACTIVE','RESTORE_ALLOWED') else 'blocked'
            elif sys=='support_platform' and category=='SUPPORT_MESSAGE':state='exposed' if status in ('IDENTIFIABLE','PRESENT') else 'redacted'
            else:state='present'
            return (sys,rid,state)
        sy=re.search(r'\bservice=([A-Za-z0-9_]+)',line); sys=sy.group(1) if sy else ''
        if sys == 'support_replica': sys='support_platform'
        if not sys:
            for prefix,system in (('tombstone_','identity_service'),('audit_record_','security_service'),('account_','account_service'),('search_','search_service'),('analytics_','analytics_platform'),('support_','support_platform'),('data_flow_','integration_service'),('backup_','backup_service'),('export_','export_service')):
                if rid.startswith(prefix):sys=system;break
        if not sys:
            for token,system in [('account','account_service'),('search','search_service'),('analytics','analytics_platform'),('support','support_platform'),('backup','backup_service'),('integration','integration_service'),('security','security_service')]:
                if token in line:sys=system;break
        if not sys:return None
        if '404' in line or 'rows=0' in line:return (sys,rid,'absent')
        if sys=='security_service':return (sys,rid,'retained')
        if sys=='integration_service':return (sys,rid,'active' if 'enabled=true' in line else 'disabled')
        if sys=='backup_service':return (sys,rid,'restore' if 'restore_allowed=true' in line or ('eligible=true' in line and 'deletion_block=false' in line) else 'blocked')
        if sys=='analytics_platform':
            if 'contact_lookup_completed' in line and ('rows=1' in line or 'rows=1 ' in line): return (sys,rid,'present')
            return (sys,rid,'exposed' if re.search(r'(email|phone|email_hash)=(?!null\b)[^ ]+',line) else 'anonymized')
        if sys=='support_platform':
            if rec.get('_pdf'): return (sys,rid,'present')
            if 'contact_query_completed' in line and re.search(r'rows=[1-9]',line): return (sys,rid,'present')
            return (sys,rid,'exposed' if re.search(r'(requester_email|requester_name|requester_phone)=(?!null\b)[^ ]+',line) or rec.get('_pdf') else 'redacted')
        return (sys,rid,'present')
    if not matched: return None
    rid=str(rec.get('resource_id') or rec.get('id') or '')
    if not rid:return None
    # Lookups explicitly encode authoritative absence.
    if rec.get('profile','missing') is None or rec.get('status_code')==404 or rec.get('http_status')==404 or rec.get('rows')==0:return (sys,rid,'absent')
    # If an email/hash/name remains exposed, this record violates deletion/redaction.
    identifiers=('email','requester_email','owner_email','customer_email','phone','requester_phone','full_name','display_name','requester_name','email_hash')
    exposed=any(rec.get(k) not in (None,'','null') and norm(rec.get(k)) in ids for k in identifiers)
    # Logs and retention are allowed; analytics should be anonymous, tombstones redacted.
    if sys=='security_service':return (sys,rid,'retained')
    if sys=='identity_service':
        return (sys,rid,'exposed' if exposed else 'redacted')
    if sys=='analytics_platform':return (sys,rid,'exposed' if exposed else 'anonymized')
    if sys=='integration_service':return (sys,rid,'active' if rec.get('enabled') in (1,'1',True) or norm(rec.get('enabled'))=='true' else 'disabled')
    if sys=='backup_service':return (sys,rid,'restore' if rec.get('restore_allowed') in (1,'1',True) or norm(rec.get('restore_allowed'))=='true' else 'blocked')
    if sys=='support_platform':return (sys,rid,'exposed' if exposed else 'redacted')
    # Account, search, exports, marketing and secondary identifiers should be absent.
    return (sys,rid,'present')

# Phase ordering follows the operation tables in problem_statement.md.
OP_ORDER={'REPORT_REMAINING_RECORD':0,'REPORT_EXPOSED_PII':1,'REPORT_ACTIVE_DATA_FLOW':2,'REPORT_RESTORE_RISK':3,'DISABLE_DATA_FLOW':0,'BLOCK_RESTORE':1,'DELETE_RECORD':2,'REDACT_RECORD':3,'ANONYMIZE_RECORD':4,'VERIFY_RECORD_ABSENT':0,'VERIFY_RECORD_PRESENT':1,'VERIFY_RECORD_REDACTED':2,'VERIFY_RECORD_ANONYMIZED':3,'VERIFY_DATA_FLOW_DISABLED':4,'VERIFY_RESTORE_BLOCKED':5}
SYS_TABLE={'account_service':0,'search_service':1,'export_service':2,'marketing_platform':3,'notification_service':4,'support_platform':5,'analytics_platform':6,'integration_service':7,'backup_service':8,'security_service':9,'identity_service':10}

def step(phase,sys,rid,op,state,eid=''):
    return {'step_no':0,'phase':phase,'system_id':sys,'resource_id':rid,'operation':op,'state':state,'evidence_id':eid}

def deletion_request(text):
    t=norm(text)
    if any(x in t for x in ('export my data','access my data','correct my','update my address','opt out','unsubscribe','marketing only','do not delete','not a deletion')): return False
    # Direct and indirect deletion language, including requests to verify a completed deletion.
    delete_cues=('delet','eras','purge','suppression','supprimer','effacer','eliminar','borrar','hapus','apagar','löschen','削除','删除','抹消','退会')
    remove_cues=('remove','clean my','wipe','close my account','close the account','close account','closed','close this account','account closure','terminate my account','shut down my account','verify that my account was deleted','verify the deletion','audit the deletion','verify the profile is gone','profile is gone','confirm that the profile is gone')
    context=('account','profile','personal','data','record','identifier','support','integration','analytics','backup','search','my account','this account','email','request')
    if any(c in t for c in delete_cues): return True
    return any(c in t for c in remove_cues) and any(c in t for c in context)
def activity_resources_for_case(case, identifiers, activities):
    cutoff=dt(case['audit_at']); linked=set()
    for event in activities:
        when=dt(event.get('event_time'))
        if not when or when>cutoff: continue
        details=norm(event.get('details',''))
        if any(v and re.search(r'(?<![A-Za-z0-9_])'+re.escape(v)+r'(?![A-Za-z0-9_])',details) for v in identifiers):
            if event.get('resource_id'): linked.add(event['resource_id'])
    return linked

def solve_case(case, identities, audits, manifest, rules, activities=()):
    if not deletion_request(case['request_text']):return 'NOT_APPLICABLE',[]
    users,ids=ids_for_case(case,identities,audits); cutoff=dt(case['audit_at'])
    linked_resources=activity_resources_for_case(case,ids,activities)
    categories={'account_service':'USER_PROFILE','search_service':'SEARCH_INDEX_ENTRY','export_service':'USER_EXPORT','marketing_platform':'MARKETING_PROFILE','support_platform':'SUPPORT_MESSAGE','analytics_platform':'ANALYTICS_PROFILE','security_service':'SECURITY_AUDIT_LOG','identity_service':'ACCOUNT_TOMBSTONE'}
    policy_actions={r['data_category']:r['required_action'].upper() for r in rules}
    action_by_system={sys:policy_actions[cat] for sys,cat in categories.items() if cat in policy_actions}
    # Resolve resource references from identity-matched records before classifying linked snapshots.
    evidence=evidence_records(manifest,cutoff)
    # Correlate identity-bearing log events to readbacks via trace ID. A started
    # event contributes identity association only; the state comes from its peer.
    trace_ids=set()
    for fid,sys,rec,path in evidence:
        line=norm(rec.get('_line',''))
        if line and any(v and re.search(r'(?<![A-Za-z0-9_])'+re.escape(v)+r'(?![A-Za-z0-9_])',line) for v in ids):
            m=re.search(r'\btrace_id=([a-z0-9_-]+)',line)
            if m: trace_ids.add((fid,m.group(1)))
    for fid,sys,rec,path in evidence:
        line=norm(rec.get('_line','')); m=re.search(r'\btrace_id=([a-z0-9_-]+)',line); rm=re.search(r'\bresource_id=([a-z0-9_-]+)',line)
        if m and rm and (fid,m.group(1)) in trace_ids: linked_resources.add(rm.group(1))
    for fid,sys,rec,path in evidence:
        if classify(sys,rec,path,users,ids,linked_resources) and rec.get('source_resource_id'):
            linked_resources.add(str(rec['source_resource_id']))
    # Gather participant-visible evidence records, preferring the latest observation per system/resource.
    found={}
    for fid,sys,rec,path in evidence:
        r=classify(sys,rec,path,users,ids,linked_resources)
        if not r:continue
        sys,rid,state=r
        if state=='exposed' and action_by_system.get(sys) in ('DELETE','DELETE_RECORD'): state='present'
        # Avoid treating a generic resource export as proof unless it ties through an identity.
        obs=dt(rec.get('observed_at') or rec.get('updated_at') or rec.get('captured_at')) or dt(next((m['captured_at'] for m in manifest if m['file_id']==fid),''))
        key=(sys,rid)
        if key not in found or obs and (not found[key][3] or obs>found[key][3]):found[key]=(state,fid,rec,obs)
    # Identifiers and resource ids in audit/event logs may corroborate, but do not infer absent records.
    violations=[]
    expected_account=None
    for (sys,rid),(state,fid,rec,obs) in found.items():
        if state in ('present','exposed','active','restore'):
            violations.append((sys,rid,state,fid))
        elif sys=='account_service' and state=='absent': expected_account=(sys,rid,state,fid)
    # Include explicit deauthorized user request as N/A; incomplete is grounded in an actual present violation.
    if violations: status='INCOMPLETE'
    else: status='COMPLETE'
    # Include evidence-backed compliant resources only when actual records/point lookups are visible.
    compliant=[]
    for (sys,rid),(state,fid,rec,obs) in found.items():
        if state in ('absent','retained','redacted','anonymized','disabled','blocked'):
            compliant.append((sys,rid,state,fid))
    # Account absence must be established by an explicit account lookup. Don't use workflow claims.
    # Present account records receive their planned absence verification below;
    # do not synthesize a conflicting compliant/absent observation for them.
    # Lack of a matched record is not evidence of deletion. Keep an authorized
    # case unresolved when there is no participant-visible state observation.
    if status=='COMPLETE' and not compliant: status='INCOMPLETE'
    steps=[]
    if status=='INCOMPLETE':
        for sys,rid,state,eid in violations:
            if state=='present': op,st='REPORT_REMAINING_RECORD','PRESENT'
            elif state=='exposed': op,st='REPORT_EXPOSED_PII','PRESENT'
            elif state=='active': op,st='REPORT_ACTIVE_DATA_FLOW','ACTIVE'
            else: op,st='REPORT_RESTORE_RISK','ACTIVE'
            steps.append(step('FINDING',sys,rid,op,st,eid))
        for sys,rid,state,eid in violations:
            if state=='active':op,st='DISABLE_DATA_FLOW','DISABLED'
            elif state=='restore':op,st='BLOCK_RESTORE','BLOCKED'
            elif state=='exposed' and action_by_system.get(sys)=='ANONYMIZE':op,st='ANONYMIZE_RECORD','ANONYMIZED'
            elif state=='exposed' and action_by_system.get(sys)=='REDACT':op,st='REDACT_RECORD','REDACTED'
            elif state=='exposed' and action_by_system.get(sys)=='REDACT':op,st='REDACT_RECORD','REDACTED'
            else:op,st='DELETE_RECORD','ABSENT'
            steps.append(step('REMEDIATION',sys,rid,op,st,''))
        # Verify primary account absent as part of every incomplete authorized request.
        account=[(s,r,st,e) for s,r,st,e in compliant if s=='account_service' and st=='absent']
        for x in account:compliant.remove(x)
        if not account:
            account=[('account_service',r,'absent','') for r in sorted(x for x in linked_resources if x.startswith('account_'))]
            if not account:
                # Only add generic account verification when an identity-matched account id was seen.
                account=[]
        for sys,rid,state,eid in account:
            steps.append(step('VERIFICATION',sys,rid,'VERIFY_RECORD_ABSENT','ABSENT',''))
        for sys,rid,state,eid in compliant:
            op={'absent':('VERIFY_RECORD_ABSENT','ABSENT'),'retained':('VERIFY_RECORD_PRESENT','PRESENT'),'redacted':('VERIFY_RECORD_REDACTED','REDACTED'),'anonymized':('VERIFY_RECORD_ANONYMIZED','ANONYMIZED'),'disabled':('VERIFY_DATA_FLOW_DISABLED','DISABLED'),'blocked':('VERIFY_RESTORE_BLOCKED','BLOCKED')}.get(state)
            if op:steps.append(step('VERIFICATION',sys,rid,op[0],op[1],''))
        for sys,rid,state,eid in violations:
            if state=='present':op,st='VERIFY_RECORD_ABSENT','ABSENT'
            elif state=='exposed' and action_by_system.get(sys)=='ANONYMIZE':op,st='VERIFY_RECORD_ANONYMIZED','ANONYMIZED'
            elif state=='exposed' and action_by_system.get(sys)=='REDACT':op,st='VERIFY_RECORD_REDACTED','REDACTED'
            elif state=='active':op,st='VERIFY_DATA_FLOW_DISABLED','DISABLED'
            else:op,st='VERIFY_RESTORE_BLOCKED','BLOCKED'
            steps.append(step('VERIFICATION',sys,rid,op,st,''))
    else:
        for sys,rid,state,eid in compliant:
            op={'absent':('VERIFY_RECORD_ABSENT','ABSENT'),'retained':('VERIFY_RECORD_PRESENT','PRESENT'),'redacted':('VERIFY_RECORD_REDACTED','REDACTED'),'anonymized':('VERIFY_RECORD_ANONYMIZED','ANONYMIZED'),'disabled':('VERIFY_DATA_FLOW_DISABLED','DISABLED'),'blocked':('VERIFY_RESTORE_BLOCKED','BLOCKED')}.get(state)
            if op:steps.append(step('VERIFICATION',sys,rid,op[0],op[1],eid))
    phase_order={'FINDING':0,'REMEDIATION':1,'VERIFICATION':2}
    steps.sort(key=lambda s:(phase_order[s['phase']],OP_ORDER[s['operation']],s['system_id'],s['resource_id']))
    for i,s in enumerate(steps,1):s['step_no']=i
    return status,steps

def main():
    requests=read_csv(DATA/'deletion_requests.csv'); identities=read_csv(DATA/'user_identities.csv'); audits=read_csv(DATA/'user_audit_log.csv');manifest=read_csv(DATA/'evidence_files.csv'); rules=read_csv(DATA/'deletion_rules.csv'); activities=read_csv(DATA/'system_activity.csv')
    # Validate all required columns and output cardinality before writing.
    expected={'case_id','deletion_status','steps_json'}
    rows=[]
    for c in requests:
        status,steps=solve_case(c,identities,audits,manifest,rules,activities)
        rows.append({'case_id':c['case_id'],'deletion_status':status,'steps_json':json.dumps(steps,ensure_ascii=False,separators=(',',':'))})
    rows.sort(key=lambda x:x['case_id'])
    if len(rows)!=518 or len({r['case_id'] for r in rows})!=518: raise ValueError(f'expected 518 unique outputs, found {len(rows)}')
    for r in rows:
        if not set(r)==expected or r['deletion_status'] not in {'COMPLETE','INCOMPLETE','NOT_APPLICABLE'}:raise ValueError('invalid output row')
        parsed=json.loads(r['steps_json'])
        if not isinstance(parsed,list) or [s['step_no'] for s in parsed]!=list(range(1,len(parsed)+1)):raise ValueError('invalid steps array')
        if r['deletion_status']=='COMPLETE' and (not parsed or any(s['phase']!='VERIFICATION' or not s['evidence_id'] for s in parsed)):raise ValueError('COMPLETE requires evidence-backed verification')
    with OUT.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['case_id','deletion_status','steps_json'],lineterminator='\n');w.writeheader();w.writerows(rows)
    print(f'Wrote {len(rows)} rows to {OUT}')
    print('Statuses:',dict((s,sum(r['deletion_status']==s for r in rows)) for s in ('COMPLETE','INCOMPLETE','NOT_APPLICABLE')))
if __name__=='__main__':main()







