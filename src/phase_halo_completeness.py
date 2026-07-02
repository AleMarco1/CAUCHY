"""
CAUCHY — Diagnostica completezza catalogo FoF a log_Mmin~13.5
src/phase_halo_completeness.py

Obiettivo: verificare quanti aloni ha Quijote nwLH a soglia di massa
log_Mmin~13.5 (M☉/h) per diverse cosmologie, in particolare alle
cosmologie estreme (w₀ molto negativo, σ₈ basso) dove il catalogo
FoF potrebbe essere incompleto.

Questo determina la fattibilità della Strada 1 (HOD log_Mmin~13.5).

Metodo:
  Per N_SIM simulazioni selezionate a cosmologie diverse (w₀ estremo,
  w₀ centrale, σ₈ basso, σ₈ alto), conta:
  - N_halos(M > 10^13.0 M☉/h)
  - N_halos(M > 10^13.5 M☉/h)
  - N_halos(M > 10^14.0 M☉/h)
  - n_gal_HOD(log_Mmin=13.5) — con HOD B3 fixed
  Verifica se n_gal varia sistematicamente con w₀ e σ₈ in modo
  che la pipeline TDA abbia abbastanza struttura da misurare.

Output: results/phase_halo_completeness.json
Tempo stimato: ~5 min (20 sim × 3 soglie, solo conteggio)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.special import erf

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--seed",         type=int, default=42)
args = parser.parse_args()

ROOT        = Path(args.project_root)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
OUTPUT_JSON = RESULTS_DIR / "phase_halo_completeness.json"

SNAPNUM    = 4
N_PART_MIN = 20
BOXSIZE    = 1000.0

# Soglie di massa da testare
MMIN_TEST = [13.0, 13.5, 14.0]

# HOD B3 fixed (per stima n_gal a log_Mmin=13.5)
HOD_B3_FIXED = dict(sigma_logM=0.55, log_M0=12.25, log_M1=13.5, alpha=1.0)

print("=" * 70)
print("CAUCHY — Diagnostica completezza FoF a log_Mmin~13.5")
print("=" * 70)

# ---------------------------------------------------------------------------
# FoF reader
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Non trovato: {fname}"
        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N
        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            return
        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()
        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)


def count_halos_above(mass_h, log_Mmin):
    return int(np.sum(mass_h >= 10**log_Mmin))


def count_ngal_hod(mass_h, log_Mmin, hod_fixed, rng):
    """Conta n_gal HOD per dato log_Mmin (solo mean field, no scatter per velocità)."""
    sigma_logM = hod_fixed["sigma_logM"]
    log_M0     = hod_fixed["log_M0"]
    log_M1     = hod_fixed["log_M1"]
    alpha      = hod_fixed["alpha"]
    log_M = np.log10(mass_h + 1e-30)
    p_cen = 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))
    p_cen = np.clip(p_cen, 0.0, 1.0)
    n_cen = rng.binomial(1, p_cen).sum()
    M0 = 10**log_M0; M1 = 10**log_M1
    mask = mass_h > M0
    lam_sat = np.zeros(len(mass_h))
    lam_sat[mask] = ((mass_h[mask] - M0) / (M1 + 1e-30))**alpha
    lam_sat *= p_cen
    lam_sat = np.clip(lam_sat, 0.0, 1e4)
    n_sat = rng.poisson(lam_sat).sum()
    return int(n_cen + n_sat)


# ---------------------------------------------------------------------------
# Selezione simulazioni: campiona diversi angoli dello spazio parametri
# ---------------------------------------------------------------------------
print("\nCaricamento parametri cosmologici...")
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]

# Seleziona simulazioni che coprono gli angoli estremi
rng = np.random.default_rng(args.seed)

def select_n(mask, n, label):
    idx = np.where(mask)[0]
    chosen = rng.choice(idx, size=min(n, len(idx)), replace=False)
    print(f"  {label}: {len(idx)} disponibili, selezionate {len(chosen)}")
    return chosen

groups = {
    "w0_very_low   (w₀<-1.20)":         select_n(w0_all < -1.20, 5, "w₀<-1.20"),
    "w0_low        (-1.20≤w₀<-1.10)":   select_n((w0_all>=-1.20)&(w0_all<-1.10), 3, "-1.20≤w₀<-1.10"),
    "w0_central    (-1.05≤w₀≤-0.95)":   select_n((w0_all>=-1.05)&(w0_all<=-0.95), 4, "-1.05≤w₀≤-0.95"),
    "w0_high       (-0.90≥w₀>-0.80)":   select_n((w0_all>=-0.90)&(w0_all<=-0.80), 3, "-0.90≤w₀≤-0.80"),
    "w0_very_high  (w₀>-0.75)":         select_n(w0_all > -0.75, 3, "w₀>-0.75"),
    "s8_low        (σ₈<0.70)":          select_n(s8_all < 0.70, 3, "σ₈<0.70"),
    "s8_high       (σ₈>0.90)":          select_n(s8_all > 0.90, 3, "σ₈>0.90"),
}

all_selected = np.unique(np.concatenate(list(groups.values())))
print(f"\n  Totale simulazioni uniche: {len(all_selected)}")

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
print(f"\n{'Sim':>5} {'w0':>6} {'s8':>5} {'Om':>5} | "
      + " ".join(f"N_h(>={m:.0f})".rjust(14) for m in MMIN_TEST)
      + f" | {'n_gal(13.5)':>12} {'n_gal(13.0)':>12}")
print("-" * 110)

results = []
t_start = time.time()

for sim_idx in sorted(all_selected):
    sim_idx = int(sim_idx)
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    fname   = snapdir / f"groups_{SNAPNUM:03d}" / f"group_tab_{SNAPNUM:03d}.0"

    if not fname.exists():
        print(f"  {sim_idx:4d} SKIP")
        continue

    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        print(f"  {sim_idx:4d} EMPTY")
        continue

    mask   = FoF.GroupLen >= N_PART_MIN
    mass_h = FoF.GroupMass[mask] * 1e10

    w0_v  = float(w0_all[sim_idx])
    s8_v  = float(s8_all[sim_idx])
    Omm_v = float(Omm_all[sim_idx])

    # Conteggio aloni per soglia
    n_halos = {m: count_halos_above(mass_h, m) for m in MMIN_TEST}

    # n_gal HOD
    rng_hod = np.random.default_rng(args.seed + sim_idx)
    n_gal_135 = count_ngal_hod(mass_h, 13.5, HOD_B3_FIXED, rng_hod)
    n_gal_130 = count_ngal_hod(mass_h, 13.0, HOD_B3_FIXED, rng_hod)

    row_str = " ".join(f"{n_halos[m]:>12,}" for m in MMIN_TEST)
    print(f"  {sim_idx:4d} {w0_v:6.3f} {s8_v:5.3f} {Omm_v:5.3f} | "
          f"{row_str} | {n_gal_135:>12,} {n_gal_130:>12,}")

    results.append({
        "sim_idx": sim_idx,
        "w0": w0_v, "s8": s8_v, "Omm": Omm_v,
        "n_halos_13.0": n_halos[13.0],
        "n_halos_13.5": n_halos[13.5],
        "n_halos_14.0": n_halos[14.0],
        "n_gal_hod_13.5": n_gal_135,
        "n_gal_hod_13.0": n_gal_130,
    })

# ---------------------------------------------------------------------------
# Summary statistico
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("SUMMARY COMPLETEZZA")
print("=" * 70)

for key, label in [("n_halos_13.0", "N_halos(≥10^13.0)"),
                   ("n_halos_13.5", "N_halos(≥10^13.5)"),
                   ("n_halos_14.0", "N_halos(≥10^14.0)"),
                   ("n_gal_hod_13.5", "n_gal HOD(log_Mmin=13.5)"),
                   ("n_gal_hod_13.0", "n_gal HOD(log_Mmin=13.0)")]:
    vals = [r[key] for r in results]
    print(f"\n  {label}:")
    print(f"    mean={np.mean(vals):.0f}, std={np.std(vals):.0f}, "
          f"min={np.min(vals):.0f}, max={np.max(vals):.0f}")

    # Correlazione con w₀ e σ₈
    w0_arr = np.array([r["w0"] for r in results])
    s8_arr = np.array([r["s8"] for r in results])
    v_arr  = np.array(vals, dtype=float)
    if v_arr.std() > 0:
        r_w0 = float(np.corrcoef(w0_arr, v_arr)[0,1])
        r_s8 = float(np.corrcoef(s8_arr, v_arr)[0,1])
        print(f"    r(w₀) = {r_w0:+.3f},  r(σ₈) = {r_s8:+.3f}")

    # Verifica completezza: frazione sim con n > soglia minima per TDA
    min_viable = 200  # minimo galassie/aloni per TDA significativo
    frac_ok = np.mean(np.array(vals) >= min_viable)
    print(f"    Frazione sim con N≥{min_viable}: {frac_ok:.0%}")

# Verifica specifica per cosmologie estreme
print(f"\n  --- Focus su w₀ < -1.20 ---")
extreme = [r for r in results if r["w0"] < -1.20]
if extreme:
    for key in ["n_halos_13.5", "n_gal_hod_13.5"]:
        vals_e = [r[key] for r in extreme]
        print(f"  {key}: mean={np.mean(vals_e):.0f}, min={np.min(vals_e):.0f}")

# Raccomandazione
print()
print("=" * 70)
print("RACCOMANDAZIONE STRADA 1")
print("=" * 70)

n_gal_135_vals = [r["n_gal_hod_13.5"] for r in results]
n_gal_130_vals = [r["n_gal_hod_13.0"] for r in results]
mean_135 = np.mean(n_gal_135_vals)
min_135  = np.min(n_gal_135_vals)
mean_130 = np.mean(n_gal_130_vals)
min_130  = np.min(n_gal_130_vals)

TARGET_BGS = 573_000  # densità BGS DR1 NGC su Quijote

print(f"\n  Target densità BGS DR1 NGC su Quijote: {TARGET_BGS:,}")
print(f"\n  log_Mmin=13.5: n_gal_mean={mean_135:.0f}, n_gal_min={min_135:.0f}")
print(f"  log_Mmin=13.0: n_gal_mean={mean_130:.0f}, n_gal_min={min_130:.0f}")

# Trova il log_Mmin più vicino al target
if abs(mean_135 - TARGET_BGS) < abs(mean_130 - TARGET_BGS):
    best_mmin = 13.5
    best_mean = mean_135
    best_min  = min_135
else:
    best_mmin = 13.0
    best_mean = mean_130
    best_min  = min_130

print(f"\n  log_Mmin più vicino al target: {best_mmin}")
print(f"  n_gal medio: {best_mean:.0f}  (target {TARGET_BGS:,})")

if best_min < 100:
    verdict = "STRADA 1 NON FATTIBILE — alcune cosmologie estreme hanno n_gal < 100"
    feasible = False
elif best_min < 500:
    verdict = "STRADA 1 RISCHIOSA — alcune cosmologie estreme hanno n_gal < 500"
    feasible = True
else:
    verdict = "STRADA 1 FATTIBILE — n_gal > 500 in tutte le cosmologie testate"
    feasible = True

print(f"\n  VERDICT: {verdict}")

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "task":           "halo_completeness_diagnostic",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "target_ngal_bgs": TARGET_BGS,
    "mmin_test":      MMIN_TEST,
    "n_sim":          len(results),
    "summary": {
        "n_gal_hod_135": {"mean": float(mean_135), "min": float(min_135),
                           "max": float(np.max(n_gal_135_vals))},
        "n_gal_hod_130": {"mean": float(mean_130), "min": float(min_130),
                           "max": float(np.max(n_gal_130_vals))},
    },
    "recommendation": {
        "best_log_Mmin":  best_mmin,
        "verdict":        verdict,
        "feasible":       feasible,
    },
    "per_sim": results,
    "t_total_min": float((time.time() - t_start) / 60),
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Output: {OUTPUT_JSON}")
print(f"  Tempo: {(time.time()-t_start)/60:.1f} min")
print("=" * 70)
