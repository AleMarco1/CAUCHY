"""Diagnosi struttura file Phase 6 input. Uso: python src/diagnose_phase6_inputs.py"""
import json, numpy as np
from pathlib import Path

ROOT = Path(".")

# BGS TDA features
bgs_file = ROOT / "results" / "phase6_bgs_tda_features.json"
print(f"=== {bgs_file} ===")
with open(bgs_file) as f:
    bgs = json.load(f)

def show_structure(d, prefix="", depth=0):
    if depth > 3: return
    for k, v in (d.items() if isinstance(d, dict) else []):
        if isinstance(v, dict):
            print(f"{prefix}{k}: {{")
            show_structure(v, prefix + "  ", depth+1)
            print(f"{prefix}}}")
        elif isinstance(v, list):
            print(f"{prefix}{k}: list[{len(v)}]  first={v[0] if v else '?'}")
        else:
            print(f"{prefix}{k}: {v}")

show_structure(bgs)

# Mock z=0.5
z05_file = ROOT / "results" / "phase6_mock_features_z05.npz"
print(f"\n=== {z05_file} ===")
z05 = np.load(z05_file)
for k in z05.keys():
    v = z05[k]
    if hasattr(v, 'shape'):
        print(f"  {k}: shape={v.shape} dtype={v.dtype}", end="")
        if v.ndim == 1 and len(v) <= 5:
            print(f"  val={v}")
        else:
            print()
