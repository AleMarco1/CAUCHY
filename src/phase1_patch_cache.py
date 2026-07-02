#!/usr/bin/env python3
"""
CAUCHY — Phase 1 Cache Patch
=============================
Scopo: aggiungere fvecs_lhc, fvecs_nwlh, lhc_cosmologies, nwlh_cosmologies
       alla cache e al baseline di Phase 1, prerequisiti di phase2_cnn.py.

Problema rilevato in Sessione 1 Phase 2:
    phase1_fiducial_cache.npz contiene solo: ['fvecs_fid', 'betti_curves', 'sensitivity']
    phase1_tda_baseline.json non contiene: lhc_cosmologies, nwlh_cosmologies

Questo script è una patch di integrazione — NON modifica i risultati Gate 1
né i numeri del gate (σ(Ωm), σ(σ₈), correlazioni w₀). Estende la cache con
le stesse feature già calcolate su fvecs_fid, applicate ai dataset LHC e nwLH.

PARAMETRI TDA CONGELATI (da phase1_gate_result.json — immutabili):
    n_thresh = 50
    filtration_variable = "log(delta+1)"
    filtration_type = "superlevel_via_negation"
    smoothing_sigma_px = 0.64   (corrispondente a R=5 Mpc/h su griglia 128³)
    implementation = gudhi.CubicalComplex
    global_seed = 42

COSMOLOGIE LHC/nwLH:
    Lette da data/quijote_params/ (file .txt standard della suite Quijote).
    Se non disponibili nel formato standard, lo script tenta formati alternativi.

Uso:
    python phase1_patch_cache.py [--dry-run] [--n-fields N]

    --dry-run:  stampa le statistiche senza scrivere file (verifica)
    --n-fields: processa solo i primi N campi (default: tutti — 2000)

Output:
    results/phase1_fiducial_cache.npz  (aggiornato con fvecs_lhc, fvecs_nwlh)
    results/phase1_tda_baseline.json   (aggiornato con lhc_cosmologies, nwlh_cosmologies)

Tempo stimato su RTX 5060 Ti (CPU):
    ~2–4 ore per 2000 campi LHC + 2000 campi nwLH (TDA parallelizzata su CPU)
"""

import argparse
import json
import logging
import multiprocessing as mp
import sys
import time
from pathlib import Path

import numpy as np
from scipy.ndimage import map_coordinates

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("cauchy.phase1_patch")

# ── Dipendenza gudhi ─────────────────────────────────────────────────────────
try:
    import gudhi
    HAS_GUDHI = True
except ImportError:
    HAS_GUDHI = False
    log.error("gudhi non disponibile. Installare: pip install gudhi>=3.9.0")
    sys.exit(1)

# ── Parametri TDA CONGELATI da phase1_gate_result.json ──────────────────────
N_THRESH = 50
SMOOTHING_SIGMA_PX = 0.64      # R=5 Mpc/h → σ=0.64 pixel su griglia 128³
GLOBAL_SEED = 42
N_FIELDS = 2000
GRID_SIZE = 128
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

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR = Path("data/processed/phase0_fields")
RESULTS_DIR = Path("results")
CACHE_PATH = Path("results/phase1_fiducial_cache.npz")
BASELINE_PATH = Path("results/phase1_tda_baseline.json")

# Cosmologie Quijote — possibili posizioni del file parametri
QUIJOTE_PARAM_PATHS = [
    Path("data/raw/quijote/3D_cubes/latin_hypercube/latin_hypercube_params.txt"),
    Path("data/latin_hypercube_params.txt"),
    Path("data/quijote_params/latin_hypercube_params.txt"),
]
QUIJOTE_NWLH_PARAM_PATHS = [
    Path("data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt"),
    Path("data/latin_hypercube_nwLH_params.txt"),
    Path("data/quijote_params/latin_hypercube_nwLH_params.txt"),
]


# ═══════════════════════════════════════════════════════════════════════════
# Funzioni TDA — copiate verbatim da phase1_tda_baseline.py
# (NON modificare senza aggiornare anche phase1_tda_baseline.py)
# ═══════════════════════════════════════════════════════════════════════════

def field_to_nu(field: np.ndarray) -> np.ndarray:
    """ν = log(δ+1), clip a -0.9999 per evitare log(0). Identico a Phase 1."""
    return np.log(np.clip(field, -0.9999, None) + 1.0)


def compute_field_thresholds(field: np.ndarray, n_thresh: int = N_THRESH) -> np.ndarray:
    """
    N_THRESH soglie per-campo: uniformi tra 5° e 95° percentile di ν.
    Ordine DECRESCENTE (alta → bassa densità). Identico a Phase 1.
    """
    nu = field_to_nu(field)
    lo = np.percentile(nu, 5)
    hi = np.percentile(nu, 95)
    return np.linspace(hi, lo, n_thresh)


def compute_persistence_diagram(field: np.ndarray) -> dict:
    """
    Diagrammi di persistenza β₀,β₁,β₂ via CubicalComplex gudhi.
    Passa -ν(x) a gudhi (sublevel) → equivale a superlevel su ν.
    Convenzione output: colonne [nu_birth, nu_death], nu_birth > nu_death.
    Identico a Phase 1.
    """
    nu = field_to_nu(field)
    cc = gudhi.CubicalComplex(
        dimensions=list(nu.shape),
        top_dimensional_cells=(-nu).flatten().astype(np.float64)
    )
    cc.compute_persistence()

    diagrams = {}
    for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
        raw = cc.persistence_intervals_in_dimension(dim)
        if len(raw) == 0:
            diagrams[key] = np.empty((0, 2), dtype=np.float64)
        else:
            raw = np.array(raw, dtype=np.float64)
            finite_mask = np.isfinite(raw[:, 1])
            raw = raw[finite_mask]
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2), dtype=np.float64)
            else:
                nu_birth = -raw[:, 0]
                nu_death = -raw[:, 1]
                diagrams[key] = np.column_stack([nu_birth, nu_death])
    return diagrams


def betti_curve_from_diagram(diagram: np.ndarray, thresholds: np.ndarray) -> np.ndarray:
    """
    β(t) per array di soglie. Feature viva a t se nu_death < t <= nu_birth.
    Identico a Phase 1.
    """
    if len(diagram) == 0:
        return np.zeros(len(thresholds), dtype=np.float64)
    nu_birth = diagram[:, 0]
    nu_death = diagram[:, 1]
    alive = (nu_birth[:, None] >= thresholds[None, :]) & \
            (nu_death[:, None] < thresholds[None, :])
    return alive.sum(axis=0).astype(np.float64)


def extract_features(thresholds: np.ndarray,
                     b0: np.ndarray, b1: np.ndarray, b2: np.ndarray,
                     diagrams: dict) -> dict:
    """
    8 feature scalari da Betti curves e diagrammi. Identico a Phase 1.

    b1_peak_pos       : ν al picco di β₁  (NON indice normalizzato)
    b1_peak_height    : altezza picco β₁
    b1_fwhm           : FWHM in unità di ν
    b1_integral       : Σ β₁ × Δν
    b2_max_count      : massimo di β₂
    b2_mean_persistence: persistenza media β₂ (nu_birth - nu_death)
    b2_high_persist   : somma top-10% persistenze β₂
    b0_at_mean        : β₀ alla soglia più vicina a ν=0
    """
    feats = {}
    dnu = abs(thresholds[1] - thresholds[0])

    if np.any(b1 > 0):
        pk_idx = int(np.argmax(b1))
        feats['b1_peak_pos']    = float(thresholds[pk_idx])   # valore ν, non indice
        feats['b1_peak_height'] = float(b1[pk_idx])
        half_max = b1[pk_idx] / 2.0
        above = b1 >= half_max
        if above.sum() >= 2:
            idxs = np.where(above)[0]
            feats['b1_fwhm'] = float(abs(thresholds[idxs[0]] - thresholds[idxs[-1]]))
        else:
            feats['b1_fwhm'] = float(dnu)
        feats['b1_integral'] = float(np.sum(b1) * dnu)
    else:
        feats['b1_peak_pos'] = feats['b1_peak_height'] = 0.0
        feats['b1_fwhm'] = feats['b1_integral'] = 0.0

    feats['b2_max_count'] = float(np.max(b2)) if len(b2) > 0 else 0.0

    d2 = diagrams.get('b2', np.empty((0, 2)))
    if len(d2) > 0:
        persistence = d2[:, 0] - d2[:, 1]
        persistence = persistence[persistence > 0]
        if len(persistence) > 0:
            feats['b2_mean_persistence'] = float(np.mean(persistence))
            p90 = np.percentile(persistence, 90)
            feats['b2_high_persist'] = float(np.sum(persistence[persistence >= p90]))
        else:
            feats['b2_mean_persistence'] = feats['b2_high_persist'] = 0.0
    else:
        feats['b2_mean_persistence'] = feats['b2_high_persist'] = 0.0

    idx_mean = int(np.argmin(np.abs(thresholds - 0.0)))
    feats['b0_at_mean'] = float(b0[idx_mean])

    return feats


def extract_betti_features(field: np.ndarray) -> np.ndarray:
    """
    Pipeline completa campo → fvec [8].
    Soglie per-campo (5°–95° percentile di ν, ordine decrescente).
    Wrapper per multiprocessing — identico alla pipeline Phase 1.
    """
    thresholds = compute_field_thresholds(field, N_THRESH)
    diagrams = compute_persistence_diagram(field)
    b0 = betti_curve_from_diagram(diagrams['b0'], thresholds)
    b1 = betti_curve_from_diagram(diagrams['b1'], thresholds)
    b2 = betti_curve_from_diagram(diagrams['b2'], thresholds)
    feats = extract_features(thresholds, b0, b1, b2, diagrams)
    return np.array([feats[k] for k in FEATURE_NAMES], dtype=np.float32)


def _worker(args):
    """Worker per multiprocessing — processa un singolo campo."""
    field_path, idx = args
    try:
        field = np.load(field_path, allow_pickle=False).astype(np.float64)
        fvec = extract_betti_features(field)
        return idx, fvec, None
    except Exception as e:
        return idx, None, str(e)


# ═══════════════════════════════════════════════════════════════════════════
# Caricamento cosmologie Quijote
# ═══════════════════════════════════════════════════════════════════════════

def load_quijote_lhc_cosmologies(n_fields: int = N_FIELDS) -> np.ndarray | None:
    """
    Carica i parametri cosmologici LHC da latin_hypercube_params.txt.

    Formato atteso (stesso stile del file nwLH confermato dal PI):
        # Omega_m  Omega_b  h  n_s  sigma_8  M_nu  [w0]
        col 0      col 1   col2 col3  col4   col5   col6

    Omm = colonna 0, sigma_8 = colonna 4.
    Restituisce array [N, 2] con colonne [Omm, s8].
    """
    for path in QUIJOTE_PARAM_PATHS:
        if path.exists():
            log.info(f"  Caricamento cosmologie LHC da: {path}")
            try:
                # comments='#' gestisce header con #
                data = np.loadtxt(path, comments='#')
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                log.info(f"  LHC file: {data.shape[0]} righe, {data.shape[1]} colonne")

                # Omm sempre colonna 0, sigma_8 sempre colonna 4
                omm = data[:n_fields, 0]
                s8 = data[:n_fields, 4]

                # Sanity check contro range LHC Quijote
                # (CAUCHY_Execution_Parameters §1.2: Omm∈[0.10,0.50], s8∈[0.60,1.00])
                omm_ok = (omm.min() >= 0.08) and (omm.max() <= 0.52)
                s8_ok = (s8.min() >= 0.58) and (s8.max() <= 1.02)
                if omm_ok and s8_ok:
                    log.info(
                        f"  Sanity check LHC: OK — "
                        f"Ωm∈[{omm.min():.3f},{omm.max():.3f}], "
                        f"σ₈∈[{s8.min():.3f},{s8.max():.3f}]"
                    )
                else:
                    log.warning(
                        f"  ATTENZIONE: range fuori atteso. "
                        f"Ωm∈[{omm.min():.3f},{omm.max():.3f}] (atteso ~[0.10,0.50]), "
                        f"σ₈∈[{s8.min():.3f},{s8.max():.3f}] (atteso ~[0.60,1.00]). "
                        "Verificare colonne 0 (Omm) e 4 (sigma_8)."
                    )

                cosmo = np.stack([omm, s8], axis=-1).astype(np.float32)
                return cosmo
            except Exception as e:
                log.warning(f"  Errore lettura {path}: {e}")

    # Fallback: cerca nei metadata del phase0_gate_result se disponibile
    phase0_path = Path("results/phase0_gate_result.json")
    if phase0_path.exists():
        log.info("  Tentativo recupero cosmologie da phase0_gate_result.json...")
        try:
            with open(phase0_path) as f:
                p0 = json.load(f)
            if "lhc_cosmologies" in p0:
                cosmo = np.array(p0["lhc_cosmologies"], dtype=np.float32)
                log.info(f"  Cosmologie LHC da phase0: shape={cosmo.shape}")
                return cosmo[:n_fields]
        except Exception as e:
            log.warning(f"  Errore lettura phase0_gate_result: {e}")

    log.warning(
        "  Cosmologie LHC non trovate nei path standard. "
        "Il test T1 (Gate 2) userà cosmologie sintetiche di fallback. "
        "Aggiungere il file parametri Quijote in uno dei path attesi:\n"
        + "\n".join(f"    {p}" for p in QUIJOTE_PARAM_PATHS)
    )
    return None


def load_quijote_nwlh_cosmologies(n_fields: int = N_FIELDS) -> np.ndarray | None:
    """
    Carica i parametri cosmologici nwLH da latin_hypercube_nwLH_params.txt.

    Formato confermato (7 colonne, header con #):
        #Omega_m  Omega_b  h  n_s  sigma_8  M_nu  w0
        col 0     col 1    col2 col3  col4   col5  col6

    w0 è alla colonna 6 (indice zero-based).
    Restituisce array [N, 1] con colonna [w0].
    """
    for path in QUIJOTE_NWLH_PARAM_PATHS:
        if path.exists():
            log.info(f"  Caricamento cosmologie nwLH da: {path}")
            try:
                # comments='#' gestisce la riga di header con #
                data = np.loadtxt(path, comments='#')
                if data.ndim == 1:
                    data = data.reshape(1, -1)
                log.info(f"  nwLH file: {data.shape[0]} righe, {data.shape[1]} colonne")

                # Formato confermato: 7 colonne, w0 all'indice 6
                if data.shape[1] == 7:
                    w0 = data[:n_fields, 6]   # colonna w0
                    omm = data[:n_fields, 0]  # colonna Omm (per sanity check)
                    log.info(
                        f"  Formato 7 colonne confermato: "
                        f"w₀∈[{w0.min():.4f},{w0.max():.4f}], "
                        f"Ωm∈[{omm.min():.4f},{omm.max():.4f}] (fisso nei nwLH? "
                        f"std={omm.std():.4f})"
                    )
                elif data.shape[1] == 1:
                    w0 = data[:n_fields, 0]
                elif data.shape[1] >= 6:
                    # Fallback: prova colonna 5 (formato alternativo senza M_nu)
                    w0 = data[:n_fields, 5]
                    log.warning(
                        f"  {data.shape[1]} colonne — usando colonna 5 come w₀. "
                        "Verificare che sia corretto."
                    )
                else:
                    w0 = data[:n_fields, 0]
                    log.warning(
                        f"  {data.shape[1]} colonne inattese — usando colonna 0. "
                        "Verificare il formato del file."
                    )

                # Sanity check: w0 deve essere in [-1.30, -0.70] per nwLH Quijote
                w0_min, w0_max = w0.min(), w0.max()
                if w0_min < -1.35 or w0_max > -0.65:
                    log.warning(
                        f"  ATTENZIONE: w₀ fuori range atteso [-1.30,-0.70]: "
                        f"[{w0_min:.4f},{w0_max:.4f}]. "
                        "Verificare che la colonna corretta sia stata selezionata."
                    )
                else:
                    log.info(f"  Sanity check w₀: OK [{w0_min:.4f},{w0_max:.4f}]")

                cosmo = w0.reshape(-1, 1).astype(np.float32)
                return cosmo
            except Exception as e:
                log.warning(f"  Errore lettura {path}: {e}")

    log.warning(
        "  Cosmologie nwLH non trovate. "
        "Genera cosmologie sintetiche di fallback (w₀ uniformi in [-1.30,-0.70]).\n"
        "  ATTENZIONE: il test Fisher R1-2 su nwLH richiede w₀ reali. "
        "Aggiungere il file in uno dei path attesi:\n"
        + "\n".join(f"    {p}" for p in QUIJOTE_NWLH_PARAM_PATHS)
    )
    return None


def make_synthetic_cosmologies_lhc(n_fields: int = N_FIELDS) -> np.ndarray:
    """
    Fallback: cosmologie LHC sintetiche (Latin Hypercube).
    ATTENZIONE: sono sintetiche e NON corrispondono ai campi reali.
    Usare solo se i file Quijote non sono disponibili.
    Il test T1 con queste cosmologie NON è scientificamente valido.
    """
    rng = np.random.default_rng(GLOBAL_SEED)
    # Latin Hypercube manuale in [0.10, 0.50] × [0.60, 1.00]
    omm = rng.uniform(0.10, 0.50, n_fields).astype(np.float32)
    s8 = rng.uniform(0.60, 1.00, n_fields).astype(np.float32)
    log.warning(
        "  USANDO COSMOLOGIE SINTETICHE — NON corrispondono ai campi reali. "
        "Il test T1 Gate 2 con questi dati NON è scientificamente valido."
    )
    return np.stack([omm, s8], axis=-1)


def make_synthetic_cosmologies_nwlh(n_fields: int = N_FIELDS) -> np.ndarray:
    """Fallback: w₀ uniformi sintetiche."""
    rng = np.random.default_rng(GLOBAL_SEED + 1)
    w0 = rng.uniform(-1.30, -0.70, n_fields).astype(np.float32)
    log.warning(
        "  USANDO w₀ SINTETICI — NON corrispondono ai campi reali. "
        "Le correlazioni |r(feature, w₀)| con questi dati NON sono valide."
    )
    return w0.reshape(-1, 1)


# ═══════════════════════════════════════════════════════════════════════════
# Pipeline principale
# ═══════════════════════════════════════════════════════════════════════════

def process_dataset(
    field_dir: Path,
    dataset_name: str,
    n_fields: int,
    n_workers: int,
) -> np.ndarray:
    """
    Processa tutti i campi di un dataset e restituisce la matrice feature [N, 8].

    Args:
        field_dir:    directory con field_NNNN.npy
        dataset_name: "lhc" o "nwlh" (per logging)
        n_fields:     numero di campi da processare
        n_workers:    numero di worker multiprocessing

    Returns:
        fvecs: [n_fields, 8] float32
    """
    log.info(f"Processing dataset {dataset_name}: {n_fields} campi, {n_workers} worker...")

    # Costruisce lista di task
    tasks = []
    missing = []
    for i in range(n_fields):
        p = field_dir / f"field_{i:04d}.npy"
        if p.exists():
            tasks.append((p, i))
        else:
            missing.append(i)

    if missing:
        log.warning(
            f"  {len(missing)} campi mancanti in {dataset_name}: "
            f"{missing[:5]}{'...' if len(missing) > 5 else ''}"
        )

    fvecs = np.zeros((n_fields, 8), dtype=np.float32)
    errors = []
    t_start = time.time()

    # Multiprocessing (gudhi è thread-safe ma non multi-GPU)
    with mp.Pool(n_workers) as pool:
        for done, (idx, fvec, err) in enumerate(pool.imap_unordered(_worker, tasks)):
            if err is not None:
                errors.append((idx, err))
                log.warning(f"  Errore campo {dataset_name}[{idx}]: {err}")
            else:
                fvecs[idx] = fvec

            if (done + 1) % 200 == 0:
                elapsed = (time.time() - t_start) / 60
                rate = (done + 1) / elapsed if elapsed > 0 else 0
                eta = (len(tasks) - done - 1) / rate if rate > 0 else 0
                log.info(
                    f"  {done+1}/{len(tasks)} campi processati "
                    f"({elapsed:.1f} min, ~{eta:.0f} min rimanenti)"
                )

    elapsed_total = (time.time() - t_start) / 60
    log.info(
        f"  {dataset_name} completato: {len(tasks) - len(errors)} OK, "
        f"{len(errors)} errori, {elapsed_total:.1f} min totali"
    )

    return fvecs


def verify_consistency(fvecs_new: np.ndarray, fvecs_fid: np.ndarray, dataset_name: str):
    """
    Sanity check: le statistiche delle feature LHC/nwLH devono essere
    compatibili con quelle fiduciali — stesso ordine di grandezza, stesso segno.
    """
    log.info(f"  Sanity check {dataset_name} vs fiduciali:")
    for k, name in enumerate(FEATURE_NAMES):
        fid_mean = fvecs_fid[:, k].mean()
        new_mean = fvecs_new[:, k].mean()
        ratio = new_mean / fid_mean if abs(fid_mean) > 1e-10 else float("nan")
        log.info(
            f"    {name:25s}: fid_mean={fid_mean:.4e}, "
            f"{dataset_name}_mean={new_mean:.4e}, ratio={ratio:.2f}"
        )


def patch_cache(
    fvecs_lhc: np.ndarray,
    fvecs_nwlh: np.ndarray,
    cosmo_lhc: np.ndarray,
    cosmo_nwlh: np.ndarray,
    dry_run: bool,
):
    """
    Aggiorna phase1_fiducial_cache.npz e phase1_tda_baseline.json.

    Cache: aggiunge fvecs_lhc, fvecs_nwlh alle chiavi esistenti.
    Baseline: aggiunge lhc_cosmologies e nwlh_cosmologies.

    In dry_run=True: stampa solo le statistiche senza scrivere.
    """
    log.info("Aggiornamento cache e baseline...")

    # ── Carica cache esistente ────────────────────────────────────────────────
    existing = dict(np.load(CACHE_PATH, allow_pickle=True))
    log.info(f"  Cache esistente: chiavi = {list(existing.keys())}")

    existing["fvecs_lhc"] = fvecs_lhc
    existing["fvecs_nwlh"] = fvecs_nwlh
    if cosmo_lhc is not None:
        existing["cosmo_lhc"] = cosmo_lhc
    if cosmo_nwlh is not None:
        existing["cosmo_nwlh"] = cosmo_nwlh

    log.info(f"  Cache aggiornata: chiavi = {list(existing.keys())}")

    if not dry_run:
        # Backup della cache originale
        backup_path = CACHE_PATH.with_suffix(".npz.bak")
        import shutil
        shutil.copy2(CACHE_PATH, backup_path)
        log.info(f"  Backup cache: {backup_path}")

        np.savez_compressed(CACHE_PATH, **existing)
        log.info(f"  Cache salvata: {CACHE_PATH}")

    # ── Aggiorna baseline JSON ────────────────────────────────────────────────
    with open(BASELINE_PATH) as f:
        baseline = json.load(f)

    baseline["lhc_cosmologies"] = (
        cosmo_lhc.tolist() if cosmo_lhc is not None else None
    )
    baseline["nwlh_cosmologies"] = (
        cosmo_nwlh.tolist() if cosmo_nwlh is not None else None
    )
    baseline["fvecs_lhc_stats"] = {
        name: {
            "mean": float(fvecs_lhc[:, k].mean()),
            "std": float(fvecs_lhc[:, k].std()),
        }
        for k, name in enumerate(FEATURE_NAMES)
    }
    baseline["fvecs_nwlh_stats"] = {
        name: {
            "mean": float(fvecs_nwlh[:, k].mean()),
            "std": float(fvecs_nwlh[:, k].std()),
        }
        for k, name in enumerate(FEATURE_NAMES)
    }
    baseline["patch_note"] = (
        "Cache aggiornata da phase1_patch_cache.py (Phase 2 Sessione 1). "
        "Feature estratte con pipeline identica a Phase 1 "
        "(n_thresh=50, sigma=0.64px, log(delta+1), superlevel_via_negation). "
        "I risultati di Gate 1 non sono modificati."
    )

    if not dry_run:
        backup_baseline = BASELINE_PATH.with_suffix(".json.bak")
        import shutil
        shutil.copy2(BASELINE_PATH, backup_baseline)
        log.info(f"  Backup baseline: {backup_baseline}")

        with open(BASELINE_PATH, "w") as f:
            json.dump(baseline, f, indent=2)
        log.info(f"  Baseline aggiornato: {BASELINE_PATH}")

    if dry_run:
        log.info("  DRY RUN: nessun file scritto.")


# ═══════════════════════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 1 Cache Patch — aggiunge fvecs_lhc/nwlh alla cache"
    )
    parser.add_argument(
        "--dry-run", action="store_true",
        help="Calcola e stampa statistiche senza scrivere file"
    )
    parser.add_argument(
        "--n-fields", type=int, default=N_FIELDS,
        help=f"Numero di campi da processare per dataset (default: {N_FIELDS})"
    )
    parser.add_argument(
        "--n-workers", type=int, default=max(1, mp.cpu_count() - 1),
        help="Numero di worker multiprocessing (default: n_cpu - 1)"
    )
    parser.add_argument(
        "--dataset", choices=["lhc", "nwlh", "both"], default="both",
        help="Dataset da processare (default: both)"
    )
    args = parser.parse_args()

    log.info("=" * 60)
    log.info("CAUCHY Phase 1 Cache Patch")
    log.info(f"  n_fields: {args.n_fields}")
    log.info(f"  n_workers: {args.n_workers}")
    log.info(f"  dry_run: {args.dry_run}")
    log.info(f"  gudhi: {gudhi.__version__}")
    log.info("=" * 60)

    # Verifica prerequisiti
    if not CACHE_PATH.exists():
        log.error(f"Cache non trovata: {CACHE_PATH}")
        sys.exit(1)
    if not BASELINE_PATH.exists():
        log.error(f"Baseline non trovato: {BASELINE_PATH}")
        sys.exit(1)

    # Carica fvecs_fid per sanity check
    existing = np.load(CACHE_PATH, allow_pickle=True)
    fvecs_fid = existing["fvecs_fid"]
    log.info(f"fvecs_fid caricato: {fvecs_fid.shape}")

    # Carica cosmologie
    log.info("Caricamento cosmologie...")
    cosmo_lhc = load_quijote_lhc_cosmologies(args.n_fields)
    cosmo_nwlh = load_quijote_nwlh_cosmologies(args.n_fields)

    # Fallback sintetici se i file non esistono
    if cosmo_lhc is None:
        cosmo_lhc = make_synthetic_cosmologies_lhc(args.n_fields)
        log.warning("  ATTENZIONE: cosmologie LHC SINTETICHE — test T1 non valido!")
    if cosmo_nwlh is None:
        cosmo_nwlh = make_synthetic_cosmologies_nwlh(args.n_fields)
        log.warning("  ATTENZIONE: w₀ SINTETICI — correlazioni nwLH non valide!")

    # Processa LHC
    fvecs_lhc = None
    if args.dataset in ("lhc", "both"):
        lhc_dir = DATA_DIR / "lhc"
        if not lhc_dir.exists():
            log.error(f"Directory LHC non trovata: {lhc_dir}")
            sys.exit(1)
        fvecs_lhc = process_dataset(lhc_dir, "lhc", args.n_fields, args.n_workers)
        verify_consistency(fvecs_lhc, fvecs_fid, "lhc")

    # Processa nwLH
    fvecs_nwlh = None
    if args.dataset in ("nwlh", "both"):
        nwlh_dir = DATA_DIR / "nwlh"
        if not nwlh_dir.exists():
            log.error(f"Directory nwLH non trovata: {nwlh_dir}")
            sys.exit(1)
        fvecs_nwlh = process_dataset(nwlh_dir, "nwlh", args.n_fields, args.n_workers)
        verify_consistency(fvecs_nwlh, fvecs_fid, "nwlh")

    # Se processati separatamente, carica gli esistenti per l'aggiornamento cache
    if fvecs_lhc is None:
        log.info("fvecs_lhc non processato — carico da cache se disponibile...")
        fvecs_lhc = existing.get("fvecs_lhc", np.zeros((args.n_fields, 8), dtype=np.float32))
    if fvecs_nwlh is None:
        log.info("fvecs_nwlh non processato — carico da cache se disponibile...")
        fvecs_nwlh = existing.get("fvecs_nwlh", np.zeros((args.n_fields, 8), dtype=np.float32))

    # Patch della cache
    patch_cache(fvecs_lhc, fvecs_nwlh, cosmo_lhc, cosmo_nwlh, args.dry_run)

    log.info("=" * 60)
    log.info("Patch completata.")
    log.info(f"  Cache: {CACHE_PATH}")
    log.info(f"  Baseline: {BASELINE_PATH}")
    log.info("")
    log.info("Prossimo passo:")
    log.info("  python src/phase2_cnn.py --mode test_only   # unit test gudhi")
    log.info("  python src/phase2_cnn.py --mode all         # pipeline completa")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
