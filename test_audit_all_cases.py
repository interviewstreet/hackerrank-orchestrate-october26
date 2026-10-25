import csv
import json
import os
import glob
import re
import sqlite3

# Load dataset
with open('dataset/deletion_requests.csv') as f:
    requests = list(csv.DictReader(f))

with open('dataset/user_identities.csv') as f:
    identities = list(csv.DictReader(f))

with open('dataset/user_audit_log.csv') as f:
    audit_logs = list(csv.DictReader(f))

with open('dataset/evidence_files.csv') as f:
    evidence_manifest = {r['file_id']: r for r in csv.DictReader(f)}

with open('output.csv') as f:
    output_rows = {r['case_id']: r for r in csv.DictReader(f)}

print(f"Loaded {len(output_rows)} output rows for audit.")
