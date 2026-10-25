"""Compare predictions to gold. Usage: python evaluation/evaluate.py pred.csv gold.csv"""
import csv, json, sys
from collections import Counter

def load(p):
    return {r["case_id"]: (r["deletion_status"], json.loads(r["steps_json"]))
            for r in csv.DictReader(open(p, newline="", encoding="utf-8"))}

def key(s): return (s["phase"], s["operation"], s["system_id"], s["resource_id"])

def main(pred_p, gold_p):
    P, G = load(pred_p), load(gold_p)
    n = len(G); status_ok = seq_ok = 0
    tp = fp = fn = 0; field_ok = Counter(); field_n = Counter()
    for cid, (gs, gsteps) in G.items():
        ps, psteps = P.get(cid, (None, []))
        status_ok += ps == gs
        gk, pk = [key(s) for s in gsteps], [key(s) for s in psteps]
        seq_ok += gk == pk
        gset, pset = Counter(gk), Counter(pk)
        tp += sum((gset & pset).values()); fp += sum((pset - gset).values()); fn += sum((gset - pset).values())
        pmap = {key(s): s for s in psteps}
        for s in gsteps:
            m = pmap.get(key(s))
            for f in ("step_no", "state", "evidence_id"):
                field_n[f] += 1
                field_ok[f] += bool(m and m[f] == s[f])
    prec = tp / (tp + fp) if tp + fp else 1.0; rec = tp / (tp + fn) if tp + fn else 1.0
    f1 = 2 * prec * rec / (prec + rec) if prec + rec else 0.0
    print(f"cases={n} status_acc={status_ok/n:.3f} exact_sequence_acc={seq_ok/n:.3f}")
    print(f"step precision={prec:.3f} recall={rec:.3f} f1={f1:.3f}")
    for f in field_n: print(f"field {f}: {field_ok[f]/field_n[f]:.3f}")

if __name__ == "__main__": main(sys.argv[1], sys.argv[2])
