"""
Diagnosi tau_to_graph per Phase 5 Ramo B.
Esegue step-by-step su tau_field_0000.npz e stampa tutto.

Uso: python diagnose_tau_graph.py [--project_root .]
"""
import argparse
import numpy as np
from pathlib import Path
import json

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

ROOT    = Path(args.project_root)
TAU_DIR = ROOT / "results" / "phase2_tau_fields" / "nwlh"
PRIOR   = ROOT / "prior" / "gate3_prior_v1_0.json"

with open(PRIOR) as f:
    prior3 = json.load(f)

P90     = prior3["frozen_graph_construction"]["persistence_threshold_p90"]
MU_LCDM = prior3["frozen_tau_source"]["mu_lcdm_norm"]

print(f"P90      = {P90:.6f}")
print(f"MU_LCDM  = {MU_LCDM:.6f}")
print()

# --- Carica campo 0 ---
tau_file = TAU_DIR / "tau_field_0000.npz"
print(f"File: {tau_file}")
print(f"Esiste: {tau_file.exists()}")
print()

tau_data = np.load(tau_file)
print(f"Chiavi nel file .npz: {list(tau_data.keys())}")

tau_raw = tau_data['tau_grid']
print(f"\ntau_grid (raw):")
print(f"  dtype  = {tau_raw.dtype}")
print(f"  shape  = {tau_raw.shape}")
print(f"  min    = {tau_raw.min():.6f}")
print(f"  max    = {tau_raw.max():.6f}")
print(f"  mean   = {tau_raw.mean():.6f}")
print(f"  std    = {tau_raw.std():.6f}")
print(f"  p50    = {np.percentile(tau_raw, 50):.6f}")
print(f"  p90    = {np.percentile(tau_raw, 90):.6f}")
print(f"  p99    = {np.percentile(tau_raw, 99):.6f}")

if 'mu_lcdm' in tau_data:
    mu_field = tau_data['mu_lcdm']
    print(f"\nmu_lcdm nel file:")
    print(f"  shape = {mu_field.shape if hasattr(mu_field, 'shape') else 'scalar'}")
    print(f"  mean  = {float(mu_field.mean()):.6f}")
    print(f"  usato come mu_lcdm_field = {float(mu_field.mean()):.6f}")
    mu_lcdm_field = float(mu_field.mean())
else:
    print("\n[WARN] mu_lcdm NON presente nel file. Uso MU_LCDM dal prior.")
    mu_lcdm_field = MU_LCDM

print()

# --- Step 1: tau_norm ---
tau_norm_raw  = np.abs(tau_raw.astype(np.float64))
tau_norm_div  = tau_norm_raw / mu_lcdm_field

print(f"tau_norm SENZA divisione (tau_raw):")
print(f"  min={tau_norm_raw.min():.4f}  max={tau_norm_raw.max():.4f}  mean={tau_norm_raw.mean():.4f}")
print(f"tau_norm CON divisione (tau_raw / mu_lcdm_field):")
print(f"  min={tau_norm_div.min():.4f}  max={tau_norm_div.max():.4f}  mean={tau_norm_div.mean():.4f}")

# Conta celle > p90 in entrambi i casi
n_above_raw = (tau_norm_raw >= P90).sum()
n_above_div = (tau_norm_div >= P90).sum()
print(f"\nCelle >= P90={P90:.4f}:")
print(f"  SENZA divisione: {n_above_raw} / {tau_norm_raw.size} ({100*n_above_raw/tau_norm_raw.size:.1f}%)")
print(f"  CON divisione:   {n_above_div} / {tau_norm_div.size} ({100*n_above_div/tau_norm_div.size:.1f}%)")

# --- Step 2: TDA su entrambi ---
print(f"\n{'='*60}")
print("TDA con gudhi — test su ENTRAMBE le normalizzazioni")
print(f"{'='*60}")

import gudhi

for label, tau_norm in [("SENZA divisione", tau_norm_raw), ("CON divisione", tau_norm_div)]:
    print(f"\n--- {label} ---")
    field_neg = -tau_norm
    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()

    diag_1 = np.array(cc.persistence_intervals_in_dimension(1))
    diag_2 = np.array(cc.persistence_intervals_in_dimension(2))

    print(f"  dim1 features totali: {len(diag_1)}")
    print(f"  dim2 features totali: {len(diag_2)}")

    def analyze_diag(diag, dim, p90):
        if len(diag) == 0:
            print(f"  dim{dim}: VUOTO")
            return 0
        fin = np.isfinite(diag[:, 1])
        d = diag[fin]
        print(f"  dim{dim}: {len(diag)} totali, {fin.sum()} finiti")
        if len(d) == 0:
            return 0
        # Convenzione v3: birth=-col1, death=-col0
        birth = -d[:, 1]
        death = -d[:, 0]
        pers  = birth - death
        print(f"    birth:  min={birth.min():.4f}  max={birth.max():.4f}  mean={birth.mean():.4f}")
        print(f"    death:  min={death.min():.4f}  max={death.max():.4f}")
        print(f"    pers:   min={pers.min():.4f}  max={pers.max():.4f}  mean={pers.mean():.4f}")
        n_above = (pers >= p90).sum()
        print(f"    pers >= p90={p90:.4f}: {n_above} nodi")
        if len(pers) > 0:
            print(f"    p90 della distribuzione di persistenza: {np.percentile(pers, 90):.4f}")
        return n_above

    n1 = analyze_diag(diag_1, 1, P90)
    n2 = analyze_diag(diag_2, 2, P90)
    print(f"  => NODI TOTALI nel grafo: {n1 + n2}")

print(f"\n{'='*60}")
print("DIAGNOSI COMPLETATA")
print(f"{'='*60}")
print("\nInterpretazione attesa:")
print(f"  - nodes_mean ~1200-1400 con normalizzazione corretta")
print(f"  - Se entrambe danno ~0 nodi: problema nella convenzione birth/death")
print(f"  - Se 'CON divisione' da ~1200+ nodi: il fix e' corretto ma non applicato")
print(f"  - Se tau_grid ha gia' valori normalizzati (range ~[0,8]): il file e' gia' diviso")
