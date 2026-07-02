"""
CAUCHY — Phase 6
src/phase6_mock_calibration.py

Costruisce mock BGS da simulazioni Quijote nwLH a z=0 e z=0.5 con HOD
forward sampling. Verifica gate D2 (n_gal calibrazione) e produce
feature TDA per il confronto con DESI BGS.

Design decisions (phase6_design_decisions.md D1, D2):
  - D1: bracket deterministico z=0 / z=0.5
  - D2: Opzione A (prior flat AbacusSummit), poi gate D2

Gate D2: |n_gal_mock - n_gal_DESI| / n_gal_DESI < 20%
  Se gate D2 PASS: prior flat confermato per Phase 6
  Se gate D2 FAIL: segnala, suggerisce Opzione C (HOD da letteratura)

n_gal_DESI target:
  NGC: 217,614 galassie in 307,805 voxel validi (fill 14.7%)
  SGC:  82,429 galassie in 172,225 voxel validi (fill 8.2%)
  Media pesata volume: ~217k galassie per box 2000 Mpc/h
  Densita: n = 217614 / (2000^3) = 2.72e-5 gal/(Mpc/h)^3

  Per box Quijote 1000 Mpc/h: n_expected = 2.72e-5 * 1000^3 = 27,200 gal
  (molto meno delle ~700k con prior flat AbacusSummit!)

Input:
  data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/{i}/groups_004/  (z=0)
  data/raw/quijote/3D_cubes/latin_hypercube_nwLH_hod/{i}/groups_003/  (z=0.5)
  results/phase5_hod_b3_features.npz  (feature z=0 gia calcolate)
  latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt

Output:
  results/phase6_mock_features_z0.npz    (riuso da Phase 5 B3)
  results/phase6_mock_features_z05.npz   (nuovo — z=0.5)
  results/phase6_calibration_diagnostics.json

Uso:
  # Pilota su 10 sim per stima tempo
  python src/phase6_mock_calibration.py --mode pilot --n_pilot 10

  # Run completo z=0.5 (z=0 gia in results/phase5_hod_b3_features.npz)
  python src/phase6_mock_calibration.py --mode full

  # Resume
  python src/phase6_mock_calibration.py --mode full --resume
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

parser = argparse.ArgumentParser()
parser.add_argument("--mode", choices=["pilot", "full"], default="pilot")
parser.add_argument("--n_pilot", type=int, default=10)
parser.add_argument("--n_sim", type=int, default=2000)
parser.add_argument("--resume", action="store_true")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--R_smooth", type=float, default=10.0,
                    help="Smoothing in Mpc/h (default 10.0 per O6-4 sensitivity check)")
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

ROOT        = Path(args.project_root)
HOD_DIR     = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
RES_DIR     = ROOT / "results"
CHAINS_DIR  = RES_DIR / "phase6_mock_chains_z05_R10"
MANIFEST    = RES_DIR / "phase6_mock_manifest_z05_R10.json"
OUTPUT_Z05  = RES_DIR / "phase6_mock_features_z05_R10.npz"
OUTPUT_Z0   = RES_DIR / "phase5_hod_b3_features.npz"  # gia esistente
OUTPUT_DIAG = RES_DIR / "phase6_calibration_diagnostics.json"
CHAINS_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)

np.random.seed(args.seed)
rng_global = np.random.default_rng(args.seed)

# ---------------------------------------------------------------------------
# Costanti fisiche Quijote
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0   # Mpc/h
NGRID      = 128
SNAPNUM_Z0  = 4       # z=0
SNAPNUM_Z05 = 3       # z=0.5
N_PART_MIN  = 20

# Target densita galattica da DESI BGS NGC
# n_gal_DESI = 217614 gal in volume effettivo ~(2000 Mpc/h)^3 * 0.147 fill
# Ma per confronto con mock Quijote (1000 Mpc/h box periodico):
# scala per volume: n_density = 217614 / (2000^3 * 0.147) Mpc^-3 h^3
# n_expected_quijote = n_density * 1000^3
N_GAL_DESI_NGC    = 217614
BOX_DESI_NGC      = 1997.4   # Mpc/h
FILL_DESI_NGC     = 0.1468
VOL_DESI_SURVEY   = BOX_DESI_NGC**3 * FILL_DESI_NGC  # Mpc^3/h^3 effettivo
N_GAL_DENSITY     = N_GAL_DESI_NGC / VOL_DESI_SURVEY  # gal / (Mpc/h)^3
N_GAL_TARGET_QUIJOTE = int(N_GAL_DENSITY * BOXSIZE**3)

print("=" * 70)
print("CAUCHY Phase 6 — Mock Calibration (z=0 e z=0.5)")
print(f"Modalita: {args.mode.upper()}")
print("=" * 70)
print(f"\nTarget densita DESI BGS NGC:")
print(f"  N_gal DESI: {N_GAL_DESI_NGC:,}  in box {BOX_DESI_NGC:.0f} Mpc/h (fill {FILL_DESI_NGC:.3f})")
print(f"  Densita: {N_GAL_DENSITY:.3e} gal/(Mpc/h)^3")
print(f"  N_gal atteso in box Quijote 1000 Mpc/h: {N_GAL_TARGET_QUIJOTE:,}")
print(f"  Gate D2 threshold: +/-20% = [{int(N_GAL_TARGET_QUIJOTE*0.8):,}, {int(N_GAL_TARGET_QUIJOTE*1.2):,}]")

# ---------------------------------------------------------------------------
# HOD AbacusSummit 9 parametri (identico Phase 5)
# ---------------------------------------------------------------------------
HOD_PARAM_NAMES = [
    "log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha",
    "A_cen", "A_sat", "eta_vel", "eta_conc"
]
HOD_PRIOR_LOW  = np.array([11.5, 0.1, 11.0, 12.5, 0.5, -1.0, -1.0, 0.0, 0.0])
HOD_PRIOR_HIGH = np.array([13.5, 1.0, 13.5, 14.5, 1.5,  1.0,  1.0, 2.0, 2.0])
HOD_MEDIAN     = 0.5 * (HOD_PRIOR_LOW + HOD_PRIOR_HIGH)

# HOD calibrato su BGS: log_Mmin piu alto per ridurre n_gal
# n_gal_target ~ 27k vs ~700k con prior flat
# La massa minima per centrale HOD scala come:
# N_cen ~ 0.5*erfc((log_Mmin - log_M) / sigma) -> aumenta log_Mmin
# Stima: da ~700k a ~27k e una riduzione di ~26x
# log(M_min_new) ~ log(M_min_old) + log(26)/alpha ~ 12.5 + 1.4/1.0 = 13.9
# Ma 13.9 e fuori prior [11.5,13.5]. Quindi usiamo log_Mmin=13.4 (limite superiore)
HOD_BGS_CALIBRATED = HOD_MEDIAN.copy()
# Target: 186k gal in box 1000 Mpc/h (densita DESI BGS NGC)
# log_Mmin=12.85 riduce N_cen di ~3.8x rispetto a mediano (12.5)
HOD_BGS_CALIBRATED[0] = 13.34  # log_Mmin -> ~186k gal target (da pilot: 12.85->403k, stima 13.34->186k)
HOD_BGS_CALIBRATED[3] = 13.8   # log_M1 leggermente piu alto
HOD_BGS_CALIBRATED[4] = 1.0    # alpha mediano


# ---------------------------------------------------------------------------
# FoF reader (identico Phase 5, formato SOA verificato)
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        if not fname.exists():
            self.Ngroups = 0
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            return
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
        x = rd_f(24 + N*12);  y = rd_f(24 + N*16);  z = rd_f(24 + N*20)
        self.GroupPos  = np.column_stack([x, y, z])


def read_halo_catalog(sim_idx, snapnum):
    snapdir = HOD_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, snapnum)
    if FoF.Ngroups == 0:
        return None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE
    mass_h = FoF.GroupMass[mask] * 1e10
    return pos_h, mass_h


# ---------------------------------------------------------------------------
# HOD populate (identico Phase 5)
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM, A_cen=0.0):
    from scipy.special import erf
    return 0.5 * (1.0 + erf((np.log10(mass_h) - log_Mmin) / (sigma_logM + 1e-10)))

def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin, A_sat=0.0):
    M0 = 10**log_M0;  M1 = 10**log_M1
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
    p_cen = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)
    gal_pos = []
    if is_central.any():
        gal_pos.append(pos_h[is_central])
    rho_crit = 2.775e11 * 0.3
    for i in range(N_h):
        if n_sat[i] <= 0:
            continue
        r_vir = np.clip((3.0*mass_h[i]/(4.0*np.pi*200.0*rho_crit))**(1.0/3.0),
                        0.01, 5.0) * eta_conc
        ns = int(n_sat[i])
        u = rng.random(ns)
        r = r_vir * u**(1.0/3.0)
        theta = np.arccos(1.0 - 2.0*rng.random(ns))
        phi   = 2.0 * np.pi * rng.random(ns)
        dx = r*np.sin(theta)*np.cos(phi)
        dy = r*np.sin(theta)*np.sin(phi)
        dz = r*np.cos(theta)
        gal_pos.append((pos_h[i] + np.column_stack([dx,dy,dz])) % BOXSIZE)
    return np.vstack(gal_pos) if gal_pos else np.zeros((0,3))


def field_from_galaxies(pos_gal, R_smooth=5.0):
    if len(pos_gal) == 0:
        return np.zeros((NGRID, NGRID, NGRID), dtype=np.float32)
    cell_size = BOXSIZE / NGRID
    sigma_px  = R_smooth / cell_size
    xyz = (pos_gal / cell_size).astype(np.float32)
    ijk = xyz.astype(np.int32) % NGRID
    d   = xyz - ijk.astype(np.float32)
    flat = np.zeros(NGRID**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0-d[:,0]) if di==0 else d[:,0]
        ii = (ijk[:,0]+di) % NGRID
        for dj in range(2):
            wy = (1.0-d[:,1]) if dj==0 else d[:,1]
            jj = (ijk[:,1]+dj) % NGRID
            for dk in range(2):
                wz = (1.0-d[:,2]) if dk==0 else d[:,2]
                kk = (ijk[:,2]+dk) % NGRID
                idx = ii*NGRID**2 + jj*NGRID + kk
                flat += np.bincount(idx, weights=wx*wy*wz,
                                    minlength=NGRID**3).astype(np.float32)
    field = flat.reshape(NGRID,NGRID,NGRID)
    mean_f = field.mean()
    if mean_f > 0:
        field = field / mean_f - 1.0
    field = gaussian_filter(field.astype(np.float64), sigma=sigma_px).astype(np.float32)
    field -= field.mean()
    return field


# ---------------------------------------------------------------------------
# TDA features (identico Phase 5/6 con fix v3)
# ---------------------------------------------------------------------------
def compute_tda_features(delta_field, n_thresh=100):
    import gudhi
    field = delta_field.astype(np.float64)
    thresholds = np.linspace(float(field.min()), float(field.max()), n_thresh)
    field_neg = -field
    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                               top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()
    diag_1 = cc.persistence_intervals_in_dimension(1)
    diag_0 = cc.persistence_intervals_in_dimension(0)

    def proc(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        m = np.isfinite(d[:,1])
        df = d[m]
        birth = -df[:,0]; death = -df[:,1]
        return birth, death, birth - death

    birth_0, death_0, pers_0 = proc(diag_0)
    birth_1, death_1, pers_1 = proc(diag_1)

    b0_curve = np.zeros(n_thresh)
    b1_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(birth_0): b0_curve[k] = np.sum((birth_0>=nu)&(death_0<nu))
        if len(birth_1): b1_curve[k] = np.sum((birth_1>=nu)&(death_1<nu))

    feats = np.zeros(8, dtype=np.float32)
    if b1_curve.max() > 0:
        pk = np.argmax(b1_curve)
        feats[0] = float(thresholds[pk])
        feats[1] = float(b1_curve[pk])
        half  = b1_curve.max()/2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = float(thresholds[above[-1]]-thresholds[above[0]]) if len(above)>1 else 0.0
        feats[3] = float(np.trapezoid(b1_curve, thresholds))
    if len(pers_1) > 0:
        feats[4] = float(len(pers_1))
        feats[5] = float(np.mean(pers_1))
        feats[6] = float(np.sum(pers_1 >= np.percentile(pers_1, 90)))
    mean_val = float(field.mean())
    feats[7] = float(b0_curve[np.argmin(np.abs(thresholds - mean_val))])
    return feats


# ---------------------------------------------------------------------------
# Caricamento parametri nwLH
# ---------------------------------------------------------------------------
assert PARAMS_FILE.exists(), f"Parametri non trovati: {PARAMS_FILE}"
cosmo = np.loadtxt(PARAMS_FILE, comments='#')
Omm_all = cosmo[:, 0]
s8_all  = cosmo[:, 4]
w0_all  = cosmo[:, 6]
print(f"\nParametri nwLH: {cosmo.shape}, w0 [{w0_all.min():.2f}, {w0_all.max():.2f}]")

# ---------------------------------------------------------------------------
# Funzione principale per una simulazione a z=0.5
# ---------------------------------------------------------------------------
def process_sim_z05(sim_idx):
    """HOD deterministico calibrato su BGS + TDA per sim sim_idx a z=0.5."""
    chain_file = CHAINS_DIR / f"z05_{sim_idx:04d}.npz"

    if args.resume and chain_file.exists():
        data = np.load(chain_file)
        return data["feat"].astype(np.float32), {
            "sim_idx": sim_idx, "status": "cache",
            "n_gal": int(data["n_gal"]), "t_s": 0.0
        }

    pos_h, mass_h = read_halo_catalog(sim_idx, SNAPNUM_Z05)
    if pos_h is None or len(pos_h) < 50:
        return np.zeros(8, dtype=np.float32), {
            "sim_idx": sim_idx, "status": "EMPTY", "n_gal": 0, "t_s": 0.0
        }

    t0 = time.time()
    rng = np.random.default_rng(args.seed + sim_idx)

    # Usa HOD calibrato su BGS (piu selettivo)
    pos_gal = populate_halos_hod(pos_h, mass_h, HOD_BGS_CALIBRATED, rng)
    n_gal   = len(pos_gal)

    delta = field_from_galaxies(pos_gal, R_smooth=args.R_smooth)
    feat  = compute_tda_features(delta)

    np.savez(chain_file, sim_idx=sim_idx, feat=feat, n_gal=n_gal,
             hod_params=HOD_BGS_CALIBRATED)

    return feat, {
        "sim_idx": sim_idx, "status": "ok",
        "n_gal": n_gal, "t_s": float(time.time()-t0)
    }


# ---------------------------------------------------------------------------
# Gate D2: verifica calibrazione n_gal
# ---------------------------------------------------------------------------
def check_gate_d2(n_gal_list, label=""):
    n_arr  = np.array([n for n in n_gal_list if n > 0])
    mean_n = float(n_arr.mean())
    std_n  = float(n_arr.std())
    discr  = abs(mean_n - N_GAL_TARGET_QUIJOTE) / N_GAL_TARGET_QUIJOTE
    passed = discr < 0.20
    print(f"\n  Gate D2 {label}:")
    print(f"    n_gal_mock medio:  {mean_n:.0f} +/- {std_n:.0f}")
    print(f"    n_gal_DESI target: {N_GAL_TARGET_QUIJOTE:,}")
    print(f"    Discrepanza:       {100*discr:.1f}%  (threshold < 20%)")
    print(f"    Verdict:           {'PASS' if passed else 'FAIL -> considera Opzione C HOD'}")
    return passed, float(discr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"Resume: {len(manifest)} sim gia completate")

n_sim = args.n_pilot if args.mode == "pilot" else args.n_sim
all_feats_z05 = np.zeros((n_sim, 8), dtype=np.float32)
all_diags     = []
n_gal_list    = []
t_start       = time.time()

print(f"\n[{args.mode.upper()}] {n_sim} simulazioni, z=0.5, HOD calibrato BGS")
print(f"HOD params: log_Mmin={HOD_BGS_CALIBRATED[0]:.2f}, "
      f"log_M1={HOD_BGS_CALIBRATED[3]:.2f}, alpha={HOD_BGS_CALIBRATED[4]:.2f}")
print("-" * 70)

for i in range(n_sim):
    sim_idx = i
    if str(sim_idx) in manifest:
        cfile = CHAINS_DIR / f"z05_{sim_idx:04d}.npz"
        if cfile.exists():
            d = np.load(cfile)
            all_feats_z05[i] = d["feat"]
            n_gal_list.append(int(d["n_gal"]))
            continue

    feat, diag = process_sim_z05(sim_idx)
    all_feats_z05[i] = feat
    all_diags.append(diag)
    if diag["n_gal"] > 0:
        n_gal_list.append(diag["n_gal"])

    manifest[str(sim_idx)] = "done"
    with open(MANIFEST, "w") as f:
        json.dump(manifest, f)

    if i == 0 or (i+1) % max(1, n_sim//10) == 0:
        elapsed = time.time() - t_start
        eta_h   = (elapsed/(i+1)) * (n_sim-i-1) / 3600
        print(f"  {i+1:4d}/{n_sim} | n_gal={diag['n_gal']:6d} | "
              f"t={diag['t_s']:.1f}s | ETA={eta_h:.1f}h")

# Gate D2
gate_d2_passed, gate_d2_discr = check_gate_d2(n_gal_list, label="z=0.5")

# Gate D2 anche su z=0 (Phase 5 B3)
if OUTPUT_Z0.exists():
    data_z0 = np.load(OUTPUT_Z0, allow_pickle=True)
    # n_gal non e salvato in B3 direttamente, usiamo le diagnostiche
    diag_b3 = RES_DIR / "phase5_hod_b3_diagnostics.json"
    if diag_b3.exists():
        with open(diag_b3) as f:
            db3 = json.load(f)
        n_gal_z0 = [d["n_gal"] for d in db3["individual_diagnostics"][:n_sim]]
        gate_d2_z0_passed, gate_d2_z0_discr = check_gate_d2(n_gal_z0, label="z=0")

# Salva feature z=0.5
np.savez(OUTPUT_Z05,
         fvecs_hod_z05=all_feats_z05[:n_sim],
         w0=w0_all[:n_sim], Omm=Omm_all[:n_sim], s8=s8_all[:n_sim],
         hod_params=HOD_BGS_CALIBRATED,
         n_sim=n_sim,
         snapnum=SNAPNUM_Z05,
         R_smooth_mpc_h=args.R_smooth)
print(f"\nSalvato: {OUTPUT_Z05}")

# Confronto feature z=0 vs z=0.5 vs DESI
print(f"\n{'='*70}")
print("CONFRONTO FEATURE: z=0 vs z=0.5 vs DESI BGS")
print(f"{'='*70}")

feature_names = [
    'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
    'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
]

# Feature z=0.5 (media sul campione pilota/completo)
valid_z05 = all_feats_z05[:n_sim][all_feats_z05[:n_sim, 4] > 0]
mean_z05 = valid_z05.mean(axis=0) if len(valid_z05) > 0 else np.zeros(8)
std_z05  = valid_z05.std(axis=0)  if len(valid_z05) > 0 else np.zeros(8)

# Feature z=0 (Phase 5 B3)
if OUTPUT_Z0.exists():
    data_z0 = np.load(OUTPUT_Z0, allow_pickle=True)
    fvecs_z0 = data_z0['fvecs_hod_b3']
    mean_z0  = fvecs_z0.mean(axis=0)
    std_z0   = fvecs_z0.std(axis=0)
else:
    mean_z0 = std_z0 = np.zeros(8)

# DESI BGS NGC
desi_feats = np.array([-0.1968, 11132.0, 1.0266, 13601.9,
                        29683.0, 0.4589, 2969.0, 86.0])

print(f"  {'Feature':<25} {'z=0 mock':>12} {'z=0.5 mock':>12} {'DESI NGC':>12}")
print(f"  {'-'*63}")
for j, name in enumerate(feature_names):
    print(f"  {name:<25} {mean_z0[j]:>12.3f} {mean_z05[j]:>12.3f} {desi_feats[j]:>12.3f}")

# Interpolazione bracket z=0 / z=0.5 -> stima z=0.2
# Frazione lineare: z=0.2 e al 40% tra z=0 e z=0.5
print(f"\n  Bracket deterministico [z=0, z=0.5] per z_eff=0.2:")
frac = 0.2 / 0.5  # interpolazione lineare
for j, name in enumerate(feature_names[:6]):  # solo feature principali
    v0   = mean_z0[j]
    v05  = mean_z05[j]
    v_lo = min(v0, v05)
    v_hi = max(v0, v05)
    desi = desi_feats[j]
    in_range = v_lo <= desi <= v_hi if v_lo != v_hi else False
    flag = "  <- DESI in range" if in_range else ""
    print(f"  {name:<25}: [{v_lo:.3f}, {v_hi:.3f}]  DESI={desi:.3f}{flag}")

# Diagnostiche finali
diag_out = {
    "schema_version": "2.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "mode": args.mode,
    "n_sim": n_sim,
    "snapnum_z05": SNAPNUM_Z05,
    "R_smooth_mpc_h": args.R_smooth,
    "hod_params_bgs_calibrated": HOD_BGS_CALIBRATED.tolist(),
    "hod_param_names": HOD_PARAM_NAMES,
    "n_gal_target_quijote": N_GAL_TARGET_QUIJOTE,
    "gate_d2_z05": {
        "passed": gate_d2_passed,
        "discrepancy_fraction": gate_d2_discr,
        "verdict": "PASS" if gate_d2_passed else "FAIL — considera Opzione C HOD"
    },
    "feature_comparison": {
        "z0_mean": mean_z0.tolist(),
        "z05_mean": mean_z05.tolist(),
        "desi_ngc": desi_feats.tolist(),
        "feature_names": feature_names,
    },
    "individual_diagnostics": all_diags,
}

with open(OUTPUT_DIAG, "w") as f:
    json.dump(diag_out, f, indent=2)

print(f"\n{'='*70}")
print(f"RIEPILOGO")
print(f"{'='*70}")
print(f"  Gate D2 z=0.5:     {'PASS' if gate_d2_passed else 'FAIL'} "
      f"(discrepanza {100*gate_d2_discr:.1f}%)")
print(f"  b2_mean_persistence z=0:   {mean_z0[5]:.4f}")
print(f"  b2_mean_persistence z=0.5: {mean_z05[5]:.4f}")
print(f"  b2_mean_persistence DESI:  {desi_feats[5]:.4f}")
print(f"\n  Output z=0.5: {OUTPUT_Z05}")
print(f"  Diagnostiche: {OUTPUT_DIAG}")
if args.mode == "pilot":
    t_per_sim = (time.time()-t_start) / n_sim
    print(f"\n  Tempo/sim: {t_per_sim:.1f}s")
    print(f"  Stima run completo 2000 sim: {t_per_sim*2000/3600:.1f}h")
    print(f"\n  Per il run completo:")
    print(f"  python src/phase6_mock_calibration.py --mode full")
print(f"{'='*70}")
