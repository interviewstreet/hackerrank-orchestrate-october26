import os
import csv
import json
import re

try:
    import fitz
except ImportError:
    fitz = None

def parse_all_evidence(ds_dir, id_to_uid):
    ev_manifest_path = os.path.join(ds_dir, 'evidence_files.csv')
    manifest = []
    fid_to_row = {}
    path_to_fid = {}
    
    with open(ev_manifest_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        manifest = list(r)
        i = 0
        n = len(manifest)
        while i < n:
            row = manifest[i]
            fid = row['file_id']
            fpath = row['file_path']
            fid_to_row[fid] = row
            path_to_fid[fpath] = fid
            i += 1
            
    # Structured evidence store:
    # uid -> list of observations:
    # {
    #   'system_id': ..., 'resource_id': ..., 'file_id': ..., 'captured_at': ...,
    #   'state': ..., 'is_finding': bool, 'finding_op': ..., 'finding_state': ...,
    #   'remed_op': ..., 'remed_state': ..., 'verif_op': ..., 'verif_state': ...
    # }
    user_observations = {}
    file_raw_text = {}
    
    # Pre-cache text of all files for fast matching
    fi = 0
    fn = len(manifest)
    while fi < fn:
        mrow = manifest[fi]
        fid = mrow['file_id']
        rel_p = mrow['file_path']
        full_p = os.path.join(ds_dir, rel_p)
        
        txt = ""
        if rel_p.endswith('.pdf') and fitz:
            try:
                doc = fitz.open(full_p)
                for page in doc:
                    txt += page.get_text() + "\n"
            except:
                pass
        elif not rel_p.endswith('.png'):
            try:
                with open(full_p, mode='r', encoding='utf-8', errors='ignore') as f:
                    txt = f.read()
            except:
                pass
        file_raw_text[fid] = txt.lower()
        fi += 1
        
    return fid_to_row, path_to_fid, file_raw_text
