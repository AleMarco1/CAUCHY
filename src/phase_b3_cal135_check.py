"""
CAUCHY — Verifica fallback cal135
src/phase_b3_cal135_check.py

Verifica che il risultato z=+8.65σ non sia dominato dai 1075 campi
in fallback log_Mmin=13.0, separando l'analisi in tre gruppi:
  - Gruppo A: 925 campi con log_Mmin=13.5 puro
  - Gruppo B: 1075 campi con fallback log_Mmin=13.0
  - Gruppo C: tutti i 2000 campi (risultato principale)

Se ⟨pers₁⟩_A ≈ ⟨pers₁⟩_B → il fallback non introduce bias sistematico
Se ⟨pers₁⟩_A ≠ ⟨pers₁⟩_B → la sistematica del fallback va dichiarata

Uso:
  python src/phase_b3_cal135_check.py
"""

import json
import numpy as np
from pathlib import Path
from scipy.stats import pearsonr

ROOT        = Path(".")
RESULTS_DIR = ROOT / "results"
CAL135_DIR  = RESULTS_DIR / "phase_b3_cal135_fields"

FEAT_FILE   = RESULTS_DIR / "phase_b3_cal135_features.npz"
DIAG_FILE   = RESULTS_DIR / "phase_b3_cal135_diagnostics.json"
PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / \
              "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"

# Riferimenti
B2_BGS      = 0.459
B2_BGS_ERR  = 0.005
B2_B3_MEAN  = 0.292
B2_B3_STD   = 0.028

print("=" * 70)
print("CAUCHY — Verifica fallback cal135 (13.5 puro vs 13.0 fallback)")
print("=" * 70)

# ---------------------------------------------------------------------------
# Carica dati
# ---------------------------------------------------------------------------
assert FEAT_FILE.exists(), f"File non trovato: {FEAT_FILE}"

data  = np.load(FEAT_FILE)
fvecs = data["fvecs_hod_cal135"]   # [2000, 8]
w0    = data["w0"]
Omm   = data["Omm"]
s8    = data["s8"]

cosmo_params = np.loadtxt(PARAMS_FILE, comments='#')

# Leggi hod_used e n_gal dai checkpoint per campo
print("Lettura checkpoint per campo...")
diags_list = []
n_sim = len(fvecs)
for sim_idx in range(n_sim):
    cache_file = CAL135_DIR / f"cal135_{sim_idx:04d}.npz"
    if cache_file.exists():
        c = np.load(cache_file, allow_pickle=True)
        diags_list.append({
            "sim_idx":  sim_idx,
            "status":   str(c["status"]),
            "n_gal":    int(c["n_gal"]),
            "hod_used": str(c["hod_used"]),
        })
    else:
        diags_list.append({
            "sim_idx":  sim_idx,
            "status":   "MISSING",
            "n_gal":    0,
            "hod_used": "unknown",
        })
print(f"  Letti {len(diags_list)} checkpoint")

# ---------------------------------------------------------------------------
# Separa i campi per hod_used
# ---------------------------------------------------------------------------

idx_135_pure  = []   # log_Mmin=13.5 puro
idx_130_fb    = []   # fallback log_Mmin=13.0
idx_dm_fb     = []   # fallback DM (da escludere)

for d in diags_list:
    i = d["sim_idx"]
    s = d["status"]
    h = d.get("hod_used", "DM")
    if "FALLBACK_DM" in s:
        idx_dm_fb.append(i)
    elif "13.0_fallback" in h:
        idx_130_fb.append(i)
    else:
        idx_135_pure.append(i)

idx_135_pure = np.array(idx_135_pure)
idx_130_fb   = np.array(idx_130_fb)
idx_dm_fb    = np.array(idx_dm_fb)

print(f"\n  Campi log_Mmin=13.5 puro:    {len(idx_135_pure)}")
print(f"  Campi log_Mmin=13.0 fallback: {len(idx_130_fb)}")
print(f"  Campi fallback DM:            {len(idx_dm_fb)}")

# ---------------------------------------------------------------------------
# ⟨pers₁⟩ per gruppo
# ---------------------------------------------------------------------------
FEAT_IDX = 5  # b2_mean_persistence

def stats(idx, label):
    if len(idx) == 0:
        print(f"\n  {label}: nessun campo")
        return None, None, None
    vals = fvecs[idx, FEAT_IDX]
    m = float(np.mean(vals))
    s = float(np.std(vals))
    z = (B2_BGS - m) / s
    print(f"\n  {label} (N={len(idx)}):")
    print(f"    ⟨pers₁⟩ = {m:.4f} ± {s:.4f}")
    print(f"    z_anomalia = {z:+.2f}σ")

    # n_gal per questo gruppo
    ngal_vals = [d["n_gal"] for d in diags_list if d["sim_idx"] in set(idx.tolist())]
    if ngal_vals:
        print(f"    n_gal medio = {np.mean(ngal_vals):.0f} ± {np.std(ngal_vals):.0f}")
        print(f"    n_gal range = [{np.min(ngal_vals):.0f}, {np.max(ngal_vals):.0f}]")
    return m, s, z

print()
print("--- ⟨pers₁⟩ per gruppo ---")
m_135, s_135, z_135 = stats(idx_135_pure, "Gruppo A — log_Mmin=13.5 puro")
m_130, s_130, z_130 = stats(idx_130_fb,   "Gruppo B — fallback log_Mmin=13.0")

# Tutti i campi HOD (esclude DM fallback)
idx_all_hod = np.concatenate([idx_135_pure, idx_130_fb])
m_all, s_all, z_all = stats(idx_all_hod, "Gruppo C — tutti HOD (risultato principale)")

# ---------------------------------------------------------------------------
# Test di differenza sistematica
# ---------------------------------------------------------------------------
print()
print("--- Test bias sistematico ---")
if m_135 is not None and m_130 is not None:
    delta = m_135 - m_130
    # Errore sulla differenza
    n_a = len(idx_135_pure); n_b = len(idx_130_fb)
    se_delta = np.sqrt(s_135**2/n_a + s_130**2/n_b)
    t_delta  = abs(delta) / se_delta
    print(f"\n  Δ⟨pers₁⟩ (13.5 − 13.0) = {delta:+.4f} ± {se_delta:.4f}")
    print(f"  t-statistic = {t_delta:.2f}σ")
    if t_delta < 2.0:
        bias_verdict = "NO BIAS SISTEMATICO — i due gruppi hanno ⟨pers₁⟩ compatibile"
    else:
        bias_verdict = f"BIAS SISTEMATICO PRESENTE — Δ={delta:+.4f} a {t_delta:.1f}σ"
    print(f"  → {bias_verdict}")

# ---------------------------------------------------------------------------
# Partial correlation w₀ per gruppo A (13.5 puro)
# ---------------------------------------------------------------------------
print()
print("--- Partial correlation w₀ (Gruppo A — 13.5 puro) ---")

if len(idx_135_pure) > 50:
    b2_a    = fvecs[idx_135_pure, FEAT_IDX]
    w0_a    = w0[idx_135_pure]
    Omm_a   = Omm[idx_135_pure]
    s8_a    = s8[idx_135_pure]
    ctrl_a  = np.column_stack([Omm_a, s8_a])

    def partial_corr(x, y, Z):
        Z_aug = np.column_stack([np.ones(len(y)), Z])
        def res(v):
            c, *_ = np.linalg.lstsq(Z_aug, v, rcond=None)
            return v - Z_aug @ c
        r, p = pearsonr(res(x), res(y))
        return float(r), float(p)

    r_pc, p_pc = partial_corr(b2_a, w0_a, ctrl_a)

    # Permutation test rapido (N=500)
    rng = np.random.default_rng(42)
    r_null = np.array([
        partial_corr(b2_a, rng.permutation(w0_a), ctrl_a)[0]
        for _ in range(500)
    ])
    sigma_pc = (abs(r_pc) - np.mean(np.abs(r_null))) / (np.std(r_null) + 1e-12)

    print(f"\n  r_partial(⟨pers₁⟩, w₀ | Ωm,σ₈) = {r_pc:+.4f}  p={p_pc:.4f}")
    print(f"  σ_partial (permutation N=500) = {sigma_pc:.3f}σ")
    print(f"  r_null mean={np.mean(r_null):.4f}, std={np.std(r_null):.4f}")
else:
    print(f"  N={len(idx_135_pure)} — troppo pochi per partial correlation affidabile")

# ---------------------------------------------------------------------------
# Cosmologie dominanti nel fallback 13.0
# ---------------------------------------------------------------------------
print()
print("--- Caratteristiche cosmologiche del fallback 13.0 ---")
if len(idx_130_fb) > 0:
    Omm_fb = Omm[idx_130_fb]
    w0_fb  = w0[idx_130_fb]
    s8_fb  = s8[idx_130_fb]
    print(f"  Ωm:  mean={Omm_fb.mean():.3f}, std={Omm_fb.std():.3f}, "
          f"range=[{Omm_fb.min():.3f},{Omm_fb.max():.3f}]")
    print(f"  w₀:  mean={w0_fb.mean():.3f}, std={w0_fb.std():.3f}, "
          f"range=[{w0_fb.min():.3f},{w0_fb.max():.3f}]")
    print(f"  σ₈:  mean={s8_fb.mean():.3f}, std={s8_fb.std():.3f}, "
          f"range=[{s8_fb.min():.3f},{s8_fb.max():.3f}]")
    print(f"  Confronto con 13.5 puro:")
    Omm_p = Omm[idx_135_pure]; w0_p = w0[idx_135_pure]; s8_p = s8[idx_135_pure]
    print(f"  Ωm (puro): mean={Omm_p.mean():.3f}  (fallback: {Omm_fb.mean():.3f})")
    print(f"  σ₈ (puro): mean={s8_p.mean():.3f}  (fallback: {s8_fb.mean():.3f})")
    print(f"  Nota: se Ωm_fallback > Ωm_puro → fallback in cosmologie ad alta densità")

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("SUMMARY VERIFICA FALLBACK")
print("=" * 70)
print(f"\n  Gruppo A (13.5 puro, N={len(idx_135_pure)}):  "
      f"⟨pers₁⟩={m_135:.4f}±{s_135:.4f}, z={z_135:+.2f}σ")
print(f"  Gruppo B (13.0 fallback, N={len(idx_130_fb)}): "
      f"⟨pers₁⟩={m_130:.4f}±{s_130:.4f}, z={z_130:+.2f}σ")
print(f"  Gruppo C (tutti, N={len(idx_all_hod)}):        "
      f"⟨pers₁⟩={m_all:.4f}±{s_all:.4f}, z={z_all:+.2f}σ")
print(f"\n  BGS riferimento: {B2_BGS}±{B2_BGS_ERR}")
print(f"  B3 riferimento:  {B2_B3_MEAN}±{B2_B3_STD}")
if m_135 is not None and m_130 is not None:
    print(f"\n  Bias fallback: {bias_verdict}")
    if t_delta < 2.0:
        print(f"  → Risultato principale (z={z_all:+.2f}σ) è affidabile")
        print(f"  → Il fallback non introduce bias sistematico dichiarabile")
    else:
        lo, hi = (min(z_135,z_130), max(z_135,z_130))
        print(f"  → Dichiarare nel paper: z_anomalia ∈ [{lo:.1f}σ, {hi:.1f}σ] ")
        print(f"     a seconda della scelta HOD per cosmologie estreme")
print("=" * 70)
