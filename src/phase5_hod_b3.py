"""
CAUCHY — Phase 5, Sessione 2 (parallelo)
src/phase5_hod_b3.py

Opzione B3 — HOD deterministico al mediano del prior AbacusSummit.
Gira in parallelo a phase5_hod_mcmc.py (Opzione A, K=10 forward samples).

Obiettivo:
  Per ogni simulazione nwLH:
    1. Leggi catalogo FoF aloni
    2. Applica HOD con parametri = mediano del prior AbacusSummit (fissi)
    3. CIC 128³ → campo galattico
    4. gudhi completo → 8 feature TDA
    5. Salva feature

Costo: ~1/K del run A — gira ~10× più veloce.
Uso: confronto diretto A vs B3 per quantificare impatto della marginalizzazione HOD.

Se |r_A - r_B3| << 1σ: la marginalizzazione HOD ha impatto trascurabile.
Se |r_A - r_B3| > 1σ: la marginalizzazione è importante e A è necessaria.

Parametri HOD mediani AbacusSummit (centro del prior flat):
  log_Mmin   = 12.50  (centro [11.5, 13.5])
  sigma_logM =  0.55  (centro [0.1,  1.0])
  log_M0     = 12.25  (centro [11.0, 13.5])
  log_M1     = 13.50  (centro [12.5, 14.5])
  alpha       =  1.00  (centro [0.5,  1.5])
  A_cen       =  0.00  (centro [-1.0, 1.0])
  A_sat       =  0.00  (centro [-1.0, 1.0])
  eta_vel     =  1.00  (centro [0.0,  2.0])
  eta_conc    =  1.00  (centro [0.0,  2.0])

Autorità:
  - CAUCHY_Systematic_Methodology_v2.md §5.1, §5.2
  - prior/gate4_prior_v1_0.json

Uso:
  python src/phase5_hod_b3.py [--n_sim 2000] [--resume] [--seed 42]

Output:
  results/phase5_hod_b3_features.npz
  results/phase5_hod_b3_diagnostics.json
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY Phase 5 — HOD B3 deterministico")
parser.add_argument("--n_sim", type=int, default=2000)
parser.add_argument("--resume", action="store_true")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--project_root", type=str, default=".")
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
B3_DIR           = RESULTS_DIR / "phase5_hod_b3_fields"
OUTPUT_FEATURES  = RESULTS_DIR / "phase5_hod_b3_features.npz"
OUTPUT_DIAG      = RESULTS_DIR / "phase5_hod_b3_diagnostics.json"
MANIFEST         = RESULTS_DIR / "phase5_hod_b3_manifest.json"

B3_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Costanti fisiche Quijote
# ---------------------------------------------------------------------------
BOXSIZE  = 1000.0
NGRID    = 128
SNAPNUM  = 4
N_PART_MIN = 20

# ---------------------------------------------------------------------------
# Parametri HOD B3 — mediano prior AbacusSummit
# ---------------------------------------------------------------------------
HOD_PRIOR_LOW  = np.array([11.5, 0.1, 11.0, 12.5, 0.5, -1.0, -1.0, 0.0, 0.0])
HOD_PRIOR_HIGH = np.array([13.5, 1.0, 13.5, 14.5, 1.5,  1.0,  1.0, 2.0, 2.0])
HOD_MEDIAN     = 0.5 * (HOD_PRIOR_LOW + HOD_PRIOR_HIGH)
HOD_PARAM_NAMES = [
    "log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha",
    "A_cen", "A_sat", "eta_vel", "eta_conc"
]

print("=" * 70)
print("CAUCHY Phase 5 — HOD B3 deterministico (mediano AbacusSummit prior)")
print("=" * 70)
print(f"Parametri HOD mediani:")
for name, val in zip(HOD_PARAM_NAMES, HOD_MEDIAN):
    print(f"  {name:<12}: {val:.4f}")
print()

# ---------------------------------------------------------------------------
# FoF reader — formato SOA verificato su file reale
# Struttura: header 24 bytes + N*84 bytes
# Offsets: GroupLen @24, GroupMass @24+N*8,
#          Pos x @24+N*12, y @24+N*16, z @24+N*20
#          Vel vx @24+N*24, vy @24+N*28, vz @24+N*32
# ---------------------------------------------------------------------------
class FoF_catalog:
    """
    Lettore catalogo FoF Quijote — formato SOA verificato su nwLH.
    Struttura: header[6 int32] + N*84 bytes (9 blocchi da N*4 + 6*N*4 types)
    """
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
        x = rd_f(24 + N*12)
        y = rd_f(24 + N*16)
        z = rd_f(24 + N*20)
        self.GroupPos  = np.column_stack([x, y, z])


def read_halo_catalog(sim_idx):
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, SNAPNUM)
    if FoF.Ngroups == 0:
        return None, None

    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE   # kpc/h → Mpc/h
    mass_h = FoF.GroupMass[mask] * 1e10              # 1e10 Msun/h → Msun/h
    return pos_h, mass_h


# ---------------------------------------------------------------------------
# HOD AbacusSummit — stessa implementazione di phase5_hod_mcmc.py
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0):
    from scipy.special import erf
    log_M = np.log10(mass_h)
    return 0.5 * (1.0 + erf((log_M - log_Mmin) / (sigma_logM + 1e-10)))


def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0):
    M0 = 10**log_M0
    M1 = 10**log_M1
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
        r_vir = np.clip((3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit))**(1.0/3.0),
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


def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    """
    Stesse 8 feature TDA di Phase 1 (Execution Parameters §9.1).
    Superlevel filtration su campo 128³ completo via gudhi CubicalComplex.
    """
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato: conda install -c conda-forge gudhi")

    field_s   = gaussian_filter(delta_field.astype(np.float64), sigma=sigma_smooth)
    field_neg = -field_s

    # Thresholds in coordinate ORIGINALI (field_s)
    # FIX v2: bug precedente usava thresholds in coord negate -> b1_curve=0 su campi asimmetrici
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
        birth = -df[:, 0]   # -birth_neg = birth in coord originali (soglia alta, superlevel)
        death = -df[:, 1]   # -death_neg = death in coord originali (soglia bassa, superlevel)
        pers  = birth - death  # > 0 per definizione
        return birth, death, pers

    birth_0, death_0, pers_0 = process_diag(diag_0)
    birth_1, death_1, pers_1 = process_diag(diag_1)

    # Betti curves — thresholds e birth/death ora in coordinate originali coerenti
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
        feats[5] = float(np.mean(pers_1))
        p90      = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))

    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])

    return feats


# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
print("Caricamento parametri nwLH...")
assert NWLH_PARAMS_FILE.exists()
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]

assert TDA_CACHE.exists()
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]  # [2000, 8] — fallback DM

print(f"  w0 range: [{w0_all.min():.2f}, {w0_all.max():.2f}]")

# Resume manifest
manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} simulazioni gia' completate.")

# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------
all_feats = np.zeros((args.n_sim, 8), dtype=np.float32)
for i in range(args.n_sim):
    all_feats[i] = fvecs_nwlh[i]  # fallback DM

all_diags  = []
t_start    = time.time()
rng_global = np.random.default_rng(args.seed)

print(f"\n[B3] {args.n_sim} simulazioni, HOD mediano deterministico")
print("-" * 70)

for sim_idx in range(args.n_sim):

    # Resume
    if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
        cache_file = B3_DIR / f"b3_{sim_idx:04d}.npz"
        if cache_file.exists():
            all_feats[sim_idx] = np.load(cache_file)["feat"]
        continue

    t0 = time.time()

    # Lettura catalogo FoF
    pos_h, mass_h = read_halo_catalog(sim_idx)
    if pos_h is None or len(pos_h) < 50:
        all_feats[sim_idx] = fvecs_nwlh[sim_idx]
        status = "FALLBACK_DM"
        t_gudhi = 0.0
        n_gal = 0
    else:
        rng_sim = np.random.default_rng(args.seed + sim_idx)

        # HOD deterministico: parametri mediani, seed fisso per riproducibilità
        pos_gal = populate_halos_hod(pos_h, mass_h, HOD_MEDIAN, rng_sim)

        if len(pos_gal) < 100:
            all_feats[sim_idx] = fvecs_nwlh[sim_idx]
            status = "FALLBACK_DM_FEW_GAL"
            t_gudhi = 0.0
            n_gal = len(pos_gal)
        else:
            n_gal = len(pos_gal)

            # Campo galattico 128³ CIC
            delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)
            delta_gal = delta_gal - delta_gal.mean()

            # Feature TDA complete (gudhi su 128³ intero — no compressione)
            t_g0 = time.time()
            feat = compute_tda_features(delta_gal)
            t_gudhi = time.time() - t_g0

            if np.isfinite(feat).all():
                all_feats[sim_idx] = feat
                status = "completed"
            else:
                all_feats[sim_idx] = fvecs_nwlh[sim_idx]
                status = "FALLBACK_DM_TDA_FAILED"

    elapsed = time.time() - t0

    # Salva checkpoint
    np.savez(B3_DIR / f"b3_{sim_idx:04d}.npz",
             sim_idx=sim_idx,
             feat=all_feats[sim_idx],
             hod_params=HOD_MEDIAN,
             n_gal=n_gal,
             t_gudhi=t_gudhi,
             status=status)

    all_diags.append({
        "sim_idx": sim_idx,
        "status": status,
        "n_gal": int(n_gal),
        "t_gudhi_s": float(t_gudhi),
        "t_total_s": float(elapsed),
    })

    # Aggiorna manifest
    manifest[str(sim_idx)] = "done"
    with open(MANIFEST, "w") as mf:
        json.dump(manifest, mf)

    # Progress ogni 100 sim + prima sim (per timing)
    if sim_idx == 0 or (sim_idx + 1) % 100 == 0:
        done = sim_idx + 1
        elapsed_total = time.time() - t_start
        eta_h = (elapsed_total / done) * (args.n_sim - done) / 3600
        t_g_str = f"{t_gudhi:.1f}s" if t_gudhi > 0 else "N/A"
        print(f"  Sim {sim_idx:4d} | t_gudhi={t_g_str} | n_gal={n_gal} "
              f"| {status} | ETA={eta_h:.1f}h")

# ---------------------------------------------------------------------------
# Salvataggio risultati
# ---------------------------------------------------------------------------
np.savez(OUTPUT_FEATURES,
         fvecs_hod_b3=all_feats,
         w0=w0_all[:args.n_sim],
         Omm=Omm_all[:args.n_sim],
         s8=s8_all[:args.n_sim],
         hod_params_median=HOD_MEDIAN,
         hod_param_names=HOD_PARAM_NAMES,
         methodology="HOD deterministico mediano AbacusSummit prior (B3)")

completed = [d for d in all_diags if d["status"] == "completed"]
fallback  = [d for d in all_diags if "FALLBACK" in d["status"]]
t_gudhi_vals = [d["t_gudhi_s"] for d in completed]

diag_out = {
    "schema_version": "2.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "method": "B3_deterministic_HOD_median",
    "n_sims": args.n_sim,
    "n_completed": len(completed),
    "n_fallback_dm": len(fallback),
    "hod_params_median": HOD_MEDIAN.tolist(),
    "t_gudhi_mean_s": float(np.mean(t_gudhi_vals)) if t_gudhi_vals else 0.0,
    "t_gudhi_std_s":  float(np.std(t_gudhi_vals))  if t_gudhi_vals else 0.0,
    "t_total_h": float((time.time() - t_start) / 3600),
    "individual_diagnostics": all_diags,
}

with open(OUTPUT_DIAG, "w") as f:
    json.dump(diag_out, f, indent=2)

print(f"\n{'='*70}")
print(f"B3 COMPLETATO")
print(f"  Simulazioni completate: {len(completed)}/{args.n_sim}")
print(f"  Fallback DM:            {len(fallback)}")
if t_gudhi_vals:
    print(f"  gudhi medio:            {np.mean(t_gudhi_vals):.1f}s")
print(f"  Tempo totale:           {(time.time()-t_start)/3600:.2f}h")
print(f"  Feature B3:             {OUTPUT_FEATURES}")
print(f"  Diagnostiche:           {OUTPUT_DIAG}")
print(f"\nConfronto A vs B3 in Sessione 3 — phase5_partial_corr.py")
print(f"{'='*70}")
