"""
CAUCHY — R5-1 Test diagnostico: solo log_Mmin libero
src/phase_r51_mmin_only.py

Obiettivo: isolare il contributo di log_Mmin alla varianza topologica,
tenendo fissi sigma_logM, log_M0, log_M1, alpha ai valori B3.

Domanda: il VIF residuo è dominato da log_Mmin o dagli altri parametri HOD?

Design:
  - log_Mmin:   libero U[12.837, 13.137] (prior v3 calibrato)
  - sigma_logM: 0.55  (fisso B3)
  - log_M0:     12.25 (fisso B3)
  - log_M1:     13.5  (fisso B3)
  - alpha:       1.0  (fisso B3)
  - N=200 campi, K=10, N_perm=500
  - Rejection n_gal ∈ [600K, 1.2M] invariato

Interpretazione:
  σ_marg > 1.5σ → altri parametri HOD dominano il VIF in v3; procedere con prior stretto su tutti
  σ_marg ~ 0    → log_Mmin stesso nella zona [12.8,13.1] causa varianza topologica; Opzione 3 completa

Output: results/phase_r51_mmin_only.json
Tempo stimato: ~6h (200 × 10 × 9.5s / 3600)
"""


import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY R5-1 — HOD prior ristretto BGS")
parser.add_argument("--n_sim",        type=int,   default=500)
parser.add_argument("--K",            type=int,   default=20,
                    help="Campioni HOD per campo (forward Monte Carlo)")
parser.add_argument("--seed",         type=int,   default=42)
parser.add_argument("--n_perm",       type=int,   default=1000)
parser.add_argument("--resume",       action="store_true")
parser.add_argument("--project_root", type=str,   default=".")
# Opzione A: rejection sampling su n_gal
parser.add_argument("--n_gal_lo",     type=int,   default=600000,
                    help="Minimo n_gal accettabile (default 600K = -33%% target BGS)")
parser.add_argument("--n_gal_hi",     type=int,   default=1200000,
                    help="Massimo n_gal accettabile (default 1.2M = +33%% target BGS)")
parser.add_argument("--max_attempts", type=int,   default=50,
                    help="Max tentativi rejection per campione k (default 50)")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths — ereditate da B3, output separati per R5-1
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE        = ROOT / "results" / "phase1_fiducial_cache.npz"
RESULTS_DIR      = ROOT / "results"
R51_CACHE_DIR    = RESULTS_DIR / "phase_r51_cache_mmin_only"
OUTPUT_FEATURES  = RESULTS_DIR / "phase_r51_features_mmin_only.npz"
OUTPUT_RESULTS   = RESULTS_DIR / "phase_r51_mmin_only.json"
MANIFEST         = RESULTS_DIR / "phase_r51_manifest_mmin_only.json"

R51_CACHE_DIR.mkdir(parents=True, exist_ok=True)
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Costanti fisiche Quijote (invariate da B3)
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20

# ---------------------------------------------------------------------------
# Prior ristretto R5-1 — Zheng 2007 5 parametri
# Derivazione: Smith & Grove 2024 (BGS DR1) + vincolo fisico Phase 5
# NOTA: A_cen, A_sat, eta_vel, eta_conc fissi a 0/0/1/1 (come B3)
#        → effettivo Zheng 2007 a 5 parametri liberi
# ---------------------------------------------------------------------------
# Bounds: [log_Mmin, sigma_logM, log_M0, log_M1, alpha]
PRIOR_LOW_5  = np.array([12.837, 0.2, 11.5, 13.0, 0.5])
PRIOR_HIGH_5 = np.array([13.137, 0.8, 13.0, 14.2, 1.5])
PRIOR_FIXED  = np.array([0.0, 0.0, 1.0, 1.0])  # A_cen, A_sat, eta_vel, eta_conc

PRIOR_NAME_5 = ["log_Mmin", "sigma_logM", "log_M0", "log_M1", "alpha"]

# Parametri B3 di riferimento (verificare che cadano dentro il prior)
B3_PARAMS_5 = np.array([12.5, 0.55, 12.25, 13.5, 1.0])

# v3: B3 params possono essere fuori prior — nessun assert

# Nota v3: B3 params (log_Mmin=12.5) sono FUORI dal prior v3 [12.837, 13.137]
# Questo è corretto — il prior v3 è calibrato su n_gal Quijote, non su B3
B3_in_prior_v3 = bool(np.all(B3_PARAMS_5 >= PRIOR_LOW_5) and np.all(B3_PARAMS_5 <= PRIOR_HIGH_5))

print("=" * 70)
print("CAUCHY R5-1 v3 — HOD prior calibrato su n_gal Quijote")
print("=" * 70)
print(f"\nPrior Zheng 5-param v3 (calibrato da phase_r51_calibrate_mmin.py):")
print(f"  {'Parametro':<14} {'Low':>8} {'High':>8} {'B3_ref':>8}  {'B3_in_prior':>12}")
for nm, lo, hi, b3 in zip(PRIOR_NAME_5, PRIOR_LOW_5, PRIOR_HIGH_5, B3_PARAMS_5):
    inside = "✓" if lo <= b3 <= hi else "— (fuori prior v3)"
    print(f"  {nm:<14} {lo:>8.3f} {hi:>8.3f} {b3:>8.3f}  {inside:>18}")
print(f"\n  NOTA: log_Mmin B3=12.5 è fuori prior v3 [12.837,13.137] — corretto.")
print(f"  Il prior v3 è calibrato su n_gal~900K su Quijote, non su B3.")
print(f"  Tutti gli altri parametri HOD hanno prior invariato rispetto a v2.")
print(f"\nDesign: N={args.n_sim} campi, K={args.K} campioni HOD accettati, N_perm={args.n_perm}")
print(f"Rejection sampling: n_gal ∈ [{args.n_gal_lo:,}, {args.n_gal_hi:,}], max_attempts={args.max_attempts}")
print(f"Threshold PASS: σ_marg ≥ 2.0σ (frozen pre-esecuzione)")
print()


# ---------------------------------------------------------------------------
# FoF reader — identico a B3 (formato SOA Quijote verificato)
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
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE
    mass_h = FoF.GroupMass[mask] * 1e10
    return pos_h, mass_h


# ---------------------------------------------------------------------------
# HOD Zheng 2007 — identico a B3
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
    """hod_params: array a 9 elementi [5 liberi + 4 fissi]"""
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


# ---------------------------------------------------------------------------
# Campo galattico CIC — identico a B3
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Feature TDA — identica a B3 (bug v3 corretti: birth=-diag[:,0], death=-diag[:,1])
# sigma_smooth=0.64 (σ_px=0.640 per Quijote 128³, R=5 Mpc/h)
# ---------------------------------------------------------------------------
def compute_tda_features(delta_field, sigma_smooth=0.64, n_thresh=100):
    try:
        import gudhi
    except ImportError:
        raise ImportError("gudhi non trovato: conda install -c conda-forge gudhi")

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
        birth = -df[:, 0]   # superlevel: birth = soglia alta
        death = -df[:, 1]   # superlevel: death = soglia bassa
        pers  = birth - death  # > 0 per definizione
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
        feats[5] = float(np.mean(pers_1))        # b2_mean_persistence ≡ ⟨pers₁⟩ — feature primaria
        p90      = np.percentile(pers_1, 90)
        feats[6] = float(np.sum(pers_1 >= p90))

    mean_field_val = float(field_s.mean())
    idx_mean = np.argmin(np.abs(thresholds - mean_field_val))
    feats[7] = float(b0_curve[idx_mean])

    return feats


# ---------------------------------------------------------------------------
# Partial correlation — OLS residualizzazione (identica a Phase 5/6/7)
# ---------------------------------------------------------------------------
def partial_corr(x, y, z_controls):
    """r(x, y | z_controls) via OLS residualizzazione"""
    def residuals(v, Z):
        Z_aug = np.column_stack([np.ones(len(v)), Z])
        coef, *_ = np.linalg.lstsq(Z_aug, v, rcond=None)
        return v - Z_aug @ coef
    rx = residuals(x, z_controls)
    ry = residuals(y, z_controls)
    r, p = pearsonr(rx, ry)
    return r, p


def permutation_sigma(feat, w0, controls, n_perm, seed):
    """σ = (|r_obs| - mean(r_null)) / std(r_null) via permutation test"""
    r_obs, _ = partial_corr(feat, w0, controls)
    rng_perm = np.random.default_rng(seed)
    r_null = np.zeros(n_perm)
    for i in range(n_perm):
        w0_perm = rng_perm.permutation(w0)
        r_null[i], _ = partial_corr(feat, w0_perm, controls)
    sigma = (np.abs(r_obs) - np.mean(np.abs(r_null))) / (np.std(r_null) + 1e-12)
    return float(sigma), float(r_obs), float(np.mean(r_null)), float(np.std(r_null))


# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
print("Caricamento parametri cosmologici nwLH...")
assert NWLH_PARAMS_FILE.exists(), f"File non trovato: {NWLH_PARAMS_FILE}"
cosmo_params = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
Omm_all = cosmo_params[:, 0]
s8_all  = cosmo_params[:, 4]
w0_all  = cosmo_params[:, 6]
print(f"  w0 range: [{w0_all.min():.2f}, {w0_all.max():.2f}], N={len(w0_all)}")

assert TDA_CACHE.exists(), f"Cache TDA non trovata: {TDA_CACHE}"
cache = np.load(TDA_CACHE, allow_pickle=True)
fvecs_nwlh = cache["fvecs_nwlh"]  # fallback DM

# ---------------------------------------------------------------------------
# Selezione N=500 campi uniformi su w₀ (seed=42, pre-specificato)
# Approccio: sort per w₀, poi ogni 4° indice → distribuzione uniforme su w₀
# ---------------------------------------------------------------------------
rng_select = np.random.default_rng(args.seed)
sort_by_w0 = np.argsort(w0_all)
# Seleziona ogni (2000/500)=4° indice → 500 campi uniformi su w₀
step = len(w0_all) // args.n_sim
selected_indices = sort_by_w0[::step][:args.n_sim]
# shuffle per evitare correlazioni sistematiche nella sequenza di processing
rng_select.shuffle(selected_indices)

print(f"\nSelezione {args.n_sim} campi uniformi su w₀ (step={step}, seed={args.seed}):")
w0_sel = w0_all[selected_indices]
print(f"  w0_sel range: [{w0_sel.min():.2f}, {w0_sel.max():.2f}]")
print(f"  w0_sel mean:  {w0_sel.mean():.4f} (atteso ~-1.0)")

# Resume manifest
manifest = {}
if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"\n  Resume: {len(manifest)} campi già completati.")

# ---------------------------------------------------------------------------
# Main loop — forward sampling K=20 per campo
# ---------------------------------------------------------------------------
# feat_matrix[i, k, :] = feature TDA per campo i, campione HOD k
# feat_marg[i, :] = media su K → feature marginalizzata
feat_matrix = np.zeros((args.n_sim, args.K, 8), dtype=np.float32)
feat_marg   = np.zeros((args.n_sim, 8), dtype=np.float32)
n_gal_matrix = np.zeros((args.n_sim, args.K), dtype=np.int32)

all_diags = []
t_start   = time.time()

# RNG globale per sampling HOD — seed deterministico
rng_hod = np.random.default_rng(args.seed + 1000)

print(f"\n[R5-1] {args.n_sim} campi × K={args.K} campioni HOD = {args.n_sim*args.K} TDA runs")
print("-" * 70)

for field_idx, sim_idx in enumerate(selected_indices):
    sim_idx = int(sim_idx)
    cache_key = str(sim_idx)

    # Resume
    if cache_key in manifest and manifest[cache_key] == "done":
        cache_file = R51_CACHE_DIR / f"r51_{sim_idx:04d}.npz"
        if cache_file.exists():
            c = np.load(cache_file)
            feat_matrix[field_idx] = c["feat_matrix_k"]
            feat_marg[field_idx]   = c["feat_marg"]
            n_gal_matrix[field_idx] = c["n_gal_k"]
        continue

    t0 = time.time()

    # Lettura catalogo aloni
    pos_h, mass_h = read_halo_catalog(sim_idx)

    if pos_h is None or len(pos_h) < 50:
        # Fallback DM: replica il vettore DM per tutti i K campioni
        for k in range(args.K):
            feat_matrix[field_idx, k] = fvecs_nwlh[sim_idx]
        feat_marg[field_idx] = fvecs_nwlh[sim_idx]
        status = "FALLBACK_DM"
        n_gal_k = np.zeros(args.K, dtype=np.int32)
        t_gudhi_mean = 0.0
        acceptance_rate = 0.0
    else:
        feat_k_list = []
        n_gal_k = np.zeros(args.K, dtype=np.int32)
        t_gudhi_list = []
        fallback_k = 0
        n_rejected_total = 0  # tentativi falliti per rejection n_gal

        for k in range(args.K):
            # Rejection sampling: campiona θ_HOD finché n_gal ∈ [n_gal_lo, n_gal_hi]
            accepted = False
            for attempt in range(args.max_attempts):
                # TEST MMIN-ONLY: solo log_Mmin libero, altri fissi a B3
                log_Mmin_k = rng_hod.uniform(PRIOR_LOW_5[0], PRIOR_HIGH_5[0])
                hod_params_full = np.array([
                    log_Mmin_k,          # log_Mmin: libero [12.837, 13.137]
                    B3_PARAMS_5[1],      # sigma_logM = 0.55 (fisso B3)
                    B3_PARAMS_5[2],      # log_M0 = 12.25 (fisso B3)
                    B3_PARAMS_5[3],      # log_M1 = 13.5 (fisso B3)
                    B3_PARAMS_5[4],      # alpha = 1.0 (fisso B3)
                    PRIOR_FIXED[0], PRIOR_FIXED[1], PRIOR_FIXED[2], PRIOR_FIXED[3]
                ])
                rng_sim_k = np.random.default_rng(args.seed + sim_idx * 100 + k * 1000 + attempt)
                pos_gal_try = populate_halos_hod(pos_h, mass_h, hod_params_full, rng_sim_k)
                n_try = len(pos_gal_try)
                if args.n_gal_lo <= n_try <= args.n_gal_hi:
                    pos_gal = pos_gal_try
                    theta_5_accepted = np.array([log_Mmin_k, B3_PARAMS_5[1],
                                                  B3_PARAMS_5[2], B3_PARAMS_5[3],
                                                  B3_PARAMS_5[4]])
                    hod_params_accepted = hod_params_full
                    n_rejected_total += attempt  # tentativi falliti prima di accettare
                    accepted = True
                    break
                n_rejected_total += 1

            if not accepted:
                # Fallback: usa HOD B3 mediano — riproducibile
                hod_b3_full = np.array([12.5, 0.55, 12.25, 13.5, 1.0,
                                        0.0, 0.0, 1.0, 1.0])
                rng_sim_k = np.random.default_rng(args.seed + sim_idx * 100 + k)
                pos_gal = populate_halos_hod(pos_h, mass_h, hod_b3_full, rng_sim_k)
                fallback_k += 1

            if len(pos_gal) < 100:
                feat_k_list.append(fvecs_nwlh[sim_idx])
                n_gal_k[k] = len(pos_gal)
                fallback_k += 1
                continue

            n_gal_k[k] = len(pos_gal)

            delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)
            delta_gal = delta_gal - delta_gal.mean()

            t_g0 = time.time()
            feat = compute_tda_features(delta_gal)
            t_gudhi_list.append(time.time() - t_g0)

            if np.isfinite(feat).all():
                feat_k_list.append(feat)
            else:
                feat_k_list.append(fvecs_nwlh[sim_idx])
                fallback_k += 1

        feat_k_arr = np.array(feat_k_list, dtype=np.float32)  # [K, 8]
        feat_matrix[field_idx] = feat_k_arr
        # Feature marginalizzata = media su K campioni HOD
        feat_marg[field_idx]   = feat_k_arr.mean(axis=0)
        n_gal_matrix[field_idx] = n_gal_k
        t_gudhi_mean = float(np.mean(t_gudhi_list)) if t_gudhi_list else 0.0
        acceptance_rate = float(args.K / max(args.K + n_rejected_total, 1))
        status = "completed" if fallback_k == 0 else f"completed_k{fallback_k}fallback"

    elapsed = time.time() - t0

    # Checkpoint per resume
    np.savez(R51_CACHE_DIR / f"r51_{sim_idx:04d}.npz",
             sim_idx=sim_idx,
             feat_matrix_k=feat_matrix[field_idx],
             feat_marg=feat_marg[field_idx],
             n_gal_k=n_gal_matrix[field_idx],
             status=status)

    all_diags.append({
        "field_idx": field_idx,
        "sim_idx":   sim_idx,
        "status":    status,
        "n_gal_mean": float(n_gal_matrix[field_idx].mean()),
        "n_gal_std":  float(n_gal_matrix[field_idx].std()),
        "acceptance_rate": float(acceptance_rate),
        "t_gudhi_mean_s": float(t_gudhi_mean),
        "t_total_s": float(elapsed),
    })

    manifest[cache_key] = "done"
    with open(MANIFEST, "w") as mf:
        json.dump(manifest, mf)

    # Progress
    if field_idx == 0 or (field_idx + 1) % 50 == 0:
        done = field_idx + 1
        elapsed_total = time.time() - t_start
        eta_h = (elapsed_total / done) * (args.n_sim - done) / 3600
        n_gal_str = f"{n_gal_matrix[field_idx].mean():.0f}"
        acc_str = f"{acceptance_rate:.2f}" if acceptance_rate > 0 else "N/A"
        print(f"  Campo {field_idx:3d}/sim{sim_idx:4d} | t_gudhi={t_gudhi_mean:.1f}s "
              f"| n_gal_mean={n_gal_str} | acc={acc_str} | {status} | ETA={eta_h:.1f}h")

# ---------------------------------------------------------------------------
# Analisi statistica
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("ANALISI STATISTICA R5-1")
print(f"{'='*70}")

# Parametri cosmologici sul subset selezionato
w0_sub  = w0_all[selected_indices]
Omm_sub = Omm_all[selected_indices]
s8_sub  = s8_all[selected_indices]

# Feature primaria: b2_mean_persistence = feats[:,5]
FEAT_IDX = 5
feat_primary_marg = feat_marg[:, FEAT_IDX]
controls = np.column_stack([Omm_sub, s8_sub])

print(f"\n--- Feature primaria: b2_mean_persistence (⟨pers₁⟩, indice {FEAT_IDX}) ---")
print(f"  N campi:       {args.n_sim}")
print(f"  K campioni:    {args.K}")
print(f"  mean±std:      {feat_primary_marg.mean():.4f} ± {feat_primary_marg.std():.4f}")

# Correlazione parziale osservata
r_obs, p_obs = partial_corr(feat_primary_marg, w0_sub, controls)
print(f"\n  r_partial(⟨pers₁⟩, w₀ | Ωm, σ₈) = {r_obs:.4f}  (p={p_obs:.4f})")

# Permutation test
print(f"\n  Permutation test (N={args.n_perm})...")
sigma_marg, r_obs2, r_null_mean, r_null_std = permutation_sigma(
    feat_primary_marg, w0_sub, controls, args.n_perm, seed=args.seed + 9999
)
print(f"  σ_marg = {sigma_marg:.3f}σ")
print(f"  r_obs={r_obs2:.4f}, null_mean={r_null_mean:.4f}, null_std={r_null_std:.4f}")

# VIF prior ristretto
sigma2_intra = feat_matrix[:, :, FEAT_IDX].var(axis=1).mean()
sigma2_inter = feat_primary_marg.var()
VIF_restricted = float(sigma2_intra / (sigma2_inter + 1e-30))
print(f"\n  VIF prior ristretto = {VIF_restricted:.4f}")
print(f"  VIF prior flat (Phase 5 riferimento) = 2.483")
print(f"  Riduzione VIF: {(2.483 - VIF_restricted)/2.483*100:.1f}%")

# Convergenza in K: σ a K=5,10,15,K
print(f"\n--- Convergenza in K ---")
sigma_by_K = {}
for k_sub in [5, 10, 15, args.K]:
    if k_sub > args.K:
        continue
    feat_k_sub = feat_matrix[:, :k_sub, FEAT_IDX].mean(axis=1)
    s, *_ = permutation_sigma(feat_k_sub, w0_sub, controls,
                               n_perm=500, seed=args.seed + k_sub)
    sigma_by_K[k_sub] = float(s)
    print(f"  K={k_sub:2d}: σ = {s:.3f}σ")

delta_sigma_convergence = abs(sigma_by_K.get(args.K, 0) - sigma_by_K.get(max(5, args.K - 5), 0))
converged = delta_sigma_convergence < 0.3
print(f"\n  Δσ(K_last vs K_prev) = {delta_sigma_convergence:.3f}σ "
      f"({'CONVERGENTE' if converged else 'NON CONVERGENTE'})")

# n_gal diagnostiche
completed_diags = [d for d in all_diags if d["status"].startswith("completed")]
n_gal_means = [d["n_gal_mean"] for d in completed_diags]
acc_rates = [d["acceptance_rate"] for d in completed_diags if d["acceptance_rate"] > 0]
print(f"\n--- Diagnostica n_gal (con rejection sampling) ---")
print(f"  n_gal_mean medio: {np.mean(n_gal_means):.0f} (target BGS: ~900K)")
print(f"  n_gal_mean std:   {np.std(n_gal_means):.0f}")
print(f"  n_gal_mean range: [{np.min(n_gal_means):.0f}, {np.max(n_gal_means):.0f}]")
print(f"  Acceptance rate medio: {np.mean(acc_rates):.3f}" if acc_rates else "  Acceptance rate: N/A")

# Gate verdict
print(f"\n{'='*70}")
print("GATE R5-1 — VERDICT")
print(f"{'='*70}")
print(f"  σ_marg = {sigma_marg:.3f}σ")
print(f"  Threshold PASS: ≥ 2.0σ  |  BORDERLINE: 1.5–2.0σ  |  FAIL: < 1.5σ")
if sigma_marg >= 2.0:
    gate_verdict = "PASS"
    gate_interpretation = "HOD mis-calibration esclusa come sistematica dominante"
elif sigma_marg >= 1.5:
    gate_verdict = "BORDERLINE"
    gate_interpretation = "Evidenza marginale. Sistematica HOD dichiarata ma non dominante"
else:
    gate_verdict = "FAIL"
    gate_interpretation = "HOD mis-calibration sistematica dominante. Claim da rivedere"
print(f"\n  VERDICT: {gate_verdict}")
print(f"  Interpretazione: {gate_interpretation}")

# ---------------------------------------------------------------------------
# Salvataggio
# ---------------------------------------------------------------------------
np.savez(OUTPUT_FEATURES,
         feat_marg=feat_marg,
         feat_matrix=feat_matrix,
         w0=w0_sub,
         Omm=Omm_sub,
         s8=s8_sub,
         selected_indices=selected_indices,
         prior_low=PRIOR_LOW_5,
         prior_high=PRIOR_HIGH_5,
         prior_fixed=PRIOR_FIXED,
         K=args.K,
         methodology="R5-1 HOD forward sampling prior ristretto BGS r<19.5")

results_out = {
    "schema_version":    "2.0",
    "task":              "R5-1_HOD_restricted_prior",
    "timestamp":         datetime.now(timezone.utc).isoformat(),
    "frozen_design": {
        "n_sim":         args.n_sim,
        "K":             args.K,
        "n_perm":        args.n_perm,
        "seed":          args.seed,
        "selection":     "uniform_w0_step4_sorted",
        "gate_threshold_pass": 2.0,
        "gate_threshold_borderline": 1.5,
        "rejection_sampling": {
            "n_gal_lo":     args.n_gal_lo,
            "n_gal_hi":     args.n_gal_hi,
            "max_attempts": args.max_attempts,
            "fallback":     "HOD_B3_median_if_max_attempts_exceeded",
        },
    },
    "prior_restricted": {
        "model":         "Zheng2007_5param",
        "source":        "phase_r51_calibrate_mmin.py — log_Mmin* calibrato su n_gal~900K "
                         "su 20 sim Quijote cosmologia centrale. Prior ±0.15 dex.",
        "parameters":    {nm: [float(lo), float(hi)]
                          for nm, lo, hi in zip(PRIOR_NAME_5, PRIOR_LOW_5, PRIOR_HIGH_5)},
        "fixed":         {"A_cen": 0.0, "A_sat": 0.0, "eta_vel": 1.0, "eta_conc": 1.0},
        "B3_params_in_prior": bool(np.all(B3_PARAMS_5 >= PRIOR_LOW_5) and
                                   np.all(B3_PARAMS_5 <= PRIOR_HIGH_5)),
        "anti_circularity": "log_Mmin* derivato da calibrazione n_gal su Quijote "
                            "(phase_r51_calibrate_mmin.py), non da segnale TDA. "
                            "B3=(12.5,...) è fuori dal prior v3 — nessuna circolarità.",
    },
    "primary_result": {
        "feature":       "b2_mean_persistence (⟨pers₁⟩, H1 mean persistence)",
        "feature_index": FEAT_IDX,
        "r_partial":     float(r_obs),
        "sigma_marg":    float(sigma_marg),
        "r_null_mean":   float(r_null_mean),
        "r_null_std":    float(r_null_std),
        "n_perm":        args.n_perm,
    },
    "vif_analysis": {
        "VIF_restricted": float(VIF_restricted),
        "VIF_flat_prior_phase5": 2.483,
        "reduction_pct": float((2.483 - VIF_restricted) / 2.483 * 100),
    },
    "K_convergence": {
        "sigma_by_K":    sigma_by_K,
        "delta_sigma":   float(delta_sigma_convergence),
        "converged":     bool(converged),
        "threshold":     0.3,
    },
    "n_gal_diagnostics": {
        "mean":  float(np.mean(n_gal_means)) if n_gal_means else 0.0,
        "std":   float(np.std(n_gal_means))  if n_gal_means else 0.0,
        "min":   float(np.min(n_gal_means))  if n_gal_means else 0.0,
        "max":   float(np.max(n_gal_means))  if n_gal_means else 0.0,
        "target_bgs": 900000,
        "rejection_window": [args.n_gal_lo, args.n_gal_hi],
        "acceptance_rate_mean": float(np.mean(acc_rates)) if acc_rates else 0.0,
        "acceptance_rate_std":  float(np.std(acc_rates))  if acc_rates else 0.0,
        "max_attempts": args.max_attempts,
    },
    "gate_r51": {
        "verdict":         gate_verdict,
        "sigma_marg":      float(sigma_marg),
        "threshold_pass":  2.0,
        "interpretation":  gate_interpretation,
    },
    "n_completed":       len(completed_diags),
    "n_fallback":        len([d for d in all_diags if "FALLBACK" in d["status"]]),
    "t_total_h":         float((time.time() - t_start) / 3600),
    "traceability": {
        "base_script":   "src/phase5_hod_b3.py",
        "prior_source":  "Smith & Grove 2024 (arXiv:2312.08792)",
        "physical_bound_source": "phase5_gate_result.json -> frozen_hod_analysis.physical_bound_log_Mmin",
        "gate_threshold_source": "PI decision 2026-06-08 (Q4)",
    },
}

with open(OUTPUT_RESULTS, "w") as f:
    json.dump(results_out, f, indent=2)

print(f"\n{'='*70}")
print(f"R5-1 v2 COMPLETATO")
print(f"  σ_marg = {sigma_marg:.3f}σ  →  {gate_verdict}")
print(f"  VIF ristretto = {VIF_restricted:.4f}  (vs flat 2.483)")
print(f"  Convergenza K: {'SÌ' if converged else 'NO'} (Δσ={delta_sigma_convergence:.3f}σ)")
print(f"  n_gal_mean: {np.mean(n_gal_means):.0f} (target 900K, window [{args.n_gal_lo:,},{args.n_gal_hi:,}])")
if acc_rates:
    print(f"  Acceptance rate medio: {np.mean(acc_rates):.3f}")
print(f"  Features: {OUTPUT_FEATURES}")
print(f"  Risultati: {OUTPUT_RESULTS}")
print(f"  Tempo totale: {(time.time()-t_start)/3600:.2f}h")
print(f"{'='*70}")
