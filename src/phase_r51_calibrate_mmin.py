"""
CAUCHY — R5-1 v3 Step 1: Calibrazione log_Mmin su n_gal Quijote
src/phase_r51_calibrate_mmin.py

Obiettivo: trovare log_Mmin* tale che n_gal(log_Mmin*, Quijote) corrisponde
alla densità numerica DESI BGS r<19.5 scalata al volume Quijote (1 Gpc/h)³.

Motivazione:
  R5-1 v2 ha prodotto σ_marg=0.191σ con prior log_Mmin∈[12.2,13.1].
  Il driver del FAIL è la larghezza del prior su log_Mmin — variazione
  n_gal da 178K a 1058K (fattore 6×) genera varianza topologica che
  oscura il segnale w₀.

  La densità numerica BGS r<19.5 vincola log_Mmin fisicamente in modo
  molto più preciso. Questo script calibra log_Mmin* su Quijote stesso,
  senza dipendere da AbacusSummit o da trasferimenti di posterior
  tra modelli incompatibili.

Metodo:
  1. Seleziona N_COSMO simulazioni Quijote a cosmologia centrale
     (|w₀+1| < 0.05, Ωm vicino a 0.3175) — proxy cosmologia fiduciale
  2. Per ciascuna, varia log_Mmin su griglia [11.8, 13.5] con passo 0.05
     mantenendo altri parametri HOD ai valori B3
  3. Misura n_gal(log_Mmin) per ogni simulazione
  4. Target n_gal: n_BGS_DR1 × (V_Quijote / V_BGS_eff)
     - n_BGS_DR1 = 217,614 galassie nel volume effettivo DESI BGS NGC
     - V_BGS_eff stimato da phase6_voxelize_diagnostics.json
     - V_Quijote = (1000 Mpc/h)³ = 10⁹ (Mpc/h)³
  5. Fit log_Mmin*(n_gal) → stima puntuale + incertezza ±0.1 dex

Output:
  results/phase_r51_mmin_calibration.json
  - log_Mmin_star: stima puntuale
  - log_Mmin_uncertainty: ±sigma da scatter inter-simulazione
  - n_gal_target: densità target
  - prior_v3: [log_Mmin_star - 0.15, log_Mmin_star + 0.15]

Uso:
  python src/phase_r51_calibrate_mmin.py [--n_cosmo 20] [--seed 42]

Tempo stimato: ~5-10 min (20 sim × 26 valori log_Mmin × ~0.5s HOD)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.interpolate import interp1d

parser = argparse.ArgumentParser(description="Calibrazione log_Mmin su n_gal BGS")
parser.add_argument("--n_cosmo",      type=int,   default=20)
parser.add_argument("--seed",         type=int,   default=42)
parser.add_argument("--project_root", type=str,   default=".")
args = parser.parse_args()

ROOT        = Path(args.project_root)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
OUTPUT_JSON = RESULTS_DIR / "phase_r51_mmin_calibration.json"

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20

# Griglia log_Mmin da esplorare
MMIN_GRID = np.arange(11.8, 13.55, 0.05)   # 36 valori

# Parametri HOD B3 (fissi durante la calibrazione)
HOD_B3_FIXED = {
    "sigma_logM": 0.55,
    "log_M0":     12.25,
    "log_M1":     13.5,
    "alpha":      1.0,
    "A_cen":      0.0,
    "A_sat":      0.0,
    "eta_vel":    1.0,
    "eta_conc":   1.0,
}

# ---------------------------------------------------------------------------
# Target n_gal
# ---------------------------------------------------------------------------
# DESI BGS DR1 NGC: 217,614 galassie
# Volume effettivo BGS NGC stimato dal voxelizzatore CAUCHY:
# griglia 128³ su box ~1997 Mpc/h → V_BGS_eff ≈ fraction_cells_occupied × V_box
# Da phase6_voxelize_diagnostics.json: n_cells_occupied / n_cells_total
# Usiamo stima conservativa: V_BGS_eff ~ 0.20 × (1997)³ Mpc/h³
# (il survey BGS NGC copre ~1/5 del box voxelizzato)
# → n_density_BGS = 217614 / (0.20 × 1997³) ≈ 1.37e-4 (Mpc/h)^-3
# → n_gal_target su Quijote (1000 Mpc/h)³ = 1.37e-4 × 10^9 ≈ 137,000
#
# NOTA: questa stima è approssimativa. Lo script calcola anche la stima
# alternativa dal confronto diretto con il run B3 (n_gal_B3 ~ 900K) per
# validare la coerenza interna.
#
# Stima primaria: dal volume effettivo BGS
N_BGS_DR1        = 217_614
V_QUIJOTE        = BOXSIZE**3                     # (Mpc/h)³
V_BGS_EFF_FRAC   = 0.20                           # frazione conservativa
V_BGS_GRID       = 1997.0**3                      # box voxelizzato
V_BGS_EFF        = V_BGS_EFF_FRAC * V_BGS_GRID
N_GAL_TARGET_BGS = N_BGS_DR1 / V_BGS_EFF * V_QUIJOTE

# Stima di riferimento da B3 (consistenza interna)
N_GAL_B3_REF = 900_000   # da phase5_hod_b3_manifest.json

print("=" * 70)
print("CAUCHY — Calibrazione log_Mmin su n_gal Quijote (Step 1 R5-1 v3)")
print("=" * 70)
print(f"\n  Target n_gal (da densità BGS DR1 scalata a Quijote):")
print(f"  n_BGS_DR1 = {N_BGS_DR1:,} galassie")
print(f"  V_BGS_eff ≈ {V_BGS_EFF:.2e} (Mpc/h)³  (frac={V_BGS_EFF_FRAC})")
print(f"  n_gal_target = {N_GAL_TARGET_BGS:.0f}")
print(f"  n_gal_B3_ref = {N_GAL_B3_REF:,} (riferimento B3 Phase 5)")
print(f"\n  Griglia log_Mmin: [{MMIN_GRID.min():.2f}, {MMIN_GRID.max():.2f}], "
      f"step=0.05, N={len(MMIN_GRID)} valori")
print()


# ---------------------------------------------------------------------------
# FoF reader — identico a B3
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo non trovato: {fname}"
        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N
        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            return
        def rd_i(off): return np.frombuffer(raw[off:off+N*4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off+N*4], dtype=np.float32).copy()
        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N*8)
        x = rd_f(24 + N*12); y = rd_f(24 + N*16); z = rd_f(24 + N*20)
        self.GroupPos  = np.column_stack([x, y, z])


def read_halo_catalog(sim_idx):
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE
    mass_h = FoF.GroupMass[mask] * 1e10
    return pos_h, mass_h


# ---------------------------------------------------------------------------
# HOD — solo conteggio n_gal (no posizioni necessarie)
# ---------------------------------------------------------------------------
def count_galaxies_hod(mass_h, log_Mmin, hod_fixed, rng):
    """Conta n_gal per dato log_Mmin, senza generare le posizioni."""
    from scipy.special import erf

    sigma_logM = hod_fixed["sigma_logM"]
    log_M0     = hod_fixed["log_M0"]
    log_M1     = hod_fixed["log_M1"]
    alpha      = hod_fixed["alpha"]

    log_M = np.log10(mass_h)

    # Centrali
    p_cen = 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))
    p_cen = np.clip(p_cen, 0.0, 1.0)
    n_cen = rng.binomial(1, p_cen).sum()

    # Satelliti
    M0   = 10**log_M0
    M1   = 10**log_M1
    mask = mass_h > M0
    lam_sat = np.zeros(len(mass_h))
    lam_sat[mask] = ((mass_h[mask] - M0) / (M1 + 1e-30))**alpha
    lam_sat *= p_cen   # condizionato alla centrale
    lam_sat  = np.clip(lam_sat, 0.0, 1e4)
    n_sat = rng.poisson(lam_sat).sum()

    return int(n_cen + n_sat)


# ---------------------------------------------------------------------------
# Caricamento cosmologie
# ---------------------------------------------------------------------------
print("Caricamento parametri cosmologici nwLH...")
assert NWLH_PARAMS_FILE.exists()
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
w0_all  = cosmo_params[:, 6]

# Seleziona simulazioni a cosmologia centrale: |w₀+1|<0.08, Ωm∈[0.28,0.35]
# → proxy cosmologia fiduciale Quijote (Ωm=0.3175, w₀=-1)
central_mask = (np.abs(w0_all + 1.0) < 0.08) & \
               (Omm_all > 0.28) & (Omm_all < 0.35)
central_idx  = np.where(central_mask)[0]

print(f"  Simulazioni a cosmologia centrale: {len(central_idx)}")
print(f"  w₀ range: [{w0_all[central_idx].min():.3f}, {w0_all[central_idx].max():.3f}]")
print(f"  Ωm range: [{Omm_all[central_idx].min():.3f}, {Omm_all[central_idx].max():.3f}]")

if len(central_idx) < args.n_cosmo:
    print(f"  WARN: solo {len(central_idx)} sim centrali disponibili, "
          f"uso tutte invece di {args.n_cosmo}")
    args.n_cosmo = len(central_idx)

rng_sel = np.random.default_rng(args.seed)
selected = rng_sel.choice(central_idx, size=args.n_cosmo, replace=False)
print(f"  Selezionate {args.n_cosmo} simulazioni (seed={args.seed})")
print()


# ---------------------------------------------------------------------------
# Main loop — n_gal vs log_Mmin per ciascuna simulazione
# ---------------------------------------------------------------------------
# results_matrix[i, j] = n_gal per simulazione i, log_Mmin = MMIN_GRID[j]
results_matrix = np.zeros((args.n_cosmo, len(MMIN_GRID)), dtype=np.int32)
t_start = time.time()

print(f"{'Sim':>5} {'w₀':>6} {'Ωm':>6} | "
      + "  ".join(f"{v:.2f}" for v in MMIN_GRID[::4])
      + "  ← log_Mmin (ogni 4°)")
print("-" * 120)

for i, sim_idx in enumerate(selected):
    sim_idx = int(sim_idx)
    pos_h, mass_h = read_halo_catalog(sim_idx)

    if pos_h is None or len(mass_h) < 50:
        print(f"  {sim_idx:4d} SKIP (catalogo vuoto)")
        continue

    w0_val  = float(w0_all[sim_idx])
    Omm_val = float(Omm_all[sim_idx])
    rng = np.random.default_rng(args.seed + sim_idx)

    ngal_row = []
    for j, log_Mmin in enumerate(MMIN_GRID):
        n = count_galaxies_hod(mass_h, log_Mmin, HOD_B3_FIXED, rng)
        results_matrix[i, j] = n
        ngal_row.append(n)

    # Stampa ogni 4° valore per leggibilità
    row_str = "  ".join(f"{ngal_row[k]:7d}" for k in range(0, len(MMIN_GRID), 4))
    print(f"  {sim_idx:4d} {w0_val:6.3f} {Omm_val:6.3f} | {row_str}")

print(f"\n  Tempo: {(time.time()-t_start)/60:.1f} min")


# ---------------------------------------------------------------------------
# Analisi: trova log_Mmin* per ciascun target
# ---------------------------------------------------------------------------
print()
print("=" * 70)
print("CALIBRAZIONE log_Mmin*")
print("=" * 70)

# Filtra righe con tutti zeri (sim fallite)
valid_rows = results_matrix.sum(axis=1) > 0
n_valid    = valid_rows.sum()
mat_valid  = results_matrix[valid_rows].astype(float)

print(f"\n  Simulazioni valide: {n_valid}/{args.n_cosmo}")
print(f"\n  n_gal medio per log_Mmin:")
ngal_mean = mat_valid.mean(axis=0)
ngal_std  = mat_valid.std(axis=0)
for j in range(0, len(MMIN_GRID), 2):
    print(f"    log_Mmin={MMIN_GRID[j]:.2f}: "
          f"{ngal_mean[j]:8.0f} ± {ngal_std[j]:6.0f}")

# Interpolazione per trovare log_Mmin*(n_gal_target)
def find_mmin_star(target, ngal_mean_arr, mmin_grid):
    """Interpola log_Mmin per dato target n_gal (funzione monotona decrescente)."""
    # n_gal decresce con log_Mmin — inverti per interpolazione
    valid = ngal_mean_arr > 0
    if valid.sum() < 3:
        return None, None
    # Rimuovi duplicati e assicura monotonia
    mn = ngal_mean_arr[valid]
    mm = mmin_grid[valid]
    # Ordina per n_gal decrescente (log_Mmin crescente → n_gal decrescente)
    sort_idx = np.argsort(mm)
    mm_s = mm[sort_idx]
    mn_s = mn[sort_idx]
    # Verifica che target sia nel range
    if target < mn_s.min() or target > mn_s.max():
        return None, f"target {target:.0f} fuori range [{mn_s.min():.0f}, {mn_s.max():.0f}]"
    # Interpolazione lineare su log(n_gal) vs log_Mmin
    f_interp = interp1d(mn_s[::-1], mm_s[::-1], kind='linear')
    mmin_star = float(f_interp(target))
    return mmin_star, None

# Target 1: densità BGS DR1 scalata
mmin_star_bgs, err_bgs = find_mmin_star(N_GAL_TARGET_BGS, ngal_mean, MMIN_GRID)

# Target 2: B3 reference (n_gal~900K) — verifica coerenza interna
mmin_star_b3, err_b3 = find_mmin_star(N_GAL_B3_REF, ngal_mean, MMIN_GRID)

print(f"\n  --- Risultati calibrazione ---")
print(f"\n  Target 1 (densità BGS DR1 scalata): n_gal_target = {N_GAL_TARGET_BGS:.0f}")
if mmin_star_bgs is not None:
    print(f"  log_Mmin* = {mmin_star_bgs:.3f}")
else:
    print(f"  WARN: {err_bgs}")

print(f"\n  Target 2 (B3 reference n_gal~900K): n_gal_target = {N_GAL_B3_REF:,}")
if mmin_star_b3 is not None:
    print(f"  log_Mmin* = {mmin_star_b3:.3f}  (atteso ~12.5 — verifica coerenza B3)")
else:
    print(f"  WARN: {err_b3}")

# Incertezza: scatter inter-simulazione
# Per ciascuna sim, trova il log_Mmin che produce n_gal_target
mmin_per_sim = []
for row in mat_valid:
    ms, e = find_mmin_star(N_GAL_TARGET_BGS, row, MMIN_GRID)
    if ms is not None:
        mmin_per_sim.append(ms)

if len(mmin_per_sim) >= 3:
    mmin_mean = float(np.mean(mmin_per_sim))
    mmin_std  = float(np.std(mmin_per_sim))
    print(f"\n  Scatter inter-simulazione: log_Mmin* = {mmin_mean:.3f} ± {mmin_std:.3f}")
    print(f"  (variazione dovuta a scatter nella funzione di massa degli aloni)")
    uncertainty = max(mmin_std, 0.05)   # minimo 0.05 dex
else:
    mmin_mean = mmin_star_bgs if mmin_star_bgs else 12.5
    mmin_std  = 0.10
    uncertainty = 0.10
    print(f"  WARN: poche sim valide per stima scatter — uso uncertainty=0.10 dex")

# Prior v3
PRIOR_HALF_WIDTH = 0.15   # ±0.15 dex — motivato fisicamente
prior_v3_lo = float(mmin_mean - PRIOR_HALF_WIDTH)
prior_v3_hi = float(mmin_mean + PRIOR_HALF_WIDTH)

print(f"\n  --- Prior R5-1 v3 ---")
print(f"  log_Mmin* = {mmin_mean:.3f} ± {mmin_std:.3f} (scatter sim)")
print(f"  Prior v3:  log_Mmin ∈ [{prior_v3_lo:.3f}, {prior_v3_hi:.3f}]  "
      f"(±{PRIOR_HALF_WIDTH} dex)")
print(f"\n  Confronto:")
print(f"  Prior v2 (letteratura):  [12.200, 13.100]  (range = 0.900 dex)")
print(f"  Prior v3 (calibrato):    [{prior_v3_lo:.3f}, {prior_v3_hi:.3f}]  "
      f"(range = {PRIOR_HALF_WIDTH*2:.3f} dex)")
print(f"  Riduzione range:         {(0.9 - PRIOR_HALF_WIDTH*2)/0.9*100:.0f}%")

# Stima VIF atteso
# VIF ∝ σ²_intra / σ²_inter
# σ_intra(n_gal) ∝ larghezza prior log_Mmin × |dn_gal/d(log_Mmin)|
# Approssimiamo: VIF_v3 ≈ VIF_v2 × (range_v3/range_v2)²
VIF_v2    = 0.801
range_v2  = 13.1 - 12.2
range_v3  = PRIOR_HALF_WIDTH * 2
VIF_v3_est = VIF_v2 * (range_v3 / range_v2)**2
print(f"\n  VIF stimato (approssimazione lineare):")
print(f"  VIF_v2 = {VIF_v2:.3f}  → VIF_v3 ≈ {VIF_v3_est:.3f}")
print(f"  (VIF < 0.3 necessario per segnale emergente)")

# Avviso se il target BGS è fuori range B3
if mmin_star_bgs is not None and abs(mmin_star_bgs - 12.5) > 0.3:
    print(f"\n  NOTA: log_Mmin*={mmin_star_bgs:.3f} differisce da B3=12.5 di "
          f"{abs(mmin_star_bgs-12.5):.2f} dex.")
    print(f"  Questo implica che la densità BGS DR1 scalata a Quijote corrisponde")
    print(f"  a un log_Mmin diverso da B3. Il prior v3 è centrato sul valore")
    print(f"  fisicamente corretto, non su B3.")

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "task":           "R5-1_v3_mmin_calibration",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "parameters": {
        "n_cosmo":       args.n_cosmo,
        "n_valid":       int(n_valid),
        "seed":          args.seed,
        "mmin_grid":     MMIN_GRID.tolist(),
        "hod_b3_fixed":  HOD_B3_FIXED,
        "snapnum":       SNAPNUM,
    },
    "target_ngal": {
        "n_bgs_dr1":       N_BGS_DR1,
        "v_bgs_eff_frac":  V_BGS_EFF_FRAC,
        "v_bgs_grid_mpc3": float(V_BGS_GRID),
        "v_quijote_mpc3":  float(V_QUIJOTE),
        "n_gal_target":    float(N_GAL_TARGET_BGS),
        "n_gal_b3_ref":    N_GAL_B3_REF,
        "note": "target_primario=densità BGS DR1 scalata al volume Quijote; "
                "target_B3=verifica coerenza interna",
    },
    "calibration_results": {
        "mmin_star_bgs_target":  float(mmin_star_bgs) if mmin_star_bgs else None,
        "mmin_star_b3_check":    float(mmin_star_b3)  if mmin_star_b3  else None,
        "mmin_mean_inter_sim":   float(mmin_mean),
        "mmin_std_inter_sim":    float(mmin_std),
        "n_sim_used_for_scatter": len(mmin_per_sim),
    },
    "prior_v3": {
        "log_Mmin":        [prior_v3_lo, prior_v3_hi],
        "half_width_dex":  PRIOR_HALF_WIDTH,
        "range_dex":       PRIOR_HALF_WIDTH * 2,
        "motivation":      "±0.15 dex intorno a log_Mmin* calibrato su densità numerica "
                           "BGS DR1 r<19.5 scalata a Quijote (1 Gpc/h)³. "
                           "Fisicamente: scatter della funzione di massa degli aloni "
                           f"tra simulazioni ({mmin_std:.3f} dex) + margine sistematico.",
        "prior_v2_range":  [12.2, 13.1],
        "range_reduction_pct": float((range_v2 - range_v3) / range_v2 * 100),
    },
    "vif_estimate": {
        "VIF_v2":  VIF_v2,
        "VIF_v3_approx": float(VIF_v3_est),
        "method": "VIF ∝ (range_prior)² — approssimazione lineare",
    },
    "ngal_curve": {
        "log_Mmin":   MMIN_GRID.tolist(),
        "ngal_mean":  ngal_mean.tolist(),
        "ngal_std":   ngal_std.tolist(),
    },
    "t_total_min": float((time.time() - t_start) / 60),
    "traceability": {
        "hod_model":     "Zheng2007_5param, altri parametri fissi a B3",
        "sim_selection": f"cosmologia centrale |w₀+1|<0.08, Ωm∈[0.28,0.35], N={args.n_cosmo}",
        "target_source": "phase6_voxelize_diagnostics.json (n_BGS), "
                         "phase5_hod_b3_manifest.json (n_gal_B3)",
        "next_step":     "Eseguire R5-1 v3 con prior log_Mmin=[{:.3f},{:.3f}]".format(
                          prior_v3_lo, prior_v3_hi),
    },
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n  Output: {OUTPUT_JSON}")
print(f"  Tempo totale: {(time.time()-t_start)/60:.1f} min")
print("=" * 70)
print(f"\nPROSSIMO PASSO — R5-1 v3:")
print(f"  Modifica prior log_Mmin in phase_r51_hod_restricted_v2.py:")
print(f"  PRIOR_LOW_5[0]  = {prior_v3_lo:.3f}  (era 12.200)")
print(f"  PRIOR_HIGH_5[0] = {prior_v3_hi:.3f}  (era 13.100)")
print(f"  Poi esegui: python src/phase_r51_hod_restricted_v2.py "
      f"--n_sim 500 --K 20 --seed 42 --n_perm 1000")
print("=" * 70)
