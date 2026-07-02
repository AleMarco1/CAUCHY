"""
CAUCHY — Phase 5, analisi preliminare Run A (1000/2000 campi)
src/phase5_analyze_run_a_partial.py

Carica le chain disponibili in results/phase5_hod_chains/,
calcola correlazione parziale e sigma su qualsiasi numero di sim completate.
Confronto diretto con B3.

Uso:
  python src/phase5_analyze_run_a_partial.py [--project_root .]
"""

import argparse
import json
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_perm", type=int, default=1000)
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

ROOT       = Path(args.project_root)
CHAINS_DIR = ROOT / "results" / "phase5_hod_chains"
PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / \
              "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
B3_FILE    = ROOT / "results" / "phase5_hod_b3_features.npz"

rng = np.random.default_rng(args.seed)

print("=" * 70)
print("CAUCHY Phase 5 — Analisi preliminare Run A")
print("=" * 70)

# Carica parametri cosmologici
cosmo   = np.loadtxt(PARAMS_FILE, comments='#')
w0_all  = cosmo[:, 6]
Omm_all = cosmo[:, 0]
s8_all  = cosmo[:, 4]

# Carica tutte le chain disponibili
chain_files = sorted(CHAINS_DIR.glob("chain_*.npz"))
print(f"\nChain trovate: {len(chain_files)}")

if len(chain_files) == 0:
    print("Nessuna chain trovata. Verifica il path.")
    exit(1)

# Estrai indici e feature marginalizzate
indices = []
feats_A = []
K_list  = []
ngal_list = []
t_list  = []

for cf in chain_files:
    data = np.load(cf)
    idx  = int(data['sim_idx'])
    feat = data['feat_marginalized'].astype(np.float32)
    K    = int(data.get('K_completed', data.get('K_requested', 10)))
    ngal = float(data.get('n_gal_list', np.array([0])).mean()) if 'n_gal_list' in data else 0.0
    t    = float(data.get('t_gudhi_mean_s', 0.0))

    indices.append(idx)
    feats_A.append(feat)
    K_list.append(K)
    ngal_list.append(ngal)
    t_list.append(t)

indices  = np.array(indices)
feats_A  = np.array(feats_A)   # [N, 8]
w0_sub   = w0_all[indices]
Omm_sub  = Omm_all[indices]
s8_sub   = s8_all[indices]
N        = len(indices)

print(f"Sim caricate: {N}")
print(f"Indici: [{indices.min()}, {indices.max()}]")
print(f"K medio: {np.mean(K_list):.1f}")
print(f"n_gal medio: {np.mean([x for x in ngal_list if x>0]):.0f}")
print(f"t_gudhi medio: {np.mean([x for x in t_list if x>0]):.1f}s")

feature_names = [
    'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
    'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
]

# Diagnosi feature
print(f"\n{'='*70}")
print("DIAGNOSI FEATURE Run A")
print(f"{'='*70}")
for j, name in enumerate(feature_names):
    f = feats_A[:, j]
    nz = (f != 0).sum()
    print(f"  {name:<25}: std={f.std():.4f}  zeros={N-nz:4d}/{N}  "
          f"range=[{f.min():.3f},{f.max():.3f}]")

# Feature valide
good = [j for j in range(8)
        if feats_A[:, j].std() > 0 and (feats_A[:, j] == 0).sum() / N < 0.10]
print(f"\nFeature usabili: {len(good)}/8 -> {[feature_names[j] for j in good]}")

# Correlazione parziale
print(f"\n{'='*70}")
print(f"CORRELAZIONE PARZIALE r(feature_A, w0 | Omm, s8) — N={N}")
print(f"{'='*70}")

X = np.column_stack([np.ones(N), Omm_sub, s8_sub])
rw = w0_sub - X @ np.linalg.lstsq(X, w0_sub, rcond=None)[0]

print(f"\n  {'Feature':<25} {'r_partial':>10} {'sigma_est':>10}")
print(f"  {'-'*48}")

r_vals = {}
for j in good:
    feat_j = feats_A[:, j]
    rf = feat_j - X @ np.linalg.lstsq(X, feat_j, rcond=None)[0]
    r, _ = pearsonr(rf, rw)
    # Stima sigma rapida con Fisher z-transform (no permutation)
    z = np.arctanh(abs(r))
    se = 1.0 / np.sqrt(N - 3)
    sigma_est = z / se
    r_vals[feature_names[j]] = (float(r), float(sigma_est))
    stars = "***" if sigma_est > 3 else ("**" if sigma_est > 2 else ("*" if sigma_est > 1 else ""))
    print(f"  {feature_names[j]:<25} {r:>10.4f} {sigma_est:>10.2f} {stars}")

# Permutation test su b2_mean_persistence (feature principale)
print(f"\nPermutation test N={args.n_perm} su b2_mean_persistence...")
bp = feats_A[:, 5]
rbp = bp - X @ np.linalg.lstsq(X, bp, rcond=None)[0]
r_obs = float(pearsonr(rbp, rw)[0])
nulls = np.array([pearsonr(rbp, rng.permutation(rw))[0] for _ in range(args.n_perm)])
sigma_b2 = (abs(r_obs) - abs(nulls.mean())) / nulls.std()
print(f"  r_obs = {r_obs:.4f}  sigma = {sigma_b2:.2f}σ")

# Combinazione ottimale
RF = np.column_stack([feats_A[:, j] - X @ np.linalg.lstsq(X, feats_A[:, j], rcond=None)[0]
                      for j in good])
beta = np.linalg.lstsq(RF, rw, rcond=None)[0]
comb = RF @ beta
r_comb = float(pearsonr(comb, rw)[0])
nulls_c = np.array([pearsonr(comb, rng.permutation(rw))[0] for _ in range(args.n_perm)])
sigma_comb = (abs(r_comb) - abs(nulls_c.mean())) / nulls_c.std()
print(f"\nCombinazione ottimale: r={r_comb:.4f}  sigma={sigma_comb:.2f}σ")

# Confronto con B3
print(f"\n{'='*70}")
print("CONFRONTO Run A vs B3")
print(f"{'='*70}")

if B3_FILE.exists():
    b3 = np.load(B3_FILE, allow_pickle=True)
    fvecs_b3 = b3['fvecs_hod_b3']

    # B3 sugli stessi indici di A per confronto equo
    fvecs_b3_sub = fvecs_b3[indices]
    X_b3 = X  # stesse covariate

    rw_b3 = w0_sub - X_b3 @ np.linalg.lstsq(X_b3, w0_sub, rcond=None)[0]
    bp_b3 = fvecs_b3_sub[:, 5]
    rbp_b3 = bp_b3 - X_b3 @ np.linalg.lstsq(X_b3, bp_b3, rcond=None)[0]
    r_b3 = float(pearsonr(rbp_b3, rw_b3)[0])
    nulls_b3 = np.array([pearsonr(rbp_b3, rng.permutation(rw_b3))[0]
                         for _ in range(args.n_perm)])
    sigma_b3 = (abs(r_b3) - abs(nulls_b3.mean())) / nulls_b3.std()

    RF_b3 = np.column_stack([
        fvecs_b3_sub[:, j] - X_b3 @ np.linalg.lstsq(X_b3, fvecs_b3_sub[:, j], rcond=None)[0]
        for j in good if fvecs_b3_sub[:, j].std() > 0
    ])
    beta_b3 = np.linalg.lstsq(RF_b3, rw_b3, rcond=None)[0]
    comb_b3 = RF_b3 @ beta_b3
    nulls_b3c = np.array([pearsonr(comb_b3, rng.permutation(rw_b3))[0]
                           for _ in range(args.n_perm)])
    sigma_b3_comb = (abs(pearsonr(comb_b3,rw_b3)[0]) - abs(nulls_b3c.mean())) / nulls_b3c.std()

    print(f"\n  Campione identico N={N} sim (indici {indices.min()}–{indices.max()}):")
    print(f"  {'':25} {'Run A (K=10)':>15} {'B3 (K=1)':>15}")
    print(f"  {'-'*57}")
    print(f"  {'b2_mean_persistence':25} {sigma_b2:>15.2f}σ {sigma_b3:>15.2f}σ")
    print(f"  {'combinazione ottimale':25} {sigma_comb:>15.2f}σ {sigma_b3_comb:>15.2f}σ")

    delta_b2   = sigma_b2   - sigma_b3
    delta_comb = sigma_comb - sigma_b3_comb
    print(f"\n  Guadagno marginalizzazione HOD (A - B3):")
    print(f"    b2_mean_persistence: {delta_b2:+.2f}σ")
    print(f"    combinazione:        {delta_comb:+.2f}σ")

    if abs(delta_b2) < 0.3:
        print(f"\n  INTERPRETAZIONE: A ≈ B3 — la marginalizzazione HOD non cambia")
        print(f"    sostanzialmente il segnale. B3 deterministico è sufficiente.")
    elif delta_b2 > 0.3:
        print(f"\n  INTERPRETAZIONE: A > B3 — la marginalizzazione HOD amplifica")
        print(f"    il segnale. K=10 campioni aggiungono informazione.")
    else:
        print(f"\n  INTERPRETAZIONE: A < B3 — la marginalizzazione HOD diluisce")
        print(f"    leggermente il segnale. Investigare.")
else:
    print("  B3 features non trovate per confronto.")

# Proiezione finale su 2000 sim
print(f"\n{'='*70}")
print(f"PROIEZIONE SU 2000 SIM (se il segnale scala come sqrt(N))")
print(f"{'='*70}")
# sigma scala come sqrt(N) se il segnale è costante
scale = np.sqrt(2000 / N)
print(f"  N corrente: {N}  ->  fattore scaling: {scale:.3f}")
print(f"  b2_mean_persistence: {sigma_b2:.2f} * {scale:.3f} = {sigma_b2*scale:.2f}σ (stima ottimista)")
print(f"  combinazione:        {sigma_comb:.2f} * {scale:.3f} = {sigma_comb*scale:.2f}σ (stima ottimista)")
print(f"  NOTA: stima ottimista — r_partial non scala esattamente come sqrt(N)")
print(f"        usa come ordine di grandezza, non come previsione precisa")

venue_b2   = "Nature Astronomy/PRL" if sigma_b2*scale >= 2 else "PRD" if sigma_b2*scale >= 1 else "JCAP"
venue_comb = "Nature Astronomy/PRL" if sigma_comb*scale >= 2 else "PRD" if sigma_comb*scale >= 1 else "JCAP"
print(f"\n  Venue proiettata (b2): {venue_b2}")
print(f"  Venue proiettata (comb): {venue_comb}")
print(f"{'='*70}")
