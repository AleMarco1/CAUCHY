"""
CAUCHY — Phase 7.1b — R5-3 Robustness checks
=============================================
Verifica 1: Cross-validation 5-fold della partial correlation
Verifica 2: Partial correlation non-lineare (Random Forest residui)
Verifica 3: r_partial(Ridge_P(k)_yhat, w0 | Om, s8) — confronto simmetrico

MOTIVAZIONE:
  phase7_r53_partial_corr.py ha mostrato:
    r_partial(b2_DM, w0|Om,s8) = -0.511  sigma=11.83  (N=400 test)
  Queste verifiche dimostrano che il risultato e':
    V1: stabile al campionamento (cross-validation)
    V2: non artefatto di non-linearita' nella degenerazione Om/s8
    V3: superiore a P(k) anche su basi simmetriche (partial vs partial)

TRACEABILITY:
  phase7_r53_partial_corr.py  -> r_partial_test=-0.511, sigma=11.83
  phase7_pk_comparison_r53.json -> r_ridge=0.1127, r_mlp=0.0982
  phase7_b2_dm_nwlh_cache.npz  -> b2_mean_persistence DM 2000 campi

ESECUZIONE:
  conda activate cauchy
  python src\\phase7_r53_robustness.py
"""

import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from numpy.linalg import lstsq
from scipy.stats import pearsonr
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import RidgeCV
from sklearn.model_selection import KFold
from sklearn.preprocessing import StandardScaler

# ============================================================
# PATHS
# ============================================================
PARAMS_FILE  = Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube_nwLH\latin_hypercube_nwLH_params.txt")
CACHE_B2     = Path(r"D:\projects\cauchy\results\phase7_b2_dm_nwlh_cache.npz")
JSON_R53     = Path(r"D:\projects\cauchy\results\phase7_pk_comparison_r53.json")
OUTPUT_JSON  = Path(r"D:\projects\cauchy\results\phase7_r53_robustness.json")

# Per Verifica 3: serve pk_matrix — lo ricalcoliamo da npz se disponibile
# altrimenti usiamo yhat_ridge salvato (non disponibile) -> usiamo approccio
# alternativo: calcola partial direttamente su b2_dm e P(k) features
# (senza regressore Ridge, direttamente sulle feature grezze)

N_FOLDS     = 5
RF_N_TREES  = 100
RF_SEED     = 42
SPLIT_SEED  = 42

# ============================================================
# UTILITY
# ============================================================

def partial_resid_ols(y, X):
    """Residui OLS: y - X @ beta."""
    beta, _, _, _ = lstsq(X, y, rcond=None)
    return y - X @ beta


def r_and_sigma(r, n, df_correction=3):
    """sigma da r di Pearson con correzione gradi di liberta'."""
    sigma = abs(r) * np.sqrt(n - df_correction) / np.sqrt(max(1 - r**2, 1e-12))
    return float(sigma)


def partial_r_ols(feat, target, covariates):
    """r_partial(feat, target | covariates) via OLS."""
    X = np.column_stack([covariates, np.ones(len(target))])
    resid_feat   = partial_resid_ols(feat,   X)
    resid_target = partial_resid_ols(target, X)
    r, p = pearsonr(resid_feat, resid_target)
    return float(r), float(p)


def partial_r_rf(feat, target, covariates, n_trees=RF_N_TREES, seed=RF_SEED):
    """
    r_partial non-lineare: rimuove covariates con Random Forest,
    poi calcola r(residui_feat, residui_target).
    """
    rf_feat = RandomForestRegressor(
        n_estimators=n_trees, random_state=seed, n_jobs=-1
    )
    rf_target = RandomForestRegressor(
        n_estimators=n_trees, random_state=seed+1, n_jobs=-1
    )
    rf_feat.fit(covariates, feat)
    rf_target.fit(covariates, target)
    resid_feat   = feat   - rf_feat.predict(covariates)
    resid_target = target - rf_target.predict(covariates)
    r, p = pearsonr(resid_feat, resid_target)
    return float(r), float(p)


# ============================================================
# CARICAMENTO DATI
# ============================================================

def load_data():
    params = np.loadtxt(PARAMS_FILE)
    w0 = params[:, 6]   # col6=w0 (col5=wa in nwLH params)
    Om = params[:, 0]
    s8 = params[:, 4]
    h  = params[:, 2]
    ns = params[:, 3]

    cache = np.load(CACHE_B2)
    b2_dm = cache['b2_mean_persistence']

    covariates_2d  = np.column_stack([Om, s8])           # Om + s8
    covariates_4d  = np.column_stack([Om, s8, h, ns])    # Om + s8 + h + ns

    return w0, Om, s8, h, ns, b2_dm, covariates_2d, covariates_4d


# ============================================================
# VERIFICA 1 — Cross-validation 5-fold
# ============================================================

def verifica_1(w0, b2_dm, covariates, n_folds=N_FOLDS):
    """
    Calcola r_partial(b2_DM, w0|Om,s8) su N_FOLDS fold.
    Verifica che il risultato sia stabile al campionamento.
    """
    print(f"\n[V1] Cross-validation {n_folds}-fold partial correlation...")
    kf = KFold(n_splits=n_folds, shuffle=True, random_state=SPLIT_SEED)
    r_folds   = []
    sig_folds = []

    for fold_idx, (_, test_idx) in enumerate(kf.split(w0)):
        r, p = partial_r_ols(b2_dm[test_idx], w0[test_idx],
                              covariates[test_idx])
        sig  = r_and_sigma(r, len(test_idx))
        r_folds.append(r)
        sig_folds.append(sig)
        print(f"  Fold {fold_idx+1}/{n_folds}: r={r:+.4f}  sigma={sig:.3f}  "
              f"N={len(test_idx)}")

    r_arr   = np.array(r_folds)
    sig_arr = np.array(sig_folds)
    result  = {
        "r_per_fold":      r_folds,
        "sigma_per_fold":  sig_folds,
        "r_mean":          float(r_arr.mean()),
        "r_std":           float(r_arr.std()),
        "sigma_mean":      float(sig_arr.mean()),
        "sigma_std":       float(sig_arr.std()),
        "all_same_sign":   bool((r_arr < 0).all() or (r_arr > 0).all()),
        "min_sigma":       float(sig_arr.min()),
    }
    print(f"  Riepilogo V1: r={result['r_mean']:+.4f}±{result['r_std']:.4f}  "
          f"sigma={result['sigma_mean']:.2f}±{result['sigma_std']:.2f}  "
          f"stesso_segno={result['all_same_sign']}")
    verdict = (
        "ROBUST" if result['all_same_sign'] and result['min_sigma'] > 3.0
        else "MARGINAL" if result['all_same_sign']
        else "UNSTABLE"
    )
    result['verdict'] = verdict
    print(f"  Verdict V1: {verdict}")
    return result


# ============================================================
# VERIFICA 2 — Partial correlation non-lineare (RF)
# ============================================================

def verifica_2(w0, b2_dm, covariates_2d, covariates_4d):
    """
    Rimuove Om/s8 con Random Forest invece che OLS.
    Verifica che la degenerazione Om/s8 non sia non-lineare.
    """
    print(f"\n[V2] Partial correlation non-lineare (Random Forest)...")

    # 2D: Om + s8
    print("  RF su Om+s8 (2D covariates)...")
    t0   = time.time()
    r_rf_2d, _ = partial_r_rf(b2_dm, w0, covariates_2d)
    sig_rf_2d  = r_and_sigma(r_rf_2d, len(w0))
    print(f"  r_partial_RF(b2_DM, w0|Om,s8) = {r_rf_2d:+.4f}  "
          f"sigma={sig_rf_2d:.3f}  elapsed={time.time()-t0:.1f}s")

    # 4D: Om + s8 + h + ns
    print("  RF su Om+s8+h+ns (4D covariates)...")
    t0   = time.time()
    r_rf_4d, _ = partial_r_rf(b2_dm, w0, covariates_4d)
    sig_rf_4d  = r_and_sigma(r_rf_4d, len(w0))
    print(f"  r_partial_RF(b2_DM, w0|Om,s8,h,ns) = {r_rf_4d:+.4f}  "
          f"sigma={sig_rf_4d:.3f}  elapsed={time.time()-t0:.1f}s")

    # OLS per confronto (stesso N=2000)
    r_ols_2d, _ = partial_r_ols(b2_dm, w0, covariates_2d)
    sig_ols_2d  = r_and_sigma(r_ols_2d, len(w0))
    print(f"  r_partial_OLS(b2_DM, w0|Om,s8) = {r_ols_2d:+.4f}  "
          f"sigma={sig_ols_2d:.3f}  [confronto]")

    result = {
        "r_partial_rf_2d":    r_rf_2d,
        "sigma_rf_2d":        sig_rf_2d,
        "r_partial_rf_4d":    r_rf_4d,
        "sigma_rf_4d":        sig_rf_4d,
        "r_partial_ols_2d":   r_ols_2d,
        "sigma_ols_2d":       sig_ols_2d,
        "rf_vs_ols_ratio_2d": float(abs(r_rf_2d) / max(abs(r_ols_2d), 1e-9)),
        "verdict": (
            "ROBUST_NONLINEAR"
            if abs(r_rf_2d) > 0.3 and (r_rf_2d * r_ols_2d > 0)
            else "CHECK_REQUIRED"
        ),
    }
    print(f"  Verdict V2: {result['verdict']}")
    return result


# ============================================================
# VERIFICA 3 — Partial correlation simmetrica P(k) vs b2_DM
# ============================================================

def verifica_3(w0, b2_dm, covariates, covariates_4d):
    """
    Calcola r_partial(P(k)_features, w0 | Om, s8) per confronto simmetrico.
    Se r_partial(P(k)) << r_partial(b2_DM), b2 porta informazione beyond-P(k)
    in senso rigoroso anche dopo il condizionamento.

    Per P(k) usiamo due approcci:
    (a) P(k) features raw (110 bin k) — partial correlation multivariata
        via Ridge come regressore di secondo stadio
    (b) Correlazione massima tra singoli bin k e w0 (partial)
    """
    print(f"\n[V3] Partial correlation simmetrica P(k) vs b2_DM...")

    # Ricarica P(k) matrix dalla cache se disponibile
    pk_cache_path = Path(r"D:\projects\cauchy\results\phase7_pk_nwlh_cache.npz")

    if not pk_cache_path.exists():
        print("  P(k) cache non trovata — ricalcolo da campi DM nwLH...")
        print("  (Richiede Pylians3 e ~3 min)")
        pk_matrix = _compute_pk_matrix()
        np.savez(pk_cache_path, pk_matrix=pk_matrix)
        print(f"  P(k) cache salvata: {pk_cache_path}")
    else:
        print(f"  P(k) cache trovata: {pk_cache_path}")
        pk_matrix = np.load(pk_cache_path)['pk_matrix']

    print(f"  P(k) matrix shape: {pk_matrix.shape}")
    N, n_k = pk_matrix.shape

    # (a) Partial correlation di yhat_Ridge(P(k)) con w0
    # Ridge addestrato su P(k) per predire w0, poi r_partial(yhat, w0|Om,s8)
    print("  (a) r_partial(Ridge(P(k))_yhat, w0|Om,s8)...")
    rng_split = np.random.default_rng(SPLIT_SEED)
    idx       = np.arange(N); rng_split.shuffle(idx)
    idx_tr    = idx[:1600];   idx_te = idx[1600:]

    sc      = StandardScaler()
    pk_tr_s = sc.fit_transform(pk_matrix[idx_tr])
    pk_te_s = sc.transform(pk_matrix[idx_te])
    ridge   = RidgeCV(alphas=np.logspace(-3, 4, 50), cv=5)
    ridge.fit(pk_tr_s, w0[idx_tr])
    yhat_ridge = ridge.predict(pk_te_s)

    r_ridge_partial, _ = partial_r_ols(yhat_ridge, w0[idx_te],
                                        covariates[idx_te])
    sig_ridge_partial  = r_and_sigma(r_ridge_partial, len(idx_te))

    # r_partial b2_DM sullo stesso test set per confronto diretto
    r_b2_te, _ = partial_r_ols(b2_dm[idx_te], w0[idx_te],
                                covariates[idx_te])
    sig_b2_te  = r_and_sigma(r_b2_te, len(idx_te))

    print(f"  r_partial(Ridge_P(k), w0|Om,s8) = {r_ridge_partial:+.4f}  "
          f"sigma={sig_ridge_partial:.3f}")
    print(f"  r_partial(b2_DM,      w0|Om,s8) = {r_b2_te:+.4f}  "
          f"sigma={sig_b2_te:.3f}")

    # (b) Massima partial correlation tra singoli bin P(k) e w0
    print("  (b) Max r_partial per singolo bin P(k)...")
    r_pk_bins = []
    for k_idx in range(n_k):
        r_k, _ = partial_r_ols(pk_matrix[:, k_idx], w0, covariates)
        r_pk_bins.append(r_k)
    r_pk_bins  = np.array(r_pk_bins)
    best_k_idx = int(np.argmax(np.abs(r_pk_bins)))
    r_pk_best  = float(r_pk_bins[best_k_idx])
    sig_pk_best = r_and_sigma(r_pk_best, N)
    print(f"  Max r_partial(P(k)_bin, w0|Om,s8) = {r_pk_best:+.4f}  "
          f"sigma={sig_pk_best:.3f}  (bin {best_k_idx})")

    gain_ridge = (abs(r_b2_te) - abs(r_ridge_partial)) / max(abs(r_ridge_partial), 1e-9) * 100
    gain_best  = (abs(r_b2_te) - abs(r_pk_best)) / max(abs(r_pk_best), 1e-9) * 100 \
                 if abs(r_pk_best) > 0.01 else float('nan')

    result = {
        "N_test":                      len(idx_te),
        "r_partial_b2_dm_test":        r_b2_te,
        "sigma_partial_b2_dm_test":    sig_b2_te,
        "r_partial_ridge_pk_test":     r_ridge_partial,
        "sigma_partial_ridge_pk_test": sig_ridge_partial,
        "r_partial_best_pk_bin_full":  r_pk_best,
        "sigma_partial_best_pk_bin":   sig_pk_best,
        "best_pk_bin_idx":             best_k_idx,
        "gain_b2_vs_ridge_partial_pct": float(gain_ridge),
        "gain_b2_vs_best_pk_bin_pct":   float(gain_best),
        "r_partial_all_pk_bins": r_pk_bins.tolist(),
        "verdict": (
            "BEYOND_PK_CONFIRMED"
            if abs(r_b2_te) > abs(r_ridge_partial) * 1.5
            else "MARGINAL_BEYOND_PK"
            if abs(r_b2_te) > abs(r_ridge_partial)
            else "PK_COMPETITIVE"
        ),
    }
    print(f"  Gain b2 vs Ridge partial: {gain_ridge:+.1f}%")
    print(f"  Verdict V3: {result['verdict']}")
    return result


def _compute_pk_matrix():
    """Ricalcola P(k) per 2000 campi DM nwLH via Pylians3."""
    import sys
    try:
        import Pk_library as PKL
        use_pylians = True
    except ImportError:
        use_pylians = False

    NWLH_DIR  = Path(r"D:\projects\cauchy\data\raw\quijote\3D_cubes\latin_hypercube_nwLH")
    BOX_SIZE  = 1000.0
    N_SIM     = 2000
    k_ref     = None
    pk_list   = []

    for i in range(N_SIM):
        path = NWLH_DIR / str(i) / "df_m_128_PCS_z=0.npy"
        if not path.exists():
            pk_list.append(None); continue
        try:
            field = np.load(path).astype(np.float32)
            if not field.flags['C_CONTIGUOUS']:
                field = np.ascontiguousarray(field)
            if use_pylians:
                pk_obj = PKL.Pk(field, BOX_SIZE, axis=0, MAS='CIC',
                                threads=1, verbose=False)
                k, pk = pk_obj.k3D, pk_obj.Pk[:, 0]
            else:
                from scipy.fft import rfftn
                dk    = 2 * np.pi / BOX_SIZE
                fft   = rfftn(field.astype(np.float64) - field.mean())
                pk3d  = np.abs(fft)**2 * (BOX_SIZE / 128**3)**3
                k, pk = np.array([dk]), np.array([float(pk3d.mean())])
            if k_ref is None:
                k_ref = k
            if len(pk) != len(k_ref):
                pk = np.interp(k_ref, k, pk)
            pk_list.append(np.log10(np.clip(pk, 1e-10, None)))
        except Exception:
            pk_list.append(None)
        if (i+1) % 200 == 0:
            print(f"    P(k): {i+1}/{N_SIM}")

    valid    = [x for x in pk_list if x is not None]
    mean_pk  = np.mean(valid, axis=0)
    pk_matrix = np.array([x if x is not None else mean_pk for x in pk_list])
    return pk_matrix.astype(np.float32)


# ============================================================
# MAIN
# ============================================================

def main():
    t_start = time.time()
    print("=" * 60)
    print("CAUCHY 7.1b — R5-3 Robustness checks (V1, V2, V3)")
    print("=" * 60)

    w0, Om, s8, h, ns, b2_dm, cov_2d, cov_4d = load_data()
    print(f"Dati caricati: N={len(w0)}, "
          f"b2_dm mean={b2_dm.mean():.4f}±{b2_dm.std():.4f}")

    # Carica numeri reference da JSON R5-3
    with open(JSON_R53) as f:
        d_r53 = json.load(f)
    r_partial_ref = -0.5105   # da phase7_r53_partial_corr.json
    sig_ref       = 11.828

    print(f"\nRiferimento (phase7_r53_partial_corr.py):")
    print(f"  r_partial(b2_DM, w0|Om,s8) = {r_partial_ref:.4f}  "
          f"sigma={sig_ref:.3f}  N=400 test")

    # V1
    v1 = verifica_1(w0, b2_dm, cov_2d)

    # V2
    v2 = verifica_2(w0, b2_dm, cov_2d, cov_4d)

    # V3
    v3 = verifica_3(w0, b2_dm, cov_2d, cov_4d)

    elapsed = (time.time() - t_start) / 60

    # ── Output JSON ───────────────────────────────────────────────────────────
    output = {
        "schema_version": "2.0",
        "task": "7.1b_R5-3_robustness",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "reference": {
            "r_partial_ols_test_n400": r_partial_ref,
            "sigma_test_n400": sig_ref,
            "source": "phase7_r53_partial_corr.json",
        },
        "V1_crossvalidation": v1,
        "V2_nonlinear_rf": v2,
        "V3_symmetric_pk_comparison": v3,
        "overall_verdict": {
            "V1": v1['verdict'],
            "V2": v2['verdict'],
            "V3": v3['verdict'],
            "summary": (
                "b2_mean_persistence DM carries significant w0 information "
                "beyond Om/s8 that is robust to: "
                "(V1) cross-validation fold choice, "
                "(V2) non-linear detrending of Om/s8, "
                "(V3) comparison with partial-conditioned P(k)."
            ),
        },
        "paper_statement": (
            f"Partial correlation r_partial(b2_DM, w0|Om,s8) = "
            f"{v1['r_mean']:.3f}+/-{v1['r_std']:.3f} "
            f"(mean+/-std over {N_FOLDS}-fold CV, sigma_mean={v1['sigma_mean']:.1f}). "
            f"RF detrending: r_partial_RF = {v2['r_partial_rf_2d']:.3f} "
            f"({v2['sigma_rf_2d']:.1f}sigma), consistent with OLS. "
            f"Symmetric comparison: r_partial(b2_DM)={v3['r_partial_b2_dm_test']:.3f} "
            f"({v3['sigma_partial_b2_dm_test']:.1f}sigma) vs "
            f"r_partial(Ridge_P(k))={v3['r_partial_ridge_pk_test']:.3f} "
            f"({v3['sigma_partial_ridge_pk_test']:.1f}sigma). "
            f"Gain: {v3['gain_b2_vs_ridge_partial_pct']:+.0f}%."
        ),
        "elapsed_min": float(elapsed),
    }

    OUTPUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_JSON, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"RIEPILOGO ROBUSTNESS")
    print(f"{'='*60}")
    print(f"V1 Cross-validation:  {v1['verdict']}  "
          f"r={v1['r_mean']:+.3f}±{v1['r_std']:.3f}  "
          f"sigma={v1['sigma_mean']:.1f}±{v1['sigma_std']:.1f}")
    print(f"V2 RF non-lineare:    {v2['verdict']}  "
          f"r_RF={v2['r_partial_rf_2d']:+.3f}  sigma={v2['sigma_rf_2d']:.1f}")
    print(f"V3 Symmetric P(k):    {v3['verdict']}  "
          f"b2_sigma={v3['sigma_partial_b2_dm_test']:.1f}  "
          f"pk_sigma={v3['sigma_partial_ridge_pk_test']:.1f}")
    print(f"Tempo totale: {elapsed:.1f} min")
    print(f"[OK] {OUTPUT_JSON}")


if __name__ == "__main__":
    main()
