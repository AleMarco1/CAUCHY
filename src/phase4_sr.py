#!/usr/bin/env python3
"""
CAUCHY Phase 4 — Symbolic Regression
======================================
Esegue 20 run indipendenti di PySR per trovare un'espressione analitica
che lega le 8 feature TDA (Ramo A) a w₀ sui campi nwLH.

Input:
  results/phase1_fiducial_cache.npz
      cosmo_nwlh [2000, 1]  — w₀ ∈ [−1.30, −0.70]
      fvecs_lhc  [2000, 8]  — feature TDA Ramo A (indici LHC)
  results/phase4_nwlh_fvecs.npz  — feature TDA Ramo A sui campi nwLH
      (generato automaticamente se mancante — vedi NOTE sotto)

Feature input (8 scalari, Ramo A, CAUCHY_Execution_Parameters §9.1):
  0: b1_peak_pos         β₁ posizione picco
  1: b1_peak_height      β₁ altezza picco
  2: b1_fwhm             β₁ larghezza a metà altezza
  3: b1_integral         β₁ integrale totale
  4: b2_max_count        β₂ numero massimo vuoti chiusi
  5: b2_mean_persistence β₂ persistenza media
  6: b2_high_persist     β₂ integrale alta persistenza (top 10%)
  7: b0_at_mean          β₀ al livello di densità media

Target: w₀ (nwLH, split 1600 train / 400 test, seed=42)

Configurazione PySR (CAUCHY_Execution_Design_v2.md §5.5):
  N run indipendenti : 20
  Seed run i         : 42 + i*100
  Backend            : Julia 1.10, PySR 0.18
  Metrica selezione  : AIC/BIC
  Operatori binari   : +, −, ×, ÷, ^2, ^3
  Operatori unari    : sqrt, log, exp, abs
  maxsize            : 20 nodi
  parsimony_coeff    : calibrato in Sessione 1 (default 0.005)
  Iterazioni         : 1000

Output:
  results/phase4_sr_run_{i:02d}.json  — per ogni run
  results/phase4_sr_expressions.json  — aggregato finale (Gate 4)

Gate 4 Threshold (CAUCHY_Execution_Parameters §6):
  Stabilità espressione : ≥ 10/20 run (50%)
  R² test set (minima)  : ≥ 0.50
  R² test set (forte)   : ≥ 0.70

Uso:
  # Verifica Julia prima del lancio:
  julia --version

  # Run completo (20 run SR):
  python src/phase4_sr.py --repo-root . --data-root .

  # Calibrazione parsimony (3 run pilota):
  python src/phase4_sr.py --repo-root . --data-root . --calibrate-parsimony

  # Resume da run i (se interrotto):
  python src/phase4_sr.py --repo-root . --data-root . --resume-from 5

NOTE sul file fvecs nwLH:
  Le feature TDA Ramo A per i campi nwLH NON sono in phase1_fiducial_cache.npz
  (che contiene solo fvecs_lhc). Lo script le calcola da phase1_tda_baseline.json
  o, se mancante, le estrae dai file τ(x) via gudhi (lento — ~30 min).
  Percorso preferito: verificare che phase1_tda_baseline.json contenga
  fvecs_nwlh [2000, 8] prima del lancio.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("phase4_sr")

# ─────────────────────────────────────────────
# FEATURE NAMES (per output e interpretazione)
# ─────────────────────────────────────────────
FEATURE_NAMES = [
    "b1_peak_pos",
    "b1_peak_height",
    "b1_fwhm",
    "b1_integral",
    "b2_max_count",
    "b2_mean_persistence",
    "b2_high_persist",
    "b0_at_mean",
]

# ─────────────────────────────────────────────
# 1.  CLI
# ─────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser(description="CAUCHY Phase 4 — Symbolic Regression")
    p.add_argument("--repo-root", type=str, default=".")
    p.add_argument("--data-root", type=str, default=".")
    p.add_argument("--n-runs", type=int, default=20,
                   help="Numero di run SR indipendenti (default: 20)")
    p.add_argument("--parsimony-coeff", type=float, default=0.005,
                   help="parsimony_coefficient PySR (default: 0.005)")
    p.add_argument("--n-iterations", type=int, default=1000,
                   help="Iterazioni per run (default: 1000)")
    p.add_argument("--calibrate-parsimony", action="store_true",
                   help="Esegui 3 run pilota con parsimony 0.001/0.005/0.010 invece dei 20 run completi")
    p.add_argument("--resume-from", type=int, default=0,
                   help="Riprendi dal run i (0=inizio, esclude run già completati)")
    p.add_argument("--maxsize", type=int, default=20,
                   help="Dimensione massima albero espressione (default: 20)")
    return p.parse_args()


# ─────────────────────────────────────────────
# 2.  ASSERT GATE3 PRIOR
# ─────────────────────────────────────────────

def verify_gate3_prior(repo_root: Path) -> dict:
    for candidate in [
        repo_root / "prior" / "gate3_prior_v1_0.json",
        repo_root / "gate3_prior_v1_0.json",
    ]:
        if candidate.exists():
            with open(candidate) as f:
                prior = json.load(f)
            assert prior["frozen_gnn_training"]["best_epoch"] == 171
            assert prior["frozen_gnn_training"]["split_seed"] == 42
            assert prior["frozen_graph_construction"]["persistence_threshold_p90"] == \
                0.35589513778686577
            log.info("  [ASSERT OK] gate3_prior: epoch=171, seed=42, p90=0.35589...")
            return prior
    raise FileNotFoundError("gate3_prior_v1_0.json non trovato")


# ─────────────────────────────────────────────
# 3.  CARICAMENTO DATI
# ─────────────────────────────────────────────

def load_data(data_root: Path, repo_root: Path):
    """
    Carica feature TDA Ramo A per i campi nwLH e i target w₀.

    Strategia di caricamento fvecs_nwlh (in ordine di priorità):
      1. results/phase4_nwlh_fvecs.npz  — cache dedicata Phase 4
      2. results/phase1_tda_baseline.json → campo "fvecs_nwlh"
      3. Calcolo on-the-fly da results/phase1_tda_data/nwlh/ (lento)
    """
    fid_cache = data_root / "results" / "phase1_fiducial_cache.npz"
    if not fid_cache.exists():
        raise FileNotFoundError(f"Non trovato: {fid_cache}")

    cache      = np.load(fid_cache)
    w0_all     = cache["cosmo_nwlh"][:, 0].astype(np.float32)   # [2000]

    log.info(f"  w₀: N={len(w0_all)}, min={w0_all.min():.3f}, max={w0_all.max():.3f}")

    # Feature TDA nwLH — priorità 1: cache dedicata
    fvecs_nwlh_cache = data_root / "results" / "phase4_nwlh_fvecs.npz"
    tda_baseline     = data_root / "results" / "phase1_tda_baseline.json"

    if fvecs_nwlh_cache.exists():
        log.info(f"  fvecs_nwlh: caricando da {fvecs_nwlh_cache}")
        fvecs_nwlh = np.load(fvecs_nwlh_cache)["fvecs_nwlh"].astype(np.float32)

    elif tda_baseline.exists():
        log.info(f"  fvecs_nwlh: caricando da {tda_baseline}")
        with open(tda_baseline) as f:
            tda_data = json.load(f)
        if "fvecs_nwlh" in tda_data:
            fvecs_nwlh = np.array(tda_data["fvecs_nwlh"], dtype=np.float32)
        else:
            log.warning("  phase1_tda_baseline.json trovato ma senza campo 'fvecs_nwlh'.")
            log.warning("  Tento caricamento da phase1_fiducial_cache.npz con chiave 'fvecs_nwlh'.")
            if "fvecs_nwlh" in cache:
                fvecs_nwlh = cache["fvecs_nwlh"].astype(np.float32)
            else:
                raise RuntimeError(
                    "fvecs_nwlh non trovato. Aggiungere al phase1_fiducial_cache.npz "
                    "o salvare in results/phase4_nwlh_fvecs.npz prima del lancio SR."
                )

    elif "fvecs_nwlh" in cache:
        log.info("  fvecs_nwlh: caricando da phase1_fiducial_cache.npz")
        fvecs_nwlh = cache["fvecs_nwlh"].astype(np.float32)

    else:
        raise RuntimeError(
            "Feature TDA nwLH non trovate. Opzioni:\n"
            "  A) Salvare in results/phase4_nwlh_fvecs.npz (chiave: fvecs_nwlh [2000,8])\n"
            "  B) Aggiungere 'fvecs_nwlh' a results/phase1_tda_baseline.json\n"
            "  C) Aggiungere 'fvecs_nwlh' a results/phase1_fiducial_cache.npz"
        )

    assert fvecs_nwlh.shape == (2000, 8), \
        f"fvecs_nwlh shape inattesa: {fvecs_nwlh.shape} (attesa (2000, 8))"
    assert len(w0_all) == 2000

    log.info(f"  fvecs_nwlh: shape={fvecs_nwlh.shape}, "
             f"nan={np.isnan(fvecs_nwlh).sum()}, inf={np.isinf(fvecs_nwlh).sum()}")

    return fvecs_nwlh, w0_all


def get_nwlh_split(n_total=2000, n_train=1600, seed=42):
    """Split nwLH 80/20 per SR su w₀ (seed=42, coerente con Phase 3)."""
    rng = np.random.default_rng(seed)
    idx = np.arange(n_total)
    rng.shuffle(idx)
    return np.sort(idx[:n_train]), np.sort(idx[n_train:])


# ─────────────────────────────────────────────
# 4.  PREPROCESSING FEATURE
# ─────────────────────────────────────────────

def preprocess_features(X_train, X_test):
    """
    Standardizzazione Z-score basata sul training set.
    PySR funziona meglio con feature in scala comparabile.
    Ritorna (X_train_scaled, X_test_scaled, mean, std).
    """
    mu  = X_train.mean(axis=0)
    std = X_train.std(axis=0)
    std = np.where(std < 1e-8, 1.0, std)   # evita divisione per zero
    return (X_train - mu) / std, (X_test - mu) / std, mu, std


# ─────────────────────────────────────────────
# 5.  CONFIGURAZIONE PYSR
# ─────────────────────────────────────────────

def build_pysr_model(seed: int, parsimony_coeff: float, n_iterations: int,
                     maxsize: int):
    """
    Costruisce un modello PySR con la configurazione CAUCHY.
    Autorità: CAUCHY_Execution_Design_v2.md §5.5

    Argomenti al minimo stabile per compatibilita' PySR >=0.17.
    square/cube sono gli unary operator per x^2 e x^3 in PySR moderno.
    """
    from pysr import PySRRegressor

    model = PySRRegressor(
        # Operatori (Execution Design §5.5)
        binary_operators=["+", "-", "*", "/"],
        unary_operators=["square", "cube", "sqrt", "log", "exp", "abs"],

        # Complessita'
        maxsize=maxsize,
        parsimony=parsimony_coeff,

        # Iterazioni e seed
        niterations=n_iterations,
        random_state=seed,
        deterministic=True,

        # Selezione modello
        model_selection="best",

        # Determinismo richiede parallelism='serial'
        parallelism="serial",

        # Verbosity
        verbosity=1,

        # Mappatura sympy per square/cube
        extra_sympy_mappings={
            "square": lambda x: x**2,
            "cube":   lambda x: x**3,
        },
    )
    return model


def compute_metrics(y_true, y_pred):
    """Calcola R², RMSE, MAE."""
    ss_res = np.sum((y_true - y_pred) ** 2)
    ss_tot = np.sum((y_true - y_true.mean()) ** 2)
    r2   = float(1 - ss_res / ss_tot) if ss_tot > 0 else float("nan")
    rmse = float(np.sqrt(np.mean((y_true - y_pred) ** 2)))
    mae  = float(np.mean(np.abs(y_true - y_pred)))
    return {"r2": r2, "rmse": rmse, "mae": mae}


def compute_aic_bic(y_true, y_pred, n_params):
    """AIC e BIC assumendo errori gaussiani."""
    n    = len(y_true)
    rss  = np.sum((y_true - y_pred) ** 2)
    sigma2 = rss / n
    ll   = -n / 2 * (np.log(2 * np.pi * sigma2) + 1)
    aic  = float(2 * n_params - 2 * ll)
    bic  = float(n_params * np.log(n) - 2 * ll)
    return aic, bic


# ─────────────────────────────────────────────
# 7.  SINGOLO RUN SR
# ─────────────────────────────────────────────

def run_sr_single(run_idx: int, X_train, y_train, X_test, y_test,
                  parsimony_coeff: float, n_iterations: int, maxsize: int,
                  results_dir: Path, feature_names: list):
    """
    Esegue un singolo run PySR e salva i risultati in
    results/phase4_sr_run_{run_idx:02d}.json.
    Restituisce il dict del risultato.
    """
    seed = 42 + run_idx * 100
    out_path = results_dir / f"phase4_sr_run_{run_idx:02d}.json"

    if out_path.exists():
        log.info(f"  Run {run_idx:02d}: già completato — carico da {out_path}")
        with open(out_path) as f:
            return json.load(f)

    log.info(f"  Run {run_idx:02d}: avvio (seed={seed}, parsimony={parsimony_coeff})...")
    t0 = time.time()

    model = build_pysr_model(seed, parsimony_coeff, n_iterations, maxsize)

    try:
        model.fit(X_train, y_train, variable_names=feature_names)
    except Exception as e:
        log.error(f"  Run {run_idx:02d}: ERRORE — {e}")
        result = {
            "run_idx": run_idx, "seed": seed, "status": "ERROR",
            "error": str(e), "elapsed_s": float(time.time() - t0),
        }
        with open(out_path, "w") as f:
            json.dump(result, f, indent=2)
        return result

    elapsed = time.time() - t0

    # Espressione migliore (secondo model_selection="best")
    best_expr    = str(model.sympy())
    # complexity: legge dalla equations_ DataFrame (compatibile con tutte le versioni PySR)
    try:
        best_row  = model.equations_.iloc[model.equations_["score"].argmax()]
        complexity = int(best_row["complexity"])
    except Exception:
        # Fallback: stima dalla stringa dell'espressione
        complexity = len(best_expr.split())
    y_pred_train = model.predict(X_train)
    y_pred_test  = model.predict(X_test)

    metrics_train = compute_metrics(y_train, y_pred_train)
    metrics_test  = compute_metrics(y_test,  y_pred_test)
    aic, bic      = compute_aic_bic(y_test, y_pred_test, complexity)

    log.info(f"  Run {run_idx:02d}: R²_test={metrics_test['r2']:.4f}, "
             f"complexity={complexity}, elapsed={elapsed:.0f}s")
    log.info(f"    Espressione: {best_expr}")

    # Tabella completa di Pareto (tutte le espressioni trovate)
    pareto = []
    try:
        for _, row in model.equations_.iterrows():
            pareto.append({
                "formula":    str(row.get("sympy_format", row.get("equation", ""))),
                "complexity": int(row.get("complexity", 0)),
                "loss":       float(row.get("loss", float("nan"))),
                "score":      float(row.get("score", float("nan"))),
            })
    except Exception:
        pass

    result = {
        "run_idx":      run_idx,
        "seed":         seed,
        "status":       "OK",
        "parsimony_coeff": parsimony_coeff,
        "n_iterations": n_iterations,
        "maxsize":      maxsize,
        "elapsed_s":    float(elapsed),
        "best_expression": {
            "formula":    best_expr,
            "complexity": complexity,
            "r2_train":   metrics_train["r2"],
            "r2_test":    metrics_test["r2"],
            "rmse_test":  metrics_test["rmse"],
            "mae_test":   metrics_test["mae"],
            "aic":        aic,
            "bic":        bic,
        },
        "pareto_front": pareto,
    }

    with open(out_path, "w") as f:
        json.dump(result, f, indent=2)
    log.info(f"  Run {run_idx:02d}: salvato in {out_path}")

    return result


# ─────────────────────────────────────────────
# 8.  AGGREGAZIONE E GATE 4
# ─────────────────────────────────────────────

def _canonical(formula: str) -> str:
    """
    Normalizzazione canonica minima per raggruppare espressioni equivalenti.
    PySR produce costanti numeriche variabili tra run — le sostituiamo
    con token generici per il confronto di forma.
    """
    import re
    # Sostituisce numeri decimali (compreso segno e esponente) con '#'
    formula = re.sub(r'-?\d+\.\d+(?:[eE][+-]?\d+)?', '#', formula)
    # Sostituisce interi isolati (non parte di nomi) con '#'
    formula = re.sub(r'(?<![a-zA-Z_])\d+(?![a-zA-Z_\.])', '#', formula)
    # Normalizza spazi
    formula = re.sub(r'\s+', ' ', formula).strip()
    return formula


def aggregate_results(run_results: list, n_runs: int, results_dir: Path,
                      y_test, X_test):
    """
    Aggrega i risultati dei 20 run:
    - Istogramma di frequenza delle espressioni (forma canonica)
    - Identificazione espressione stabile (≥50% run)
    - Verdetto Gate 4
    """
    from collections import Counter

    # Conta frequenza per forma canonica
    successful = [r for r in run_results if r.get("status") == "OK"]
    log.info(f"  Run completati con successo: {len(successful)}/{n_runs}")

    canonical_counter = Counter()
    canonical_to_examples = {}   # canonical -> lista di (formula, r2_test, complexity)

    for r in successful:
        expr    = r["best_expression"]
        formula = expr["formula"]
        canon   = _canonical(formula)
        canonical_counter[canon] += 1
        if canon not in canonical_to_examples:
            canonical_to_examples[canon] = []
        canonical_to_examples[canon].append({
            "formula":    formula,
            "r2_test":    expr["r2_test"],
            "complexity": expr["complexity"],
            "aic":        expr["aic"],
            "run_idx":    r["run_idx"],
        })

    # Istogramma ordinato per frequenza
    histogram = []
    for canon, count in canonical_counter.most_common():
        examples = canonical_to_examples[canon]
        r2_values = [e["r2_test"] for e in examples]
        histogram.append({
            "canonical_formula": canon,
            "frequency":         count,
            "frequency_pct":     float(count / n_runs * 100),
            "r2_test_mean":      float(np.mean(r2_values)),
            "r2_test_max":       float(np.max(r2_values)),
            "r2_test_min":       float(np.min(r2_values)),
            "best_example":      max(examples, key=lambda e: e["r2_test"]),
        })

    # Gate 4 thresholds (CAUCHY_Execution_Parameters §6)
    STABILITY_THRESHOLD = 0.50   # ≥ 10/20 run
    R2_MIN              = 0.50
    R2_STRONG           = 0.70

    # Espressione candidata: la più frequente
    best_expr_info = None
    gate4_status   = "FAIL_NEGATIVE"

    if histogram:
        top = histogram[0]
        freq_frac  = top["frequency"] / n_runs
        r2_best    = top["r2_test_max"]

        log.info(f"  Espressione top: freq={top['frequency']}/{n_runs} "
                 f"({freq_frac*100:.1f}%), R²_max={r2_best:.4f}")
        log.info(f"    Formula canonica: {top['canonical_formula']}")

        best_example = top["best_example"]
        aic_val = best_example.get("aic", float("nan"))

        best_expr_info = {
            "formula":     best_example["formula"],
            "canonical":   top["canonical_formula"],
            "frequency":   top["frequency"],
            "frequency_pct": float(freq_frac * 100),
            "r2_test":     r2_best,
            "complexity":  best_example["complexity"],
            "aic":         aic_val,
        }

        if freq_frac >= STABILITY_THRESHOLD and r2_best >= R2_STRONG:
            gate4_status = "PASS"
        elif freq_frac >= STABILITY_THRESHOLD and r2_best >= R2_MIN:
            gate4_status = "PASS_WEAK"
        else:
            gate4_status = "FAIL_NEGATIVE"

    log.info(f"  Gate 4 status: {gate4_status}")

    # Interpretazione fisica
    if gate4_status == "PASS":
        physical_interp = (
            "Espressione simbolica stabile trovata con R² ≥ 0.70 sul test set. "
            "La relazione algebrica tra feature TDA e w₀ è interpretabile fisicamente. "
            "Procedere con analisi di interpretazione fisica e chiusura Gate 4."
        )
    elif gate4_status == "PASS_WEAK":
        physical_interp = (
            "Espressione simbolica stabile trovata con 0.50 ≤ R² < 0.70 sul test set. "
            "Relazione parziale presente — interpretazione fisica possibile con caveat. "
            "Gate 4 passa debolmente. Motivare Phase 5 (z multipli) per segnale più forte."
        )
    else:
        physical_interp = (
            "Nessuna espressione stabile trovata con R² ≥ 0.50. "
            "Risultato negativo: la relazione tra feature TDA (Ramo A) e w₀ non è "
            "algebricamente semplice a z=0. Fisicamente atteso: H(z=0) ≡ H₀, D(z=0) ≡ 1 "
            "rendono l'effetto di w₀ sulle strutture topologiche non distinguibile a z=0. "
            "Gate 4 chiuso negativamente — documentazione esplicita come da Methodology §4.3. "
            "Phase 5 (z=0.5/1.0/2.0, redshift space) motivata."
        )

    return {
        "n_runs_total":        n_runs,
        "n_runs_successful":   len(successful),
        "stability_threshold": STABILITY_THRESHOLD,
        "r2_threshold_min":    R2_MIN,
        "r2_threshold_strong": R2_STRONG,
        "best_expression":     best_expr_info,
        "expression_histogram": histogram,
        "gate4_status":        gate4_status,
        "physical_interpretation": physical_interp,
    }


# ─────────────────────────────────────────────
# 9.  CALIBRAZIONE PARSIMONY
# ─────────────────────────────────────────────

def calibrate_parsimony(X_train, y_train, X_test, y_test,
                        n_iterations: int, maxsize: int,
                        results_dir: Path, feature_names: list):
    """
    3 run pilota con parsimony ∈ {0.001, 0.005, 0.010}.
    Logga complessità media e R² per supportare la scelta.
    """
    parsimony_values = [0.001, 0.005, 0.010]
    log.info("CALIBRAZIONE PARSIMONY: 3 run pilota...")
    log.info(f"  Valori testati: {parsimony_values}")

    results = []
    for i, p in enumerate(parsimony_values):
        log.info(f"\n  Pilota {i+1}/3: parsimony={p}")
        r = run_sr_single(
            run_idx=200 + i,   # idx fuori range run normali
            X_train=X_train, y_train=y_train,
            X_test=X_test,   y_test=y_test,
            parsimony_coeff=p,
            n_iterations=min(n_iterations, 300),   # più veloce per calibrazione
            maxsize=maxsize,
            results_dir=results_dir,
            feature_names=feature_names,
        )
        results.append(r)

    log.info("\n  === SOMMARIO CALIBRAZIONE PARSIMONY ===")
    log.info(f"  {'Parsimony':<12} {'R²_test':<10} {'Complexity':<12} {'Formula'}")
    for p, r in zip(parsimony_values, results):
        if r.get("status") == "OK":
            expr = r["best_expression"]
            log.info(f"  {p:<12} {expr['r2_test']:<10.4f} {expr['complexity']:<12} {expr['formula'][:60]}")
        else:
            log.info(f"  {p:<12} ERROR")

    log.info("\n  Seleziona il parsimony_coefficient che bilancia:")
    log.info("    - R² ragionevole (non zero, ma nemmeno overfitting)")
    log.info("    - Complessità < 15 nodi (espressione interpretabile)")
    log.info("  Poi lancia il run completo con --parsimony-coeff <valore_scelto>")

    return results


# ─────────────────────────────────────────────
# 10. MAIN
# ─────────────────────────────────────────────

def main():
    args      = parse_args()
    repo_root = Path(args.repo_root).resolve()
    data_root = Path(args.data_root).resolve()

    log.info("=" * 60)
    log.info("CAUCHY Phase 4 — Symbolic Regression")
    if args.calibrate_parsimony:
        log.info("  MODALITÀ: calibrazione parsimony (3 run pilota)")
    else:
        log.info(f"  MODALITÀ: {args.n_runs} run SR completi")
    log.info(f"  repo_root       : {repo_root}")
    log.info(f"  data_root       : {data_root}")
    log.info(f"  parsimony_coeff : {args.parsimony_coeff}")
    log.info(f"  n_iterations    : {args.n_iterations}")
    log.info(f"  maxsize         : {args.maxsize}")
    log.info("=" * 60)

    # 1. Assert prior
    log.info("[STEP 1] Verifica gate3_prior...")
    verify_gate3_prior(repo_root)

    # 2. Verifica Julia
    log.info("[STEP 2] Verifica Julia...")
    import subprocess
    try:
        result = subprocess.run(["julia", "--version"], capture_output=True, text=True, timeout=10)
        log.info(f"  {result.stdout.strip()}")
    except Exception as e:
        log.error(f"  Julia non trovato o non accessibile: {e}")
        log.error("  Installare Julia 1.10 e aggiungerlo al PATH prima del lancio PySR.")
        sys.exit(1)

    # 3. Carica dati
    log.info("[STEP 3] Caricamento feature TDA nwLH e target w₀...")
    fvecs_nwlh, w0_all = load_data(data_root, repo_root)

    # 4. Split nwLH 80/20 seed=42
    train_idx, test_idx = get_nwlh_split(n_total=2000, n_train=1600, seed=42)
    X_train_raw = fvecs_nwlh[train_idx]   # [1600, 8]
    X_test_raw  = fvecs_nwlh[test_idx]    # [400, 8]
    y_train     = w0_all[train_idx]        # [1600]
    y_test      = w0_all[test_idx]         # [400]

    log.info(f"  Split: train={len(y_train)}, test={len(y_test)}")
    log.info(f"  w₀ train: mean={y_train.mean():.3f}, std={y_train.std():.3f}")
    log.info(f"  w₀ test:  mean={y_test.mean():.3f},  std={y_test.std():.3f}")

    # 5. Preprocessing
    X_train, X_test, feat_mean, feat_std = preprocess_features(X_train_raw, X_test_raw)
    log.info(f"  Feature standardizzate (Z-score su train set)")

    # Sanity check: correlazioni lineari feature-w₀ prima del SR
    from scipy.stats import pearsonr
    log.info("  Correlazioni |r(feature, w₀)| sul train set:")
    for i, name in enumerate(FEATURE_NAMES):
        r, _ = pearsonr(X_train_raw[:, i], y_train)
        log.info(f"    {name:<25} |r| = {abs(r):.4f}")

    # 6. Output dir
    results_dir     = data_root / "results"
    sr_runs_dir     = results_dir / "phase4_sr_runs"
    sr_runs_dir.mkdir(parents=True, exist_ok=True)

    # 7. Modalità calibrazione o run completo
    if args.calibrate_parsimony:
        log.info("[STEP 4] Calibrazione parsimony coefficient...")
        calibrate_parsimony(
            X_train, y_train, X_test, y_test,
            n_iterations=args.n_iterations,
            maxsize=args.maxsize,
            results_dir=sr_runs_dir,
            feature_names=FEATURE_NAMES,
        )
        return

    # 8. 20 run SR
    log.info(f"[STEP 4] Avvio {args.n_runs} run SR indipendenti...")
    log.info(f"  parsimony_coeff = {args.parsimony_coeff}")
    log.info(f"  Seed run i = 42 + i*100")
    log.info(f"  Resume da run {args.resume_from}")

    run_results = []
    t_total = time.time()
    for run_idx in range(args.n_runs):
        if run_idx < args.resume_from:
            # Prova a caricare il run già completato
            out_path = sr_runs_dir / f"phase4_sr_run_{run_idx:02d}.json"
            if out_path.exists():
                with open(out_path) as f:
                    run_results.append(json.load(f))
            continue

        result = run_sr_single(
            run_idx=run_idx,
            X_train=X_train, y_train=y_train,
            X_test=X_test,   y_test=y_test,
            parsimony_coeff=args.parsimony_coeff,
            n_iterations=args.n_iterations,
            maxsize=args.maxsize,
            results_dir=sr_runs_dir,
            feature_names=FEATURE_NAMES,
        )
        run_results.append(result)

        # Progress
        ok   = sum(1 for r in run_results if r.get("status") == "OK")
        done = len(run_results)
        log.info(f"  Progresso: {done}/{args.n_runs} run completati, {ok} OK")

    elapsed_total = time.time() - t_total
    log.info(f"\n  Tutti i run completati in {elapsed_total/3600:.1f}h")

    # 9. Aggregazione e Gate 4
    log.info("[STEP 5] Aggregazione risultati e valutazione Gate 4...")
    agg = aggregate_results(run_results, args.n_runs, results_dir, y_test, X_test)

    # 10. Salva output Gate 4
    gate4_output = {
        "schema_version": "2.0",
        "generated_at":   datetime.now(timezone.utc).isoformat(),
        "gate":           "GATE_4",
        "script":         "src/phase4_sr.py",
        "target":         "w0",
        "target_dataset": "nwLH — 2000 campi, split 1600/400 seed=42",
        "features":       FEATURE_NAMES,
        "n_features":     8,
        "parsimony_coeff": args.parsimony_coeff,
        "n_iterations":   args.n_iterations,
        "maxsize":        args.maxsize,
        "feature_preprocessing": "Z-score su train set",
        "preprocessing_mean": feat_mean.tolist(),
        "preprocessing_std":  feat_std.tolist(),
        **agg,
    }

    out_path = results_dir / "phase4_sr_expressions.json"
    with open(out_path, "w") as f:
        json.dump(gate4_output, f, indent=2)
    log.info(f"  [SALVATO] {out_path}")

    # 11. Sommario finale
    log.info("=" * 60)
    log.info("SOMMARIO GATE 4")
    log.info(f"  Run completati : {agg['n_runs_successful']}/{args.n_runs}")
    log.info(f"  Gate 4 status  : {agg['gate4_status']}")
    if agg["best_expression"]:
        b = agg["best_expression"]
        log.info(f"  Best expr freq : {b['frequency']}/{args.n_runs} ({b['frequency_pct']:.1f}%)")
        log.info(f"  Best expr R²   : {b['r2_test']:.4f}")
        log.info(f"  Best expr cmpl : {b['complexity']} nodi")
        log.info(f"  Formula        : {b['formula']}")
    log.info(f"  Interpretazione: {agg['physical_interpretation'][:100]}...")
    log.info("=" * 60)
    log.info(f"Riporta phase4_sr_expressions.json nella Sessione 3 per chiusura Gate 4.")


if __name__ == "__main__":
    main()
