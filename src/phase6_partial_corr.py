"""
CAUCHY — Phase 6 Script 4
src/phase6_partial_corr.py

Obiettivo: confronto DESI BGS vs distribuzione mock (z=0 e z=0.5) tramite
correlazione parziale. Quantifica la discrepanza residua dopo controllo per
densità galattica n_gal — discrimina segnale fisico (w0 != -1) da artefatto HOD.

Input:
  results/phase5_hod_b3_features.npz      — feature TDA mock z=0 (2000 campi nwLH, HOD B3)
  results/phase6_mock_features_z05.npz    — feature TDA mock z=0.5 (2000 campi nwLH)
  results/phase6_bgs_tda_features.json    — feature TDA DESI BGS (NGC + SGC)
  results/phase5_ramo_b_results.json      — risultati Ramo B j* (per completezza record)

Output:
  results/phase6_partial_corr.json        — risultati numerici completi

Metrica principale: per ogni feature TDA,
  - percentile DESI nella distribuzione mock (z=0 e z=0.5)
  - discrepanza normalizzata: (DESI - mock_median) / mock_std
  - partial correlation b2_mean_persistence ~ n_gal su mock: stima quanto
    della variazione mock è spiegata da n_gal vs cosmologia
  - discrepanza residua DESI dopo sottrazione del trend n_gal

Uso:
  python src/phase6_partial_corr.py [--project_root .] [--seed 42]
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats
from numpy.linalg import lstsq

parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--seed", type=int, default=42)
args = parser.parse_args()

ROOT = Path(args.project_root)
rng  = np.random.default_rng(args.seed)

FEATURE_NAMES = [
    "b1_peak_pos", "b1_peak_height", "b1_fwhm", "b1_integral",
    "b2_max_count", "b2_mean_persistence", "b2_high_persist", "b0_at_mean"
]
B2_IDX = 5  # b2_mean_persistence — feature primaria

print("=" * 70)
print("CAUCHY Phase 6 — Script 4: Partial Correlation DESI vs Mock")
print("=" * 70)

# ---------------------------------------------------------------------------
# 1. Carica mock z=0 (Phase 5 B3)
# ---------------------------------------------------------------------------
b3_file = ROOT / "results" / "phase5_hod_b3_features.npz"
b3_data = np.load(b3_file)

# Auto-detect chiave feature
feat_key_z0 = None
for k in ["fvecs_hod_b3", "fvecs_hod_marginalized", "fvecs", "features"]:
    if k in b3_data:
        feat_key_z0 = k
        break
if feat_key_z0 is None:
    for k in b3_data.keys():
        v = b3_data[k]
        if hasattr(v, "shape") and len(v.shape) == 2 and v.shape[1] == 8:
            feat_key_z0 = k
            break

fvecs_z0   = b3_data[feat_key_z0].astype(float)   # (2000, 8)
w0_z0      = b3_data["w0"].astype(float)
Omm_z0     = b3_data["Omm"].astype(float)
s8_z0      = b3_data["s8"].astype(float)

# n_gal mock z=0 — cerca nel diagnostics se non nel npz
n_gal_z0 = None
if "n_gal" in b3_data:
    n_gal_z0 = b3_data["n_gal"].astype(float)
else:
    diag_file = ROOT / "results" / "phase5_hod_b3_diagnostics.json"
    if diag_file.exists():
        with open(diag_file) as f:
            diag = json.load(f)
        if "individual_diagnostics" in diag:
            n_gal_z0 = np.array([d["n_gal"] for d in diag["individual_diagnostics"]],
                                 dtype=float)

print(f"Mock z=0: {fvecs_z0.shape[0]} campi, chiave='{feat_key_z0}'")
if n_gal_z0 is not None:
    print(f"  n_gal: mean={n_gal_z0.mean():.0f}  std={n_gal_z0.std():.0f}")

# ---------------------------------------------------------------------------
# 2. Carica mock z=0.5
# ---------------------------------------------------------------------------
z05_file = ROOT / "results" / "phase6_mock_features_z05.npz"
z05_data = np.load(z05_file)

feat_key_z05 = None
for k in ["fvecs_z05", "fvecs_hod_b3", "fvecs", "features"]:
    if k in z05_data:
        feat_key_z05 = k
        break
if feat_key_z05 is None:
    for k in z05_data.keys():
        v = z05_data[k]
        if hasattr(v, "shape") and len(v.shape) == 2 and v.shape[1] == 8:
            feat_key_z05 = k
            break

fvecs_z05  = z05_data[feat_key_z05].astype(float)  # (2000, 8)
w0_z05     = z05_data["w0"].astype(float) if "w0" in z05_data else w0_z0
Omm_z05    = z05_data["Omm"].astype(float) if "Omm" in z05_data else Omm_z0

n_gal_z05 = None
if "n_gal" in z05_data:
    n_gal_z05 = z05_data["n_gal"].astype(float)

print(f"Mock z=0.5: {fvecs_z05.shape[0]} campi, chiave='{feat_key_z05}'")
if n_gal_z05 is not None:
    print(f"  n_gal: mean={n_gal_z05.mean():.0f}  std={n_gal_z05.std():.0f}")

# ---------------------------------------------------------------------------
# 3. Carica DESI BGS
# ---------------------------------------------------------------------------
bgs_file = ROOT / "results" / "phase6_bgs_tda_features.json"
with open(bgs_file) as f:
    bgs_raw = json.load(f)

# Auto-detect struttura: può essere {NGC: {feat: val}, SGC: ...} o {feat: val}
def extract_region(data, region):
    """Estrae feature scalari per una regione (NGC/SGC) o dal top-level.
    Supporta sia formato dict {feat_name: val} che lista con feature_names separato.
    """
    # Naviga in data["regions"][region] oppure data[region]
    src = None
    if "regions" in data and region in data["regions"]:
        src = data["regions"][region]
    elif region in data:
        src = data[region]
    else:
        src = data

    if src is None:
        return None

    # Formato lista: src["features"] = [val0, val1, ...], src["feature_names"] = [name0, ...]
    if "features" in src and isinstance(src["features"], list):
        names = src.get("feature_names", FEATURE_NAMES)
        feats = {names[i]: float(src["features"][i]) for i in range(min(len(names), len(src["features"])))}
        # n_gal dal campo diagnostics o n_valid_voxels come proxy
        diag = src.get("tda_diagnostics", {})
        n_gal = src.get("n_gal", diag.get("n_gal", src.get("n_valid_voxels", 0)))
        feats["_n_gal"] = float(n_gal)
        feats["_persistence_mean"] = float(diag.get("persistence_mean", 0))
        return feats

    # Formato dict diretto: {feat_name: val}
    feats = {}
    for fn in FEATURE_NAMES:
        if fn in src:
            feats[fn] = float(src[fn])
    return feats if feats else None

bgs_ngc = extract_region(bgs_raw, "NGC")
bgs_sgc = extract_region(bgs_raw, "SGC")
bgs_all = extract_region(bgs_raw, "ALL") or extract_region(bgs_raw, "combined")

# Se non c'è un combined, calcola la media NGC+SGC pesata per n_gal
if bgs_all is None and bgs_ngc is not None and bgs_sgc is not None:
    n_ngc = bgs_raw.get("NGC", {}).get("n_gal", 1)
    n_sgc = bgs_raw.get("SGC", {}).get("n_gal", 1)
    if isinstance(n_ngc, (int, float)) and isinstance(n_sgc, (int, float)) and (n_ngc + n_sgc) > 0:
        w_n = n_ngc / (n_ngc + n_sgc)
        w_s = n_sgc / (n_ngc + n_sgc)
        bgs_all = {fn: w_n * bgs_ngc[fn] + w_s * bgs_sgc[fn]
               for fn in bgs_ngc if not fn.startswith("_")}
    else:
        bgs_all = {fn: (bgs_ngc[fn] + bgs_sgc[fn]) / 2
                   for fn in bgs_ngc if not fn.startswith("_")}

# n_gal DESI — estratto da _n_gal (iniettato da extract_region) o da n_valid_voxels
n_gal_desi_ngc = float(bgs_ngc.get("_n_gal", 0)) if bgs_ngc else 0.0
n_gal_desi_sgc = float(bgs_sgc.get("_n_gal", 0)) if bgs_sgc else 0.0
# n_valid_voxels non è n_gal — serve il vero conteggio galassie dal tda_diagnostics
# Se non disponibile, usa 0 (skip partial corr n_gal)

print(f"DESI BGS:")
def safe_print_feat(d, label):
    if d is None: return
    val = d.get("b2_mean_persistence")
    ngal = d.get("_n_gal", 0)
    if val is not None:
        print(f"  {label} b2_mean_persistence = {val:.4f}  (n_valid_voxels={ngal:.0f})")
    else:
        print(f"  {label}: feature non trovata. Chiavi: {[k for k in d if not k.startswith('_')][:6]}")
safe_print_feat(bgs_ngc, "NGC")
safe_print_feat(bgs_sgc, "SGC")
safe_print_feat(bgs_all, "ALL")

# ---------------------------------------------------------------------------
# 4. Analisi per feature: bracket mock, percentile DESI, discrepanza
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("CONFRONTO DESI vs MOCK")
print(f"{'='*70}")

def bracket_analysis(feat_name, fi, fvecs, desi_val, label):
    """Calcola bracket [p5,p95], percentile DESI, z-score."""
    col = fvecs[:, fi]
    p5, p50, p95 = np.percentile(col, [5, 50, 95])
    mock_std  = col.std()
    mock_mean = col.mean()
    z_score   = (desi_val - mock_mean) / (mock_std + 1e-30)
    pctile    = float(stats.percentileofscore(col, desi_val))
    return {
        "label": label,
        "mock_mean": float(mock_mean),
        "mock_std":  float(mock_std),
        "mock_p5":   float(p5),
        "mock_p50":  float(p50),
        "mock_p95":  float(p95),
        "desi_value": float(desi_val),
        "z_score":   float(z_score),
        "percentile_in_mock": pctile,
        "outside_bracket_p5_p95": bool(desi_val < p5 or desi_val > p95)
    }

results_by_feature = {}
for fi, fn in enumerate(FEATURE_NAMES):
    if fn.startswith("_"):
        continue
    desi_val_ngc = bgs_ngc.get(fn) if bgs_ngc else None
    desi_val_all = bgs_all.get(fn) if bgs_all else None
    desi_val     = desi_val_ngc if desi_val_ngc is not None else desi_val_all

    if desi_val is None:
        continue

    r_z0  = bracket_analysis(fn, fi, fvecs_z0,  desi_val, "z=0")
    r_z05 = bracket_analysis(fn, fi, fvecs_z05, desi_val, "z=0.5")

    marker = " *** PRIMARIA" if fi == B2_IDX else ""
    print(f"\n  {fn}{marker}")
    print(f"    DESI NGC = {desi_val:.4f}")
    print(f"    Mock z=0:   [{r_z0['mock_p5']:.3f}, {r_z0['mock_p95']:.3f}]  "
          f"z={r_z0['z_score']:+.2f}  pctile={r_z0['percentile_in_mock']:.1f}%")
    print(f"    Mock z=0.5: [{r_z05['mock_p5']:.3f}, {r_z05['mock_p95']:.3f}]  "
          f"z={r_z05['z_score']:+.2f}  pctile={r_z05['percentile_in_mock']:.1f}%")

    results_by_feature[fn] = {"z0": r_z0, "z05": r_z05, "desi_ngc": desi_val}

# ---------------------------------------------------------------------------
# 5. Partial correlation: b2_mean_persistence ~ n_gal su mock
#    Stima quanta della variazione inter-mock è spiegata da n_gal
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("PARTIAL CORRELATION b2_mean_persistence | n_gal (mock z=0)")
print(f"{'='*70}")

partial_results = {}

def partial_resid(x, controls):
    C  = np.column_stack([controls, np.ones(len(x))])
    return x - C @ lstsq(C, x, rcond=None)[0]

if n_gal_z0 is not None:
    b2_z0     = fvecs_z0[:, B2_IDX]
    rho_raw,_ = stats.spearmanr(b2_z0, w0_z0)

    # Partial b2 vs w0 | n_gal
    b2_res  = partial_resid(b2_z0,   n_gal_z0.reshape(-1,1))
    w0_res  = partial_resid(w0_z0,   n_gal_z0.reshape(-1,1))
    rho_partial_ngal, _ = stats.spearmanr(b2_res, w0_res)

    # Partial b2 vs w0 | Omm, s8
    b2_res2 = partial_resid(b2_z0,   np.column_stack([Omm_z0, s8_z0]))
    w0_res2 = partial_resid(w0_z0,   np.column_stack([Omm_z0, s8_z0]))
    rho_partial_cosmo, _ = stats.spearmanr(b2_res2, w0_res2)

    # Predizione b2 DESI dopo rimozione trend n_gal
    if n_gal_desi_ngc > 0:
        # Fit lineare b2 ~ n_gal su mock z=0
        slope, intercept, r_lin, _, _ = stats.linregress(n_gal_z0, b2_z0)
        b2_desi_predicted_by_ngal = slope * n_gal_desi_ngc + intercept
        desi_b2_ngc = bgs_ngc.get("b2_mean_persistence", 0) if bgs_ngc else 0
        b2_desi_residual = desi_b2_ngc - b2_desi_predicted_by_ngal
        mock_residuals   = b2_z0 - (slope * n_gal_z0 + intercept)
        residual_std     = mock_residuals.std()
        z_residual       = b2_desi_residual / (residual_std + 1e-30)
        pctile_residual  = float(stats.percentileofscore(mock_residuals, b2_desi_residual))

        print(f"  ρ(b2, w0) raw           = {rho_raw:+.4f}")
        print(f"  ρ(b2, w0 | n_gal)       = {rho_partial_ngal:+.4f}")
        print(f"  ρ(b2, w0 | Omm, s8)     = {rho_partial_cosmo:+.4f}")
        print(f"\n  Trend n_gal → b2 (lineare): slope={slope:.2e}  R={r_lin:.3f}")
        print(f"  b2_DESI_NGC osservato   = {desi_b2_ngc:.4f}")
        print(f"  b2_DESI predetto da n_gal = {b2_desi_predicted_by_ngal:.4f}")
        print(f"  Residuo DESI dopo n_gal = {b2_desi_residual:+.4f}")
        print(f"  z_residuo               = {z_residual:+.2f}σ")
        print(f"  Percentile residuo      = {pctile_residual:.1f}% (nella distribuzione residui mock)")

        partial_results = {
            "rho_b2_w0_raw":         float(rho_raw),
            "rho_b2_w0_partial_ngal":  float(rho_partial_ngal),
            "rho_b2_w0_partial_cosmo": float(rho_partial_cosmo),
            "ngal_trend_slope":      float(slope),
            "ngal_trend_intercept":  float(intercept),
            "ngal_trend_r":          float(r_lin),
            "desi_ngc_n_gal":        float(n_gal_desi_ngc),
            "desi_b2_observed":      float(desi_b2_ngc),
            "desi_b2_predicted_ngal": float(b2_desi_predicted_by_ngal),
            "desi_b2_residual":      float(b2_desi_residual),
            "mock_residual_std":     float(residual_std),
            "z_score_residual":      float(z_residual),
            "percentile_residual":   pctile_residual,
            "interpretation": (
                "z_score_residual > 2: discrepanza DESI non spiegabile da n_gal → segnale fisico"
                if abs(z_residual) > 2 else
                "z_score_residual < 2: discrepanza DESI parzialmente spiegabile da n_gal"
            )
        }
    else:
        print("  [WARN] n_gal DESI non disponibile — skip regressione n_gal")
else:
    print("  [WARN] n_gal mock z=0 non disponibile — skip partial correlation")

# ---------------------------------------------------------------------------
# 6. Bracket combinato z=0 + z=0.5
# ---------------------------------------------------------------------------
print(f"\n{'='*70}")
print("BRACKET COMBINATO z=0 + z=0.5 per b2_mean_persistence")
print(f"{'='*70}")

b2_z0_arr  = fvecs_z0[:, B2_IDX]
b2_z05_arr = fvecs_z05[:, B2_IDX]
b2_combined = np.concatenate([b2_z0_arr, b2_z05_arr])

desi_b2_ngc = bgs_ngc.get("b2_mean_persistence", 0) if bgs_ngc else 0
pctile_combined = float(stats.percentileofscore(b2_combined, desi_b2_ngc))
z_combined = (desi_b2_ngc - b2_combined.mean()) / (b2_combined.std() + 1e-30)

print(f"  Mock z=0:   range [{b2_z0_arr.min():.3f}, {b2_z0_arr.max():.3f}]  "
      f"mean={b2_z0_arr.mean():.3f}  std={b2_z0_arr.std():.4f}")
print(f"  Mock z=0.5: range [{b2_z05_arr.min():.3f}, {b2_z05_arr.max():.3f}]  "
      f"mean={b2_z05_arr.mean():.3f}  std={b2_z05_arr.std():.4f}")
print(f"  Mock combined: mean={b2_combined.mean():.3f}  std={b2_combined.std():.4f}")
print(f"  DESI NGC = {desi_b2_ngc:.4f}")
print(f"  Percentile DESI in combined mock: {pctile_combined:.1f}%")
print(f"  z-score DESI vs combined:         {z_combined:+.2f}σ")

discrepancy_pct_z0  = 100 * (desi_b2_ngc - b2_z0_arr.mean()) / b2_z0_arr.mean()
discrepancy_pct_z05 = 100 * (desi_b2_ngc - b2_z05_arr.mean()) / b2_z05_arr.mean()
print(f"  Discrepanza DESI vs mock_mean z=0:   {discrepancy_pct_z0:+.1f}%")
print(f"  Discrepanza DESI vs mock_mean z=0.5: {discrepancy_pct_z05:+.1f}%")

# ---------------------------------------------------------------------------
# 7. Output JSON
# ---------------------------------------------------------------------------
output = {
    "schema_version": "2.0",
    "generated_at": datetime.now(timezone.utc).isoformat(),
    "script": "phase6_partial_corr.py",
    "gate": "GATE_6_preparazione",
    "seed": args.seed,

    "inputs": {
        "mock_z0_file":   str(b3_file),
        "mock_z0_n_sims": int(fvecs_z0.shape[0]),
        "mock_z05_file":  str(z05_file),
        "mock_z05_n_sims": int(fvecs_z05.shape[0]),
        "desi_file":      str(bgs_file),
        "desi_regions_available": [r for r, v in
            [("NGC", bgs_ngc), ("SGC", bgs_sgc), ("ALL", bgs_all)] if v]
    },

    "feature_analysis": results_by_feature,

    "b2_mean_persistence_summary": {
        "desi_ngc_value": float(desi_b2_ngc),
        "mock_z0_mean":   float(b2_z0_arr.mean()),
        "mock_z0_std":    float(b2_z0_arr.std()),
        "mock_z0_bracket_p5_p95": [float(np.percentile(b2_z0_arr, 5)),
                                    float(np.percentile(b2_z0_arr, 95))],
        "mock_z05_mean":  float(b2_z05_arr.mean()),
        "mock_z05_std":   float(b2_z05_arr.std()),
        "mock_z05_bracket_p5_p95": [float(np.percentile(b2_z05_arr, 5)),
                                     float(np.percentile(b2_z05_arr, 95))],
        "discrepancy_pct_vs_z0":   float(discrepancy_pct_z0),
        "discrepancy_pct_vs_z05":  float(discrepancy_pct_z05),
        "percentile_in_combined_mock": pctile_combined,
        "z_score_vs_combined": float(z_combined),
    },

    "partial_correlation_ngal": partial_results,

    "phase5bis_input": {
        "note": "Questi valori sono input per O5b-4 (Delta_D/D) di Phase 5bis",
        "b2_desi_ngc": float(desi_b2_ngc),
        "b2_mock_z0_mean": float(b2_z0_arr.mean()),
        "b2_mock_z05_mean": float(b2_z05_arr.mean()),
        "discrepancy_vs_z0_pct": float(discrepancy_pct_z0),
        "residual_after_ngal_control_zscore": float(
            partial_results.get("z_score_residual", float("nan"))
        )
    }
}

out_path = ROOT / "results" / "phase6_partial_corr.json"
with open(out_path, "w") as f:
    json.dump(output, f, indent=2)

print(f"\n{'='*70}")
print(f"Output: {out_path}")
print(f"{'='*70}")
print(f"  b2_DESI_NGC = {desi_b2_ngc:.4f}")
print(f"  Discrepanza vs mock z=0:   {discrepancy_pct_z0:+.1f}%")
print(f"  Discrepanza vs mock z=0.5: {discrepancy_pct_z05:+.1f}%")
print(f"  Percentile DESI in combined mock: {pctile_combined:.1f}%")
if partial_results:
    print(f"  Residuo dopo controllo n_gal: {partial_results.get('z_score_residual',0):+.2f}σ")
print()
print("Prossimo: Phase 5bis Sessione 1")
