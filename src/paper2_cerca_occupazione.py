import json, os, sys
from pathlib import Path
from collections import Counter
root = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
pat = ("multipl", "occup", "molteplic", "shared", "n_gal_per_vox", "voxel_mult")
print("=== chiavi che somigliano a occupazione/molteplicita', nei registri ===")
def piatto(o, pre=""):
    out = {}
    for k, v in (o or {}).items():
        q = "%s.%s" % (pre, k) if pre else str(k)
        if isinstance(v, dict): out.update(piatto(v, q))
        else: out[q] = v
    return out
trovati = Counter()
for d in ("results",):
    for p in sorted((root / d).rglob("*.json*")):
        if p.stat().st_size > 60_000_000: continue
        try:
            if p.suffix == ".jsonl":
                with p.open("r", encoding="utf-8", errors="replace") as fh:
                    riga = next((l for l in fh if l.strip()), None)
                recs = [json.loads(riga)] if riga else []
            else:
                recs = [json.loads(p.read_text(encoding="utf-8", errors="replace"))]
        except Exception:
            continue
        for r in recs:
            if not isinstance(r, dict): continue
            for k in piatto(r):
                if any(x in k.lower() for x in pat):
                    trovati[(str(p.relative_to(root)), k)] += 1
for (f, k), _ in sorted(trovati.items()):
    print("  %-58s %s" % (f, k))
if not trovati:
    print("  nessuna")
