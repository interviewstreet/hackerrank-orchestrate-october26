"""Presentation-only mapping of Member Two results; audit decisions remain untouched."""
from notifications.slack import FINDINGS


def present(result):
    raw = result.to_dict()
    findings = []
    for i, f in enumerate(result.findings):
        level, title = FINDINGS.get(f.get('operation'), ('HIGH', 'Review finding'))
        findings.append({'id': f'finding-{i}', 'title': title, 'severity': level,
                         'system_id': f['system_id'], 'resource_id': f['resource_id'],
                         'evidence_id': f['evidence_id'], 'description': title})
    ids = {f['resource_id'] for f in findings}
    nodes = []
    for n in result.graph_data['nodes']:
        subject = n.get('type') == 'subject'
        nodes.append({'id': n['id'], 'type': 'IDENTITY' if subject else n['type'],
                      'label': 'Subject identity' if subject else n['id'],
                      'status': 'ISSUE' if n['id'] in ids else 'CONNECTED' if subject else 'VERIFIED' if n.get('status') == 'COMPLIANT' else 'PENDING',
                      'system_id': n.get('system', ''),
                      'evidence_ids': sorted({s['evidence_id'] for s in result.steps if s['resource_id'] == n['id'] and s['evidence_id']})})
    raw.update(identities=[], findings=findings,
               evidence=[{'id': e['evidence_id'], 'label': 'Audit evidence', 'captured_at': e['captured_at']} for e in result.evidence],
               graph_data={'nodes': nodes, 'edges': [{'id': f'edge-{i}', 'source': e['source'], 'target': e['target'],
                            'relationship': e['relation'], 'status': 'CONNECTED'} for i, e in enumerate(result.graph_data['edges'])]})
    return raw
