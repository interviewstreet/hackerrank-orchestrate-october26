import csv

def build_id_map(ident_path, audit_path):
    # Hash maps for O(1) lookups
    u_map = {}  # uid -> dict of identifiers
    e_to_u = {} # email (lower) -> uid
    p_to_u = {} # phone -> uid
    h_to_u = {} # hash -> uid
    
    # Read identities
    with open(ident_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        rows = list(r)
        i = 0
        n = len(rows)
        while i < n:
            row = rows[i]
            uid = row['user_id']
            em = row['email'].strip().lower()
            ph = row['phone'].strip()
            eh = row['email_hash'].strip().lower()
            nm = row['name'].strip()
            
            u_map[uid] = {
                'user_id': uid,
                'names': {nm} if nm else set(),
                'emails': {em} if em else set(),
                'phones': {ph} if ph else set(),
                'hashes': {eh} if eh else set()
            }
            if em:
                e_to_u[em] = uid
            if ph:
                p_to_u[ph] = uid
            if eh:
                h_to_u[eh] = uid
            i += 1

    # Read audit log for historical transitions (BFS / transitive closure)
    with open(audit_path, mode='r', encoding='utf-8') as f:
        r = csv.DictReader(f)
        a_rows = list(r)
        j = 0
        m = len(a_rows)
        while j < m:
            ar = a_rows[j]
            uid = ar['user_id']
            fn = ar['field_name']
            old_v = ar['old_value'].strip()
            new_v = ar['new_value'].strip()
            
            if uid in u_map:
                if fn == 'email':
                    if old_v:
                        u_map[uid]['emails'].add(old_v.lower())
                        e_to_u[old_v.lower()] = uid
                    if new_v:
                        u_map[uid]['emails'].add(new_v.lower())
                        e_to_u[new_v.lower()] = uid
                elif fn == 'phone':
                    if old_v:
                        u_map[uid]['phones'].add(old_v)
                        p_to_u[old_v] = uid
                    if new_v:
                        u_map[uid]['phones'].add(new_v)
                        p_to_u[new_v] = uid
                elif fn == 'email_hash':
                    if old_v:
                        u_map[uid]['hashes'].add(old_v.lower())
                        h_to_u[old_v.lower()] = uid
                    if new_v:
                        u_map[uid]['hashes'].add(new_v.lower())
                        h_to_u[new_v.lower()] = uid
                elif fn == 'name':
                    if old_v:
                        u_map[uid]['names'].add(old_v)
                    if new_v:
                        u_map[uid]['names'].add(new_v)
            j += 1

    return u_map, e_to_u, p_to_u, h_to_u

def resolve_uid(email, e_to_u):
    if not email:
        return None
    em = email.strip().lower()
    return e_to_u.get(em)
