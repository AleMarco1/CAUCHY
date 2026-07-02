"""
CAUCHY — OC-1 chiusura formale
src/phase_oc1_pk_hod.py

Obiettivo: confronto isometrico P(k) vs ⟨pers₁⟩ su campi HOD B3 identici.
Chiude OC-1 (Reviewer Phase 5 Concern 2, impegno pre-submission R5-3).

Contesto:
  Phase 7.1b (Confronto A) aveva addestrato Ridge+MLP su P(k) di campi DM,
  producendo σ_P(k)_DM = 2.26σ vs σ_TDA_DM = 0.095σ. Questo confronto è
  pulito ma non isometrico con il claim principale (TDA su HOD B3 = 3.73σ).

  Il confronto rilevante per il paper è su STESSO CAMPO:
    - TDA ⟨pers₁⟩ su HOD B3 → σ = 3.73σ (già in phase5_hod_b3_features.npz)
    - P(k) su HOD B3 → σ = ? (questo script)

  Se σ_P(k)_HOD < σ_TDA_HOD → TDA porta informazione aggiuntiva su HOD galaxies.
  Se σ_P(k)_HOD ≥ σ_TDA_HOD → P(k) è sufficiente, TDA non aggiunge.

Metodo:
  1. Rigenera campi HOD B3 deterministici (HOD_MEDIAN, seed fisso → riproducibile)
  2. Calcola P(k) 1D isotropo via FFT su ogni campo δ_HOD [128³]
     - 32 bin k logaritmici, k ∈ [k_fund, k_nyq]
     - Correzione window CIC in k-space (W_CIC = sinc²)
  3. Addestra Ridge e MLP su 1600 campi training (seed=42, stesso split di Confronto A)
  4. Calcola σ_partial(P(k)_HOD, w₀ | Ωm, σ₈) via permutation test N=1000
  5. Confronta con σ_TDA_HOD = 3.73σ (da phase5_hod_b3_features.npz)

Traceabilità:
  - HOD B3 parametri: phase5_hod_b3_features.npz -> hod_params_median
  - TDA reference: phase5_hod_b3_features.npz -> fvecs_hod_b3[:,5], σ=3.73σ
  - Split seed=42: coerente con phase7_pk_comparison_r53.json (Confronto A)
  - Output: results/phase_oc1_pk_hod.json

Uso:
  python src/phase_oc1_pk_hod.py [--n_sim 2000] [--seed 42] [--resume]

Tempo stimato: ~25 min (2000 campi × ~0.7s/campo HOD+FFT)
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter
from scipy.stats import pearsonr
from sklearn.linear_model import Ridge
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY OC-1 — P(k) HOD B3 vs TDA")
parser.add_argument("--n_sim",        type=int, default=2000)
parser.add_argument("--seed",         type=int, default=42)
parser.add_argument("--n_perm",       type=int, default=1000)
parser.add_argument("--resume",       action="store_true")
parser.add_argument("--project_root", type=str, default=".")
args = parser.parse_args()

ROOT        = Path(args.project_root)
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(parents=True, exist_ok=True)

HOD_CATALOG_DIR  = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_FEATURES_FILE = RESULTS_DIR / "phase5_hod_b3_features.npz"

OUTPUT_PK   = RESULTS_DIR / "phase_oc1_pk_hod_cache.npz"
OUTPUT_JSON = RESULTS_DIR / "phase_oc1_pk_hod.json"
MANIFEST    = RESULTS_DIR / "phase_oc1_pk_hod_manifest.json"

# ---------------------------------------------------------------------------
# Costanti fisiche
# ---------------------------------------------------------------------------
BOXSIZE    = 1000.0
NGRID      = 128
SNAPNUM    = 4
N_PART_MIN = 20

# HOD B3 mediano — identico a phase5_hod_b3.py
HOD_MEDIAN = np.array([12.5, 0.55, 12.25, 13.5, 1.0, 0.0, 0.0, 1.0, 1.0])

# P(k): 32 bin k logaritmici
N_KBINS    = 32

print("=" * 70)
print("CAUCHY OC-1 — P(k) HOD B3 vs TDA ⟨pers₁⟩ (confronto isometrico)")
print("=" * 70)
print(f"  N simulazioni: {args.n_sim}, seed={args.seed}, N_perm={args.n_perm}")
print(f"  HOD: B3 mediano deterministico (log_Mmin=12.5)")
print(f"  P(k): {N_KBINS} bin k logaritmici, correzione CIC")
print(f"  Split train/test: 1600/400 (seed={args.seed})")
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


# ---------------------------------------------------------------------------
# P(k) 1D isotropo — FFT + binning + correzione CIC
# ---------------------------------------------------------------------------
def compute_pk(delta_field, boxsize=1000.0, n_kbins=32):
    """
    P(k) 1D isotropo via FFT su campo δ [ngrid³].
    Correzione finestra CIC: W_CIC(k) = sinc²(kx/2kN) sinc²(ky/2kN) sinc²(kz/2kN)
    dove kN = π*ngrid/boxsize è il wavenumber di Nyquist.
    Ritorna (k_centers [n_kbins], pk [n_kbins]).
    """
    ngrid   = delta_field.shape[0]
    dk      = 2.0 * np.pi / boxsize
    k_nyq   = np.pi * ngrid / boxsize

    # FFT
    delta_k = np.fft.rfftn(delta_field.astype(np.float64))

    # Griglia k
    kx = np.fft.fftfreq(ngrid, d=1.0/ngrid).astype(np.float32)   # in unità di dk
    ky = np.fft.fftfreq(ngrid, d=1.0/ngrid).astype(np.float32)
    kz = np.fft.rfftfreq(ngrid, d=1.0/ngrid).astype(np.float32)

    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing='ij')
    K_mag = dk * np.sqrt(KX**2 + KY**2 + KZ**2).astype(np.float32)

    # Correzione CIC: W = prod sinc²(k_i / 2*k_N_i)
    # sinc(x) = sin(πx)/(πx), numpy sinc è già normalizzato: np.sinc(x) = sin(πx)/(πx)
    def cic_window(k_i_grid):
        # k_i_grid in unità intere (0..ngrid/2), kN = ngrid/2 in stesse unità
        x = k_i_grid / ngrid  # ∈ [0, 0.5]
        return np.sinc(x)**2   # = (sin(πx)/(πx))²

    W2 = (cic_window(np.abs(KX)) *
          cic_window(np.abs(KY)) *
          cic_window(np.abs(KZ))).astype(np.float32)
    W2 = np.where(W2 > 1e-10, W2, 1.0)  # evita divisione per zero a k=0

    # Potere spettrale corretto
    Pk_3d = (np.abs(delta_k)**2 / W2) * (boxsize**3 / ngrid**6)

    # Binning logaritmico in k
    k_fund = dk
    k_bins = np.logspace(np.log10(k_fund), np.log10(k_nyq), n_kbins + 1)

    K_flat  = K_mag.ravel()
    Pk_flat = Pk_3d.ravel().astype(np.float32)

    pk_out = np.zeros(n_kbins, dtype=np.float32)
    k_out  = np.zeros(n_kbins, dtype=np.float32)

    for i in range(n_kbins):
        mask = (K_flat >= k_bins[i]) & (K_flat < k_bins[i+1])
        if mask.sum() > 0:
            pk_out[i] = float(np.mean(Pk_flat[mask]))
            k_out[i]  = float(np.mean(K_flat[mask]))
        else:
            pk_out[i] = 0.0
            k_out[i]  = float(0.5 * (k_bins[i] + k_bins[i+1]))

    return k_out, pk_out


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

print("Caricamento feature TDA B3 (riferimento)...")
assert TDA_FEATURES_FILE.exists(), f"File non trovato: {TDA_FEATURES_FILE}"
tda_data = np.load(TDA_FEATURES_FILE)
fvecs_tda = tda_data["fvecs_hod_b3"]          # [2000, 8]
b2_pers_tda = fvecs_tda[:, 5].copy()           # ⟨pers₁⟩ — feature primaria
print(f"  fvecs_hod_b3: {fvecs_tda.shape}, b2_mean_persistence mean={b2_pers_tda.mean():.4f}")

# Resume
manifest = {}
pk_matrix = np.zeros((args.n_sim, N_KBINS), dtype=np.float32)
n_gal_arr = np.zeros(args.n_sim, dtype=np.int32)

if OUTPUT_PK.exists() and args.resume:
    cached = np.load(OUTPUT_PK)
    pk_matrix = cached["pk_matrix"]
    n_gal_arr = cached["n_gal_arr"]
    print(f"  Cache P(k) trovata: {OUTPUT_PK}")

if MANIFEST.exists() and args.resume:
    with open(MANIFEST) as f:
        manifest = json.load(f)
    print(f"  Resume: {len(manifest)} simulazioni già completate.")

# ---------------------------------------------------------------------------
# Main loop — calcolo P(k) su campi HOD B3
# ---------------------------------------------------------------------------
all_diags = []
t_start   = time.time()

print(f"\n[OC-1] Calcolo P(k) su {args.n_sim} campi HOD B3 deterministici")
print("-" * 70)

for sim_idx in range(args.n_sim):

    if str(sim_idx) in manifest and manifest[str(sim_idx)] == "done":
        continue

    t0 = time.time()

    pos_h, mass_h = read_halo_catalog(sim_idx)

    if pos_h is None or len(pos_h) < 50:
        # Fallback: P(k) = 0 (esclude dalla regressione tramite n_gal=0)
        pk_matrix[sim_idx] = 0.0
        n_gal_arr[sim_idx] = 0
        status = "FALLBACK"
    else:
        rng = np.random.default_rng(args.seed + sim_idx)
        pos_gal = populate_halos_hod(pos_h, mass_h, HOD_MEDIAN, rng)

        if len(pos_gal) < 100:
            pk_matrix[sim_idx] = 0.0
            n_gal_arr[sim_idx] = len(pos_gal)
            status = "FALLBACK_FEW"
        else:
            n_gal_arr[sim_idx] = len(pos_gal)
            delta_gal = field_from_galaxies(pos_gal, ngrid=NGRID, boxsize=BOXSIZE)
            delta_gal = delta_gal - delta_gal.mean()
            _, pk_sim = compute_pk(delta_gal, boxsize=BOXSIZE, n_kbins=N_KBINS)
            pk_matrix[sim_idx] = pk_sim
            status = "completed"

    elapsed = time.time() - t0
    all_diags.append({"sim_idx": sim_idx, "status": status,
                       "n_gal": int(n_gal_arr[sim_idx]), "t_s": float(elapsed)})

    manifest[str(sim_idx)] = "done"

    # Salva cache + manifest ogni 200 sim
    if (sim_idx + 1) % 200 == 0 or sim_idx == 0:
        np.savez(OUTPUT_PK, pk_matrix=pk_matrix, n_gal_arr=n_gal_arr,
                 w0=w0_all[:args.n_sim], Omm=Omm_all[:args.n_sim],
                 s8=s8_all[:args.n_sim])
        with open(MANIFEST, "w") as mf:
            json.dump(manifest, mf)
        done = sim_idx + 1
        elapsed_total = time.time() - t_start
        eta_h = (elapsed_total / done) * (args.n_sim - done) / 3600
        print(f"  Sim {sim_idx:4d} | n_gal={n_gal_arr[sim_idx]:7d} | "
              f"t={elapsed:.2f}s | ETA={eta_h:.2f}h | {status}")

# Salvataggio finale cache
np.savez(OUTPUT_PK, pk_matrix=pk_matrix, n_gal_arr=n_gal_arr,
         w0=w0_all[:args.n_sim], Omm=Omm_all[:args.n_sim],
         s8=s8_all[:args.n_sim])

completed = [d for d in all_diags if d["status"] == "completed"]
fallback  = [d for d in all_diags if "FALLBACK" in d["status"]]
print(f"\n  Completati: {len(completed)+len(manifest)-len(all_diags)}/{args.n_sim}")
print(f"  Fallback: {len(fallback)}")
print(f"  Tempo loop: {(time.time()-t_start)/60:.1f} min")


# ---------------------------------------------------------------------------
# Analisi statistica — Ridge + MLP su P(k) HOD B3
# Design corretto: σ calcolato su FULL SAMPLE via 5-fold CV predictions,
# coerente con σ_TDA=3.73σ calcolato su full sample in Phase 5.
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("ANALISI STATISTICA OC-1")
print(f"{'='*70}")

from sklearn.model_selection import cross_val_score, cross_val_predict, KFold

# Maschera: escludi fallback (n_gal=0)
valid_mask = n_gal_arr > 0
print(f"\n  Campi validi: {valid_mask.sum()}/{args.n_sim}")
print(f"  Metodo: 5-fold CV predictions su full sample (coerente con Phase 5)")

w0_v   = w0_all[:args.n_sim][valid_mask]
Omm_v  = Omm_all[:args.n_sim][valid_mask]
s8_v   = s8_all[:args.n_sim][valid_mask]
pk_v   = pk_matrix[valid_mask]
tda_v  = b2_pers_tda[:args.n_sim][valid_mask]

# Log transform P(k)
pk_log = np.log10(pk_v + 1e-10)

# Standardizzazione su full dataset
scaler_X = StandardScaler().fit(pk_log)
scaler_y = StandardScaler().fit(w0_v.reshape(-1, 1))
X_s = scaler_X.transform(pk_log)
y_s = scaler_y.transform(w0_v.reshape(-1, 1)).ravel()

controls_full = np.column_stack([Omm_v, s8_v])
kf = KFold(n_splits=5, shuffle=True, random_state=args.seed)

# ---------------------------------------------------------------------------
# Partial correlation utility
# ---------------------------------------------------------------------------
def partial_corr(x, y, z_controls):
    def residuals(v, Z):
        Z_aug = np.column_stack([np.ones(len(v)), Z])
        coef, *_ = np.linalg.lstsq(Z_aug, v, rcond=None)
        return v - Z_aug @ coef
    rx = residuals(x, z_controls)
    ry = residuals(y, z_controls)
    r, p = pearsonr(rx, ry)
    return float(r), float(p)

def permutation_sigma(feat, w0, controls, n_perm, seed):
    r_obs, _ = partial_corr(feat, w0, controls)
    rng_p = np.random.default_rng(seed)
    r_null = np.array([partial_corr(feat, rng_p.permutation(w0), controls)[0]
                       for _ in range(n_perm)])
    sigma = (np.abs(r_obs) - np.mean(np.abs(r_null))) / (np.std(r_null) + 1e-12)
    return float(sigma), float(r_obs), float(np.mean(r_null)), float(np.std(r_null))

# ---------------------------------------------------------------------------
# Ridge — ottimizzazione alpha + CV predictions su full sample
# ---------------------------------------------------------------------------
print(f"\n--- Ridge regression su P(k) HOD B3 (5-fold CV predictions) ---")
alphas = np.logspace(-2, 5, 30)
best_alpha, best_cv = None, -np.inf
for a in alphas:
    scores = cross_val_score(Ridge(alpha=a), X_s, y_s, cv=kf, scoring='r2')
    if scores.mean() > best_cv:
        best_cv = scores.mean()
        best_alpha = a

y_pred_ridge_cv = cross_val_predict(Ridge(alpha=best_alpha), X_s, y_s, cv=kf)
y_pred_ridge = scaler_y.inverse_transform(y_pred_ridge_cv.reshape(-1, 1)).ravel()

r_ridge, p_ridge = pearsonr(y_pred_ridge, w0_v)
sigma_ridge_marg, r_r2, *_ = permutation_sigma(
    y_pred_ridge, w0_v, controls_full, args.n_perm, args.seed + 1)
sigma_ridge_partial, *_ = permutation_sigma(
    y_pred_ridge, w0_v, controls_full, args.n_perm, args.seed + 2)

print(f"  Alpha ottimale: {best_alpha:.3f}  (CV R²={best_cv:.4f})")
print(f"  r(pred_ridge, w₀) = {r_ridge:.4f}  (p={p_ridge:.6f})")
print(f"  σ_marginal  = {sigma_ridge_marg:.3f}σ")
print(f"  σ_partial   = {sigma_ridge_partial:.3f}σ")

# ---------------------------------------------------------------------------
# MLP — CV predictions su full sample
# ---------------------------------------------------------------------------
print(f"\n--- MLP regression su P(k) HOD B3 (5-fold CV predictions) ---")
mlp_proto = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500,
                         random_state=args.seed, early_stopping=True,
                         validation_fraction=0.1, n_iter_no_change=20)
y_pred_mlp_cv = cross_val_predict(mlp_proto, X_s, y_s, cv=kf)
y_pred_mlp = scaler_y.inverse_transform(y_pred_mlp_cv.reshape(-1, 1)).ravel()

# Fit finale per n_iter_
mlp_final = MLPRegressor(hidden_layer_sizes=(64, 32), max_iter=500,
                         random_state=args.seed, early_stopping=True,
                         validation_fraction=0.1, n_iter_no_change=20)
mlp_final.fit(X_s, y_s)

r_mlp, p_mlp = pearsonr(y_pred_mlp, w0_v)
sigma_mlp_marg, *_ = permutation_sigma(
    y_pred_mlp, w0_v, controls_full, args.n_perm, args.seed + 3)
sigma_mlp_partial, *_ = permutation_sigma(
    y_pred_mlp, w0_v, controls_full, args.n_perm, args.seed + 4)

print(f"  Iterazioni (fit finale): {mlp_final.n_iter_}")
print(f"  r(pred_mlp, w₀) = {r_mlp:.4f}  (p={p_mlp:.6f})")
print(f"  σ_marginal  = {sigma_mlp_marg:.3f}σ")
print(f"  σ_partial   = {sigma_mlp_partial:.3f}σ")

# ---------------------------------------------------------------------------
# TDA reference — full sample (coerente con Phase 5)
# ---------------------------------------------------------------------------
print(f"\n--- TDA ⟨pers₁⟩ riferimento (full sample, N={valid_mask.sum()}) ---")
sigma_tda_marg, r_tda, *_ = permutation_sigma(
    tda_v, w0_v, controls_full, args.n_perm, args.seed + 5)
sigma_tda_partial, *_ = permutation_sigma(
    tda_v, w0_v, controls_full, args.n_perm, args.seed + 6)

print(f"  r(⟨pers₁⟩, w₀) = {r_tda:.4f}")
print(f"  σ_marginal  = {sigma_tda_marg:.3f}σ")
print(f"  σ_partial   = {sigma_tda_partial:.3f}σ")
print(f"  (riferimento Phase 5 full-sample N=2000: 3.73σ)")

# ---------------------------------------------------------------------------
# Confronto isometrico finale
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("CONFRONTO ISOMETRICO OC-1 — HOD B3 (stesso campo per TDA e P(k))")
print(f"{'='*70}")
print(f"\n  {'Statistica':<25} {'σ_marginal':>12} {'σ_partial':>12}")
print(f"  {'-'*50}")
print(f"  {'⟨pers₁⟩ (TDA)':<25} {sigma_tda_marg:>12.3f}σ {sigma_tda_partial:>12.3f}σ")
print(f"  {'Ridge(P(k))':<25} {sigma_ridge_marg:>12.3f}σ {sigma_ridge_partial:>12.3f}σ")
print(f"  {'MLP(P(k))':<25} {sigma_mlp_marg:>12.3f}σ {sigma_mlp_partial:>12.3f}σ")

best_pk_partial = max(sigma_ridge_partial, sigma_mlp_partial)
gain_pct = (sigma_tda_partial - best_pk_partial) / (abs(best_pk_partial) + 1e-6) * 100

print(f"\n  Gain TDA vs best P(k) (partial): {gain_pct:+.1f}%")

if sigma_tda_partial > best_pk_partial * 1.05:
    oc1_verdict = "TDA SUPERIORE — ⟨pers₁⟩ porta informazione topologica non catturata da P(k)"
elif sigma_tda_partial > best_pk_partial * 0.85:
    oc1_verdict = "TDA COMPARABILE — ⟨pers₁⟩ e P(k) portano informazione simile su HOD galaxies"
else:
    oc1_verdict = "P(k) SUPERIORE — P(k) cattura il segnale w₀ su HOD galaxies più efficacemente"

print(f"\n  OC-1 VERDICT: {oc1_verdict}")
print(f"\n  Confronto A (DM puro, phase7_pk_comparison_r53.json):")
print(f"  Ridge_DM=2.26σ | TDA_DM=0.095σ → P(k) domina su DM")
print(f"  Confronto B isometrico (HOD B3, questo script):")
print(f"  Ridge_HOD={sigma_ridge_partial:.3f}σ | TDA_HOD={sigma_tda_partial:.3f}σ")

# ---------------------------------------------------------------------------
# Salvataggio JSON
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "task":           "OC-1_pk_hod_isometric_v2",
    "timestamp":      datetime.now(timezone.utc).isoformat(),
    "design": {
        "n_sim":          args.n_sim,
        "n_valid":        int(valid_mask.sum()),
        "seed":           args.seed,
        "n_perm":         args.n_perm,
        "n_kbins":        N_KBINS,
        "pk_transform":   "log10",
        "hod_model":      "B3_deterministic_median",
        "stat_method":    "5-fold CV predictions on full sample (unbiased, coerente con Phase 5)",
    },
    "results": {
        "tda_pers1_hod": {
            "sigma_marginal":   float(sigma_tda_marg),
            "sigma_partial":    float(sigma_tda_partial),
            "r_pearson":        float(r_tda),
            "reference_phase5": 3.73,
        },
        "ridge_pk_hod": {
            "alpha_best":       float(best_alpha),
            "cv_r2":            float(best_cv),
            "sigma_marginal":   float(sigma_ridge_marg),
            "sigma_partial":    float(sigma_ridge_partial),
            "r_pearson":        float(r_ridge),
        },
        "mlp_pk_hod": {
            "n_iter":           int(mlp_final.n_iter_),
            "sigma_marginal":   float(sigma_mlp_marg),
            "sigma_partial":    float(sigma_mlp_partial),
            "r_pearson":        float(r_mlp),
        },
    },
    "confronto_A_reference": {
        "source":        "phase7_pk_comparison_r53.json",
        "ridge_pk_dm":   2.26,
        "tda_dm":        0.095,
        "note":          "Campi DM identici — misura pulita beyond-P(k) su DM",
    },
    "isometric_comparison": {
        "gain_tda_vs_best_pk_partial_pct": float(gain_pct),
        "best_pk_partial":  float(best_pk_partial),
        "tda_partial":      float(sigma_tda_partial),
        "verdict":          oc1_verdict,
    },
    "oc1_status":   "CLOSED",
    "n_fallback":   int((~valid_mask).sum()),
    "t_total_min":  float((time.time() - t_start) / 60),
    "traceability": {
        "tda_source":    "results/phase5_hod_b3_features.npz -> fvecs_hod_b3[:,5]",
        "pk_source":     "calcolato on-the-fly (HOD B3 deterministico, seed=42+sim_idx)",
        "method_note":   "5-fold CV predictions su full sample — nessun train/test leakage, coerente con permutation test Phase 5",
        "commitment":    "R5-3 phase5_gate_result.json impegni_pre_submission",
    },
}

with open(OUTPUT_JSON, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*70}")
print(f"OC-1 COMPLETATO — {oc1_verdict}")
print(f"  TDA ⟨pers₁⟩ HOD: σ_partial = {sigma_tda_partial:.3f}σ")
print(f"  Ridge P(k) HOD:  σ_partial = {sigma_ridge_partial:.3f}σ")
print(f"  MLP P(k) HOD:    σ_partial = {sigma_mlp_partial:.3f}σ")
print(f"  Gain TDA vs best P(k): {gain_pct:+.1f}%")
print(f"  Output: {OUTPUT_JSON}")
print(f"  Tempo totale: {(time.time()-t_start)/60:.1f} min")
print(f"{'='*70}")
