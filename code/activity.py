import csv
import re

def parse_activities(act_path):
    # Hash maps for lookups
    act_by_res = {}      # resource_id -> list of activities
    non_del_accounts = set()
    catalog_links = {}   # resource_id -> {'email': ..., 'user_id': ...}
    
    with open(act_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows = list(r)
        i = 0
        n = len(rows)
        while i < n:
            a = rows[i]
            rid = a['resource_id']
            ev_type = a['event_type']
            details = a['details']
            
            if rid not in act_by_res:
                act_by_res[rid] = []
            act_by_res[rid].append(a)
            
            # Check for non-deletion classification
            if ev_type == 'CLASSIFY_REQUEST':
                non_del_accounts.add(rid)
            
            # Check for catalog links
            if ev_type == 'LINK_RESOURCE_IDENTITY':
                m1 = re.search(r'linked (\w+) .* to (\S+) and (\w+)', details)
                if m1:
                    catalog_links[m1.group(1)] = {
                        'email': m1.group(2).lower(),
                        'user_id': m1.group(3),
                        'time': a['event_time']
                    }
                m2 = re.search(r'confirmed (\w+) .* belongs only to (\S+) and (\w+)', details)
                if m2:
                    catalog_links[m2.group(1)] = {
                        'email': m2.group(2).lower(),
                        'user_id': m2.group(3),
                        'time': a['event_time']
                    }
            
            i += 1
            
    return act_by_res, non_del_accounts, catalog_links
