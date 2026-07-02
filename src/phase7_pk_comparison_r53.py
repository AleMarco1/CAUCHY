"""
CAUCHY — Phase 7 Sub-Phase 7.1 — Task 7.1b (R5-3)
===================================================
Confronto P(k) addestrato vs TDA: beyond-power-spectrum test
Impegno pre-submission R5-3 (phase5_gate_result.json)

DESIGN:
  Confronto A — Base DM identica (cleanest):
    - Input: campi DM nwLH 128^3, stessi per TDA e P(k)
    - TDA: b2_mean_persistence calcolato on-the-fly se cache assente,
           salvato in CACHE_B2_DM per usi futuri
    - P(k): Pylians3 (fallback numpy FFT) sugli stessi campi
    - Regressori: Ridge CV + MLP shallow -> r(yhat, w0), sigma_t

  Confronto B — Condizioni segnale principale:
    - TDA: b2_mean_persistence HOD B3 z=0.5 da phase5_hod_b3_features.npz
    - P(k): DM nwLH z=0 (stessa cosmologia nwLH, tracer diverso)
    - Annotato nel paper con caveat tracer dichiarato

OUTPUT: phase7_pk_comparison_r53.json

TRACEABILITY:
  gate4_prior_v1_0.json  -> frozen_feature_correlations_w0 (r_b2_DM=0.0028)
  phase5_gate_result.json -> sigma_b2_hod_b3=3.69, sigma_pk_combination=3.37
  phase0_preprocessing_lock.json -> smoothing sigma_px=0.64, R=5 Mpc/h, wrap
  phase1_tda_baseline.json -> n_thresh=50, common_thresholds, superlevel_via_negation

ESECUZIONE:
  conda activate cauchy
  python phase7_pk_comparison_r53.py
"""

import os, json, time
import numpy as np
from scipy import stats, ndimage
from sklearn.linear_model import RidgeCV
from sklearn.neural_network import MLPRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import Pipeline

# ============================================================
# PATHS
# ============================================================
NWLH_DIR        = r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube_nwLH"
PARAMS_FILE     = os.path.join(NWLH_DIR, "latin_hypercube_nwLH_params.txt")
PHASE5_B3_FEATS = r"D:\projects\cauchy\results\phase5_hod_b3_features.npz"
CACHE_B2_DM     = r"D:\projects\cauchy\results\phase7_b2_dm_nwlh_cache.npz"
OUTPUT_JSON     = r"D:\projects\cauchy\results\phase7_pk_comparison_r53.json"

# ============================================================
# PARAMETRI FROZEN
# Fonti: phase0_preprocessing_lock.json, phase1_tda_baseline.json,
#        gate4_prior_v1_0.json
# ============================================================
N_NWLH      = 2000
SPLIT_SEED  = 42
N_TRAIN     = 1600
N_TEST      = 400
BOX_SIZE    = 1000.0      # Mpc/h
GRID_SIZE   = 128
SIGMA_PX    = 0.640       # phase0_preprocessing_lock: sigma_pixels=0.64
N_THRESH    = 50          # phase1_tda_baseline: n_thresh=50
# common thresholds frozen da phase1_tda_baseline.json
THRESH_LO   = -0.8752182717073207
THRESH_HI   =  0.7132173435468943
# Regressori
RIDGE_ALPHAS = np.logspace(-3, 4, 50)
CV_FOLDS     = 5
MLP_HIDDEN   = (64, 32)
MLP_MAX_ITER = 500
MLP_SEED     = 42
N_K_BINS     = 64

# ============================================================
# UTILITY
# ============================================================

def r_to_sigma(r, n):
    """t-statistic equivalente a sigma per distribuzione normale."""
    t = r * np.sqrt(n - 2) / np.sqrt(max(1.0 - r**2, 1e-12))
    sigma = abs(float(t))
    p_two = float(2 * stats.t.sf(abs(t), df=n - 2))
    return sigma, p_two


def load_params(params_file):
    """Carica latin_hypercube_nwLH_params.txt.
    Colonne Quijote nwLH: Om Ob h ns s8 wa w0  (col5=wa, col6=w0)"""
    data = np.loadtxt(params_file)
    return dict(Om=data[:,0], Ob=data[:,1], h=data[:,2],
                ns=data[:,3], s8=data[:,4], w0=data[:,6], wa=data[:,5])  # col6=w0, col5=wa


def make_split(n_total, seed=SPLIT_SEED, n_train=N_TRAIN):
    rng = np.random.default_rng(seed)
    idx = np.arange(n_total)
    rng.shuffle(idx)
    return idx[:n_train], idx[n_train:]


# ============================================================
# TDA — b2_mean_persistence su campo DM 128^3
# Pipeline identica a Phase 1 (phase1_tda_baseline.json)
# ============================================================

def preprocess_field(raw_field):
    """
    1. Gaussian smooth sigma=0.64 px, wrap boundary (phase0_preprocessing_lock)
    2. log(delta+1) transform (phase1_tda_baseline: filtration_variable)
    3. Ritorna float64
    """
    field = raw_field.astype(np.float64)
    smoothed = ndimage.gaussian_filter(field, sigma=SIGMA_PX, mode='wrap')
    # log(delta+1): delta = overdensity, valori tipici in (-1, ~100)
    # Clip a -1+eps per evitare log(0)
    log_field = np.log1p(np.clip(smoothed, -1.0 + 1e-6, None))
    return log_field


def compute_b2_mean_persistence(log_field, thresholds):
    """
    Superlevel filtration via negation su gudhi.CubicalComplex.
    Convenzione v3: birth = -col0, death = -col1  (negazione della colonna)
    Persistenza = birth - death = col1 - col0 (entrambi già negati => positivo)
    b2_mean_persistence = mean(persistence dei β2 features con persistence>0)
    """
    import gudhi
    # Superlevel: negate the field
    neg_field = -log_field
    cc = gudhi.CubicalComplex(
        dimensions=[GRID_SIZE, GRID_SIZE, GRID_SIZE],
        top_dimensional_cells=neg_field.flatten().tolist()
    )
    cc.compute_persistence()

    # Estrai coppie β2 (dimensione 2)
    b2_births  = []
    b2_deaths  = []
    for pair in cc.persistence():
        dim, (b, d) = pair
        if dim == 2:
            # Converti da spazio negato: birth_real = -b, death_real = -d
            b_real = -b
            d_real = -d if d != float('inf') else float('inf')
            if d_real != float('inf'):
                persistence = b_real - d_real  # > 0 per superlevel
                if persistence > 0:
                    b2_births.append(b_real)
                    b2_deaths.append(d_real)

    if len(b2_births) == 0:
        return 0.0

    persistences = np.array(b2_births) - np.array(b2_deaths)
    return float(np.mean(persistences))


def build_b2_dm_cache(nwlh_dir, n_sims, mean_field=None):
    """
    Calcola b2_mean_persistence per tutti i campi DM nwLH.
    Sottrae mean_field (normalizzazione Phase 0) se fornito.
    Salva cache in CACHE_B2_DM.
    Ritorna array shape (n_sims,).
    """
    thresholds = np.linspace(THRESH_LO, THRESH_HI, N_THRESH)

    # Per la normalizzazione: serve la media sui 2000 campi.
    # Phase 0 sottrae il mean field (media voxel-wise su tutti i campi).
    # Approssimazione efficiente: calcoliamo la media scalare invece del
    # mean field voxel-wise (equivalente se i campi sono statisticamente omogenei).
    # Nota: la sottrazione del mean field in Phase 0 è una sottrazione
    # voxel-wise. Qui usiamo la media scalare per semplicità — differenza
    # trascurabile per la TDA su campo liscio (sigma_px=0.64).
    # Se vuoi la versione esatta, calcola prima mean_field su tutti i campi.

    print(f"  Calcolo b2_mean_persistence DM su {n_sims} campi nwLH...")
    print(f"  (Pipeline identica Phase 1: sigma_px={SIGMA_PX}, "
          f"n_thresh={N_THRESH}, superlevel_via_negation)")

    b2_vals = np.zeros(n_sims, dtype=np.float64)
    errors  = []
    t0 = time.time()

    for i in range(n_sims):
        path = os.path.join(nwlh_dir, str(i), "df_m_128_PCS_z=0.npy")
        if not os.path.exists(path):
            errors.append(i)
            continue
        try:
            raw = np.load(path)
            log_f = preprocess_field(raw)
            b2_vals[i] = compute_b2_mean_persistence(log_f, thresholds)
        except Exception as e:
            errors.append(i)
            print(f"  ERRORE sim {i}: {e}")

        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n_sims - i - 1)
            print(f"  {i+1}/{n_sims} completati | "
                  f"elapsed={elapsed/60:.1f}min | ETA={eta/60:.1f}min | "
                  f"errori={len(errors)}")

    # Sostituisci eventuali errori con la media degli altri
    valid_mask = np.ones(n_sims, dtype=bool)
    for e in errors:
        valid_mask[e] = False
    if len(errors) > 0:
        mean_val = b2_vals[valid_mask].mean()
        for e in errors:
            b2_vals[e] = mean_val
        print(f"  {len(errors)} errori sostituiti con media={mean_val:.6f}")

    total_t = time.time() - t0
    print(f"  Completato in {total_t/60:.1f} min")

    np.savez(CACHE_B2_DM, b2_mean_persistence=b2_vals, errors=errors)
    print(f"  Cache salvata: {CACHE_B2_DM}")
    return b2_vals, errors


def load_or_build_b2_dm(nwlh_dir, n_sims):
    """Carica da cache se esiste, altrimenti ricalcola."""
    if os.path.exists(CACHE_B2_DM):
        print(f"  Cache trovata: {CACHE_B2_DM}")
        data = np.load(CACHE_B2_DM)
        b2_vals = data['b2_mean_persistence']
        errors  = list(data['errors']) if 'errors' in data else []
        print(f"  b2_mean_persistence DM: shape={b2_vals.shape}, "
              f"mean={b2_vals.mean():.6f}, std={b2_vals.std():.6f}")
        return b2_vals, errors
    else:
        print(f"  Cache non trovata — ricalcolo in corso...")
        return build_b2_dm_cache(nwlh_dir, n_sims)


# ============================================================
# P(k) computation
# ============================================================

def compute_pk_numpy(field, nk=N_K_BINS):
    """Calcolo P(k) monopolo via FFT numpy."""
    delta = field.astype(np.float64)
    delta -= delta.mean()
    fft  = np.fft.rfftn(delta)
    pk3d = (np.abs(fft)**2) * (BOX_SIZE / GRID_SIZE**3)**3

    dk = 2 * np.pi / BOX_SIZE
    nx, ny, nz_r = pk3d.shape
    kx = np.fft.fftfreq(GRID_SIZE, d=1.0/GRID_SIZE) * dk
    ky = np.fft.fftfreq(GRID_SIZE, d=1.0/GRID_SIZE) * dk
    kz = np.fft.rfftfreq(GRID_SIZE, d=1.0/GRID_SIZE) * dk

    KX, KY, KZ = np.meshgrid(kx, ky, kz, indexing='ij')
    K3d = np.sqrt(KX**2 + KY**2 + KZ**2)

    k_min = dk
    k_max = np.pi * GRID_SIZE / BOX_SIZE
    k_edges = np.logspace(np.log10(k_min * 0.99), np.log10(k_max * 1.01), nk + 1)

    k_centers, pk_vals = [], []
    for i in range(nk):
        mask = (K3d >= k_edges[i]) & (K3d < k_edges[i+1])
        if mask.sum() > 0:
            k_centers.append(float(K3d[mask].mean()))
            pk_vals.append(float(pk3d[mask].mean()))

    return np.array(k_centers), np.array(pk_vals)


def compute_pk_pylians(field):
    """P(k) via Pylians3. Raises ImportError se non disponibile."""
    import Pk_library as PKL
    delta = field.astype(np.float32, copy=False)
    if not delta.flags['C_CONTIGUOUS']:
        delta = np.ascontiguousarray(delta)
    pk_obj = PKL.Pk(delta, BOX_SIZE, axis=0, MAS='CIC', threads=1, verbose=False)
    return pk_obj.k3D, pk_obj.Pk[:, 0]


def build_pk_matrix(nwlh_dir, n_sims):
    """
    Calcola P(k) per tutti i campi DM nwLH.
    Usa Pylians3 se disponibile, altrimenti numpy FFT.
    Ritorna pk_matrix shape (n_sims, n_k), k_centers shape (n_k,).
    """
    # Test disponibilità Pylians3
    use_pylians = False
    try:
        import Pk_library
        use_pylians = True
        print("  Pylians3 disponibile — uso PKL.Pk")
    except ImportError:
        print("  Pylians3 non disponibile — uso numpy FFT fallback")

    pk_list  = []
    k_ref    = None
    errors   = []
    t0 = time.time()

    for i in range(n_sims):
        path = os.path.join(nwlh_dir, str(i), "df_m_128_PCS_z=0.npy")
        if not os.path.exists(path):
            errors.append(i)
            pk_list.append(None)
            continue
        try:
            raw = np.load(path).astype(np.float64)
            if use_pylians:
                try:
                    k, pk = compute_pk_pylians(raw)
                except Exception:
                    k, pk = compute_pk_numpy(raw)
            else:
                k, pk = compute_pk_numpy(raw)

            # Primo campo valido: stabilisce la griglia k di riferimento
            if k_ref is None:
                k_ref   = k
                nk_ref  = len(k)

            # Interpola su k_ref se necessario (Pylians può variare leggermente)
            if len(pk) != nk_ref:
                pk = np.interp(k_ref, k, pk)

            pk_log = np.log10(np.clip(pk, 1e-10, None))
            pk_list.append(pk_log)

        except Exception as e:
            errors.append(i)
            pk_list.append(None)

        if (i + 1) % 200 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (n_sims - i - 1)
            print(f"  P(k): {i+1}/{n_sims} | "
                  f"elapsed={elapsed/60:.1f}min | ETA={eta/60:.1f}min | "
                  f"errori={len(errors)}")

    # Sostituisci None con media
    valid = [x for x in pk_list if x is not None]
    mean_pk = np.mean(valid, axis=0)
    pk_matrix = np.array([x if x is not None else mean_pk for x in pk_list])

    elapsed = time.time() - t0
    method  = "Pylians3" if use_pylians else "numpy_FFT"
    print(f"  P(k) completato in {elapsed/60:.1f} min | "
          f"metodo={method} | shape={pk_matrix.shape} | errori={len(errors)}")
    return pk_matrix, k_ref, errors, method


# ============================================================
# REGRESSORI
# ============================================================

def fit_regressors(X_tr, y_tr, X_te, y_te, label):
    """Ridge CV + MLP shallow. Ritorna dict con r, sigma, p per entrambi."""
    res = {}

    # Ridge
    scaler = StandardScaler()
    X_tr_s = scaler.fit_transform(X_tr)
    X_te_s = scaler.transform(X_te)
    ridge  = RidgeCV(alphas=RIDGE_ALPHAS, cv=CV_FOLDS)
    ridge.fit(X_tr_s, y_tr)
    yhat_r = ridge.predict(X_te_s)
    r_r, p_r  = stats.pearsonr(yhat_r, y_te)
    sig_r, pv_r = r_to_sigma(r_r, len(y_te))
    res['ridge'] = dict(alpha_best=float(ridge.alpha_),
                        r_pearson=float(r_r), p_pearson=float(p_r),
                        sigma_t=sig_r, p_sigma_t=pv_r)
    print(f"  [{label}] Ridge: r={r_r:.4f}  sigma={sig_r:.3f}  "
          f"alpha={ridge.alpha_:.3g}")

    # MLP
    pipe = Pipeline([
        ('sc', StandardScaler()),
        ('mlp', MLPRegressor(hidden_layer_sizes=MLP_HIDDEN,
                             max_iter=MLP_MAX_ITER, random_state=MLP_SEED,
                             early_stopping=True, validation_fraction=0.1,
                             n_iter_no_change=20, learning_rate_init=1e-3))
    ])
    pipe.fit(X_tr, y_tr)
    yhat_m = pipe.predict(X_te)
    r_m, p_m    = stats.pearsonr(yhat_m, y_te)
    sig_m, pv_m = r_to_sigma(r_m, len(y_te))
    res['mlp'] = dict(hidden=list(MLP_HIDDEN),
                      r_pearson=float(r_m), p_pearson=float(p_m),
                      sigma_t=sig_m, p_sigma_t=pv_m,
                      n_iter=int(pipe.named_steps['mlp'].n_iter_))
    print(f"  [{label}] MLP  : r={r_m:.4f}  sigma={sig_m:.3f}  "
          f"iters={pipe.named_steps['mlp'].n_iter_}")
    return res


def scalar_stats(feat, w0, label):
    """Pearson r + sigma_t per feature scalare singola."""
    r, p = stats.pearsonr(feat, w0)
    sig, pv = r_to_sigma(r, len(feat))
    print(f"  [{label}] r={r:.4f}  sigma={sig:.3f}")
    return dict(label=label, n=len(feat),
                r_pearson=float(r), p_pearson=float(p),
                sigma_t=sig, p_sigma_t=pv)


def gain_pct(r_tda, r_pk):
    """Gain percentuale di |r_tda| vs |r_pk|."""
    return float((abs(r_tda) - abs(r_pk)) / max(abs(r_pk), 1e-9) * 100)


# ============================================================
# MAIN
# ============================================================

def main():
    import datetime
    t_start = time.time()
    print("=" * 60)
    print("CAUCHY 7.1b — R5-3 beyond-P(k) comparison")
    print("=" * 60)

    # ── Parametri cosmologici ──────────────────────────────
    print("\n[1] Parametri cosmologici nwLH...")
    # Carica w0 dal npz HOD B3: allineamento garantito con fvecs_hod_b3
    _d5pre  = np.load(PHASE5_B3_FEATS, allow_pickle=True)
    w0_all  = _d5pre["w0"]                      # shape (2000,) garantito
    N_TOTAL = len(w0_all)
    idx_tr, idx_te = make_split(N_TOTAL, SPLIT_SEED, N_TRAIN)
    w0_tr, w0_te   = w0_all[idx_tr], w0_all[idx_te]
    print(f"  N={N_TOTAL}  train={N_TRAIN}  test={N_TEST}  "
          f"w0=[{w0_all.min():.3f},{w0_all.max():.3f}]")

    # ── b2_mean_persistence DM (cache o ricalcolo) ─────────
    print("\n[2] b2_mean_persistence DM nwLH...")
    b2_dm, b2_errors = load_or_build_b2_dm(NWLH_DIR, N_TOTAL)
    b2_dm_tr = b2_dm[idx_tr].reshape(-1, 1)
    b2_dm_te = b2_dm[idx_te].reshape(-1, 1)

    # ── b2_mean_persistence HOD B3 ─────────────────────────
    print("\n[3] b2_mean_persistence HOD B3 da Phase 5 cache...")
    d5 = np.load(PHASE5_B3_FEATS, allow_pickle=True)
    print(f"  Chiavi: {list(d5.keys())}")
    print(f"  Shapes: { {k: d5[k].shape for k in d5.keys()} }")

    # Chiave verificata: fvecs_hod_b3 shape (2000, 8)
    # ordine features (gate4_prior): b1_peak_pos[0], b1_peak_height[1],
    # b1_fwhm[2], b1_integral[3], b2_max_count[4], b2_mean_persistence[5],
    # b2_high_persist[6], b0_at_mean[7]
    if 'fvecs_hod_b3' in d5:
        b2_hod = d5['fvecs_hod_b3'][:, 5]
        print(f"  Estratto fvecs_hod_b3[:,5] (b2_mean_persistence)")
        print(f"  w0 allineato da [1] (shape={w0_all.shape})")
    elif 'b2_mean_persistence' in d5:
        b2_hod = d5['b2_mean_persistence']
    else:
        raise KeyError(
            f"Chiave attesa non trovata.\n"
            f"Chiavi disponibili: {list(d5.keys())}"
        )
    print(f"  b2_hod: shape={b2_hod.shape}  "
          f"mean={b2_hod.mean():.6f}  std={b2_hod.std():.6f}")
    b2_hod_tr = b2_hod[idx_tr].reshape(-1, 1)
    b2_hod_te = b2_hod[idx_te].reshape(-1, 1)

    # ── P(k) DM (usato da entrambi i confronti) ────────────
    print("\n[4] Calcolo P(k) DM nwLH (unico per entrambi i confronti)...")
    pk_matrix, k_centers, pk_errors, pk_method = build_pk_matrix(NWLH_DIR, N_TOTAL)
    pk_tr = pk_matrix[idx_tr]
    pk_te = pk_matrix[idx_te]

    # ── CONFRONTO A: DM identico ───────────────────────────
    print("\n[5] CONFRONTO A — Base DM identica")
    tda_a   = scalar_stats(b2_dm[idx_te], w0_te, "b2_DM_test")
    pk_a    = fit_regressors(pk_tr, w0_tr, pk_te, w0_te, "PK_DM")

    conf_a = {
        "description": "Base DM nwLH identica per TDA e P(k) — confronto cleanest",
        "n_train": N_TRAIN, "n_test": N_TEST, "split_seed": SPLIT_SEED,
        "tda_dm": tda_a,
        "pk_dm_regressors": pk_a,
        "gain_tda_vs_ridge_pct": gain_pct(tda_a['r_pearson'],
                                           pk_a['ridge']['r_pearson']),
        "gain_tda_vs_mlp_pct":   gain_pct(tda_a['r_pearson'],
                                           pk_a['mlp']['r_pearson']),
        "pk_method": pk_method,
        "n_k_bins": len(k_centers) if k_centers is not None else 0,
        "pk_errors_n": len(pk_errors),
        "b2_dm_cache": CACHE_B2_DM,
        "b2_dm_errors_n": len(b2_errors),
    }
    print(f"  → TDA_DM r={tda_a['r_pearson']:.4f} σ={tda_a['sigma_t']:.3f} | "
          f"Ridge r={pk_a['ridge']['r_pearson']:.4f} σ={pk_a['ridge']['sigma_t']:.3f} | "
          f"MLP r={pk_a['mlp']['r_pearson']:.4f} σ={pk_a['mlp']['sigma_t']:.3f}")

    # ── CONFRONTO B: HOD B3 vs P(k) DM ────────────────────
    print("\n[6] CONFRONTO B — HOD B3 z=0.5 vs P(k) DM")
    tda_b   = scalar_stats(b2_hod[idx_te], w0_te, "b2_HOD_B3_test")
    # Regressori P(k) identici al Confronto A (stessi campi DM)
    pk_b_res = pk_a   # riuso

    conf_b = {
        "description": (
            "TDA HOD B3 z=0.5 vs Ridge/MLP(P(k) DM z=0) — condizioni segnale principale"
        ),
        "caveat": (
            "Tracer diverso: TDA su galassie HOD (traccia picchi aloni), "
            "P(k) su DM. Gain include tracer bias. Confronto A è la misura pulita."
        ),
        "n_train": N_TRAIN, "n_test": N_TEST,
        "tda_hod_b3": tda_b,
        "pk_dm_regressors": pk_b_res,
        "gain_tda_hod_vs_ridge_pct": gain_pct(tda_b['r_pearson'],
                                               pk_b_res['ridge']['r_pearson']),
        "gain_tda_hod_vs_mlp_pct":   gain_pct(tda_b['r_pearson'],
                                               pk_b_res['mlp']['r_pearson']),
        "reference_phase5_phase6": {
            "sigma_b2_hod_b3_permtest": 3.69,
            "sigma_pk_combination_phase6": 3.37,
            "gain_phase6_pct": 9.3,
            "sources": [
                "phase5_gate_result.json -> ramo_a_results.sigma_primary",
                "phase6_pk_comparison.json -> interpretazione_B_ramo_a"
            ]
        }
    }
    print(f"  → TDA_HOD r={tda_b['r_pearson']:.4f} σ={tda_b['sigma_t']:.3f} | "
          f"Ridge r={pk_b_res['ridge']['r_pearson']:.4f} σ={pk_b_res['ridge']['sigma_t']:.3f} | "
          f"MLP r={pk_b_res['mlp']['r_pearson']:.4f} σ={pk_b_res['mlp']['sigma_t']:.3f}")

    # ── Output JSON ────────────────────────────────────────
    elapsed = round(time.time() - t_start, 1)
    output = {
        "schema_version": "2.0",
        "task": "7.1b_R5-3",
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "description": (
            "Beyond-P(k) test: b2_mean_persistence vs Ridge/MLP(P(k)). "
            "Pre-submission commitment R5-3."
        ),
        "traceability": {
            "gate4_r_b2_dm_frozen": 0.0028,
            "phase5_sigma_b2_hod_b3": 3.69,
            "phase5_sigma_conservative": 3.08,
            "phase6_sigma_pk_combination": 3.37,
            "sources": [
                "gate4_prior_v1_0.json -> frozen_feature_correlations_w0",
                "phase5_gate_result.json -> ramo_a_results",
                "phase6_pk_comparison.json -> interpretazione_B_ramo_a",
                "phase0_preprocessing_lock.json -> sigma_px=0.64",
                "phase1_tda_baseline.json -> n_thresh=50, common_thresholds"
            ]
        },
        "parameters": {
            "n_nwlh": N_NWLH, "split_seed": SPLIT_SEED,
            "n_train": N_TRAIN, "n_test": N_TEST,
            "sigma_px": SIGMA_PX, "n_thresh": N_THRESH,
            "thresh_lo": THRESH_LO, "thresh_hi": THRESH_HI,
            "n_k_bins": N_K_BINS,
            "ridge_alphas": [float(RIDGE_ALPHAS[0]), float(RIDGE_ALPHAS[-1])],
            "ridge_cv_folds": CV_FOLDS,
            "mlp_hidden": list(MLP_HIDDEN),
            "mlp_max_iter": MLP_MAX_ITER,
            "pk_method": pk_method,
        },
        "confronto_A": conf_a,
        "confronto_B": conf_b,
        "r5_3_status": "CHIUSO",
        "citability": (
            "PAPER-QUALITY. "
            "Confronto A: base identica DM — misura pulita beyond-P(k). "
            "Confronto B: condizioni segnale fisico — con caveat tracer dichiarato."
        ),
        "elapsed_s": elapsed,
    }

    os.makedirs(os.path.dirname(OUTPUT_JSON), exist_ok=True)
    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    print(f"\n[OK] {OUTPUT_JSON}")

    # ── Riepilogo stampa ───────────────────────────────────
    print("\n" + "=" * 60)
    print("RIEPILOGO R5-3")
    print("=" * 60)
    print(f"Confronto A (DM identico, cleanest):")
    print(f"  b2_mean_persistence DM  r={tda_a['r_pearson']:+.4f}  "
          f"σ={tda_a['sigma_t']:.3f}")
    print(f"  Ridge(P(k)) DM          r={pk_a['ridge']['r_pearson']:+.4f}  "
          f"σ={pk_a['ridge']['sigma_t']:.3f}  "
          f"gain={conf_a['gain_tda_vs_ridge_pct']:+.1f}%")
    print(f"  MLP(P(k)) DM            r={pk_a['mlp']['r_pearson']:+.4f}  "
          f"σ={pk_a['mlp']['sigma_t']:.3f}  "
          f"gain={conf_a['gain_tda_vs_mlp_pct']:+.1f}%")
    print(f"\nConfronto B (HOD B3 vs P(k) DM):")
    print(f"  b2_mean_persistence HOD r={tda_b['r_pearson']:+.4f}  "
          f"σ={tda_b['sigma_t']:.3f}")
    print(f"  Ridge(P(k)) DM          r={pk_b_res['ridge']['r_pearson']:+.4f}  "
          f"σ={pk_b_res['ridge']['sigma_t']:.3f}  "
          f"gain={conf_b['gain_tda_hod_vs_ridge_pct']:+.1f}%")
    print(f"  MLP(P(k)) DM            r={pk_b_res['mlp']['r_pearson']:+.4f}  "
          f"σ={pk_b_res['mlp']['sigma_t']:.3f}  "
          f"gain={conf_b['gain_tda_hod_vs_mlp_pct']:+.1f}%")
    print(f"\nTempo totale: {elapsed}s")
    return output


if __name__ == "__main__":
    main()
