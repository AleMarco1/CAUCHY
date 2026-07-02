"""
CAUCHY — Run B3 calibrato (log_Mmin=13.5)
src/phase_b3_cal135_v2.py

Obiettivo: risposta al BLOCKING 1 del Reviewer R5-1 (2026-06-13).
Calcola la distribuzione mock di ⟨pers₁⟩ con HOD calibrato sulla
densità numerica BGS DR1 NGC reale su Quijote.

Motivazione:
  Il confronto principale +3.09σ usa HOD B3 con log_Mmin=12.5,
  che produce n_gal~900K su Quijote. La densità BGS DR1 NGC
  (217,614 galassie in V_eff~3.8×10⁸ (Mpc/h)³) corrisponde a
  n_gal~573K su Quijote (1 Gpc/h)³, ovvero log_Mmin~13.5.
  Il Reviewer ha classificato questo mismatch come BLOCKING perché
  ⟨pers₁⟩ è sensibile alla densità del tracer.

  Questo script esegue il confronto corretto:
  ⟨pers₁⟩_BGS_NGC = 0.459 ± 0.005
  vs ⟨pers₁⟩_mock con log_Mmin=13.5 (densità BGS-calibrata)

Parametri HOD:
  log_Mmin   = 13.5   ← CALIBRATO (densità BGS reale su Quijote)
  sigma_logM = 0.55   ← B3 invariato
  log_M0     = 12.25  ← B3 invariato
  log_M1     = 13.5   ← B3 invariato
  alpha      = 1.0    ← B3 invariato
  A_cen/A_sat/eta_vel/eta_conc = 0,0,1,1 ← fissi

Nessun fallback HOD:
  log_Mmin=13.5 fisso su tutte le 2000 simulazioni senza finestra n_gal.
  La variazione di n_gal con Ωm/σ₈ è gestita dalla partial correlation.
  Solo fallback DM se il catalogo FoF è vuoto (< 100 galassie).
  Motivazione: il Gruppo A del run v1 (925 sim con n_gal∈[300K,800K]) mostra
  z=+21.95σ ma è condizionato a cosmologie a bassa densità. Il run v2 usa
  tutte le 2000 sim senza selezione, producendo un confronto non distorto.

σ_px: 0.64 (invariato per coerenza metodologica con Confronto B)
  Dichiarazione: la scala fisica di smoothing è invariata; la variazione
  di ⟨pers₁⟩ con la densità è il segnale che si vuole misurare.

Output:
  results/phase_b3_cal135_features.npz
  results/phase_b3_cal135_diagnostics.json

Uso:
  python src/phase_b3_cal135_v2.py [--n_sim 2000] [--seed 42] [--resume]

Tempo stimato: ~5h (2000 sim × ~9s gudhi, n_gal più basso → più veloce)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY B3 calibrato log_Mmin=13.5")
parser.add_argument("--n_sim",        type=int,  default=2000)
parser.add_argument("--seed",         type=int,  default=42)
parser.add_argument("--resume",       action="store_true")
parser.add_argument("--project_root", type=str,  default=".")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE        = ROOT / "results" / "phase1_fiducial_cache.npz"
RESULTS_DIR      = ROOT / "results"
CAL135_DIR       = RESULTS_DIR / "phase_b3_cal135_v2_fields"
OUTPUT_FEATURES  = RESULTS_DIR / "phase_b3_cal135_v2_features.npz"
OUTPUT_DIAG      = RESULTS_DIR / "phase_b3_cal135_v2_diagnostics.json"
MANIFEST         = RESULTS_DIR / "phase_b3_cal135_v2_manifest.json"

CAL135_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Costanti
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20
SIGMA_SMOOTH = 0.64  # identico a Confronto B

# ---------------------------------------------------------------------------
# Parametri HOD calibrati
# ---------------------------------------------------------------------------
# log_Mmin=13.5 calibrato su densità BGS DR1 NGC su Quijote
# (phase_halo_completeness.py: n_gal_BGS~573K → log_Mmin~13.5)
# Altri parametri invariati da B3
HOD_CAL135 = np.array([
    13.5,   # log_Mmin  ← CALIBRATO
    0.55,   # sigma_logM ← B3
    12.25,  # log_M0     ← B3
    13.5,   # log_M1     ← B3
    1.0,    # alpha      ← B3
    0.0,    # A_cen
    0.0,    # A_sat
    1.0,    # eta_vel
    1.0,    # eta_conc
])
HOD_PARAM_NAMES = ["log_Mmin","sigma_logM","log_M0","log_M1","alpha",
                   "A_cen","A_sat","eta_vel","eta_conc"]

# v2: nessun fallback HOD, nessuna finestra n_gal
# La variazione n_gal con cosmologia è gestita dalla partial correlation
N_GAL_TARGET   = 573_000  # solo per stampa informativa

# Riferimento BGS — da phase6_bgs_tda_features.json
B2_PERS_BGS    = 0.459
B2_PERS_BGS_ERR = 0.005
# Riferimento B3 originale — da phase5_hod_b3_features.npz
B2_PERS_B3_MEAN = 0.292
B2_PERS_B3_STD  = 0.028

print("=" * 70)
print("CAUCHY — Run B3 calibrato (log_Mmin=13.5, densità BGS-calibrata)")
print("=" * 70)
print(f"\nParametri HOD calibrati:")
for nm, v in zip(HOD_PARAM_NAMES, HOD_CAL135):
    tag = " ← CALIBRATO (densità BGS)" if nm == "log_Mmin" else " ← B3 invariato"
    print(f"  {nm:<14}: {v:.4f}{tag}")
print(f"\nσ_px: {SIGMA_SMOOTH} (identico a Confronto B — coerenza metodologica)")
print(f"n_gal target: ~{N_GAL_TARGET:,} (densità BGS DR1 NGC su Quijote)")
print(f"Finestra accettazione: NESSUNA (v2 — nessun fallback HOD)")
print(f"\nRiferimento BGS:  ⟨pers₁⟩ = {B2_PERS_BGS} ± {B2_PERS_BGS_ERR}")
print(f"Riferimento B3:   ⟨pers₁⟩ = {B2_PERS_B3_MEAN} ± {B2_PERS_B3_STD}")
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
# HOD — identico a B3
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0):
    from scipy.special import erf
    log_M = np.log10(mass_h)
    return 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))

def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0):
    M0 = 10**log_M0; M1 = 10**log_M1
    N_sat = np.zeros(len(mass_h))
    mask = mass_h > M0
    ratio = np.where(mask, (mass_h - M0) / (M1 + 1e-30), 0.0)
    N_sat[mask] = ratio[mask]**alpha
    N_sat *= mean_Ncen(mass_h, log_Mmin, 0.2)
    return N_sat

def populate_halos_hod(pos_h, mass_h, hod_params, rng):
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3))
    p_cen = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)
    gal_positions = []
    if is_central.any():
        gal_positions.append(pos_h[is_central])
    rho_crit = 2.775e11 * 0.3
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        r_vir = np.clip(
            (3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0),
            0.01, 5.0) * eta_conc
        n_s = int(n_sat[i])
        u = rng.random(n_s)
        r = r_vir * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(n_s))
        phi = 2.0 * np.pi * rng.random(n_s)
        dx = r * np.sin(theta) * np.cos(phi)
        dy = r * np.sin(theta) * np.sin(phi)
        dz = r * np.cos(theta)
        pos_sat = (pos_h[i] + np.column_stack([dx, dy, dz])) % BOXSIZE
        gal_positions.append(pos_sat)
    return np.vstack(gal_positions) if gal_positions else np.zeros((0, 3))


def field_from_galaxies(pos_gal, ngrid=128, boxsize=1000.0):
    if len(pos_gal) == 0:
        return np.zeros((ngrid, ngrid, ngrid), dtype=np.float32)
    cell_size = boxsize / ngrid
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32) % ngrid
    d   = xyz - ijk.astype(np.float32)
    flat = np.zeros(ngrid**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = (ijk[:, 0] + di) % ngrid
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = (ijk[:, 1] + dj) % ngrid
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = (ijk[:, 2] + dk) % ngrid
                idx = ii * ngrid**2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz,
                                    minlength=ngrid**3).astype(np.float32)
    field = flat.reshape(ngrid, ngrid, ngrid)
    mean_f = field.mean()
    if mean_f > 0:
        field = field / mean_f - 1.0
    return field


def compute_tda_features(delta_field, sigma_smooth=SIGMA_SMOOTH, n_thresh=100):
    """Identico a phase5_hod_b3.py — bug v3 corretti (birth=-col0, death=-col1)."""
    import gudhi
    field_s   = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)
    field_neg = -field_s
    thresholds = np.linspace(float(field_s.min()), float(field_s.max()), n_thresh)
    cc = gudhi.CubicalComplex(
        dimensions=list(field_neg.shape),
        top_dimensional_cells=field_neg.flatten()
    )
    cc.compute_persistence()
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def process_diag(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        mask = np.isfinite(d[:, 1])
        df = d[mask]
        birth = -df[:, 0]
        death = -df[:, 1]
        pers  = birth - death
        return birth, death, pers

    birth_0, death_0, pers_0 = process_diag(diag_0)
    birth_1, death_1, pers_1 = process_diag(diag_1)

    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(birth_0):
            b0_curve[k] = np.sum((birth_0 >= nu) & (death_0 < nu))
        if len(birth_1):
            b1_curve[k] = np.sum((birth_1 >= nu) & (death_1 < nu))

    feats = np.zeros(8, dtype=np.float32)
    if b1_curve.max() > 0:
        pk_idx   = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk_idx])
        feats[1] = float(b1_curve[pk_idx])
        half     = b1_curve.max() / 2.0
        above    = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))
        feats[5] = float(np.mean(pers_1))        # ⟨pers₁⟩ — feature primaria
        p90      = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))
    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])
    return feats


# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
print("Caricamento parametri cosmologici nwLH...")
assert NWLH_PARAMS_FILE.exists()
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]
print(f"  w0 range: [{w0_all.min():.2f}, {w0_all.max():.2f}]")

assert TDA_CACHE.exists(), f"Cache TDA non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]  # fallback DM

# Resume
manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} simulazioni già completate.")

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
all_feats = np.zeros((args.n_sim, 8), dtype=np.float32)
for i in range(args.n_sim):
    all_feats[i] = fvecs_nwlh[i]  # fallback DM default

all_diags = []
t_start   = time.time()

print(f"\n[CAL135] {args.n_sim} sim, HOD log_Mmin=13.5 (densità BGS-calibrata)")
print("-" * 70)

for sim_idx in range(args.n_sim):

    # Resume
    if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
        cache_file = CAL135_DIR / f"cal135_{sim_idx:04d}.npz"
        if cache_file.exists():
            all_feats[sim_idx] = np.load(cache_file)["feat"]
        continue

    t0 = time.time()
    rng_sim = np.random.default_rng(args.seed + sim_idx)

    pos_h, mass_h = read_halo_catalog(sim_idx)

    if pos_h is None or len(pos_h) < 50:
        all_feats[sim_idx] = fvecs_nwlh[sim_idx]
        status = "FALLBACK_DM"
        n_gal = 0
        t_gudhi = 0.0
        hod_used = "DM"
    else:
        # log_Mmin=13.5 fisso — nessun fallback HOD (v2)
        # La variazione di n_gal con cosmologia è gestita dalla partial correlation
        pos_gal  = populate_halos_hod(pos_h, mass_h, HOD_CAL135, rng_sim)
        n_gal    = len(pos_gal)
        hod_used = "13.5"

        if n_gal < 100:
            all_feats[sim_idx] = fvecs_nwlh[sim_idx]
            status  = "FALLBACK_DM_FEW_GAL"
            t_gudhi = 0.0
        else:
            delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)
            delta_gal = delta_gal - delta_gal.mean()

            t_g0 = time.time()
            feat = compute_tda_features(delta_gal)
            t_gudhi = time.time() - t_g0

            if np.isfinite(feat).all():
                all_feats[sim_idx] = feat
                status = f"completed_{hod_used}"
            else:
                all_feats[sim_idx] = fvecs_nwlh[sim_idx]
                status = "FALLBACK_DM_TDA_FAILED"

    elapsed = time.time() - t0

    # Checkpoint
    np.savez(CAL135_DIR / f"cal135_{sim_idx:04d}.npz",
             sim_idx=sim_idx, feat=all_feats[sim_idx],
             n_gal=n_gal, hod_used=hod_used,
             t_gudhi=t_gudhi, status=status)

    all_diags.append({
        "sim_idx": sim_idx, "status": status,
        "n_gal": int(n_gal), "hod_used": hod_used,
        "t_gudhi_s": float(t_gudhi), "t_total_s": float(elapsed),
    })

    manifest[str(sim_idx)] = "done"
    with open(MANIFEST, "w") as mf:
        json.dump(manifest, mf)

    if sim_idx == 0 or (sim_idx + 1) % 100 == 0:
        done = sim_idx + 1
        elapsed_total = time.time() - t_start
        eta_h = (elapsed_total / done) * (args.n_sim - done) / 3600
        t_g_str = f"{t_gudhi:.1f}s" if t_gudhi > 0 else "N/A"
        print(f"  Sim {sim_idx:4d} | t_gudhi={t_g_str} | n_gal={n_gal:>7,} "
              f"| hod={hod_used} | {status} | ETA={eta_h:.1f}h")

# ---------------------------------------------------------------------------
# Analisi risultati
# ---------------------------------------------------------------------------
completed = [d for d in all_diags if d["status"].startswith("completed")]
fallback  = [d for d in all_diags if "FALLBACK" in d["status"]]
fallback_13 = []  # v2: nessun fallback HOD

b2_pers_all  = all_feats[:, 5]
valid_mask   = np.array([d["status"].startswith("completed") for d in all_diags]
                         + [False] * (args.n_sim - len(all_diags)))
valid_mask   = valid_mask[:args.n_sim]

# Ricostruisci valid_mask correttamente dai dati caricate
b2_vals = all_feats[:args.n_sim, 5]
# Esclude i fallback DM (che hanno valori DM non-HOD)
n_gal_arr = np.array([d["n_gal"] for d in all_diags] + [0] * (args.n_sim - len(all_diags)))
valid = n_gal_arr[:args.n_sim] > 100

b2_valid = b2_vals[valid]
w0_valid = w0_all[:args.n_sim][valid]
Omm_valid = Omm_all[:args.n_sim][valid]
s8_valid  = s8_all[:args.n_sim][valid]

b2_mean = float(np.mean(b2_valid))
b2_std  = float(np.std(b2_valid))
n_gal_vals = [d["n_gal"] for d in all_diags if d["n_gal"] > 0]

# z-score anomalia BGS
z_anomaly_cal135 = (B2_PERS_BGS - b2_mean) / b2_std
z_anomaly_b3     = (B2_PERS_BGS - B2_PERS_B3_MEAN) / B2_PERS_B3_STD

print(f"\n{'='*70}")
print("RISULTATI B3 CALIBRATO (log_Mmin=13.5)")
print(f"{'='*70}")
print(f"\n  N simulazioni completate (HOD): {len(completed)}/{args.n_sim}")
print(f"  Fallback DM:                    {len(fallback)}")
print(f"  Fallback log_Mmin=13.0:         0 (v2 — nessun fallback)")
print(f"  n_gal medio: {np.mean(n_gal_vals):.0f} ± {np.std(n_gal_vals):.0f}")
print(f"  n_gal range: [{np.min(n_gal_vals):.0f}, {np.max(n_gal_vals):.0f}]")
print(f"\n  ⟨pers₁⟩ mock cal135: {b2_mean:.4f} ± {b2_std:.4f} (N={valid.sum()})")
print(f"  ⟨pers₁⟩ mock B3:     {B2_PERS_B3_MEAN:.4f} ± {B2_PERS_B3_STD:.4f}")
print(f"  ⟨pers₁⟩ BGS NGC:     {B2_PERS_BGS:.4f} ± {B2_PERS_BGS_ERR:.4f}")
print(f"\n  z_anomalia (cal135): {z_anomaly_cal135:+.2f}σ")
print(f"  z_anomalia (B3 ref): {z_anomaly_b3:+.2f}σ")
print(f"\n  Shift mock mean: {b2_mean - B2_PERS_B3_MEAN:+.4f} "
      f"({'più basso' if b2_mean < B2_PERS_B3_MEAN else 'più alto'} di B3)")

# Interpretazione
print(f"\n  --- INTERPRETAZIONE ---")
if b2_mean < B2_PERS_B3_MEAN and z_anomaly_cal135 > z_anomaly_b3:
    print(f"  Mock cal135 < B3 → segnale BGS SI RAFFORZA con densità calibrata")
    print(f"  Il mismatch densità NON spiega l'anomalia — anzi la amplifica.")
    interp = "SEGNALE_RAFFORZATO"
elif abs(b2_mean - B2_PERS_BGS) < 2 * b2_std:
    print(f"  Mock cal135 ≈ BGS → mismatch densità SPIEGA l'anomalia")
    print(f"  Il segnale +3.09σ era un artefatto di densità galattica diversa.")
    interp = "SEGNALE_SPIEGATO_DA_DENSITA"
elif z_anomaly_cal135 > 2.0:
    print(f"  z_anomalia={z_anomaly_cal135:.2f}σ > 2σ → anomalia PERSISTE a densità calibrata")
    print(f"  Il mismatch densità riduce ma non elimina l'anomalia.")
    interp = "ANOMALIA_PERSISTENTE"
else:
    print(f"  z_anomalia={z_anomaly_cal135:.2f}σ < 2σ → anomalia INDEBOLITA a densità calibrata")
    print(f"  Il mismatch densità spiega parte sostanziale del segnale.")
    interp = "ANOMALIA_INDEBOLITA"

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
np.savez(OUTPUT_FEATURES,
         fvecs_hod_cal135=all_feats,
         w0=w0_all[:args.n_sim],
         Omm=Omm_all[:args.n_sim],
         s8=s8_all[:args.n_sim],
         hod_params=HOD_CAL135,
         hod_param_names=HOD_PARAM_NAMES,
         methodology="HOD deterministico log_Mmin=13.5 fisso, nessun fallback HOD (v2)")

diag_out = {
    "schema_version": "2.0",
    "task":           "B3_calibrated_log_Mmin_13.5_v2_no_fallback",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "motivation":     "Risposta BLOCKING 1 Reviewer R5-1 v2 (nessun fallback HOD): "
                      "mismatch densità galattica B3 (900K) vs BGS reale (573K) su Quijote.",
    "hod_params":     HOD_CAL135.tolist(),
    "hod_param_names": HOD_PARAM_NAMES,
    "sigma_smooth":   SIGMA_SMOOTH,
    "n_gal_target":   N_GAL_TARGET,
    "n_gal_window":   "NESSUNA (v2)",  # nessun fallback HOD
    "n_sims":         args.n_sim,
    "n_completed_hod": len(completed),
    "n_fallback_dm":  len(fallback),
    "n_fallback_13":  len(fallback_13),
    "n_gal_stats": {
        "mean": float(np.mean(n_gal_vals)) if n_gal_vals else 0.0,
        "std":  float(np.std(n_gal_vals))  if n_gal_vals else 0.0,
        "min":  float(np.min(n_gal_vals))  if n_gal_vals else 0.0,
        "max":  float(np.max(n_gal_vals))  if n_gal_vals else 0.0,
    },
    "primary_result": {
        "b2_mean_persistence_cal135": {"mean": b2_mean, "std": b2_std,
                                        "n": int(valid.sum())},
        "b2_mean_persistence_b3_ref": {"mean": B2_PERS_B3_MEAN, "std": B2_PERS_B3_STD},
        "b2_mean_persistence_bgs":    {"value": B2_PERS_BGS, "err": B2_PERS_BGS_ERR},
        "z_anomaly_cal135":  float(z_anomaly_cal135),
        "z_anomaly_b3_ref":  float(z_anomaly_b3),
        "mock_mean_shift":   float(b2_mean - B2_PERS_B3_MEAN),
        "interpretation":    interp,
    },
    "t_total_h": float((time.time() - t_start) / 3600),
    "traceability": {
        "base_script":      "src/phase5_hod_b3.py",
        "log_Mmin_source":  "phase_halo_completeness.json: n_gal_BGS=573K → log_Mmin~13.5",
        "n_gal_target_src": "phase_hod_fit_wp_bgs.json: n_bgs=217614, V_eff=3.8e8 (Mpc/h)³",
        "reviewer_concern": "BLOCKING 1 — Reviewer R5-1 2026-06-13",
    },
}

with open(OUTPUT_DIAG, "w") as f:
    json.dump(diag_out, f, indent=2)

print(f"\n{'='*70}")
print(f"CAL135 COMPLETATO")
print(f"  z_anomalia = {z_anomaly_cal135:+.2f}σ  ({interp})")
print(f"  ⟨pers₁⟩ mock cal135 = {b2_mean:.4f} ± {b2_std:.4f}")
print(f"  ⟨pers₁⟩ BGS NGC     = {B2_PERS_BGS:.4f} ± {B2_PERS_BGS_ERR:.4f}")
print(f"  Features: {OUTPUT_FEATURES}")
print(f"  Diagnostiche: {OUTPUT_DIAG}")
print(f"  Tempo totale: {(time.time()-t_start)/3600:.2f}h")
print(f"{'='*70}")
