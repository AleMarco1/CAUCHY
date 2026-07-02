#!/usr/bin/env python3
"""
CAUCHY — Phase 1 TDA Baseline (Ramo A)
Script: phase1_tda_baseline.py

Genera le Betti curves da filtrazione di supralivello su campi di densità 128³,
estrae 8 feature fisicamente motivate, esegue analisi Fisher (Gate 1a) e
correlazioni con w0 (Gate 1b).

Autore: generato da Claude per il PI del Progetto CAUCHY
Riferimento metodologico: CAUCHY_Systematic_Methodology_v2.md §1.2–1.4
Riferimento parametri: CAUCHY_Execution_Parameters.md v1.1
Benchmark: Abedi et al. 2025 (arXiv:2410.01751v2)

Usage:
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode sanity
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode sensitivity
    python phase1_tda_baseline.py --data-root D:/projects/cauchy --repo-root . --mode full
"""

import argparse
import json
import logging
import multiprocessing as mp
import os
import sys
import time
import warnings
from datetime import datetime, timezone
from pathlib import Path

import gudhi
import numpy as np
import scipy.ndimage
import scipy.stats
from tqdm import tqdm

# ---------------------------------------------------------------------------
# GLOBAL CONFIGURATION
# ---------------------------------------------------------------------------

GLOBAL_SEED = 42
np.random.seed(GLOBAL_SEED)

N_THRESH = 50          # soglie di filtrazione per Betti curve
N_SENSITIVITY = 50     # campi fiduciali per sensitivity check (indici 0-49)
N_FIDUCIAL_FULL = 2000 # campi fiduciali totali
N_LHC = 2000           # campi LHC
N_NWLH = 2000          # campi nwLH
N_FEAT = 8             # numero di feature scalari

# Colonne nei file parametri (0-indexed, dopo header)
LHC_COL_OMM   = 0  # Omega_m
LHC_COL_S8    = 4  # sigma_8
NWLH_COL_OMM  = 0  # Omega_m
NWLH_COL_S8   = 4  # sigma_8
NWLH_COL_W0   = 6  # w0

# Valori fiduciali Quijote (Planck 2018)
FID_OMM  = 0.3175
FID_S8   = 0.8340
FID_W0   = -1.0

# Parametri di smoothing (Resolution: 1 Gpc/h / 128 voxel = 7.8125 Mpc/h per voxel)
# R=5 Mpc/h → sigma_pixel = 5 / 7.8125 = 0.64 px
# R=10 Mpc/h → sigma_pixel = 10 / 7.8125 = 1.28 px
BOX_SIZE_MPCH  = 1000.0
N_GRID         = 128
PIX_SIZE_MPCH  = BOX_SIZE_MPCH / N_GRID  # 7.8125 Mpc/h
SIGMA_R5_PX    = 5.0  / PIX_SIZE_MPCH    # 0.64 px
SIGMA_R10_PX   = 10.0 / PIX_SIZE_MPCH    # 1.28 px

# Gate 1 threshold (CAUCHY_Execution_Parameters.md v1.1 §3.3–3.4)
GATE1A_SIGMA_OMM_MAX  = 0.10
GATE1A_SIGMA_S8_MAX   = 0.030
GATE1B_R_MIN_HARD     = 0.10   # b1_peak_pos e b2_mean_persistence
GATE1B_R_MIN_SOFT     = 0.15   # almeno una feature

# Regione locale per derivate numeriche Fisher
# |theta - theta_fid| <= 0.3 * range_theta
FISHER_LOCAL_FRAC = 0.3

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("cauchy.phase1")


# ---------------------------------------------------------------------------
# CORE TDA FUNCTIONS
# ---------------------------------------------------------------------------

def field_to_nu(field: np.ndarray) -> np.ndarray:
    """
    Converte campo di densità δ(x) nella variabile di filtrazione
    ν = log(δ + 1), come in Abedi et al. 2025.

    I campi preprocessati sono mean-subtracted (⟨δ⟩ = 0), quindi
    δ può essere < 0. Il minimo fisico è δ = -1 (vuoto totale).
    Il clipping a -0.9999 evita log(0) o log(negativo).
    """
    return np.log(np.clip(field, -0.9999, None) + 1.0)


def compute_persistence_diagram(field: np.ndarray):
    """
    Calcola i diagrammi di persistenza per β₀, β₁, β₂ tramite
    filtrazione di supralivello su gudhi CubicalComplex.

    La filtrazione di supralivello su ν(x) è implementata passando
    -ν(x) a gudhi (che implementa filtrazione di sottolivel):
    abbassare la soglia su -ν equivale ad alzarla su ν.

    Convenzione gudhi → ν originale:
        gudhi opera in spazio -ν (sottolivel) e restituisce:
            birth_g < death_g   (in spazio -ν: birth_g = -ν_birth, death_g = -ν_death)
        Conversione corretta:
            nu_birth = -birth_g   (col 0 negata: alta densità, feature nasce)
            nu_death = -death_g   (col 1 negata: bassa densità, feature muore)
            nu_birth > nu_death   ✓ (coerente con superlevel)

    Restituisce:
        dict con chiavi 'b0', 'b1', 'b2', ciascuna un array (N, 2)
        con colonne [nu_birth, nu_death] in unità di ν.
        nu_birth > nu_death (superlevel: feature nasce ad alta densità).
    """
    nu = field_to_nu(field)

    # gudhi CubicalComplex: top_dimensional_cells in ordine C (row-major)
    cc = gudhi.CubicalComplex(
        dimensions=list(nu.shape),
        top_dimensional_cells=(-nu).flatten().astype(np.float64)
    )
    cc.compute_persistence()

    diagrams = {}
    for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
        raw = cc.persistence_intervals_in_dimension(dim)  # (N, 2) in -ν
        if len(raw) == 0:
            diagrams[key] = np.empty((0, 2), dtype=np.float64)
        else:
            raw = np.array(raw, dtype=np.float64)
            # Scarta feature con death = +inf (componente illimitata β₀)
            finite_mask = np.isfinite(raw[:, 1])
            raw = raw[finite_mask]
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2), dtype=np.float64)
            else:
                # Conversione corretta: nu_birth=-col0, nu_death=-col1
                # gudhi col0=birth_g (basso in -nu = alta densita in nu, feature NASCE)
                # gudhi col1=death_g (alto in -nu  = bassa densita in nu, feature MUORE)
                nu_birth = -raw[:, 0]
                nu_death = -raw[:, 1]
                diagrams[key] = np.column_stack([nu_birth, nu_death])
                # nu_birth > nu_death per costruzione (superlevel)

    return diagrams


def betti_curve_from_diagram(diagram: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """
    Calcola la Betti curve β(t) per un array di soglie.

    Convenzione: diagram ha colonne [nu_birth, nu_death] con nu_birth > nu_death.
    Una feature è 'viva' alla soglia t (superlevel) se:
        nu_death < t <= nu_birth
    (nata a densità alta nu_birth, ancora viva finché t > nu_death)

    Parametri:
        diagram:    array (N, 2) con colonne [nu_birth, nu_death]
        thresholds: array (M,) di soglie (tipicamente decrescenti)

    Restituisce:
        array (M,) con numero di feature vive a ogni soglia
    """
    if len(diagram) == 0:
        return np.zeros(len(thresholds), dtype=np.float64)

    nu_birth = diagram[:, 0]  # (N,) — alta densita
    nu_death = diagram[:, 1]  # (N,) — bassa densita

    # feature viva a t se: nu_death < t <= nu_birth
    alive = (nu_birth[:, None] >= thresholds[None, :]) & (nu_death[:, None] < thresholds[None, :])
    return alive.sum(axis=0).astype(np.float64)


def compute_betti_curves_from_field(field: np.ndarray, thresholds: np.ndarray):
    """
    Pipeline completa: campo → diagrammi di persistenza → Betti curves.

    Restituisce:
        (diagrams, b0_curve, b1_curve, b2_curve)
        - diagrams: dict con 'b0','b1','b2' array (N,2)
        - b*_curve: array (N_THRESH,)
    """
    diagrams = compute_persistence_diagram(field)
    b0 = betti_curve_from_diagram(diagrams['b0'], thresholds)
    b1 = betti_curve_from_diagram(diagrams['b1'], thresholds)
    b2 = betti_curve_from_diagram(diagrams['b2'], thresholds)
    return diagrams, b0, b1, b2


def compute_field_thresholds(field: np.ndarray, n_thresh: int = N_THRESH):
    """
    Calcola le N_THRESH soglie per-campo: uniformi tra 5° e 95° percentile
    della variabile di filtrazione ν = log(δ+1).

    Restituisce array (N_THRESH,) in ordine DECRESCENTE (alta→bassa densità),
    coerente con la direzione della filtrazione di supralivello.
    """
    nu = field_to_nu(field)
    lo = np.percentile(nu, 5)
    hi = np.percentile(nu, 95)
    return np.linspace(hi, lo, n_thresh)


# ---------------------------------------------------------------------------
# FEATURE EXTRACTION
# ---------------------------------------------------------------------------

def extract_features(thresholds: np.ndarray,
                     b0: np.ndarray, b1: np.ndarray, b2: np.ndarray,
                     diagrams: dict) -> dict:
    """
    Estrae le 8 feature scalari da Betti curves e diagrammi di persistenza.
    Riferimento: CAUCHY_Systematic_Methodology_v2.md §1.2 e
                 CAUCHY_Execution_Parameters.md §9.1

    Le soglie sono in ordine decrescente (alta → bassa densità).
    Per 'posizione del picco' usiamo il valore di ν corrispondente.

    Feature:
        b1_peak_pos          : ν al picco di β₁
        b1_peak_height       : altezza del picco di β₁
        b1_fwhm              : FWHM della curva β₁ (in unità di ν)
        b1_integral          : integrale di β₁ (somma × Δν)
        b2_max_count         : massimo di β₂
        b2_mean_persistence  : persistenza media su tutte le feature β₂
        b2_high_persist      : integrale top-10% persistenza β₂ (su Betti curve)
        b0_at_mean           : β₀ alla soglia più vicina a ν=0 (densità media)
    """
    feats = {}
    dnu = abs(thresholds[1] - thresholds[0])  # passo di integrazione

    # --- β₁ features ---
    if np.any(b1 > 0):
        pk_idx = int(np.argmax(b1))
        feats['b1_peak_pos']    = float(thresholds[pk_idx])
        feats['b1_peak_height'] = float(b1[pk_idx])

        # FWHM
        half_max = b1[pk_idx] / 2.0
        above = b1 >= half_max
        if above.sum() >= 2:
            idxs = np.where(above)[0]
            feats['b1_fwhm'] = float(abs(thresholds[idxs[0]] - thresholds[idxs[-1]]))
        else:
            feats['b1_fwhm'] = float(dnu)

        feats['b1_integral'] = float(np.sum(b1) * dnu)
    else:
        feats['b1_peak_pos']    = 0.0
        feats['b1_peak_height'] = 0.0
        feats['b1_fwhm']        = 0.0
        feats['b1_integral']    = 0.0

    # --- β₂ features ---
    feats['b2_max_count'] = float(np.max(b2)) if len(b2) > 0 else 0.0

    # Persistenza da diagramma
    d2 = diagrams.get('b2', np.empty((0, 2)))
    if len(d2) > 0:
        persistence = d2[:, 0] - d2[:, 1]  # nu_birth - nu_death > 0 per costruzione
        persistence = persistence[persistence > 0]
        if len(persistence) > 0:
            feats['b2_mean_persistence'] = float(np.mean(persistence))
            # Top 10% per alta persistenza
            p90 = np.percentile(persistence, 90)
            feats['b2_high_persist'] = float(np.sum(persistence[persistence >= p90]))
        else:
            feats['b2_mean_persistence'] = 0.0
            feats['b2_high_persist']     = 0.0
    else:
        feats['b2_mean_persistence'] = 0.0
        feats['b2_high_persist']     = 0.0

    # --- β₀ al livello di densità media ---
    # Cercare la soglia più vicina a ν=0 (log(0+1)=0, cioè δ=0, densità media)
    target_nu = 0.0
    idx_mean = int(np.argmin(np.abs(thresholds - target_nu)))
    feats['b0_at_mean'] = float(b0[idx_mean])

    return feats


FEATURE_NAMES = [
    'b1_peak_pos', 'b1_peak_height', 'b1_fwhm', 'b1_integral',
    'b2_max_count', 'b2_mean_persistence', 'b2_high_persist', 'b0_at_mean'
]


def features_to_vector(feats: dict) -> np.ndarray:
    """Converte dict feature in vettore numpy ordinato come FEATURE_NAMES."""
    return np.array([feats[k] for k in FEATURE_NAMES], dtype=np.float64)


# ---------------------------------------------------------------------------
# WORKER FUNCTIONS (multiprocessing)
# ---------------------------------------------------------------------------

def _worker_init(shared_thresholds_):
    """Inizializza variabile globale nel worker per le soglie comuni."""
    global _shared_thresholds
    _shared_thresholds = shared_thresholds_


def _process_field_sanity(args):
    """
    Worker per modalità sanity: processa un campo fiduciale.
    Restituisce (thresholds_perfield, b0, b1, b2, features_dict).
    """
    field_path, common_thresholds = args
    try:
        field = np.load(field_path).astype(np.float64)
        thresholds_pf = compute_field_thresholds(field, N_THRESH)
        diagrams, b0_pf, b1_pf, b2_pf = compute_betti_curves_from_field(field, thresholds_pf)

        # Interpola su griglia comune
        b0_c = np.interp(common_thresholds, thresholds_pf[::-1], b0_pf[::-1])
        b1_c = np.interp(common_thresholds, thresholds_pf[::-1], b1_pf[::-1])
        b2_c = np.interp(common_thresholds, thresholds_pf[::-1], b2_pf[::-1])

        feats = extract_features(thresholds_pf, b0_pf, b1_pf, b2_pf, diagrams)
        return (common_thresholds, b0_c, b1_c, b2_c, feats, None)
    except Exception as e:
        return (None, None, None, None, None, str(e))


def _process_field_full(args):
    """
    Worker per modalità full: processa un campo qualsiasi.
    Restituisce (features_vec, pd_b1_birth, pd_b1_death, pd_b2_birth, pd_b2_death, error).
    save_pd: bool, se True salva anche i diagrammi di persistenza.
    """
    field_path, common_thresholds, save_pd = args
    try:
        field = np.load(field_path).astype(np.float64)
        thresholds_pf = compute_field_thresholds(field, N_THRESH)
        diagrams, b0_pf, b1_pf, b2_pf = compute_betti_curves_from_field(field, thresholds_pf)

        feats = extract_features(thresholds_pf, b0_pf, b1_pf, b2_pf, diagrams)
        fvec  = features_to_vector(feats)

        if save_pd:
            d1 = diagrams.get('b1', np.empty((0, 2)))
            d2 = diagrams.get('b2', np.empty((0, 2)))
            pd_data = (
                d1[:, 0] if len(d1) else np.array([]),
                d1[:, 1] if len(d1) else np.array([]),
                d2[:, 0] if len(d2) else np.array([]),
                d2[:, 1] if len(d2) else np.array([]),
            )
        else:
            pd_data = None

        return (fvec, pd_data, None)
    except Exception as e:
        return (None, None, str(e))


def _process_field_sensitivity(args):
    """
    Worker per sensitivity check: processa un campo con due smoothing.
    Restituisce (b0_R5, b1_R5, b2_R5, b0_R10, b1_R10, b2_R10, error).
    """
    field_path, common_thresholds = args
    try:
        field_R5 = np.load(field_path).astype(np.float64)
        # field_R5 è già smoothed a R=5 Mpc/h dalla Phase 0
        # Re-smoothing a R=10: applica Gaussian aggiuntivo
        # σ_combined = sqrt(σ_R10² - σ_R5²) in pixel
        sigma_extra = np.sqrt(SIGMA_R10_PX**2 - SIGMA_R5_PX**2)
        field_R10 = scipy.ndimage.gaussian_filter(field_R5, sigma=sigma_extra)

        # Betti curves per R5
        th5 = compute_field_thresholds(field_R5, N_THRESH)
        diag5, b0_5, b1_5, b2_5 = compute_betti_curves_from_field(field_R5, th5)
        b0_5c = np.interp(common_thresholds, th5[::-1], b0_5[::-1])
        b1_5c = np.interp(common_thresholds, th5[::-1], b1_5[::-1])
        b2_5c = np.interp(common_thresholds, th5[::-1], b2_5[::-1])

        # Betti curves per R10
        th10 = compute_field_thresholds(field_R10, N_THRESH)
        diag10, b0_10, b1_10, b2_10 = compute_betti_curves_from_field(field_R10, th10)
        b0_10c = np.interp(common_thresholds, th10[::-1], b0_10[::-1])
        b1_10c = np.interp(common_thresholds, th10[::-1], b1_10[::-1])
        b2_10c = np.interp(common_thresholds, th10[::-1], b2_10[::-1])

        return (b0_5c, b1_5c, b2_5c, b0_10c, b1_10c, b2_10c, None)
    except Exception as e:
        return (None, None, None, None, None, None, str(e))


# ---------------------------------------------------------------------------
# COMMON THRESHOLD GRID
# ---------------------------------------------------------------------------

def build_common_threshold_grid(fiducial_paths: list, n_sample: int = 50) -> np.ndarray:
    """
    Costruisce la griglia comune di N_THRESH soglie come media dei percentili
    5° e 95° della variabile ν calcolati su n_sample campi fiduciali.

    Questo garantisce una griglia rappresentativa del range fisico tipico
    preservando la coerenza tra la media per-campo e la griglia comune.
    """
    log.info(f"Costruzione griglia comune da {n_sample} campi fiduciali sample...")
    lo_vals, hi_vals = [], []
    sample_paths = fiducial_paths[:n_sample]
    for fp in tqdm(sample_paths, desc="Grid sampling", leave=False):
        field = np.load(fp).astype(np.float64)
        nu = field_to_nu(field)
        lo_vals.append(np.percentile(nu, 5))
        hi_vals.append(np.percentile(nu, 95))

    lo_mean = float(np.mean(lo_vals))
    hi_mean = float(np.mean(hi_vals))
    log.info(f"Griglia comune: ν ∈ [{lo_mean:.4f}, {hi_mean:.4f}]")
    # Ordine decrescente (superlevel: alta → bassa densità)
    return np.linspace(hi_mean, lo_mean, N_THRESH)


# ---------------------------------------------------------------------------
# DATA LOADING
# ---------------------------------------------------------------------------

def load_params(params_path: Path, col_map: dict) -> dict:
    """
    Carica il file dei parametri cosmologici.
    col_map: dict {nome_param: indice_colonna}
    Restituisce dict {nome_param: array(N,)}
    """
    data = np.loadtxt(params_path, comments='#')
    result = {}
    for name, col in col_map.items():
        result[name] = data[:, col]
    log.info(f"Parametri caricati da {params_path.name}: {data.shape[0]} righe")
    return result


def list_field_paths(dataset_dir: Path, n_fields: int) -> list:
    """Lista i path dei campi in ordine: field_0000.npy ... field_{n-1:04d}.npy"""
    paths = [dataset_dir / f"field_{i:04d}.npy" for i in range(n_fields)]
    missing = [p for p in paths if not p.exists()]
    if missing:
        log.warning(f"{len(missing)} file mancanti in {dataset_dir}")
        if len(missing) > 10:
            log.warning(f"Primi 5 mancanti: {missing[:5]}")
    return paths


# ---------------------------------------------------------------------------
# SMOOTHING SENSITIVITY CHECK
# ---------------------------------------------------------------------------

def run_sensitivity_check(field_paths: list, common_thresholds: np.ndarray,
                          n_workers: int) -> dict:
    """
    Impegno Review 0 Concern 1 (CAUCHY_Review_and_GATE.md).
    Confronta Betti curves medie a R=5 Mpc/h vs R=10 Mpc/h su N_SENSITIVITY campi.

    Metrica: Δβ_k = |⟨β_k⟩_{R=10} − ⟨β_k⟩_{R=5}| / σ_{R=5}
    (media point-wise della differenza normalizzata sulla curva)
    """
    log.info(f"Sensitivity check su {N_SENSITIVITY} campi fiduciali "
             f"(R=5 vs R=10 Mpc/h)...")

    paths_sub = field_paths[:N_SENSITIVITY]
    args = [(p, common_thresholds) for p in paths_sub]

    b0_5_all, b1_5_all, b2_5_all = [], [], []
    b0_10_all, b1_10_all, b2_10_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_sensitivity, args),
                        total=len(args), desc="Sensitivity"):
            b0_5, b1_5, b2_5, b0_10, b1_10, b2_10, err = res
            if err:
                n_errors += 1
                log.warning(f"Errore sensitivity: {err}")
            else:
                b0_5_all.append(b0_5);  b1_5_all.append(b1_5);  b2_5_all.append(b2_5)
                b0_10_all.append(b0_10); b1_10_all.append(b1_10); b2_10_all.append(b2_10)

    if len(b0_5_all) == 0:
        log.error("Sensitivity check fallito: nessun campo processato correttamente.")
        return {"error": "no_fields_processed"}

    b0_5_arr  = np.array(b0_5_all);   b1_5_arr  = np.array(b1_5_all);   b2_5_arr  = np.array(b2_5_all)
    b0_10_arr = np.array(b0_10_all);  b1_10_arr = np.array(b1_10_all);  b2_10_arr = np.array(b2_10_all)

    def delta_normalized(arr5, arr10):
        """Differenza media normalizzata point-wise sulla curva."""
        mean5  = arr5.mean(axis=0)
        std5   = arr5.std(axis=0)
        mean10 = arr10.mean(axis=0)
        # Evita divisione per zero nelle regioni dove std≈0
        with np.errstate(invalid='ignore', divide='ignore'):
            ratio = np.where(std5 > 1e-10, np.abs(mean10 - mean5) / std5, 0.0)
        return float(np.mean(ratio))

    delta_b0 = delta_normalized(b0_5_arr, b0_10_arr)
    delta_b1 = delta_normalized(b1_5_arr, b1_10_arr)
    delta_b2 = delta_normalized(b2_5_arr, b2_10_arr)

    # Verdict: se Δβ_k > 1 per qualsiasi k, segnala al Reviewer
    max_delta = max(delta_b0, delta_b1, delta_b2)
    if max_delta > 1.0:
        verdict = f"WARNING: Δβ_max={max_delta:.3f} > 1σ — informare il Reviewer (Concern 1)"
    else:
        verdict = f"OK: Δβ_max={max_delta:.3f} < 1σ — smoothing scale robusto"

    log.info(f"Sensitivity: Δβ₀={delta_b0:.3f}, Δβ₁={delta_b1:.3f}, Δβ₂={delta_b2:.3f}")
    log.info(f"Verdict: {verdict}")

    return {
        "n_fields_tested":       N_SENSITIVITY,
        "n_errors":              n_errors,
        "delta_b0_normalized":   delta_b0,
        "delta_b1_normalized":   delta_b1,
        "delta_b2_normalized":   delta_b2,
        "sigma_R5_px":           SIGMA_R5_PX,
        "sigma_R10_px":          SIGMA_R10_PX,
        "verdict":               verdict,
    }


# ---------------------------------------------------------------------------
# SANITY MODE: 50 campi fiduciali
# ---------------------------------------------------------------------------

def run_sanity_mode(fiducial_paths: list, common_thresholds: np.ndarray,
                    n_workers: int) -> dict:
    """
    Processa 50 campi fiduciali → Betti curves medie + sensitivity check.
    Output parziale del JSON (senza Fisher e correlazioni).
    """
    log.info("=== MODALITÀ SANITY: 50 campi fiduciali ===")
    paths_sub = fiducial_paths[:N_SENSITIVITY]
    args = [(p, common_thresholds) for p in paths_sub]

    b0_all, b1_all, b2_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_sanity, args),
                        total=len(args), desc="Sanity TDA"):
            ct, b0, b1, b2, feats, err = res
            if err:
                n_errors += 1
                log.warning(f"Errore sanity: {err}")
            else:
                b0_all.append(b0); b1_all.append(b1); b2_all.append(b2)

    if len(b0_all) == 0:
        raise RuntimeError("Sanity check fallito: nessun campo processato.")

    b0_arr = np.array(b0_all)
    b1_arr = np.array(b1_all)
    b2_arr = np.array(b2_all)

    betti_result = {
        "n_fields":  len(b0_all),
        "n_errors":  n_errors,
        "mean_b0":   b0_arr.mean(axis=0).tolist(),
        "mean_b1":   b1_arr.mean(axis=0).tolist(),
        "mean_b2":   b2_arr.mean(axis=0).tolist(),
        "std_b0":    b0_arr.std(axis=0).tolist(),
        "std_b1":    b1_arr.std(axis=0).tolist(),
        "std_b2":    b2_arr.std(axis=0).tolist(),
        "thresholds": common_thresholds.tolist(),
    }

    log.info(f"Betti curves medie calcolate su {len(b0_all)} campi ({n_errors} errori)")
    log.info(f"β₁ picco medio: {b1_arr.mean(axis=0).max():.2f} "
             f"a ν={common_thresholds[b1_arr.mean(axis=0).argmax()]:.4f}")
    log.info(f"β₂ picco medio: {b2_arr.mean(axis=0).max():.2f} "
             f"a ν={common_thresholds[b2_arr.mean(axis=0).argmax()]:.4f}")

    return betti_result


# ---------------------------------------------------------------------------
# FULL MODE — FIDUCIAL: matrice di covarianza
# ---------------------------------------------------------------------------

def run_fiducial_covariance(fiducial_paths: list, common_thresholds: np.ndarray,
                             n_workers: int):
    """
    Processa tutti i 2000 campi fiduciali per:
    1. Betti curves medie (μ_ΛCDM)
    2. Matrice di covarianza del rumore C_noise [8×8]
    """
    log.info("=== FIDUCIAL: 2000 campi → Betti curves + C_noise ===")
    args = [(p, common_thresholds, False) for p in fiducial_paths]

    fvecs = []
    b0_all, b1_all, b2_all = [], [], []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_full, args),
                        total=len(args), desc="Fiducial"):
            fvec, pd_data, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)
                # Per Betti curves medie: ricalcolo dalla Betti curve
                # (già estratte nelle feature ma vogliamo le curve complete)

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo fiduciale processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    log.info(f"Fiducial: {len(fvecs)} campi OK ({n_errors} errori)")

    # Matrice di covarianza con fattore di Hartlap
    n_fid = len(fvecs)
    hartlap = (n_fid - N_FEAT - 2) / (n_fid - 1)
    C_noise = np.cov(fvecs.T)   # (8, 8)
    log.info(f"C_noise calcolata. Hartlap α = {hartlap:.6f}")

    return fvecs, C_noise, hartlap, n_errors


# ---------------------------------------------------------------------------
# FULL MODE — LHC: analisi Fisher (Gate 1a)
# ---------------------------------------------------------------------------

def run_lhc_fisher(lhc_paths: list, lhc_params: dict, common_thresholds: np.ndarray,
                   C_noise: np.ndarray, hartlap: float, n_workers: int) -> dict:
    """
    Gate 1a: matrice Fisher su (Ωm, σ₈) da campi LHC.

    Metodo derivate numeriche: regressione lineare locale
    su campi con |θ − θ_fid| ≤ FISHER_LOCAL_FRAC × range_θ.
    """
    log.info("=== LHC FISHER: 2000 campi → Gate 1a ===")

    # Processa tutti i campi LHC
    args = [(p, common_thresholds, False) for p in lhc_paths]
    fvecs = []
    n_errors = 0

    with mp.Pool(n_workers) as pool:
        for res in tqdm(pool.imap(_process_field_full, args),
                        total=len(args), desc="LHC Fisher"):
            fvec, _, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo LHC processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    omm_arr = lhc_params['Omega_m'][:len(fvecs)]
    s8_arr  = lhc_params['sigma_8'][:len(fvecs)]

    log.info(f"LHC: {len(fvecs)} campi OK ({n_errors} errori)")

    def numerical_derivative(feat_vals: np.ndarray, param_vals: np.ndarray,
                             fid_val: float) -> float:
        """Regressione lineare locale intorno al valore fiduciale."""
        param_range = param_vals.max() - param_vals.min()
        local_mask = np.abs(param_vals - fid_val) <= FISHER_LOCAL_FRAC * param_range
        if local_mask.sum() < 5:
            # Fallback: usa tutti i punti
            local_mask = np.ones(len(param_vals), dtype=bool)
            log.warning("Regressione locale: meno di 5 punti → uso tutti i dati")
        slope, intercept, r, p, se = scipy.stats.linregress(
            param_vals[local_mask], feat_vals[local_mask]
        )
        return float(slope)

    # Derivate ∂feature_k/∂Omega_m e ∂feature_k/∂sigma_8
    derivs_omm = np.array([
        numerical_derivative(fvecs[:, k], omm_arr, FID_OMM) for k in range(N_FEAT)
    ])
    derivs_s8 = np.array([
        numerical_derivative(fvecs[:, k], s8_arr, FID_S8) for k in range(N_FEAT)
    ])

    # Deriva anche ∂/∂w0 se disponibile (non nel LHC standard, solo documentazione)
    # Per Gate 1a σ(w0) non è threshold pass/fail — solo documentato
    # Il LHC non varia w0, quindi σ(w0) viene da nwLH (calcolato separatamente)

    # Matrice Fisher F_ij = (∂f/∂θ_i)^T × (α × C_noise^{-1}) × (∂f/∂θ_j)
    try:
        C_inv = np.linalg.inv(C_noise) * hartlap
    except np.linalg.LinAlgError:
        log.warning("C_noise singolare — uso pseudoinversa")
        C_inv = np.linalg.pinv(C_noise) * hartlap

    # Matrice delle derivate: D[k, θ] con θ ∈ {Ωm, σ8}
    D = np.column_stack([derivs_omm, derivs_s8])  # (8, 2)

    F = D.T @ C_inv @ D  # (2, 2): [Ωm, σ₈]

    try:
        F_inv = np.linalg.inv(F)
        sigma_omm = float(np.sqrt(F_inv[0, 0]))
        sigma_s8  = float(np.sqrt(F_inv[1, 1]))
        rho = float(F_inv[0, 1] / (sigma_omm * sigma_s8))
    except np.linalg.LinAlgError:
        log.error("Matrice Fisher non invertibile — gate FAIL automatico")
        sigma_omm = np.inf
        sigma_s8  = np.inf
        rho = 0.0

    # σ(w0) non calcolabile dal LHC (w0 fisso) — viene da nwLH Fisher esteso
    # Per ora placeholder; sarà aggiornato se si esegue Fisher esteso su nwLH
    sigma_w0 = None

    gate1a_pass = (sigma_omm <= GATE1A_SIGMA_OMM_MAX) and (sigma_s8 <= GATE1A_SIGMA_S8_MAX)
    gate1a_status = "PASS" if gate1a_pass else "FAIL"

    log.info(f"Fisher Gate 1a: σ(Ωm)={sigma_omm:.4f}, σ(σ₈)={sigma_s8:.4f}, "
             f"ρ(Ωm,σ₈)={rho:.3f} → {gate1a_status}")
    log.info(f"  Threshold: σ(Ωm) ≤ {GATE1A_SIGMA_OMM_MAX}, "
             f"σ(σ₈) ≤ {GATE1A_SIGMA_S8_MAX}")

    result = {
        "sigma_Omega_m":     sigma_omm,
        "sigma_sigma8":      sigma_s8,
        "sigma_w0":          sigma_w0,  # None → da aggiornare con nwLH
        "rho_Omegam_sigma8": rho,
        "hartlap_factor":    hartlap,
        "n_fields_ok":       len(fvecs),
        "n_errors":          n_errors,
        "derivatives_dOmm":  derivs_omm.tolist(),
        "derivatives_ds8":   derivs_s8.tolist(),
        "fisher_matrix":     F.tolist(),
        "gate1a_status":     gate1a_status,
    }
    return result


# ---------------------------------------------------------------------------
# FULL MODE — nwLH: correlazioni con w₀ (Gate 1b)
# ---------------------------------------------------------------------------

def run_nwlh_correlations(nwlh_paths: list, nwlh_params: dict,
                          common_thresholds: np.ndarray,
                          n_workers: int, pd_output_dir: Path) -> dict:
    """
    Gate 1b: correlazioni |r(feature_k, w₀)| su campi nwLH.
    Salva anche i diagrammi di persistenza per Phase 3 (GNN).
    """
    log.info("=== nwLH CORRELATIONS + PD SAVE: 2000 campi → Gate 1b ===")

    pd_output_dir.mkdir(parents=True, exist_ok=True)
    args = [(p, common_thresholds, True) for p in nwlh_paths]

    fvecs = []
    n_errors = 0
    n_saved_pd = 0

    with mp.Pool(n_workers) as pool:
        for i, res in enumerate(tqdm(pool.imap(_process_field_full, args),
                                      total=len(args), desc="nwLH Corr")):
            fvec, pd_data, err = res
            if err:
                n_errors += 1
            else:
                fvecs.append(fvec)
                if pd_data is not None:
                    b1_birth, b1_death, b2_birth, b2_death = pd_data
                    out_path = pd_output_dir / f"nwlh_field_{i:04d}_pd.npz"
                    np.savez_compressed(out_path,
                                        b1_birth=b1_birth, b1_death=b1_death,
                                        b2_birth=b2_birth, b2_death=b2_death)
                    n_saved_pd += 1

    if len(fvecs) == 0:
        raise RuntimeError("Nessun campo nwLH processato correttamente.")

    fvecs = np.array(fvecs)  # (N_ok, 8)
    w0_arr = nwlh_params['w0'][:len(fvecs)]

    log.info(f"nwLH: {len(fvecs)} campi OK ({n_errors} errori), {n_saved_pd} PD salvati")

    correlations = {}
    for k, name in enumerate(FEATURE_NAMES):
        r, p_val = scipy.stats.pearsonr(fvecs[:, k], w0_arr)
        correlations[name] = float(abs(r))

    max_corr = max(correlations.values())

    # Gate 1b check
    hard_pass = (
        correlations.get('b1_peak_pos', 0.0) >= GATE1B_R_MIN_HARD and
        correlations.get('b2_mean_persistence', 0.0) >= GATE1B_R_MIN_HARD
    )
    soft_pass = max_corr >= GATE1B_R_MIN_SOFT
    gate1b_pass = hard_pass and soft_pass
    gate1b_status = "PASS" if gate1b_pass else "FAIL"

    log.info("Gate 1b correlazioni |r|:")
    for name in FEATURE_NAMES:
        log.info(f"  {name}: {correlations[name]:.4f}")
    log.info(f"  max |r| = {max_corr:.4f} → Gate 1b: {gate1b_status}")

    return {
        "correlations":    correlations,
        "max_correlation": max_corr,
        "n_fields_ok":     len(fvecs),
        "n_errors":        n_errors,
        "n_pd_saved":      n_saved_pd,
        "gate1b_status":   gate1b_status,
    }


# ---------------------------------------------------------------------------
# OUTPUT JSON
# ---------------------------------------------------------------------------

def build_output_json(mode: str, tda_params: dict, sensitivity: dict,
                      betti_curves: dict, gate1a: dict, gate1b: dict) -> dict:
    """Assembla il JSON di output nel formato specificato dal prompt di sessione."""

    overall = None
    if gate1a and gate1b:
        overall = ("PASS"
                   if gate1a.get('gate1a_status') == "PASS" and
                      gate1b.get('gate1b_status') == "PASS"
                   else "FAIL")

    output = {
        "schema_version":    "2.0",
        "generated_at":      datetime.now(timezone.utc).isoformat(),
        "cauchy_version":    "v2.0",
        "gate":              "GATE_1",
        "mode":              mode,
        "tda_parameters":    tda_params,
    }

    if sensitivity:
        output["smoothing_sensitivity"] = sensitivity
    if betti_curves:
        output["fiducial_betti_curves"] = betti_curves
    if gate1a:
        output["gate1a"] = gate1a
    if gate1b:
        output["gate1b"] = gate1b
    if overall is not None:
        output["overall_gate1_status"] = overall

    return output


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="CAUCHY Phase 1 — TDA Baseline (Ramo A)"
    )
    p.add_argument(
        "--data-root", required=True, type=Path,
        help="Root del progetto dati (es. D:/projects/cauchy)"
    )
    p.add_argument(
        "--repo-root", required=True, type=Path,
        help="Root del repository (es. . o D:/projects/cauchy/repo)"
    )
    p.add_argument(
        "--mode", required=True,
        choices=["sanity", "full", "sensitivity", "resume"],
        help=(
            "sanity: 50 campi fiduciali + sensitivity (10-20 min); "
            "sensitivity: solo sensitivity check; "
            "full: tutti 6000 campi + PD (3-12 ore); "
            "resume: salta fiducial+PD gia completati, carica cache e riprende "
            "da LHC Fisher (da usare quando full ha crashato dopo i fiduciali)"
        )
    )
    p.add_argument(
        "--n-workers", type=int,
        default=min(mp.cpu_count(), 8),
        help="Numero di worker multiprocessing (default: min(cpu_count, 8))"
    )
    p.add_argument(
        "--skip-sensitivity", action="store_true",
        help="Salta il sensitivity check (solo in modalita full/resume)"
    )
    p.add_argument(
        "--lhc-params", type=Path, default=None,
        help="Path esplicito a latin_hypercube_params.txt. "
             "Se omesso, cerca in data-root/data/raw/quijote/3D_cubes/"
    )
    p.add_argument(
        "--nwlh-params", type=Path, default=None,
        help="Path esplicito a latin_hypercube_nwLH_params.txt. "
             "Se omesso, cerca in data-root/data/raw/quijote/3D_cubes/latin_hypercube_nwLH/"
    )
    return p.parse_args()


def main():
    args = parse_args()
    t_start = time.time()

    log.info(f"CAUCHY Phase 1 TDA Baseline — modalità: {args.mode.upper()}")
    log.info(f"data-root: {args.data_root}")
    log.info(f"n-workers: {args.n_workers}")
    log.info(f"gudhi version: {gudhi.__version__}")
    log.info(f"numpy version: {np.__version__}")

    # Paths
    data_root   = args.data_root
    repo_root   = args.repo_root
    fid_dir     = data_root / "data" / "processed" / "phase0_fields" / "fiducial"
    lhc_dir     = data_root / "data" / "processed" / "phase0_fields" / "lhc"
    nwlh_dir    = data_root / "data" / "processed" / "phase0_fields" / "nwlh"
    results_dir = repo_root / "results"
    results_dir.mkdir(parents=True, exist_ok=True)
    pd_dir      = results_dir / "phase1_persistence_diagrams"

    # Path default dei file parametri (con override CLI via --lhc-params / --nwlh-params)
    _lhc_default  = (data_root / "data" / "raw" / "quijote" / "3D_cubes" /
                     "latin_hypercube" / "latin_hypercube_params.txt")
    _nwlh_default = (data_root / "data" / "raw" / "quijote" / "3D_cubes" /
                     "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt")
    lhc_params_path  = args.lhc_params  if args.lhc_params  else _lhc_default
    nwlh_params_path = args.nwlh_params if args.nwlh_params else _nwlh_default

    output_json_path = results_dir / "phase1_tda_baseline.json"

    # Validazione anticipata di tutti i path critici (prima di iniziare elaborazione)
    path_errors = []
    for d, name in [(fid_dir, "fiducial"), (lhc_dir, "lhc"), (nwlh_dir, "nwlh")]:
        if not d.exists():
            log.warning(f"Directory {name} non trovata: {d}")
    if args.mode in ("full", "resume"):
        if not lhc_params_path.exists():
            path_errors.append(f"LHC params non trovato: {lhc_params_path}")
        if not nwlh_params_path.exists():
            path_errors.append(f"nwLH params non trovato: {nwlh_params_path}")
    if path_errors:
        for e in path_errors:
            log.error(e)
        log.error("Correggere i path con --lhc-params e/o --nwlh-params e riprovare.")
        sys.exit(1)
    log.info(f"LHC params:  {lhc_params_path}")
    log.info(f"nwLH params: {nwlh_params_path}")

    # File paths
    fiducial_paths = list_field_paths(fid_dir, N_FIDUCIAL_FULL)

    # TDA parameters record
    tda_params = {
        "n_thresh":           N_THRESH,
        "filtration_variable": "log(delta+1)",
        "filtration_type":    "superlevel_via_negation",
        "implementation":     "gudhi.CubicalComplex",
        "gudhi_version":      gudhi.__version__,
        "numpy_version":      np.__version__,
        "global_seed":        GLOBAL_SEED,
        "grid_size":          "128^3",
        "box_size_mpch":      BOX_SIZE_MPCH,
        "threshold_range":    "5th-95th percentile of nu per field, interpolated to common grid",
        "common_grid_method": "mean of 5th/95th percentiles over 50 fiducial fields",
    }

    # -------------------------------------------------------------------------
    # Griglia comune (necessaria per tutte le modalità)
    # -------------------------------------------------------------------------
    log.info("Costruzione griglia comune di soglie...")
    common_thresholds = build_common_threshold_grid(
        fiducial_paths, n_sample=min(50, len(fiducial_paths))
    )
    tda_params["common_thresholds_lo"] = float(common_thresholds[-1])
    tda_params["common_thresholds_hi"] = float(common_thresholds[0])

    # -------------------------------------------------------------------------
    # MODALITÀ SENSITIVITY (standalone)
    # -------------------------------------------------------------------------
    if args.mode == "sensitivity":
        sensitivity = run_sensitivity_check(fiducial_paths, common_thresholds, args.n_workers)
        output = build_output_json("sensitivity", tda_params, sensitivity, None, None, None)
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")
        return

    # -------------------------------------------------------------------------
    # MODALITÀ SANITY
    # -------------------------------------------------------------------------
    if args.mode == "sanity":
        # Betti curves su 50 campi
        betti_curves = run_sanity_mode(fiducial_paths, common_thresholds, args.n_workers)

        # Sensitivity check (impegno Review 0 Concern 1)
        sensitivity = run_sensitivity_check(fiducial_paths, common_thresholds, args.n_workers)

        output = build_output_json("sanity", tda_params, sensitivity, betti_curves, None, None)
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")

        # Stampa digest per Sessione 2
        print("\n" + "="*60)
        print("DIGEST PER SESSIONE 2 — copiare nel prompt:")
        print("="*60)
        b1_mean = np.array(betti_curves["mean_b1"])
        b2_mean = np.array(betti_curves["mean_b2"])
        thresh  = np.array(betti_curves["thresholds"])
        print(f"β₁ picco: {b1_mean.max():.2f} a ν={thresh[b1_mean.argmax()]:.4f}")
        print(f"β₂ picco: {b2_mean.max():.2f} a ν={thresh[b2_mean.argmax()]:.4f}")
        s = sensitivity
        print(f"Sensitivity: Δβ₀={s['delta_b0_normalized']:.3f}, "
              f"Δβ₁={s['delta_b1_normalized']:.3f}, "
              f"Δβ₂={s['delta_b2_normalized']:.3f}")
        print(f"Verdict: {s['verdict']}")
        print("="*60)
        return

    # -------------------------------------------------------------------------
    # MODALITÀ RESUME: riprende da LHC Fisher dopo crash nel full
    # Presuppone che results/phase1_fiducial_cache.npz esista (prodotto da full)
    # -------------------------------------------------------------------------
    if args.mode == "resume":
        cache_path = results_dir / "phase1_fiducial_cache.npz"
        if not cache_path.exists():
            log.error(f"Cache fiduciale non trovata: {cache_path}")
            log.error("Eseguire prima --mode full (o aspettare che produca la cache).")
            sys.exit(1)
        log.info(f"Caricamento cache fiduciale da {cache_path}...")
        cache = np.load(cache_path, allow_pickle=True)
        fvecs_fid   = cache["fvecs_fid"]
        betti_curves = cache["betti_curves"].item()
        sensitivity  = cache["sensitivity"].item()
        n_fid_ok = len(fvecs_fid)
        hartlap  = (n_fid_ok - N_FEAT - 2) / (n_fid_ok - 1)
        C_noise  = np.cov(fvecs_fid.T)
        log.info(f"Cache caricata: {n_fid_ok} campi fiduciali, Hartlap={hartlap:.6f}")

        lhc_params = load_params(lhc_params_path, {
            "Omega_m": LHC_COL_OMM, "sigma_8": LHC_COL_S8
        })
        lhc_paths = list_field_paths(lhc_dir, N_LHC)
        gate1a = run_lhc_fisher(
            lhc_paths, lhc_params, common_thresholds,
            C_noise, hartlap, args.n_workers
        )

        nwlh_params = load_params(nwlh_params_path, {
            "Omega_m": NWLH_COL_OMM, "sigma_8": NWLH_COL_S8, "w0": NWLH_COL_W0
        })
        nwlh_paths = list_field_paths(nwlh_dir, N_NWLH)
        gate1b = run_nwlh_correlations(
            nwlh_paths, nwlh_params, common_thresholds,
            args.n_workers, pd_dir / "nwlh"
        )

        output = build_output_json(
            "full", tda_params, sensitivity, betti_curves, gate1a, gate1b
        )
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)
        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale sessione resume: {(time.time()-t_start)/60:.1f} min")
        print("\n" + "="*60)
        print("DIGEST RESUME")
        print("="*60)
        print(f"Gate 1a: {gate1a['gate1a_status']} — "
              f"sigma(Om)={gate1a['sigma_Omega_m']:.4f}, "
              f"sigma(s8)={gate1a['sigma_sigma8']:.4f}, "
              f"rho={gate1a['rho_Omegam_sigma8']:.3f}")
        print(f"Gate 1b: {gate1b['gate1b_status']} — "
              f"max|r|={gate1b['max_correlation']:.4f}")
        print(f"Overall: {output['overall_gate1_status']}")
        print("="*60)
        return

    # -------------------------------------------------------------------------
    # MODALITÀ FULL
    # -------------------------------------------------------------------------
    if args.mode == "full":
        log.info("=== MODALITÀ FULL: tutti 6000 campi ===")

        # Stima spazio disco per i PD
        # Stimare: per campo, ~100-500 feature PH, ~2000 b1/b2 total points
        # Ogni NPZ file ≈ 5-20 KB → 2000 campi nwLH ≈ 10-40 MB
        # (molto meno di quanto temuto nel prompt di sessione)
        log.info("Stima spazio disco PD: ~10-40 MB per 2000 campi nwLH (NPZ compressi)")

        # 1) Sensitivity check (a meno di --skip-sensitivity)
        if not args.skip_sensitivity:
            sensitivity = run_sensitivity_check(
                fiducial_paths, common_thresholds, args.n_workers
            )
        else:
            sensitivity = {"skipped": True}

        # 2) Fiducial: covarianza + Betti curves
        # (run_sanity_mode usa solo 50 campi per le curve medie nel sanity;
        #  per il full, calcoliamo le curve su tutti i fiduciali per μ_ΛCDM)
        log.info("Betti curves medie su tutti i 2000 campi fiduciali (μ_ΛCDM)...")
        fid_args = [(p, common_thresholds) for p in fiducial_paths]
        b0_all, b1_all, b2_all, fvecs_fid = [], [], [], []
        n_err_fid = 0

        with mp.Pool(args.n_workers) as pool:
            for res in tqdm(pool.imap(_process_field_sanity, fid_args),
                            total=len(fid_args), desc="Fiducial full"):
                ct, b0, b1, b2, feats, err = res
                if err:
                    n_err_fid += 1
                else:
                    b0_all.append(b0); b1_all.append(b1); b2_all.append(b2)
                    fvecs_fid.append(features_to_vector(feats))

        b0_arr = np.array(b0_all); b1_arr = np.array(b1_all); b2_arr = np.array(b2_all)
        fvecs_fid = np.array(fvecs_fid)

        betti_curves = {
            "n_fields":   len(b0_all),
            "n_errors":   n_err_fid,
            "mean_b0":    b0_arr.mean(axis=0).tolist(),
            "mean_b1":    b1_arr.mean(axis=0).tolist(),
            "mean_b2":    b2_arr.mean(axis=0).tolist(),
            "std_b0":     b0_arr.std(axis=0).tolist(),
            "std_b1":     b1_arr.std(axis=0).tolist(),
            "std_b2":     b2_arr.std(axis=0).tolist(),
            "thresholds": common_thresholds.tolist(),
        }

        # Matrice di covarianza
        n_fid_ok = len(fvecs_fid)
        hartlap  = (n_fid_ok - N_FEAT - 2) / (n_fid_ok - 1)
        C_noise  = np.cov(fvecs_fid.T)
        log.info(f"C_noise [8x8] calcolata. Hartlap a = {hartlap:.6f}")

        # Salva cache fiduciale per eventuale resume dopo crash
        cache_path = results_dir / "phase1_fiducial_cache.npz"
        np.savez_compressed(cache_path,
                            fvecs_fid=fvecs_fid,
                            betti_curves=np.array(betti_curves, dtype=object),
                            sensitivity=np.array(sensitivity, dtype=object))
        log.info(f"Cache fiduciale salvata: {cache_path} — safe point raggiunto")

        # Anche PD per i fiduciali (per μ_ΛCDM in Phase 3)
        log.info("Salvataggio PD fiduciali...")
        pd_fid_dir = pd_dir / "fiducial"
        pd_fid_dir.mkdir(parents=True, exist_ok=True)
        fid_pd_args = [(p, common_thresholds, True) for p in fiducial_paths]
        with mp.Pool(args.n_workers) as pool:
            for i, res in enumerate(tqdm(pool.imap(_process_field_full, fid_pd_args),
                                          total=len(fid_pd_args), desc="Fiducial PD")):
                fvec, pd_data, err = res
                if not err and pd_data is not None:
                    b1b, b1d, b2b, b2d = pd_data
                    np.savez_compressed(
                        pd_fid_dir / f"fiducial_field_{i:04d}_pd.npz",
                        b1_birth=b1b, b1_death=b1d, b2_birth=b2b, b2_death=b2d
                    )

        # 3) LHC: Fisher Gate 1a
        lhc_params = load_params(lhc_params_path, {
            'Omega_m': LHC_COL_OMM, 'sigma_8': LHC_COL_S8
        })
        lhc_paths = list_field_paths(lhc_dir, N_LHC)
        gate1a = run_lhc_fisher(
            lhc_paths, lhc_params, common_thresholds,
            C_noise, hartlap, args.n_workers
        )

        # 4) nwLH: correlazioni Gate 1b + PD salvati
        nwlh_params = load_params(nwlh_params_path, {
            'Omega_m': NWLH_COL_OMM, 'sigma_8': NWLH_COL_S8, 'w0': NWLH_COL_W0
        })
        nwlh_paths = list_field_paths(nwlh_dir, N_NWLH)
        gate1b = run_nwlh_correlations(
            nwlh_paths, nwlh_params, common_thresholds,
            args.n_workers, pd_dir / "nwlh"
        )

        # Assembla output
        output = build_output_json(
            "full", tda_params, sensitivity, betti_curves, gate1a, gate1b
        )
        with open(output_json_path, "w") as f:
            json.dump(output, f, indent=2)

        log.info(f"Output salvato: {output_json_path}")
        log.info(f"Tempo totale: {(time.time()-t_start)/60:.1f} min")

        # Digest finale
        print("\n" + "="*60)
        print("DIGEST FINALE FULL RUN")
        print("="*60)
        print(f"Gate 1a: {gate1a['gate1a_status']} — "
              f"σ(Ωm)={gate1a['sigma_Omega_m']:.4f}, "
              f"σ(σ₈)={gate1a['sigma_sigma8']:.4f}, "
              f"ρ={gate1a['rho_Omegam_sigma8']:.3f}")
        print(f"Gate 1b: {gate1b['gate1b_status']} — "
              f"max|r|={gate1b['max_correlation']:.4f}")
        print(f"Overall: {output['overall_gate1_status']}")
        print("="*60)


if __name__ == "__main__":
    # Su Windows, multiprocessing richiede il guard if __name__ == '__main__'
    mp.freeze_support()
    main()
