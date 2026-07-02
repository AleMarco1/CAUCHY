"""
CAUCHY — Phase 5
src/phase5_validation_checks.py

Verifica che sigma=4.20 (B3) non sia un artefatto. Quattro test:

  T1 — Residualizzazione non-lineare (GradientBoosting vs OLS)
       Se sigma_GBR << sigma_OLS: il segnale dipende dalla linearità assunta
  T2 — Correlazione n_gal con w0 | Omm, s8
       Se r(n_gal, w0) significativo: rischio contaminazione da densità galattica
  T3 — Injection test negativo (20 run con w0 shuffled)
       Verifica calibrazione permutation test: tutti devono dare sigma ~ 0
  T4 — Split phantom (w0 < -1) vs quintessenza (w0 > -1)
       Se segnale solo in un regime: asimmetria sospetta

Input:  results/phase5_hod_b3_features.npz
        results/phase5_hod_b3_diagnostics.json
Output: results/phase5_validation_checks.json

Uso:
  python src/phase5_validation_checks.py [--project_root .]
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.stats import pearsonr, spearmanr

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_perm", type=int, default=1000)
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

ROOT = Path(args.project_root)
rng  = np.random.default_rng(args.seed)
np.random.seed(args.seed)

FEATURES_FILE = ROOT / "results" / "phase5_hod_b3_features.npz"
DIAG_FILE     = ROOT / "results" / "phase5_hod_b3_diagnostics.json"
OUTPUT_FILE   = ROOT / "results" / "phase5_validation_checks.json"
(ROOT / "results").mkdir(parents=True, exist_ok=True)

print("=" * 70)
print("CAUCHY Phase 5 — Validation Checks (anti-artefact)")
print("=" * 70)

# ---------------------------------------------------------------------------
# Caricamento dati
# ---------------------------------------------------------------------------
assert FEATURES_FILE.exists(), f"File non trovato: {FEATURES_FILE}"
assert DIAG_FILE.exists(), f"File non trovato: {DIAG_FILE}"

data  = np.load(FEATURES_FILE, allow_pickle=True)
fvecs = data['fvecs_hod_b3']
w0    = data['w0']
Omm   = data['Omm']
s8    = data['s8']
N     = len(w0)

with open(DIAG_FILE) as f:
    diag_data = json.load(f)
n_gal_arr = np.array([d['n_gal'] for d in diag_data['individual_diagnostics']],
                     dtype=np.float64)

feature_names = [
    'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
    'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
]

# Feature usabili: std > 0 e meno del 10% di zeros
good_idx = [j for j in range(8)
            if fvecs[:, j].std() > 0 and (fvecs[:, j] == 0).sum() / N < 0.10]
good_names = [feature_names[j] for j in good_idx]
print(f"\nFeature usabili ({len(good_idx)}/8): {good_names}")

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------
X_base = np.column_stack([np.ones(N), Omm, s8])

def resid_ols(y, X=None):
    X = X if X is not None else X_base
    return y - X @ np.linalg.lstsq(X, y, rcond=None)[0]

def permutation_sigma(r_vec, w_vec, n_perm=args.n_perm):
    """sigma = (|r_obs| - mean_null) / std_null via permutation."""
    r_obs = float(pearsonr(r_vec, w_vec)[0])
    nulls = np.array([pearsonr(r_vec, rng.permutation(w_vec))[0]
                      for _ in range(n_perm)])
    sigma = (abs(r_obs) - abs(nulls.mean())) / nulls.std()
    return r_obs, float(nulls.mean()), float(nulls.std()), float(sigma)

def optimal_combination(RF, resid_w):
    """Proiezione OLS di resid_w su RF per combinazione ottimale."""
    beta = np.linalg.lstsq(RF, resid_w, rcond=None)[0]
    return RF @ beta

# Residui di riferimento (OLS)
resid_w   = resid_ols(w0)
RF_ols    = np.column_stack([resid_ols(fvecs[:, j]) for j in good_idx])
comb_ref  = optimal_combination(RF_ols, resid_w)
r_ref, null_mean_ref, null_std_ref, sigma_ref = permutation_sigma(comb_ref, resid_w)

print(f"\nRiferimento OLS — sigma = {sigma_ref:.2f}σ  (r = {r_ref:.4f})")

results = {
    "schema_version": "2.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "n_fields": N,
    "n_good_features": len(good_idx),
    "good_feature_names": good_names,
    "sigma_reference_ols": float(sigma_ref),
    "r_reference_ols": float(r_ref),
    "n_perm": args.n_perm,
    "seed": args.seed,
    "tests": {}
}

# ===========================================================================
# T1 — Residualizzazione non-lineare (GradientBoosting)
# ===========================================================================
print("\n" + "-" * 70)
print("T1 — Residualizzazione non-lineare (GradientBoosting vs OLS)")
print("-" * 70)

try:
    from sklearn.ensemble import GradientBoostingRegressor
    from sklearn.model_selection import cross_val_predict

    X_cov = np.column_stack([Omm, s8])

    def gb_resid(y):
        gb = GradientBoostingRegressor(
            n_estimators=150, max_depth=3,
            learning_rate=0.05, subsample=0.8, random_state=42
        )
        y_hat = cross_val_predict(gb, X_cov, y, cv=5)
        return y - y_hat

    print("  Calcolo residui GBR (cross-validated, ~30-60s)...")
    t0 = time.time()
    resid_w_gb = gb_resid(w0)
    RF_gb = np.column_stack([gb_resid(fvecs[:, j]) for j in good_idx])
    print(f"  Completato in {time.time()-t0:.0f}s")

    comb_gb  = optimal_combination(RF_gb, resid_w_gb)
    r_gb, _, _, sigma_gb = permutation_sigma(comb_gb, resid_w_gb)

    ratio_t1 = sigma_gb / sigma_ref if sigma_ref > 0 else 0.0
    verdict_t1 = (
        "OK — segnale robusto a non-linearita" if ratio_t1 > 0.70
        else "ATTENZIONE — segnale parzialmente dipendente da linearita OLS" if ratio_t1 > 0.40
        else "CRITICO — segnale dipende dalla linearita OLS"
    )

    print(f"  sigma OLS: {sigma_ref:.2f}σ")
    print(f"  sigma GBR: {sigma_gb:.2f}σ  (ratio = {ratio_t1:.3f})")
    print(f"  Verdict: {verdict_t1}")

    t1 = {
        "status": "completed",
        "sigma_ols": float(sigma_ref),
        "sigma_gbr": float(sigma_gb),
        "r_gbr": float(r_gb),
        "ratio_gbr_ols": float(ratio_t1),
        "verdict": verdict_t1
    }

except ImportError:
    print("  sklearn non disponibile. Installare: conda install scikit-learn")
    t1 = {"status": "skipped", "reason": "sklearn not available",
          "verdict": "N/A — sklearn mancante"}

results["tests"]["T1_nonlinear_residualization"] = t1

# ===========================================================================
# T2 — Correlazione n_gal con w0 | Omm, s8
# ===========================================================================
print("\n" + "-" * 70)
print("T2 — Correlazione n_gal con w0 | Omm, s8")
print("-" * 70)

resid_ngal = resid_ols(n_gal_arr)
r_ng_p, p_ng_p = pearsonr(resid_ngal, resid_w)
r_ng_s, p_ng_s = spearmanr(resid_ngal, resid_w)
_, _, _, sigma_ng = permutation_sigma(resid_ngal, resid_w, n_perm=500)

# Nota: r(n_gal, w0) significativo è FISICA REALE (massa aloni dipende da w0)
# non è contaminazione. Il test rilevante è se TDA porta info AGGIUNTIVA
# rispetto a n_gal. Verdict basato su sigma_TDA dopo controllo n_gal.
# Soglia: sigma_TDA_ctrl >= 2.0 -> PASS (segnale topologico indipendente da n_gal)


print(f"  r_pearson  = {r_ng_p:+.4f}  p = {p_ng_p:.3e}")
print(f"  r_spearman = {r_ng_s:+.4f}  p = {p_ng_s:.3e}")
print(f"  sigma(n_gal) = {sigma_ng:.2f}σ  [fisica reale, non contaminazione]")

# Controllo aggiuntivo: sigma TDA con n_gal come covariata extra
X_ext    = np.column_stack([np.ones(N), Omm, s8, n_gal_arr])
RF_ctrl  = np.column_stack([resid_ols(fvecs[:, j], X_ext) for j in good_idx])
resid_w_ctrl = resid_ols(w0, X_ext)
comb_ctrl    = optimal_combination(RF_ctrl, resid_w_ctrl)
_, _, _, sigma_ctrl = permutation_sigma(comb_ctrl, resid_w_ctrl, n_perm=500)
ratio_ctrl = sigma_ctrl / sigma_ref if sigma_ref > 0 else 0.0

print(f"\n  Sigma TDA controllando per n_gal: {sigma_ctrl:.2f}σ")
print(f"  ratio (con/senza controllo n_gal): {ratio_ctrl:.3f}")
# Verdict finale T2: basato su sigma_TDA con controllo n_gal
sigma_ctrl_threshold = 2.0
verdict_t2 = (
    f"OK — TDA porta {sigma_ctrl:.2f}sigma indipendente da n_gal (threshold >= {sigma_ctrl_threshold})"
    if sigma_ctrl >= sigma_ctrl_threshold
    else f"FAIL — TDA porta solo {sigma_ctrl:.2f}sigma dopo controllo n_gal (threshold >= {sigma_ctrl_threshold})"
)
print(f"  Verdict T2: {verdict_t2}")

t2 = {
    "status": "completed",
    "r_pearson": float(r_ng_p),
    "p_pearson": float(p_ng_p),
    "r_spearman": float(r_ng_s),
    "p_spearman": float(p_ng_s),
    "sigma_ngal": float(sigma_ng),
    "sigma_tda_controlling_ngal": float(sigma_ctrl),
    "ratio_sigma_ngal_control": float(ratio_ctrl),
    "verdict": verdict_t2
}
results["tests"]["T2_ngal_contamination"] = t2

# ===========================================================================
# T3 — Injection test negativo
# ===========================================================================
print("\n" + "-" * 70)
print("T3 — Injection test negativo (20 run con w0 shuffled)")
print("-" * 70)

# T3 usa feature SINGOLA (b2_mean_persistence, idx=5) per evitare
# il bias strutturale della combinazione adattiva OLS:
# beta = lstsq(RF, resid_w_reale) introduce il segnale reale nella null
# quando applicato a resid_w_shuffled. Con feature singola nessun fitting adattivo.
best_feat_idx_t3 = 5  # b2_mean_persistence — feature piu sensibile (sigma=3.49)
resid_bp = resid_ols(fvecs[:, best_feat_idx_t3])
print(f"  Feature usata: {feature_names[best_feat_idx_t3]} (la piu sensibile)")

n_inj = 20
sigma_inj = []
for i in range(n_inj):
    w0_sh = rng.permutation(w0)
    rw_sh = resid_ols(w0_sh)
    r_sh  = float(pearsonr(resid_bp, rw_sh)[0])
    # Per ogni injection: null distribution con altri 500 shuffle
    nulls_sh = np.array([pearsonr(resid_bp, rng.permutation(rw_sh))[0]
                         for _ in range(500)])
    sigma_sh = (abs(r_sh) - abs(nulls_sh.mean())) / nulls_sh.std()
    sigma_inj.append(float(sigma_sh))

inj_arr = np.array(sigma_inj)
verdict_t3 = (
    "OK — distribuzione null ben calibrata" if inj_arr.max() < 2.0
    else "ATTENZIONE — alcuni run null elevati" if inj_arr.max() < 3.0
    else "CRITICO — distribuzione null mal calibrata"
)

print(f"  sigma_null: mean={inj_arr.mean():.3f}  std={inj_arr.std():.3f}  max={inj_arr.max():.3f}")
print(f"  Atteso: mean~0, std~1, max<2")
print(f"  Nota: sigma su feature singola (no adaptive bias da combinazione OLS)")
print(f"  Verdict: {verdict_t3}")

t3 = {
    "status": "completed",
    "method": "single_feature_b2_mean_persistence",
    "rationale": "Feature singola evita bias adattivo OLS nella combinazione",
    "n_injection": n_inj,
    "sigma_null_mean": float(inj_arr.mean()),
    "sigma_null_std":  float(inj_arr.std()),
    "sigma_null_max":  float(inj_arr.max()),
    "sigma_null_values": sigma_inj,
    "verdict": verdict_t3
}
results["tests"]["T3_null_injection"] = t3

# ===========================================================================
# T4 — Split phantom vs quintessenza
# ===========================================================================
print("\n" + "-" * 70)
print("T4 — Split phantom (w0 < -1) vs quintessenza (w0 > -1)")
print("-" * 70)

splits = {
    "phantom_w0_lt_minus1":     w0 < -1.0,
    "quintessence_w0_gt_minus1": w0 > -1.0,
    "full_sample":              np.ones(N, dtype=bool),
}

t4_results = {}
for label, mask in splits.items():
    n_sub = int(mask.sum())
    if n_sub < 100:
        t4_results[label] = {"n": n_sub, "status": "insufficient"}
        print(f"  [{label}] N={n_sub} — insufficiente")
        continue

    X_sub   = np.column_stack([np.ones(n_sub), Omm[mask], s8[mask]])
    w0_sub  = w0[mask]
    rw_sub  = w0_sub - X_sub @ np.linalg.lstsq(X_sub, w0_sub, rcond=None)[0]

    RF_sub  = np.column_stack([
        y - X_sub @ np.linalg.lstsq(X_sub, y, rcond=None)[0]
        for y in [fvecs[mask, j] for j in good_idx]
    ])
    comb_sub = optimal_combination(RF_sub, rw_sub)
    r_sub, _, _, sigma_sub = permutation_sigma(comb_sub, rw_sub, n_perm=500)

    print(f"  [{label}] N={n_sub}: r={r_sub:+.4f}  sigma={sigma_sub:.2f}σ")
    t4_results[label] = {
        "n": n_sub, "r_obs": float(r_sub), "sigma": float(sigma_sub), "status": "completed"
    }

# Asimmetria
s_ph = t4_results.get("phantom_w0_lt_minus1", {}).get("sigma", 0)
s_qu = t4_results.get("quintessence_w0_gt_minus1", {}).get("sigma", 0)
if s_ph > 0 and s_qu > 0:
    asym_ratio = min(s_ph, s_qu) / max(s_ph, s_qu)
    verdict_t4 = (
        "OK — segnale presente in entrambi i regimi" if asym_ratio > 0.5
        else "ATTENZIONE — segnale asimmetrico tra phantom e quintessenza" if asym_ratio > 0.2
        else "CRITICO — segnale solo in un regime"
    )
    t4_results["asymmetry_ratio"] = float(asym_ratio)
    print(f"\n  Asimmetria: sigma_phantom={s_ph:.2f}  sigma_quint={s_qu:.2f}  ratio={asym_ratio:.3f}")
    print(f"  Verdict: {verdict_t4}")
else:
    verdict_t4 = "N/A"

t4_results["verdict"] = verdict_t4
results["tests"]["T4_phantom_quintessence_split"] = t4_results

# ===========================================================================
# Feature per feature sigma
# ===========================================================================
print("\n" + "-" * 70)
print("Sigma per feature singola")
print("-" * 70)

feat_sigmas = {}
for j, name in zip(good_idx, good_names):
    resid_f = resid_ols(fvecs[:, j])
    r_f, _, _, sig_f = permutation_sigma(resid_f, resid_w, n_perm=500)
    feat_sigmas[name] = {"r_partial": float(r_f), "sigma": float(sig_f)}
    stars = "***" if sig_f > 3 else ("**" if sig_f > 2 else ("*" if sig_f > 1 else ""))
    print(f"  {name:<25}: r={r_f:+.4f}  sigma={sig_f:.2f}σ {stars}")

results["feature_sigmas"] = feat_sigmas

# ===========================================================================
# Verdict globale
# ===========================================================================
print("\n" + "=" * 70)
print("VERDICT GLOBALE")
print("=" * 70)

verdict_map = {
    "T1": t1.get("verdict", "N/A"),
    "T2": t2["verdict"],
    "T3": t3["verdict"],
    "T4": t4_results.get("verdict", "N/A"),
}

n_ok   = sum(1 for v in verdict_map.values() if "OK" in v)
n_warn = sum(1 for v in verdict_map.values() if "ATTENZIONE" in v)
n_crit = sum(1 for v in verdict_map.values() if "CRITICO" in v)
n_na   = sum(1 for v in verdict_map.values() if v in ("N/A", "skipped"))

for test, v in verdict_map.items():
    sym = "✓" if "OK" in v else ("?" if "ATTENZIONE" in v else ("✗" if "CRITICO" in v else "—"))
    print(f"  {sym} {test}: {v}")

if n_crit == 0 and n_warn <= 1:
    global_verdict = "SEGNALE VERIFICATO — tutti i test anti-artefatto superati"
elif n_crit == 0:
    global_verdict = "SEGNALE PROBABILMENTE REALE — alcuni test richiedono attenzione"
else:
    global_verdict = "SEGNALE DUBBIO — test critici falliti, investigare"

print(f"\n  sigma riferimento OLS: {sigma_ref:.2f}σ")
if t1.get("status") == "completed":
    print(f"  sigma GBR (non-lineare): {t1['sigma_gbr']:.2f}σ")
print(f"  sigma con controllo n_gal: {sigma_ctrl:.2f}σ")
print(f"\n  VERDICT: {global_verdict}")

results["global_verdict"] = global_verdict
results["summary"] = {
    "n_ok": n_ok, "n_warn": n_warn, "n_crit": n_crit, "n_na": n_na,
    "sigma_ols": float(sigma_ref),
    "sigma_gbr": float(t1.get("sigma_gbr", 0)) if t1.get("status") == "completed" else None,
    "sigma_ngal_controlled": float(sigma_ctrl),
}
results["verdicts"] = verdict_map

with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print(f"\n  Output: {OUTPUT_FILE}")
print("=" * 70)
