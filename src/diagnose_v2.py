"""
Diagnosi tau_to_graph v2 — testa convenzione birth/death corretta.
Uso: python diagnose_v2.py [--project_root .]
"""
import argparse, numpy as np, json, gudhi
from pathlib import Path

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()
ROOT = Path(args.project_root)

with open(ROOT / "prior" / "gate3_prior_v1_0.json") as f:
    prior3 = json.load(f)
P90 = prior3["frozen_graph_construction"]["persistence_threshold_p90"]
print(f"P90 frozen = {P90:.6f}\n")

tau_data = np.load(ROOT / "results" / "phase2_tau_fields" / "nwlh" / "tau_field_0000.npz")
tau_norm = np.abs(tau_data['tau_grid'].astype(np.float64))
print(f"tau_norm: min={tau_norm.min():.4f}  max={tau_norm.max():.4f}  mean={tau_norm.mean():.4f}")
print(f"p90 empirico campo: {np.percentile(tau_norm, 90):.4f}\n")

cc = gudhi.CubicalComplex(dimensions=list(tau_norm.shape), top_dimensional_cells=(-tau_norm).flatten())
cc.compute_persistence()
diag_1 = np.array(cc.persistence_intervals_in_dimension(1))
diag_2 = np.array(cc.persistence_intervals_in_dimension(2))
print(f"dim1: {len(diag_1)} features   dim2: {len(diag_2)} features\n")

def test(diag, dim, col_b, col_d, label):
    fin = np.isfinite(diag[:, 1]); d = diag[fin]
    if len(d) == 0: print(f"  dim{dim} [{label}]: VUOTO"); return 0
    birth = -d[:, col_b]; death = -d[:, col_d]; pers = birth - death
    above = (pers >= P90).sum()
    print(f"  dim{dim} [{label}]: pers=[{pers.min():.3f},{pers.max():.3f}] mean={pers.mean():.4f}  "
          f"p90_emp={np.percentile(pers,90):.4f}  nodi>={P90:.4f}: {above}")
    return above

print("=== birth=-col1, death=-col0  (convenzione v3-orig) ===")
print(f"  NODI: {test(diag_1,1,1,0,'v3')+test(diag_2,2,1,0,'v3')}\n")

print("=== birth=-col0, death=-col1  (convenzione CORRETTA?) ===")
print(f"  NODI: {test(diag_1,1,0,1,'fix')+test(diag_2,2,0,1,'fix')}\n")

print(f"Atteso con convenzione corretta: ~1200-1400 nodi")
