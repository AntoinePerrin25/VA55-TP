#!/usr/bin/env python3
"""Audit TP suivi de ligne, sans modifier les logs. python3 slidesTP1/audit_logs.py"""
import csv
import io
import json
import math
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
FILES = [
    ('bang_bang', 'logsPIDbetter/bang_bang.csv', None),
    ('droite', 'logsTP1/log_pid_STRAIGHT.csv', 50),
    ('tapis', 'logsPIDbetter/suivi_pid_tapis_spir.csv', 300),
]
def median(values):
    q = sorted(values); n = len(q)
    return (q[(n-1)//2] + q[n//2]) / 2

def main():
    result = {}
    for name, rel, limit in FILES:
        lines = (ROOT / rel).read_text().splitlines()
        old = lines[0].startswith('#meta')
        rows = list(csv.DictReader(io.StringIO('\n'.join(lines[1:] if old else lines)), delimiter=';' if old else ','))
        t = [float(r['Temps (s)' if old else 'time_ms']) / (1 if old else 1000) for r in rows]
        e = [float(r['Erreur' if old else 'error']) for r in rows]
        u = [float(r['Commande (deg/s)' if old else 'steering']) for r in rows]
        if not old:
            assert all(float(r['error']) == float(r['reflection']) - 50 for r in rows)
        record = dict(source=rel, samples=len(rows), log_duration_s=t[-1]-t[0], median_dt_ms=1000*median([b-a for a,b in zip(t,t[1:])]), mean_error=sum(e)/len(e), mae=sum(abs(x) for x in e)/len(e), rmse=math.sqrt(sum(x*x for x in e)/len(e)), max_abs_error=max(abs(x) for x in e))
        if limit:
            record['saturated_samples'] = sum(abs(x) >= limit for x in u)
            record['saturated_percent'] = 100 * record['saturated_samples'] / len(u)
        if name == 'bang_bang':
            assert all(float(r['steering']) == (-200 if float(r['reflection']) <= 20 else 200) for r in rows)
        if name == 'tapis':
            gains=(2,1.7,.035)
            reconstructed=[max(-300,min(300,sum(g*float(r[k]) for g,k in zip(gains,('error','integral','derivative'))))) for r in rows]
            residual=max(abs(a-b) for a,b in zip(reconstructed,u))
            assert residual < 1e-9
            record.update(verified_gains=gains, max_reconstruction_residual=residual)
        result[name] = record
    result['tapis_duplicate'] = (ROOT/'logsPIDbetter/suivi_pid_tapis.csv').read_bytes() == (ROOT/'logsPIDbetter/suivi_pid_tapis_spir.csv').read_bytes()
    print(json.dumps(result, ensure_ascii=False, indent=2))
if __name__ == '__main__':
    main()
