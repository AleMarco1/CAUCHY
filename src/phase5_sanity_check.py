"""
CAUCHY — Phase 5, Sessione 1
src/phase5_sanity_check.py

Obiettivo:
  1. Assert prior Gate 3 e Gate 4 (obbligatori pre-codice)
  2. HOD fixed check — verifica che nessun HOD fisso sia stato applicato
  3. Correlazione parziale preliminare r(feature_TDA, w0 | Omm, s8) su 100
     campi nwLH dark-matter-only — lower bound del segnale atteso
  4. Permutation test leggero (N=50) per stima della distribuzione null
  5. Verifica toolchain emcee
  6. Output: results/phase5_opening_stats.json

Autorità:
  - CAUCHY_Systematic_Methodology_v2.md §5.1
  - CAUCHY_Execution_Parameters.md §7
  - prior/gate4_prior_v1_0.json
  - prior/gate3_prior_v1_0.json

VINCOLO HARD (Methodology §5.2):
  HOD fisso = errore bloccante. Questo script non applica alcun HOD.
  La marginalizzazione HOD completa è in phase5_hod_mcmc.py (Sessione 2).

Uso:
  python src/phase5_sanity_check.py [--n_fields 100] [--n_perm 50] [--seed 42]

Output:
  results/phase5_opening_stats.json
"""

import argparse
import json
import os
import sys
import hashlib
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy import stats
from scipy.stats import pearsonr

# ---------------------------------------------------------------------------
# Argparse
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser(description="CAUCHY Phase 5 — Sanity Check")
parser.add_argument("--n_fields", type=int, default=100,
                    help="Numero campi nwLH per correlazione parziale preliminare (default: 100)")
parser.add_argument("--n_perm", type=int, default=50,
                    help="Numero permutazioni per null distribution preliminare (default: 50)")
parser.add_argument("--seed", type=int, default=42,
                    help="Seed globale (default: 42)")
parser.add_argument("--project_root", type=str, default=".",
                    help="Root del progetto (default: .)")
args = parser.parse_args()

np.random.seed(args.seed)
ROOT = Path(args.project_root)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PRIOR_GATE3 = ROOT / "prior" / "gate3_prior_v1_0.json"
PRIOR_GATE4 = ROOT / "prior" / "gate4_prior_v1_0.json"
NWLH_FIELDS_DIR = ROOT / "data" / "processed" / "phase0_fields" / "nwlh"
NWLH_PARAMS_FILE = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt"
TDA_CACHE = ROOT / "results" / "phase1_fiducial_cache.npz"
RESULTS_DIR = ROOT / "results"
OUTPUT_FILE = RESULTS_DIR / "phase5_opening_stats.json"

RESULTS_DIR.mkdir(parents=True, exist_ok=True)

results = {
    "schema_version": "2.0",
    "metadata": {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "phase": 5,
        "script": "src/phase5_sanity_check.py",
        "seed": args.seed,
        "n_fields_used": args.n_fields,
        "n_perm": args.n_perm,
        "python_version": sys.version,
        "deviations_from_protocol": "none"
    },
    "prior_asserts": {},
    "hod_fixed_check": {},
    "emcee_check": {},
    "partial_correlation_dm_only": {},
    "permutation_test_preliminary": {},
    "verdict": {}
}

print("=" * 70)
print("CAUCHY Phase 5 — Sanity Check")
print("=" * 70)

# ===========================================================================
# FASE 1 — ASSERT PRIOR GATE 3 e GATE 4 (obbligatori)
# ===========================================================================
print("\n[1/5] Assert prior Gate 3 e Gate 4...")

def load_prior(path, gate_id):
    assert path.exists(), f"FAIL: prior non trovato: {path}"
    with open(path) as f:
        p = json.load(f)
    assert p.get("gate_id") == gate_id, \
        f"FAIL: gate_id errato in {path}: atteso {gate_id}, trovato {p.get('gate_id')}"
    assert p.get("schema_version") == "2.0", \
        f"FAIL: schema_version errato in {path}"
    return p

# Gate 3 assert
p3 = load_prior(PRIOR_GATE3, "GATE_3")

assert p3["gate_criteria"]["corr_GNN_Omm_threshold"]["observed"] >= 0.20, \
    "FAIL GATE3: r_GNN_Omm < 0.20"
assert p3["gate_criteria"]["corr_GNN_s8_threshold"]["observed"] >= 0.20, \
    "FAIL GATE3: r_GNN_s8 < 0.20"

g3_best_epoch = p3["frozen_gnn_training"]["best_epoch"]
g3_checkpoint = p3["frozen_gnn_training"]["checkpoint_path"]
g3_p90 = p3["frozen_graph_construction"]["persistence_threshold_p90"]
g3_r_Omm = p3["gate_criteria"]["corr_GNN_Omm_threshold"]["observed"]
g3_r_s8  = p3["gate_criteria"]["corr_GNN_s8_threshold"]["observed"]

print(f"  Gate 3: best_epoch={g3_best_epoch}, checkpoint={g3_checkpoint}")
print(f"  Gate 3: r_Omm={g3_r_Omm:.4f}, r_s8={g3_r_s8:.4f}, p90={g3_p90:.6f}")
print(f"  Gate 3: ASSERT PASS")

# Gate 4 assert
p4 = load_prior(PRIOR_GATE4, "GATE_4")

assert p4["gate4_outcome"]["gate_passed"] == True, \
    "FAIL GATE4: gate_passed != True"
assert p4["gate4_outcome"]["reviewer_verdict"] == "NON-BLOCKING", \
    "FAIL GATE4: reviewer_verdict non è NON-BLOCKING"
assert p4["phase5_authorization"]["authorized"] == True, \
    "FAIL GATE4: Phase 5 non autorizzata nel prior Gate 4"

g4_r_Omm = p4["frozen_prerequisites_r3"]["R3_1"]["r_yhat_Omm"]
g4_r_s8  = p4["frozen_prerequisites_r3"]["R3_1"]["r_yhat_s8"]
g4_mmd_p = p4["frozen_prerequisites_r3"]["R3_3"]["mmd_pvalue"]
g4_r2_max_sr = p4["frozen_sr_results"]["r2_max"]

assert g4_r_Omm >= 0.20, f"FAIL GATE4: R3-1 r_Omm={g4_r_Omm} < 0.20"
assert g4_r_s8  >= 0.20, f"FAIL GATE4: R3-1 r_s8={g4_r_s8} < 0.20"

print(f"  Gate 4: outcome={p4['gate4_outcome']['status']}, "
      f"reviewer={p4['gate4_outcome']['reviewer_verdict']}")
print(f"  Gate 4: R3-1 r_Omm={g4_r_Omm:.4f}, r_s8={g4_r_s8:.4f}")
print(f"  Gate 4: R3-3 MMD p={g4_mmd_p:.4f} (non significativo, atteso)")
print(f"  Gate 4: SR R2_max={g4_r2_max_sr:.6f} (FAIL_NEGATIVE, atteso)")
print(f"  Gate 4: Phase 5 authorized={p4['phase5_authorization']['authorized']}")
print(f"  Gate 4: ASSERT PASS")

results["prior_asserts"] = {
    "gate3_path": str(PRIOR_GATE3),
    "gate3_schema_version": p3["schema_version"],
    "gate3_best_epoch": g3_best_epoch,
    "gate3_checkpoint": g3_checkpoint,
    "gate3_r_Omm_observed": g3_r_Omm,
    "gate3_r_s8_observed": g3_r_s8,
    "gate3_persistence_p90": g3_p90,
    "gate4_path": str(PRIOR_GATE4),
    "gate4_outcome": p4["gate4_outcome"]["status"],
    "gate4_reviewer": p4["gate4_outcome"]["reviewer_verdict"],
    "gate4_r3_1_r_Omm": g4_r_Omm,
    "gate4_r3_1_r_s8": g4_r_s8,
    "gate4_r3_3_mmd_pvalue": g4_mmd_p,
    "gate4_sr_r2_max": g4_r2_max_sr,
    "gate4_phase5_authorized": p4["phase5_authorization"]["authorized"],
    "verdict": "PASS"
}
print("  Prior asserts: PASS\n")

# ===========================================================================
# FASE 2 — HOD FIXED CHECK (Methodology §5.2 — VINCOLO HARD)
# ===========================================================================
print("[2/5] HOD fixed check (VINCOLO HARD Methodology §5.2)...")

# Verifica che non esistano campi galattici pre-generati con HOD fisso
# Qualsiasi campo galattico dovrebbe essere in latin_hypercube_nwLH_hod/
# Se quella directory contiene campi numpy pre-processati con HOD fisso = ERRORE
hod_fixed_error = False
hod_fixed_msg = "OK — nessun HOD fisso applicato. I campi usati in questo script sono DM puri."

suspicious_paths = [
    ROOT / "data" / "processed" / "phase5_fields_hod_fixed",
    ROOT / "data" / "processed" / "nwlh_hod_fixed",
]
for sp in suspicious_paths:
    if sp.exists() and any(sp.iterdir()):
        hod_fixed_error = True
        hod_fixed_msg = f"ERRORE: trovata directory sospetta con HOD fisso: {sp}"

assert not hod_fixed_error, f"VINCOLO HARD VIOLATO: {hod_fixed_msg}"

results["hod_fixed_check"] = {
    "hod_fixed_applied": False,
    "fields_source": "dark_matter_only_nwLH",
    "fields_path": str(NWLH_FIELDS_DIR),
    "note": "Marginalizzazione HOD AbacusSummit 9 parametri in phase5_hod_mcmc.py (Sessione 2)",
    "vincolo_hard_ref": "Methodology §5.2",
    "verdict": "PASS — " + hod_fixed_msg
}
print(f"  {hod_fixed_msg}")
print("  HOD fixed check: PASS\n")

# ===========================================================================
# FASE 3 — VERIFICA EMCEE
# ===========================================================================
print("[3/5] Verifica toolchain emcee...")

emcee_ok = False
emcee_version = "NOT_FOUND"
emcee_error = None

try:
    import emcee
    emcee_version = emcee.__version__
    emcee_ok = True
    print(f"  emcee version: {emcee_version} — OK")

    # Test funzionale minimale: sampler su una gaussiana 2D
    def log_prob_test(x):
        return -0.5 * np.sum(x**2)

    n_walkers_test = 10
    n_dim_test = 2
    p0_test = np.random.randn(n_walkers_test, n_dim_test) * 0.1
    sampler_test = emcee.EnsembleSampler(n_walkers_test, n_dim_test, log_prob_test)
    sampler_test.run_mcmc(p0_test, 20, progress=False)
    chain_test = sampler_test.get_chain()
    assert chain_test.shape == (20, n_walkers_test, n_dim_test), "emcee chain shape errata"
    print(f"  emcee functional test (10 walker, 2D Gaussian, 20 steps): PASS")

except ImportError as e:
    emcee_error = str(e)
    print(f"  emcee NON TROVATO: {e}")
    print("  Installare con: conda install -c conda-forge emcee")
except Exception as e:
    emcee_error = str(e)
    print(f"  emcee errore funzionale: {e}")

results["emcee_check"] = {
    "emcee_found": emcee_ok,
    "emcee_version": emcee_version,
    "functional_test": "PASS" if emcee_ok else "FAIL",
    "error": emcee_error,
    "n_walkers_phase5": 36,
    "n_walkers_note": "36 = 4 × 9 parametri HOD AbacusSummit (PI decision B.3)",
    "verdict": "PASS" if emcee_ok else "FAIL — installare emcee prima di Sessione 2"
}

if not emcee_ok:
    print("  ATTENZIONE: emcee non disponibile — necessario per Sessione 2")
    print("  Questo non blocca il completamento di questo script.\n")
else:
    print("  emcee check: PASS\n")

# ===========================================================================
# FASE 4 — CARICAMENTO DATI nwLH
# ===========================================================================
print("[4/5] Correlazione parziale DM-only su nwLH...")
print(f"  Caricamento parametri cosmologici nwLH da {NWLH_PARAMS_FILE}...")

assert NWLH_PARAMS_FILE.exists(), \
    f"FAIL: file parametri nwLH non trovato: {NWLH_PARAMS_FILE}"

# Formato: 7 colonne, header "#Omega_m Omega_b h n_s sigma_8 M_nu w0"
# col.0 = Omm, col.4 = s8, col.6 = w0
cosmo_nwlh = np.loadtxt(NWLH_PARAMS_FILE, comments='#')
assert cosmo_nwlh.shape == (2000, 7), \
    f"FAIL: shape parametri nwLH errata: {cosmo_nwlh.shape}, atteso (2000,7)"

Omm_all = cosmo_nwlh[:, 0]
s8_all  = cosmo_nwlh[:, 4]
w0_all  = cosmo_nwlh[:, 6]

# Sanity check sui range
assert w0_all.min() >= -1.31 and w0_all.max() <= -0.69, \
    f"FAIL: range w0 fuori dai limiti nwLH: [{w0_all.min():.3f}, {w0_all.max():.3f}]"
assert Omm_all.min() >= 0.09 and Omm_all.max() <= 0.51, \
    f"FAIL: range Omm fuori dai limiti: [{Omm_all.min():.3f}, {Omm_all.max():.3f}]"

print(f"  Parametri nwLH: shape={cosmo_nwlh.shape}")
print(f"  w0  range: [{w0_all.min():.3f}, {w0_all.max():.3f}] (atteso [-1.30,-0.70])")
print(f"  Omm range: [{Omm_all.min():.3f}, {Omm_all.max():.3f}]")
print(f"  s8  range: [{s8_all.min():.3f}, {s8_all.max():.3f}]")

# Caricamento feature TDA nwLH dal cache Phase 1
print(f"\n  Caricamento feature TDA nwLH da {TDA_CACHE}...")
assert TDA_CACHE.exists(), \
    f"FAIL: cache TDA Phase 1 non trovata: {TDA_CACHE}. " \
    f"Rieseguire phase1_tda_baseline.py prima di questo script."

cache = np.load(TDA_CACHE, allow_pickle=True)
cache_keys = list(cache.keys())
print(f"  Cache keys: {cache_keys}")

# Cerca la chiave corretta per i feature vectors nwLH
fvecs_key = None
for candidate in ["fvecs_nwlh", "fvecs_nwLH", "features_nwlh", "features_nwLH"]:
    if candidate in cache_keys:
        fvecs_key = candidate
        break

assert fvecs_key is not None, \
    f"FAIL: nessuna chiave nwLH trovata nel cache TDA. Keys disponibili: {cache_keys}. " \
    f"Atteso: fvecs_nwlh"

fvecs_nwlh = cache[fvecs_key]
print(f"  Feature TDA nwLH: shape={fvecs_nwlh.shape}, dtype={fvecs_nwlh.dtype}")
assert fvecs_nwlh.shape[0] == 2000, \
    f"FAIL: numero campi nwLH errato: {fvecs_nwlh.shape[0]}, atteso 2000"
assert fvecs_nwlh.shape[1] == 8, \
    f"FAIL: numero feature TDA errato: {fvecs_nwlh.shape[1]}, atteso 8"
assert np.isfinite(fvecs_nwlh).all(), "FAIL: feature TDA nwLH contengono NaN/Inf"

# Feature names (Execution Parameters §9.1)
feature_names = [
    "b1_peak_pos", "b1_peak_height", "b1_fwhm", "b1_integral",
    "b2_max_count", "b2_mean_persistence", "b2_high_persist", "b0_at_mean"
]

# Selezione campione di N_FIELDS con seed frozen
rng = np.random.default_rng(args.seed)
idx_sample = rng.choice(2000, size=args.n_fields, replace=False)
idx_sample = np.sort(idx_sample)

fvecs_sample = fvecs_nwlh[idx_sample]
Omm_sample   = Omm_all[idx_sample]
s8_sample    = s8_all[idx_sample]
w0_sample    = w0_all[idx_sample]

print(f"\n  Campione: {args.n_fields} campi, seed={args.seed}")
print(f"  idx_sample range: [{idx_sample.min()}, {idx_sample.max()}]")

# ===========================================================================
# CORRELAZIONE PARZIALE r(feature, w0 | Omm, s8)
# Residualizzazione OLS: regress feature su (Omm, s8), prendi residui
# Methodology §5.1: regressione lineare standard
# ===========================================================================

def partial_correlation_ols(y, x1, x2, z):
    """
    Calcola r(y, z | x1, x2) tramite residualizzazione OLS.
    Residualizza y e z rispetto a (x1, x2), poi calcola Pearson sui residui.

    Args:
        y:  feature TDA [N]
        x1: Omm [N]
        x2: s8  [N]
        z:  w0  [N]
    Returns:
        r_partial, p_value
    """
    N = len(y)
    # Design matrix con intercetta
    X = np.column_stack([np.ones(N), x1, x2])

    # OLS per y ~ Omm + s8
    beta_y, _, _, _ = np.linalg.lstsq(X, y, rcond=None)
    resid_y = y - X @ beta_y

    # OLS per z ~ Omm + s8
    beta_z, _, _, _ = np.linalg.lstsq(X, z, rcond=None)
    resid_z = z - X @ beta_z

    # Pearson sui residui
    r, p = pearsonr(resid_y, resid_z)
    return float(r), float(p)


print(f"\n  Calcolo correlazione parziale r(feature_TDA, w0 | Omm, s8)...")
print(f"  {'Feature':<25} {'r_partial':>10} {'p_value':>12} {'|r|':>8}")
print(f"  {'-'*60}")

partial_corr_results = {}
for j, fname in enumerate(feature_names):
    feat_j = fvecs_sample[:, j]
    r_j, p_j = partial_correlation_ols(feat_j, Omm_sample, s8_sample, w0_sample)
    partial_corr_results[fname] = {"r_partial": r_j, "p_value": p_j}
    sig_flag = " ***" if abs(r_j) > 0.10 else (" *" if abs(r_j) > 0.05 else "")
    print(f"  {fname:<25} {r_j:>10.4f} {p_j:>12.4e} {abs(r_j):>8.4f}{sig_flag}")

r_values = [v["r_partial"] for v in partial_corr_results.values()]
max_abs_r = max(abs(r) for r in r_values)
best_feature = feature_names[np.argmax([abs(v["r_partial"]) for v in partial_corr_results.values()])]

print(f"\n  max|r_partial| = {max_abs_r:.4f} (feature: {best_feature})")
print(f"  Gate 1b threshold era 0.10 — confronto indicativo (DM-only, n={args.n_fields})")

# ===========================================================================
# PERMUTATION TEST PRELIMINARE (N_PERM=50 — lower bound)
# Methodology §5.1: N=1000 nel run completo, qui solo stima della null
# ===========================================================================
print(f"\n  Permutation test preliminare (N={args.n_perm} shuffles)...")

# Usa la feature con |r_partial| massimo
best_feat_idx = np.argmax([abs(v["r_partial"]) for v in partial_corr_results.values()])
feat_best = fvecs_sample[:, best_feat_idx]

r_obs, _ = partial_correlation_ols(feat_best, Omm_sample, s8_sample, w0_sample)

r_null = np.zeros(args.n_perm)
for i in range(args.n_perm):
    w0_perm = rng.permutation(w0_sample)
    r_null[i], _ = partial_correlation_ols(feat_best, Omm_sample, s8_sample, w0_perm)

null_mean = float(np.mean(r_null))
null_std  = float(np.std(r_null))
sigma_prelim = (abs(r_obs) - abs(null_mean)) / null_std if null_std > 0 else 0.0

print(f"  r_obs = {r_obs:.4f}")
print(f"  null: mean={null_mean:.4f}, std={null_std:.4f}")
print(f"  sigma_preliminare = {sigma_prelim:.2f}σ (da {args.n_perm} perm, DM-only)")
print(f"  NOTA: questo è un lower bound — run completo usa N=1000 e tutti i 2000 campi")

# Interpretazione
if sigma_prelim >= 2.0:
    perm_interp = "SEGNALE FORTE anche su DM-only — ottimistico per Phase 5 completa"
elif sigma_prelim >= 1.0:
    perm_interp = "SEGNALE MARGINALE su DM-only — HOD potrebbe amplificarlo"
elif sigma_prelim >= 0.5:
    perm_interp = "SEGNALE DEBOLE su DM-only — lower bound, atteso per campione ridotto"
else:
    perm_interp = "SEGNALE NON RILEVABILE su DM-only — lower bound, atteso"

print(f"  Interpretazione: {perm_interp}")

# ===========================================================================
# ASSEMBLAGGIO RISULTATI
# ===========================================================================
results["partial_correlation_dm_only"] = {
    "n_fields": args.n_fields,
    "idx_sample_min": int(idx_sample.min()),
    "idx_sample_max": int(idx_sample.max()),
    "seed": args.seed,
    "method": "OLS residualization — regress feature su (Omm, s8), Pearson sui residui",
    "authority": "Methodology §5.1",
    "note": "Dark matter only — lower bound del segnale atteso. HOD non applicato.",
    "features": partial_corr_results,
    "max_abs_r_partial": max_abs_r,
    "best_feature": best_feature,
    "gate1b_threshold_ref": 0.10,
    "comparison_note": "Gate 1b usava correlazione diretta (non parziale) su tutti i 2000 campi. "
                       "Questo test usa correlazione parziale su campione ridotto — non comparabile direttamente."
}

results["permutation_test_preliminary"] = {
    "n_perm": args.n_perm,
    "feature_tested": best_feature,
    "r_obs": float(r_obs),
    "null_mean": null_mean,
    "null_std": null_std,
    "sigma_preliminary": float(sigma_prelim),
    "interpretation": perm_interp,
    "note": f"Preliminare — N={args.n_perm} permutazioni, {args.n_fields} campi DM-only. "
            f"Run completo (Sessione 3-4): N=1000, 2000 campi con HOD."
}

# Verdict complessivo
all_pass = (
    results["prior_asserts"]["verdict"] == "PASS" and
    results["hod_fixed_check"]["verdict"].startswith("PASS") and
    (results["emcee_check"]["verdict"] == "PASS" or not emcee_ok)  # non bloccante qui
)

results["verdict"] = {
    "prior_asserts": results["prior_asserts"]["verdict"],
    "hod_fixed_check": "PASS",
    "emcee": results["emcee_check"]["verdict"],
    "partial_corr_computed": "PASS",
    "permutation_preliminary": "PASS",
    "phase5_session1_status": "COMPLETE" if emcee_ok else "COMPLETE_EMCEE_MISSING",
    "next_step": (
        "Attendere completamento Globus transfer halo catalogs nwLH. "
        "Poi Sessione 2: phase5_hod_mcmc.py con marginalizzazione MCMC AbacusSummit 9 parametri."
    ) if emcee_ok else (
        "Installare emcee (`conda install -c conda-forge emcee`), "
        "poi attendere completamento Globus transfer halo catalogs nwLH."
    )
}

# ===========================================================================
# SALVATAGGIO
# ===========================================================================
with open(OUTPUT_FILE, "w") as f:
    json.dump(results, f, indent=2)

print("\n" + "=" * 70)
print("RIEPILOGO PHASE 5 — SANITY CHECK")
print("=" * 70)
print(f"  Prior Gate 3 assert:    {results['prior_asserts']['verdict']}")
print(f"  Prior Gate 4 assert:    {results['prior_asserts']['verdict']}")
print(f"  HOD fixed check:        PASS (HOD non applicato — DM pura)")
print(f"  emcee:                  {results['emcee_check']['verdict']}")
print(f"  Correlazione parziale:  max|r|={max_abs_r:.4f} (feature: {best_feature})")
print(f"  Sigma preliminare:      {sigma_prelim:.2f}σ ({args.n_perm} perm, {args.n_fields} campi DM)")
print(f"  Interpretazione:        {perm_interp}")
print(f"\n  Output: {OUTPUT_FILE}")
print(f"  Status: {results['verdict']['phase5_session1_status']}")
print(f"  Next:   {results['verdict']['next_step']}")
print("=" * 70)

if not emcee_ok:
    print("\nATTENZIONE: emcee non installato.")
    print("  conda install -c conda-forge emcee")
    sys.exit(1)
