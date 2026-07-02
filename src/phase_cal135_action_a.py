"""
CAUCHY — Action A post-Reviewer Round 2
src/phase_cal135_action_a.py

Risolve Concern 1 e Concern 2 del Reviewer Round 2:

C1: Verifica robustezza z_anomalia cal135 v2 sul sottoinsieme
    density-controlled: simulazioni con n_gal∈[400K, 750K]
    Domanda: ⟨pers₁⟩_mock_subset è coerente con 0.260?

C2: Ricalcolo σ_partial(⟨pers₁⟩, w₀ | Ωm, σ₈) su cal135 v2
    completo (2000 sim, nessun fallback) — sostituisce il valore
    biased da Gruppo A v1 (N=925, fallback presente).

Output: results/phase_cal135_action_a.json
Tempo stimato: ~5 min (analisi su dati già calcolati)
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr

ROOT        = Path(".")
RESULTS_DIR = ROOT / "results"
CAL135_DIR  = RESULTS_DIR / "phase_b3_cal135_v2_fields"

FEAT_FILE   = RESULTS_DIR / "phase_b3_cal135_v2_features.npz"
PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / \
              "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
OUTPUT      = RESULTS_DIR / "phase_cal135_action_a.json"

# Riferimenti
B2_BGS      = 0.459
B2_BGS_ERR  = 0.005
B2_B3_MEAN  = 0.292
B2_B3_STD   = 0.028
Z_B3        = 5.96

# Finestra density-controlled (Reviewer Concern 1)
# ±30% attorno al target 573K → [400K, 750K]
N_GAL_DC_LO = 400_000
N_GAL_DC_HI = 750_000

N_PERM = 1000

print("=" * 70)
print("CAUCHY — Action A: density-controlled subset + σ_partial cal135 v2")
print("=" * 70)
print(f"\n  Finestra density-controlled: [{N_GAL_DC_LO:,}, {N_GAL_DC_HI:,}]")
print(f"  (±30% attorno a target 573K)")
print(f"  N_perm permutation test: {N_PERM}")

# ---------------------------------------------------------------------------
# Carica features cal135 v2
# ---------------------------------------------------------------------------
assert FEAT_FILE.exists(), f"File non trovato: {FEAT_FILE}"
data  = np.load(FEAT_FILE)
fvecs = data["fvecs_hod_cal135"]   # [2000, 8]
w0    = data["w0"]
Omm   = data["Omm"]
s8    = data["s8"]
n_sim = len(fvecs)
print(f"\n  Caricato: {n_sim} simulazioni cal135 v2")

# Carica n_gal da checkpoint
print("  Lettura n_gal dai checkpoint...")
n_gal_arr = np.zeros(n_sim, dtype=np.int64)
missing = 0
for sim_idx in range(n_sim):
    cf = CAL135_DIR / f"cal135_{sim_idx:04d}.npz"
    if cf.exists():
        c = np.load(cf, allow_pickle=True)
        n_gal_arr[sim_idx] = int(c["n_gal"])
    else:
        missing += 1
if missing > 0:
    print(f"  WARN: {missing} checkpoint mancanti — n_gal=0 per queste sim")
print(f"  n_gal medio: {n_gal_arr.mean():.0f} ± {n_gal_arr.std():.0f}")
print(f"  n_gal range: [{n_gal_arr.min():.0f}, {n_gal_arr.max():.0f}]")

cosmo_params = np.loadtxt(PARAMS_FILE, comments='#')
FEAT_IDX = 5  # b2_mean_persistence = ⟨pers₁⟩

# ---------------------------------------------------------------------------
# Partial correlation utility
# ---------------------------------------------------------------------------
def partial_corr(x, y, Z):
    Z_aug = np.column_stack([np.ones(len(y)), Z])
    def res(v):
        c, *_ = np.linalg.lstsq(Z_aug, v, rcond=None)
        return v - Z_aug @ c
    r, p = pearsonr(res(x), res(y))
    return float(r), float(p)

def permutation_sigma(feat, w0_arr, controls, n_perm, seed=42):
    r_obs, p_obs = partial_corr(feat, w0_arr, controls)
    rng = np.random.default_rng(seed)
    r_null = np.array([
        partial_corr(feat, rng.permutation(w0_arr), controls)[0]
        for _ in range(n_perm)
    ])
    sigma = (abs(r_obs) - np.mean(np.abs(r_null))) / (np.std(r_null) + 1e-12)
    return float(sigma), float(r_obs), float(p_obs), \
           float(np.mean(r_null)), float(np.std(r_null))

# ---------------------------------------------------------------------------
# C2 — σ_partial su cal135 v2 COMPLETO (2000 sim, nessun fallback)
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("C2 — σ_partial(⟨pers₁⟩, w₀ | Ωm, σ₈) su cal135 v2 completo")
print("=" * 70)

# Escludi solo sim con n_gal=0 (catalogo FoF vuoto — caso estremo)
valid_all = n_gal_arr > 0
b2_all    = fvecs[valid_all, FEAT_IDX]
w0_all    = w0[valid_all]
Omm_all   = Omm[valid_all]
s8_all    = s8[valid_all]
ctrl_all  = np.column_stack([Omm_all, s8_all])

print(f"\n  N validi (n_gal > 0): {valid_all.sum()}/{n_sim}")
print(f"  ⟨pers₁⟩ mean: {b2_all.mean():.4f} ± {b2_all.std():.4f}")

t0 = time.time()
print(f"  Permutation test (N={N_PERM})...")
sigma_v2, r_v2, p_v2, r_null_mean_v2, r_null_std_v2 = permutation_sigma(
    b2_all, w0_all, ctrl_all, N_PERM, seed=42
)
print(f"\n  r_partial(⟨pers₁⟩, w₀ | Ωm,σ₈) = {r_v2:+.4f}  p={p_v2:.4f}")
print(f"  σ_partial (N={N_PERM}) = {sigma_v2:.3f}σ")
print(f"  null: mean={r_null_mean_v2:.4f}, std={r_null_std_v2:.4f}")
print(f"  Tempo: {time.time()-t0:.1f}s")

if sigma_v2 >= 2.0:
    c2_verdict = f"CITABILE — σ_partial={sigma_v2:.2f}σ ≥ 2σ su campione non biased"
elif sigma_v2 >= 1.5:
    c2_verdict = f"MARGINALE — σ_partial={sigma_v2:.2f}σ, citabile come 'indizio debole'"
else:
    c2_verdict = f"NON CITABILE — σ_partial={sigma_v2:.2f}σ < 1.5σ su campione non biased"
print(f"\n  → {c2_verdict}")

# ---------------------------------------------------------------------------
# C1 — ⟨pers₁⟩ e z_anomalia su sottoinsieme density-controlled
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print(f"C1 — Sottoinsieme density-controlled: n_gal∈[{N_GAL_DC_LO:,},{N_GAL_DC_HI:,}]")
print("=" * 70)

dc_mask = (n_gal_arr >= N_GAL_DC_LO) & (n_gal_arr <= N_GAL_DC_HI)
n_dc    = dc_mask.sum()
print(f"\n  Simulazioni nel sottoinsieme: {n_dc}/{n_sim} ({n_dc/n_sim*100:.1f}%)")

if n_dc < 50:
    print(f"  WARN: N={n_dc} troppo piccolo per analisi affidabile")
    b2_dc_mean = float(np.nan)
    b2_dc_std  = float(np.nan)
    z_dc       = float(np.nan)
    sigma_dc   = float(np.nan)
    c1_verdict = "INSUFFICIENTE — troppo poche simulazioni nel sottoinsieme"
else:
    b2_dc   = fvecs[dc_mask, FEAT_IDX]
    w0_dc   = w0[dc_mask]
    Omm_dc  = Omm[dc_mask]
    s8_dc   = s8[dc_mask]
    ctrl_dc = np.column_stack([Omm_dc, s8_dc])

    b2_dc_mean = float(np.mean(b2_dc))
    b2_dc_std  = float(np.std(b2_dc))
    z_dc       = float((B2_BGS - b2_dc_mean) / b2_dc_std)

    n_gal_dc = n_gal_arr[dc_mask]
    print(f"  n_gal nel sottoinsieme: {n_gal_dc.mean():.0f} ± {n_gal_dc.std():.0f}")
    print(f"  ⟨pers₁⟩ DC mean: {b2_dc_mean:.4f} ± {b2_dc_std:.4f}")
    print(f"  z_anomalia DC:   {z_dc:+.2f}σ")
    print(f"  (vs cal135 v2 full: +9.45σ, vs B3: +5.96σ)")

    # Shift rispetto al full sample
    shift = b2_dc_mean - b2_all.mean()
    print(f"\n  Shift DC vs full: {shift:+.4f} "
          f"({'più alto' if shift > 0 else 'più basso'} del full sample)")
    print(f"  → Se più alto: le sim con n_gal basso abbassavano il full mean")
    print(f"  → Se comparabile (|shift|<0.010): full sample è robusto")

    # σ_partial nel sottoinsieme
    print(f"\n  σ_partial nel sottoinsieme (N={N_PERM})...")
    t0 = time.time()
    sigma_dc, r_dc, p_dc, *_ = permutation_sigma(
        b2_dc, w0_dc, ctrl_dc, N_PERM, seed=42
    )
    print(f"  r_partial = {r_dc:+.4f}  p={p_dc:.4f}")
    print(f"  σ_partial = {sigma_dc:.3f}σ  ({time.time()-t0:.1f}s)")

    # Verifica coerenza
    if abs(shift) < 0.010:
        c1_verdict = (f"ROBUSTO — ⟨pers₁⟩_DC={b2_dc_mean:.4f} coerente con "
                      f"full sample (shift={shift:+.4f}). z_DC={z_dc:+.2f}σ.")
    elif b2_dc_mean > b2_all.mean():
        c1_verdict = (f"GONFIATO — full sample z={9.45:.2f}σ sovrastima. "
                      f"Valore corretto: z_DC={z_dc:+.2f}σ. "
                      f"Shift={shift:+.4f} (sim a basso n_gal abbassavano il mean).")
    else:
        c1_verdict = (f"CONSERVATIVO — full sample z={9.45:.2f}σ sottostima. "
                      f"Valore DC: z_DC={z_dc:+.2f}σ. Shift={shift:+.4f}.")

    print(f"\n  → {c1_verdict}")

# ---------------------------------------------------------------------------
# Analisi n_gal vs ⟨pers₁⟩ — verifica dipendenza diretta
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("Dipendenza ⟨pers₁⟩ da n_gal (verifica confounding)")
print("=" * 70)

# Correlazione diretta ⟨pers₁⟩ vs n_gal
r_ngal, p_ngal = pearsonr(b2_all, np.log10(n_gal_arr[valid_all] + 1))
print(f"\n  r(⟨pers₁⟩, log n_gal) = {r_ngal:+.4f}  p={p_ngal:.6f}")
if abs(r_ngal) > 0.3:
    print(f"  WARN: correlazione forte con n_gal — la partial corr su Ωm/σ₈")
    print(f"  potrebbe non rimuovere completamente il confounding da n_gal")
else:
    print(f"  OK: correlazione debole con n_gal")

# Partial correlation ⟨pers₁⟩ vs w₀ aggiungendo log(n_gal) come covariata
print(f"\n  Partial corr con log(n_gal) come covariata aggiuntiva...")
log_ngal = np.log10(n_gal_arr[valid_all] + 1)
ctrl_with_ngal = np.column_stack([Omm_all, s8_all, log_ngal])
sigma_ngal_ctrl, r_ngal_ctrl, p_ngal_ctrl, *_ = permutation_sigma(
    b2_all, w0_all, ctrl_with_ngal, N_PERM, seed=42
)
print(f"  r_partial(⟨pers₁⟩, w₀ | Ωm,σ₈,n_gal) = {r_ngal_ctrl:+.4f}  p={p_ngal_ctrl:.4f}")
print(f"  σ_partial = {sigma_ngal_ctrl:.3f}σ")
print(f"  (vs senza n_gal: {sigma_v2:.3f}σ)")

# ---------------------------------------------------------------------------
# Summary finale
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("SUMMARY ACTION A")
print("=" * 70)
print(f"\n  --- C2: σ_partial cal135 v2 completo ---")
print(f"  σ_partial(⟨pers₁⟩, w₀ | Ωm,σ₈) = {sigma_v2:.3f}σ  (N=2000, unbiased)")
print(f"  → {c2_verdict}")

print(f"\n  --- C1: Sottoinsieme density-controlled [400K,750K] ---")
if not np.isnan(z_dc):
    print(f"  N_DC = {n_dc}, ⟨pers₁⟩_DC = {b2_dc_mean:.4f}±{b2_dc_std:.4f}")
    print(f"  z_anomalia_DC = {z_dc:+.2f}σ  (vs full +9.45σ)")
    print(f"  → {c1_verdict}")
else:
    print(f"  N_DC = {n_dc} — sottoinsieme troppo piccolo")

print(f"\n  --- Confounding n_gal ---")
print(f"  r(⟨pers₁⟩, log n_gal) = {r_ngal:+.4f}")
print(f"  σ_partial con n_gal controllato = {sigma_ngal_ctrl:.3f}σ")

print(f"\n  --- Quadro completo z_anomalia ---")
print(f"  B3 originale (log_Mmin=12.5):      z = +5.96σ")
print(f"  Cal135 v2 full (log_Mmin=13.5):    z = +9.45σ")
if not np.isnan(z_dc):
    print(f"  Cal135 v2 DC  (n_gal∈[400K,750K]): z = {z_dc:+.2f}σ")

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "task":           "cal135_action_a_reviewer_round2",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "concern_C2_sigma_partial_v2": {
        "n_sims":        int(valid_all.sum()),
        "r_partial":     float(r_v2),
        "p_value":       float(p_v2),
        "sigma_partial": float(sigma_v2),
        "r_null_mean":   float(r_null_mean_v2),
        "r_null_std":    float(r_null_std_v2),
        "n_perm":        N_PERM,
        "verdict":       c2_verdict,
        "note":          "Cal135 v2 completo, nessun fallback — sostituisce "
                         "valore biased da Gruppo A v1 (N=925)",
    },
    "concern_C1_density_controlled": {
        "n_gal_window":  [N_GAL_DC_LO, N_GAL_DC_HI],
        "n_sims_dc":     int(n_dc),
        "frac_dc":       float(n_dc / n_sim),
        "b2_mean_dc":    float(b2_dc_mean) if not np.isnan(b2_dc_mean) else None,
        "b2_std_dc":     float(b2_dc_std)  if not np.isnan(b2_dc_std)  else None,
        "z_anomaly_dc":  float(z_dc)       if not np.isnan(z_dc)       else None,
        "sigma_partial_dc": float(sigma_dc) if not np.isnan(z_dc)      else None,
        "shift_vs_full": float(b2_dc_mean - b2_all.mean()) if not np.isnan(b2_dc_mean) else None,
        "verdict":       c1_verdict,
    },
    "ngal_confounding": {
        "r_b2_log_ngal":          float(r_ngal),
        "p_b2_log_ngal":          float(p_ngal),
        "sigma_partial_with_ngal": float(sigma_ngal_ctrl),
        "sigma_partial_without_ngal": float(sigma_v2),
        "delta_sigma":            float(sigma_v2 - sigma_ngal_ctrl),
    },
    "z_anomaly_summary": {
        "B3_original":     5.96,
        "cal135_v2_full":  9.45,
        "cal135_v2_DC":    float(z_dc) if not np.isnan(z_dc) else None,
        "BGS_value":       B2_BGS,
        "B3_mock_mean":    B2_B3_MEAN,
        "cal135_v2_mock_mean": float(b2_all.mean()),
        "cal135_v2_DC_mock_mean": float(b2_dc_mean) if not np.isnan(b2_dc_mean) else None,
    },
    "traceability": {
        "features_source": "results/phase_b3_cal135_v2_features.npz",
        "n_gal_source":    "results/phase_b3_cal135_v2_fields/cal135_XXXX.npz",
        "reviewer_concern": "Round 2 NON-BLOCKING C1+C2 (2026-06-14)",
    },
}

with open(OUTPUT, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Output: {OUTPUT}")
print("=" * 70)
