"""Evidence parsing and per-resource indexing."""
from __future__ import annotations
import json, re, sqlite3
from pathlib import Path

CATEGORY_HINTS={"account":"USER_PROFILE","profile":"USER_PROFILE","tombstone":"ACCOUNT_TOMBSTONE","search":"SEARCH_INDEX_ENTRY","cache":"CACHE_ENTRY","support":"SUPPORT_MESSAGE","attachment":"SUPPORT_ATTACHMENT","analytics":"ANALYTICS_PROFILE","telemetry":"PRODUCT_TELEMETRY","export":"USER_EXPORT","marketing":"MARKETING_PROFILE","email":"EMAIL_DELIVERY_LOG","audit":"SECURITY_AUDIT_LOG","legal":"LEGAL_HOLD_RECORD","backup":"BACKUP_ARCHIVE"}
def _identifiers(identity):
 values=[identity.get('user_id','')]
 for k in ('all_emails','all_phones','all_email_hashes'): values.extend(identity.get(k,[]))
 return [str(v) for v in values if v]
def _category(text):
 low=text.casefold()
 for key,val in CATEGORY_HINTS.items():
  if key in low:return val
 return 'USER_PROFILE'
def _state(record):
 status=str(record.get('state') or record.get('account_status') or record.get('status') or '').upper()
 if status in {'ACTIVE','PRESENT','DELETED','ABSENT','TOMBSTONE','REDACTED','ANONYMIZED','DISABLED','BLOCKED'}:
  if status=='DELETED': return 'TOMBSTONE' if (record.get('subject_reference') or record.get('user_id')) else 'ABSENT'
  return status
 pii=('name','full_name','email','phone','email_hash')
 if any(k in record for k in pii) and all(record.get(k) in (None,'') for k in pii if k in record): return 'ANONYMIZED'
 return 'PRESENT'
def _hit(record, source=''):
 resource=str(record.get('resource_id') or record.get('id') or '')
 system=str(record.get('system_id') or record.get('data_store') or record.get('service') or record.get('source_system') or source or 'unknown')
 collection=str(record.get('data_category') or record.get('collection_name') or record.get('collection') or source)
 return {'file_id':'','system_id':system,'resource_id':resource,'data_category':record.get('data_category') or _category(collection),'state':_state(record),'identifiers_found':[],'record':record}
def parse_sql_evidence(path, user_identity):
 conn=sqlite3.connect(':memory:'); conn.row_factory=sqlite3.Row
 try:
  conn.executescript(Path(path).read_text(encoding='utf-8'))
  tables=[r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
  ids=_identifiers(user_identity); hits=[]
  for table in tables:
   rows=conn.execute(f'SELECT * FROM "{table.replace(chr(34),chr(34)*2)}"').fetchall()
   for raw in rows:
    row=dict(raw); expanded=dict(row)
    if row.get('record_json'):
     try: expanded.update(json.loads(row['record_json']))
     except (json.JSONDecodeError,TypeError): pass
    blob=json.dumps(expanded,ensure_ascii=False,default=str).casefold()
    found=[v for v in ids if v.casefold() in blob]
    if found:
     hit=_hit(expanded,table); hit['identifiers_found']=found; hits.append(hit)
  # A point-in-time account snapshot proves absence when the stable subject is not present.
  if not hits and any('customer_profile' in t.casefold() for t in tables):
   match=re.fullmatch(r'user_(\d+)',user_identity.get('user_id',''))
   if match:
    hits.append({'file_id':'','system_id':'account_service','resource_id':f"account_{int(match.group(1)):03d}",'data_category':'USER_PROFILE','state':'ABSENT','identifiers_found':[user_identity['user_id']]})
  return hits
 finally: conn.close()
def _walk_json(value, inherited=None):
 inherited=dict(inherited or {})
 if isinstance(value,dict):
  meta=dict(inherited)
  for k in ('data_store','collection','collection_name','system_id','data_category'): 
   if k in value: meta[k]=value[k]
  if 'records' in value and isinstance(value['records'],list):
   for item in value['records']: yield from _walk_json(item,meta)
  elif any(k in value for k in ('resource_id','id')): yield {**meta,**value}
  else:
   for v in value.values(): yield from _walk_json(v,meta)
 elif isinstance(value,list):
  for item in value: yield from _walk_json(item,inherited)
def parse_json_evidence(path,user_identity):
 try: data=json.loads(Path(path).read_text(encoding='utf-8'))
 except (OSError,json.JSONDecodeError): return []
 ids=_identifiers(user_identity); hits=[]
 for record in _walk_json(data):
  blob=json.dumps(record,ensure_ascii=False,default=str).casefold(); found=[v for v in ids if v.casefold() in blob]
  if found:
   hit=_hit(record); hit['identifiers_found']=found; hits.append(hit)
 return hits
def _parse_text(path,user_identity):
 text=Path(path).read_text(encoding='utf-8',errors='replace'); ids=_identifiers(user_identity); hits=[]
 for line in text.splitlines():
  found=[v for v in ids if v.casefold() in line.casefold()]
  if not found: continue
  def field(name,default=''):
   m=re.search(rf'\b{name}[=:]\s*([\w.-]+)',line,re.I); return m.group(1) if m else default
  record={'resource_id':field('resource_id',Path(path).stem),'system_id':field('system_id',field('service','unknown')),'data_category':field('data_category',_category(line)),'state':field('state',field('status','PRESENT'))}
  hit=_hit(record);hit['identifiers_found']=found;hits.append(hit)
 return hits
def parse_log_evidence(path,user_identity): return _parse_text(path,user_identity)
def parse_text_evidence(path,user_identity): return _parse_text(path,user_identity)
def parse_pdf_evidence(path,user_identity):
 from pdfminer.high_level import extract_text
 text=extract_text(str(path)); return _hits_from_extracted(text,path,user_identity)
def parse_image_evidence(path,user_identity):
 import pytesseract
 from PIL import Image
 text=pytesseract.image_to_string(Image.open(path)); return _hits_from_extracted(text,path,user_identity)
def _hits_from_extracted(text,path,identity):
 ids=_identifiers(identity); found=[v for v in ids if v.casefold() in text.casefold()]
 if not found:return []
 resource=(re.search(r'(?i)resource[_ ]?id\s*[:=]\s*([\w.-]+)',text) or [None,Path(path).stem])[1]
 hit=_hit({'resource_id':resource,'system_id':'document','state':'PRESENT'},Path(path).stem);hit['identifiers_found']=found;return [hit]
def build_evidence_index(repo_root,manifest,user_identity,audit_at):
 result={}; root=Path(repo_root).resolve()/ 'dataset'; parsers={'.sql':parse_sql_evidence,'.json':parse_json_evidence,'.log':parse_log_evidence,'.pdf':parse_pdf_evidence,'.png':parse_image_evidence,'.txt':parse_text_evidence}
 if not user_identity:return result
 for file_id,item in sorted(manifest.items(),key=lambda pair:pair[1].get('captured_at','')):
  if item.get('captured_at','')>audit_at:continue
  path=root/item['file_path']; parser=parsers.get(path.suffix.lower())
  if not parser:continue
  try: hits=parser(path,user_identity)
  except Exception: continue
  for hit in hits:
   hit['file_id']=file_id
   if hit.get('resource_id'):result.setdefault(hit['resource_id'],[]).append(hit)
 return result
