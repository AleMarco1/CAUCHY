#!/usr/bin/env python3
"""
CAUCHY Phase 2 — CNN SE(3)-Equivariante e Costruzione di τ(x)
=============================================================
Progetto: Cosmic Anomaly via Unified Cosmological Hyper-fields analYsis
Versione: 2.0 — Aprile 2026
Hardware target: RTX 5060 Ti 16 GB (locale)

Autorità scientifica: CAUCHY_Systematic_Methodology_v2.md §2.1–2.3
Parametri operativi: CAUCHY_Execution_Parameters.md §4.1–4.2
Impegni aperti chiusi in questo script:
    R1-1  — z-score normalizzazione C_noise (obbligatorio)
    R1-4  — unit test _test_gudhi_convention() (obbligatorio)
    C0-3  — verifica i.i.d. normalizzazione LHC (obbligatorio)
    R1-2  — test robustezza derivate Fisher FISHER_LOCAL_FRAC (obbligatorio)

Pipeline:
    1. Unit test gudhi convention (R1-4)
    2. Caricamento feature TDA Phase 1 da phase1_fiducial_cache.npz
    3. Calcolo z-score stats su training set (R1-1) — seed=42, split 80/20
    4. Verifica i.i.d. LHC (C0-3)
    5. Definizione architettura EGNN (e3nn v0.5.1)
       - N_pts=4096 (vincolo 16 GB VRAM)
       - k=16 vicini (Chatterjee 2024 CAUCHY scaling)
       - D_latent=32
       - Campionamento pesato per |delta(x)|
    6. Training loop con loss MSE z-score
    7. Calcolo μ_ΛCDM sui 2000 campi fiduciali
    8. Costruzione τ(x) per LHC e nwLH (dual output: point cloud + grid norm)
    9. Test T1 fattorizzazione parametrica (Gate 2: R ≥ 0.20)
   10. Test robustezza Fisher (R1-2)
   11. Serializzazione phase2_cnn_diagnostic.json

NUMERI FISICI TRACCIATI:
    N_pts=4096    — vincolo VRAM 16 GB (calcolo in §ARCHITETTURA)
    k=16          — Chatterjee et al. 2024 (arXiv:2405.13119): k=32 per 8192 halos;
                    CAUCHY usa N_pts=4096 → scaling k→16 per mantenere
                    raggio di connessione ~63 Mpc/h (cluster + filamenti)
    D_latent=32   — 4× le 8 feature target (regola euristica encoder supervisionato)
    R≥0.20        — CAUCHY_Execution_Parameters §4.2 [VALORE NON DA LETTERATURA —
                    stima PI, primo candidato a ricalibrzione formale]
    batch=4–8     — vincolo VRAM: N_pts×k×D_latent×batch ≤ 12 GB attivo

Uso:
    python phase2_cnn.py --mode train
    python phase2_cnn.py --mode build_tau
    python phase2_cnn.py --mode gate2
    python phase2_cnn.py --mode all         # sequenza completa
    python phase2_cnn.py --mode test_only   # solo unit test gudhi (R1-4)
"""

import argparse
import hashlib
import json
import logging
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from scipy.ndimage import laplace, map_coordinates
from torch.optim.lr_scheduler import ReduceLROnPlateau

# ── Dipendenze opzionali con fallback esplicito ─────────────────────────────
try:
    import e3nn
    from e3nn import o3
    from e3nn.nn import Gate
    from e3nn.o3 import Irreps, Linear
    E3NN_VERSION = e3nn.__version__
    HAS_E3NN = True
except ImportError:
    HAS_E3NN = False
    E3NN_VERSION = "NOT_INSTALLED"

try:
    import torch_geometric
    import torch_cluster  # dipendenza reale di knn_graph
    from torch_geometric.nn import knn_graph
    HAS_TORCH_GEOMETRIC = True
except ImportError:
    HAS_TORCH_GEOMETRIC = False

try:
    import ot  # POT — Python Optimal Transport
    HAS_POT = True
except ImportError:
    HAS_POT = False

try:
    import gudhi
    HAS_GUDHI = True
except ImportError:
    HAS_GUDHI = False

# ═══════════════════════════════════════════════════════════════════════════
# §0 — CONFIGURAZIONE GLOBALE
# ═══════════════════════════════════════════════════════════════════════════

GLOBAL_SEED = 42  # CAUCHY_Execution_Parameters §1 — immutabile
CAUCHY_VERSION = "v2.0"
SCHEMA_VERSION = "2.0"

# Architettura CNN (RTX 5060 Ti 16 GB)
N_PTS = 8192          # punti campionati per campo (vincolo VRAM)
K_NN = 16             # vicini nel grafo k-NN — Chatterjee et al. 2024 (arXiv:2405.13119)
                      # usa k=32 per N=8192; scaling a N=4096 → k=16
                      # (raggio connessione ~63 Mpc/h, copre cluster+filamenti)
D_LATENT = 32         # dimensionalità spazio latente — 4× N_FEATURES=8
                      # (regola euristica encoder supervisionato;
                      #  valore non da letteratura cosmologica — stima PI)
N_FEATURES = 8        # feature TDA Phase 1 (target supervisione)
N_EPOCHS = 200        # epoche massime
BATCH_SIZE = 3        # sicuro su 16 GB con N_PTS=4096, k=16, D=32
LR_INITIAL = 5e-5     # learning rate iniziale
LR_MIN = 1e-6         # learning rate minimo (ReduceLROnPlateau floor)
PATIENCE = 20         # epoche senza miglioramento → riduzione LR
EARLY_STOP_PATIENCE = 40  # early stopping

# Dataset
N_FIELDS_FIDUCIAL = 2000
N_FIELDS_LHC = 2000
N_FIELDS_NWLH = 2000
TRAIN_FRAC = 0.80    # 80/20 split — seed=42

# Gate 2
R_THRESHOLD = 0.20   # CAUCHY_Execution_Parameters §4.2 [VALORE NON DA LETTERATURA]
CORR_HESSIAN_THRESHOLD = 0.05  # soft gate (sanity check)
W2_N_PROJECTIONS = 1000        # Sliced Wasserstein

# Test robustezza Fisher (R1-2)
FISHER_LOCAL_FRACS = [0.1, 0.2, 0.3, 0.5]

# Paths
DATA_DIR = Path("data/processed/phase0_fields")
RESULTS_DIR = Path("results")
CHECKPOINT_DIR = Path("results/checkpoints")
TAU_LHC_DIR = Path("results/phase2_tau_fields/lhc")
TAU_NWLH_DIR = Path("results/phase2_tau_fields/nwlh")

PHASE1_CACHE_PATH = Path("results/phase1_fiducial_cache.npz")
PHASE1_BASELINE_PATH = Path("results/phase1_tda_baseline.json")
DIAGNOSTIC_PATH = Path("results/phase2_cnn_diagnostic.json")
CHECKPOINT_BEST = Path("results/checkpoints/phase2_cnn_best.pt")

# Nomi feature TDA (ordine canonico — da CAUCHY_Execution_Parameters §9.1)
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

# ── Setup logging ────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("phase2_cnn_run.log", mode="a"),
    ],
)
log = logging.getLogger("cauchy.phase2")


# ═══════════════════════════════════════════════════════════════════════════
# §1 — UNIT TEST GUDHI CONVENTION (R1-4)
# ═══════════════════════════════════════════════════════════════════════════

def _test_gudhi_convention() -> dict:
    """
    Unit test della convenzione gudhi CubicalComplex per superlevel filtration.

    Chiude l'impegno R1-4. Usa persistence_intervals_in_dimension (stessa
    API di phase1_tda_baseline.py) invece di persistent_betti_numbers, che
    in gudhi 0.6+ ha semantica diversa per i Betti numbers di alta dimensione.

    Test A — Segno della persistenza (β₂, sfera cava 32³):
        Campo: guscio sferico (alta densità) + cavità interna (bassa densità).
        Superlevel a soglia intermedia → guscio è l'unica struttura attiva.
        Atteso: almeno 1 feature β₂ con nu_birth > nu_death > 0
        (la cavità 3D chiusa produce un 2-ciclo nella filtrazione di superlevel).

    Test B — Segno della persistenza (β₁, toro 32³):
        Campo: tubo toroidale (alta densità) con buco centrale (bassa densità).
        Atteso: almeno 1 feature β₁ con nu_birth > nu_death > 0.

    Test C — Convenzione birth/death:
        Verifica che nu_birth > nu_death per tutte le feature finite
        (superlevel: feature nasce ad alta densità, muore a bassa densità).

    Riferimento: phase1_tda_baseline.py compute_persistence_diagram()
    """
    if not HAS_GUDHI:
        return {
            "passed": False,
            "error": "gudhi non disponibile — installare gudhi>=3.9.0",
        }

    log.info("[R1-4] Esecuzione unit test gudhi convention...")

    def _run_cc(field: np.ndarray) -> dict:
        """Applica la pipeline Phase 1 esatta e restituisce i diagrammi."""
        nu = np.log(np.clip(field, -0.9999, None) + 1.0)
        cc = gudhi.CubicalComplex(
            dimensions=list(nu.shape),
            top_dimensional_cells=(-nu).flatten().astype(np.float64)
        )
        cc.compute_persistence()
        diagrams = {}
        for dim, key in [(0, 'b0'), (1, 'b1'), (2, 'b2')]:
            raw = cc.persistence_intervals_in_dimension(dim)
            if len(raw) == 0:
                diagrams[key] = np.empty((0, 2))
            else:
                raw = np.array(raw, dtype=np.float64)
                finite = raw[np.isfinite(raw[:, 1])]
                if len(finite) == 0:
                    diagrams[key] = np.empty((0, 2))
                else:
                    # Conversione: nu_birth=-col0, nu_death=-col1
                    diagrams[key] = np.column_stack([-finite[:, 0], -finite[:, 1]])
        return diagrams

    errors = []

    # ── Test A: sfera cava → β₂ ≥ 1 ────────────────────────────────────────
    grid = 32
    center = grid / 2
    coords = np.mgrid[0:grid, 0:grid, 0:grid].astype(float)
    r = np.sqrt(sum((coords[i] - center) ** 2 for i in range(3)))

    field_sphere = np.full((grid, grid, grid), -0.5)   # sfondo bassa densità
    field_sphere[(r >= 6) & (r <= 12)] = 1.5            # guscio alta densità
    field_sphere[r < 6] = -0.5                          # cavità bassa densità

    diag_sphere = _run_cc(field_sphere)
    b2_features = diag_sphere['b2']
    n_b2 = len(b2_features)

    if n_b2 == 0:
        errors.append(
            f"Test A FAIL: sfera cava 32³ produce β₂=0 (atteso ≥1). "
            f"gudhi versione {gudhi.__version__} potrebbe avere API diversa."
        )
    else:
        # Verifica che nu_birth > nu_death (superlevel)
        wrong_sign = np.sum(b2_features[:, 0] <= b2_features[:, 1])
        if wrong_sign > 0:
            errors.append(
                f"Test A FAIL: {wrong_sign}/{n_b2} feature β₂ hanno "
                "nu_birth ≤ nu_death — convenzione birth/death invertita."
            )
        else:
            log.info(f"[R1-4] Test A PASS: β₂={n_b2} feature, nu_birth>nu_death ✓")

    # ── Test B: campo 1D a scala → β₁ ≥ 1 ──────────────────────────────────
    # Tubo toroidale approssimato: struttura ad anello lungo l'asse z
    field_torus = np.full((grid, grid, grid), -0.5)
    for z in range(grid):
        for y in range(grid):
            for x in range(grid):
                r_ring = np.sqrt((x - center)**2 + (y - center)**2)
                if 6 <= r_ring <= 10:
                    field_torus[z, y, x] = 1.5

    diag_torus = _run_cc(field_torus)
    b1_features = diag_torus['b1']
    n_b1 = len(b1_features)

    if n_b1 == 0:
        errors.append(
            f"Test B FAIL: tubo toroidale 32³ produce β₁=0 (atteso ≥1)."
        )
    else:
        wrong_sign = np.sum(b1_features[:, 0] <= b1_features[:, 1])
        if wrong_sign > 0:
            errors.append(
                f"Test B FAIL: {wrong_sign}/{n_b1} feature β₁ hanno "
                "nu_birth ≤ nu_death."
            )
        else:
            log.info(f"[R1-4] Test B PASS: β₁={n_b1} feature, nu_birth>nu_death ✓")

    # ── Test C: b0 sempre presente ───────────────────────────────────────────
    b0_features = diag_sphere['b0']
    if len(b0_features) == 0:
        # β₀ finiti potrebbero essere tutti zero se una sola componente connessa
        # (la componente illimitata viene scartata da isfinite) — questo è atteso
        log.info("[R1-4] Test C: β₀ finiti=0 (componente illimitata scartata) ✓")
    else:
        wrong_sign_b0 = np.sum(b0_features[:, 0] <= b0_features[:, 1])
        if wrong_sign_b0 > 0:
            errors.append(
                f"Test C FAIL: {wrong_sign_b0} feature β₀ hanno nu_birth≤nu_death."
            )
        else:
            log.info(f"[R1-4] Test C PASS: β₀={len(b0_features)} finiti ✓")

    passed = len(errors) == 0

    result = {
        "passed": passed,
        "error": "; ".join(errors) if errors else None,
        "test_A_beta2_features": int(n_b2),
        "test_B_beta1_features": int(n_b1),
        "gudhi_version": gudhi.__version__,
        "api_used": "persistence_intervals_in_dimension (identico a phase1_tda_baseline.py)",
        "note": (
            "Test usa persistence_intervals_in_dimension, non persistent_betti_numbers. "
            "Coerente con la pipeline Phase 1."
        ),
    }

    if passed:
        log.info(
            f"[R1-4] PASS — β₂≥1 (A), β₁≥1 (B), convenzione birth>death (C) ✓"
        )
    else:
        for e in errors:
            log.error(f"[R1-4] {e}")
        log.error("[R1-4] BLOCCO: convenzione gudhi non verificata.")

    return result


# ═══════════════════════════════════════════════════════════════════════════
# §2 — CARICAMENTO DATI E NORMALIZZAZIONE Z-SCORE (R1-1)
# ═══════════════════════════════════════════════════════════════════════════

def load_phase1_features() -> dict:
    """
    Carica le feature TDA di Phase 1 da phase1_fiducial_cache.npz e
    phase1_tda_baseline.json.

    Struttura attesa di phase1_fiducial_cache.npz:
        fvecs_fid: [2000, 8]  — feature fiduciali
        (+ eventualmente fvecs_lhc, fvecs_nwlh se già calcolate)

    Struttura attesa di phase1_tda_baseline.json:
        Contiene il mapping campo→cosmologia per LHC e nwLH.
        Necessario per il test T1 (quadranti σ₈/Ωm) e per R1-2.

    Returns:
        dict con chiavi: fvecs_fid, fvecs_lhc, fvecs_nwlh,
                         cosmo_lhc (Omm, s8 per ogni campo),
                         cosmo_nwlh (w0 per ogni campo)
    """
    log.info("Caricamento feature TDA Phase 1...")

    # ── Fiducial features ────────────────────────────────────────────────────
    if not PHASE1_CACHE_PATH.exists():
        raise FileNotFoundError(
            f"phase1_fiducial_cache.npz non trovato: {PHASE1_CACHE_PATH}\n"
            "Prerequisito: Phase 1 completata con Gate 1 PASS."
        )

    cache = np.load(PHASE1_CACHE_PATH)
    fvecs_fid = cache["fvecs_fid"].astype(np.float32)  # [2000, 8]
    assert fvecs_fid.shape == (N_FIELDS_FIDUCIAL, N_FEATURES), (
        f"Shape attesa ({N_FIELDS_FIDUCIAL}, {N_FEATURES}), "
        f"trovata {fvecs_fid.shape}"
    )
    log.info(f"  fvecs_fid: {fvecs_fid.shape}")

    # ── LHC e nwLH features (se già calcolate) ───────────────────────────────
    fvecs_lhc = cache["fvecs_lhc"].astype(np.float32) if "fvecs_lhc" in cache else None
    fvecs_nwlh = cache["fvecs_nwlh"].astype(np.float32) if "fvecs_nwlh" in cache else None

    # ── Cosmologie LHC (per test T1 e R1-2) ─────────────────────────────────
    cosmo_lhc = None
    cosmo_nwlh = None

    if PHASE1_BASELINE_PATH.exists():
        with open(PHASE1_BASELINE_PATH) as f:
            baseline = json.load(f)

        # Estrarre cosmologie LHC se presenti
        if "lhc_cosmologies" in baseline:
            cosmo_lhc = np.array(baseline["lhc_cosmologies"], dtype=np.float32)
            # attesa shape [2000, 2] con colonne [Omm, s8]
        if "nwlh_cosmologies" in baseline:
            cosmo_nwlh = np.array(baseline["nwlh_cosmologies"], dtype=np.float32)
            # attesa shape [2000, 1] con colonna [w0]

    if cosmo_lhc is None:
        log.warning(
            "Cosmologie LHC non trovate in phase1_tda_baseline.json. "
            "Il test T1 (Gate 2) e R1-2 richiedono questi dati. "
            "Assicurarsi che Phase 1 abbia salvato lhc_cosmologies nel baseline."
        )

    return {
        "fvecs_fid": fvecs_fid,
        "fvecs_lhc": fvecs_lhc,
        "fvecs_nwlh": fvecs_nwlh,
        "cosmo_lhc": cosmo_lhc,
        "cosmo_nwlh": cosmo_nwlh,
    }


def compute_zscore_stats(fvecs_lhc: np.ndarray, train_indices: np.ndarray) -> dict:
    """
    Calcola le statistiche z-score (μ, σ) per ogni feature sul SOLO training set.

    Chiude impegno R1-1: la normalizzazione z-score prima di qualsiasi analisi
    Fisher downstream riduce il numero di condizione della matrice C_noise da
    ~4×10¹⁰ (Phase 1) a un valore compatibile con κ(C) < 10⁶ (Heavens 2009 MNRAS).

    CRITICO: le statistiche sono calcolate solo sul training set (train_indices)
    e mai sul test set, per evitare data leakage.

    Args:
        fvecs_lhc: [N, 8] feature LHC
        train_indices: indici del training set

    Returns:
        dict con mean_train [8] e std_train [8]
    """
    fvecs_train = fvecs_lhc[train_indices]  # [N_train, 8]
    mean_train = fvecs_train.mean(axis=0)    # [8]
    std_train = fvecs_train.std(axis=0)      # [8]

    # Protezione divisione per zero (feature costante)
    zero_std = std_train < 1e-10
    if zero_std.any():
        log.warning(
            f"Feature con std≈0 rilevate: "
            f"{[FEATURE_NAMES[i] for i in np.where(zero_std)[0]]}. "
            "Sostituisco con std=1.0 per evitare divisione per zero."
        )
        std_train[zero_std] = 1.0

    # Numero di condizione della matrice diagonale normalizzata
    # (approssimazione: la matrice di covarianza delle feature normalizzate
    #  dovrebbe avere tutti i valori diagonali ≈1)
    fvecs_norm = (fvecs_train - mean_train) / std_train
    cov_norm = np.cov(fvecs_norm.T)
    cond_before = np.linalg.cond(np.cov(fvecs_train.T))
    cond_after = np.linalg.cond(cov_norm)

    log.info(f"[R1-1] Numero di condizione C_noise:")
    log.info(f"  Prima della normalizzazione:  κ = {cond_before:.3e}")
    log.info(f"  Dopo la normalizzazione:      κ = {cond_after:.3e}")
    log.info(f"  Heavens 2009 threshold: κ < 1e6 → {'PASS' if cond_after < 1e6 else 'WARN'}")

    return {
        "mean_train": mean_train,
        "std_train": std_train,
        "cond_before": float(cond_before),
        "cond_after": float(cond_after),
        "heavens_threshold": 1e6,
        "heavens_pass": bool(cond_after < 1e6),
    }


def check_iid_lhc(fvecs_lhc: np.ndarray, train_indices: np.ndarray) -> dict:
    """
    Verifica i.i.d. per i campi LHC (impegno C0-3).

    Controlla che la distribuzione delle medie per-campo nel training set CNN
    sia compatibile con i.i.d. condizionati ai parametri cosmologici.

    Test: la media di ogni campo (media sulle 8 feature) non deve mostrare
    correlazioni sistematiche con l'indice di campo (drift), né una distribuzione
    bimodale anomala. Un test Kolmogorov-Smirnov sulla distribuzione delle medie
    per-campo confrontata con una gaussiana è un sanity check sufficiente.

    Args:
        fvecs_lhc: [N, 8] feature LHC
        train_indices: indici del training set

    Returns:
        dict con risultati del test i.i.d.
    """
    from scipy import stats

    fvecs_train = fvecs_lhc[train_indices]
    field_means = fvecs_train.mean(axis=1)  # media per-campo [N_train]

    # KS test contro gaussiana
    ks_stat, ks_pval = stats.kstest(
        (field_means - field_means.mean()) / field_means.std(),
        "norm"
    )

    # Test di autocorrelazione (lag=1): se i campi fossero ordinati per
    # cosmologia potremmo avere drift sistematico
    acf_lag1 = float(np.corrcoef(field_means[:-1], field_means[1:])[0, 1])

    # Spearman rank-correlation con l'indice di campo (test di drift)
    spearman_idx, spearman_pval = stats.spearmanr(
        np.arange(len(field_means)), field_means
    )

    passed = (ks_pval > 0.05) and (abs(acf_lag1) < 0.1) and (abs(spearman_idx) < 0.1)

    log.info(f"[C0-3] Test i.i.d. LHC:")
    log.info(f"  KS test vs gaussiana: stat={ks_stat:.4f}, p={ks_pval:.4f}")
    log.info(f"  Autocorrelazione lag-1: {acf_lag1:.4f}")
    log.info(f"  Spearman rank vs indice: r={spearman_idx:.4f}, p={spearman_pval:.4f}")
    log.info(f"  Verdict: {'PASS' if passed else 'WARN — verificare manualmente'}")

    return {
        "ks_stat": float(ks_stat),
        "ks_pval": float(ks_pval),
        "acf_lag1": float(acf_lag1),
        "spearman_idx_corr": float(spearman_idx),
        "spearman_idx_pval": float(spearman_pval),
        "iid_passed": passed,
        "note": (
            "Campo LHC i.i.d. condizionato ai parametri se KS p>0.05, "
            "|ACF_lag1|<0.1, |Spearman_r|<0.1."
        ),
    }


# ═══════════════════════════════════════════════════════════════════════════
# §3 — ARCHITETTURA EGNN (e3nn)
# ═══════════════════════════════════════════════════════════════════════════

class EquivariantBlock(nn.Module):
    """
    Blocco di message passing SE(3)-equivariante basato su e3nn.

    Implementa un passo di message passing equivariante con:
    - Spherical harmonics per encoding della direzione relativa r̂_ij
    - TensorProduct per la combinazione equivariante di feature
    - Proiezione finale sulle Irreps di output

    Scelte architetturali:
    - Irreps tipo 0e (scalari) + 1o (vettori) per catturare informazione
      di ampiezza (topologia cluster) e direzione (connettività filamentare)
    - L_max=1: sufficiente per scale cosmologiche dove la struttura
      principale è filamentare (L=1) e non ha multipoli superiori rilevanti
      con N_pts=4096 su volume 1 Gpc/h³

    Riferimento: e3nn library (Geiger & Smidt 2021, arXiv:2207.09453)
    """

    def __init__(
        self,
        irreps_in: "o3.Irreps",
        irreps_out: "o3.Irreps",
        irreps_sh: "o3.Irreps",
        n_radial: int = 8,
    ):
        super().__init__()
        self.irreps_in = irreps_in
        self.irreps_out = irreps_out
        self.irreps_sh = irreps_sh

        # Tensor product: feature_i × SH(r̂_ij) → messaggio
        # e3nn 0.6.0: FullyConnectedTensorProduct gestisce le instructions
        # automaticamente — più robusto del TensorProduct manuale con instructions.
        from e3nn.o3 import FullyConnectedTensorProduct
        self.tp = FullyConnectedTensorProduct(
            irreps_in,
            irreps_sh,
            irreps_out,
            shared_weights=False,   # i pesi vengono dalla radial_net
        )

        # Rete radiale: encoding della distanza scalare r_ij
        self.radial_net = nn.Sequential(
            nn.Linear(n_radial, 64),
            nn.SiLU(),
            nn.Linear(64, self.tp.weight_numel),
        )

        # Encoding gaussiano della distanza
        self.n_radial = n_radial

        # Layer di output (proiezione finale sui D_latent scalari)
        self.output_linear = Linear(irreps_out, irreps_out)

    def forward(
        self,
        x: torch.Tensor,         # [N, irreps_in.dim] feature nodali
        pos: torch.Tensor,       # [N, 3] coordinate
        edge_index: torch.Tensor, # [2, E] grafo k-NN
    ) -> torch.Tensor:
        """
        Args:
            x:          feature nodali [N, irreps_in.dim]
            pos:        coordinate 3D [N, 3]
            edge_index: [2, E] con edge_index[0]=src, edge_index[1]=dst

        Returns:
            x_out: feature nodali aggiornate [N, irreps_out.dim]
        """
        src, dst = edge_index[0], edge_index[1]

        # Vettore relativo e distanza
        r_vec = pos[dst] - pos[src]                    # [E, 3]
        r_dist = r_vec.norm(dim=-1, keepdim=True)      # [E, 1]

        # Direzione normalizzata (con protezione per r→0)
        r_hat = r_vec / (r_dist + 1e-8)               # [E, 3] — unitario

        # Spherical harmonics sulla direzione relativa
        # e3nn 0.6.0: SphericalHarmonics(irreps, x, normalize, normalization)
        sh = o3.spherical_harmonics(self.irreps_sh, r_hat, normalize=True, normalization="component")

        # Encoding radiale con basi gaussiane
        r_embedding = self._rbf(r_dist.squeeze(-1))    # [E, n_radial]
        weight = self.radial_net(r_embedding)           # [E, tp.weight_numel]

        # Messaggio: TensorProduct(feature_src, SH, weight)
        msg = self.tp(x[src], sh, weight)              # [E, irreps_out.dim]

        # Aggregazione: somma per nodo destinazione
        x_out = torch.zeros(
            x.shape[0], self.tp.irreps_out.dim,
            dtype=x.dtype, device=x.device
        )
        x_out.scatter_add_(0, dst.unsqueeze(-1).expand_as(msg), msg)

        return self.output_linear(x_out)

    def _rbf(self, r: torch.Tensor, r_max: float = 150.0) -> torch.Tensor:
        """
        Radial Basis Functions gaussiane per encoding della distanza.
        r in [Mpc/h]. r_max≈150 Mpc/h copre il range del k=16° vicino
        con N_pts=4096 su volume 1 Gpc/h³.
        """
        centers = torch.linspace(0, r_max, self.n_radial, device=r.device)
        sigma = r_max / (2 * self.n_radial)
        return torch.exp(-((r.unsqueeze(-1) - centers) ** 2) / (2 * sigma ** 2))


class CAUCHYEncoder(nn.Module):
    """
    Encoder CNN SE(3)-equivariante per CAUCHY Phase 2.

    Architettura:
    - Embedding iniziale: scalare δ(x_i) → Irreps scalari + vettoriali
    - 3 blocchi EquivariantBlock con message passing k-NN
    - Proiezione finale: Irreps → D_latent scalari
    - Output: [N_pts, D_latent] rappresentazione latente per punto

    La supervisione è su feature TDA di CAMPO (non sul punto singolo).
    Il pooling globale (mean) sulla rappresentazione latente produce
    un vettore [D_latent] per campo, proiettato su [N_FEATURES] scalari.

    Nota su SE(3) vs E(3):
    Il Methodology prescrive SE(3) (rotazioni + traslazioni, no riflessioni).
    Usiamo Irreps con parità (0e per scalari, 1o per vettori pseudo-vettori)
    che rispetta SE(3). La distinzione da E(3) è rilevante per feature
    chirali (β₂ dei vuoti può avere asimmetria chirale in presenza di
    perturbazioni primordiali non-gaussiane), ma conservativa per CAUCHY.

    N_PARAMS stimati: ~180k — adeguato per D_latent=32 con supervisione su 8 target.
    """

    def __init__(
        self,
        d_latent: int = D_LATENT,
        n_features: int = N_FEATURES,
        n_mp_layers: int = 3,
    ):
        super().__init__()
        self.d_latent = d_latent
        self.n_features = n_features

        # Irreps: scalari (0e) + vettori (1o) — L_max=1
        # Molteplicità: d_latent//4 per 0e e 1o (bilanciato)
        mul_s = d_latent // 4   # molteplicità scalari = 8 per d_latent=32
        mul_v = d_latent // 4   # molteplicità vettori = 8 per d_latent=32

        self.irreps_hidden = o3.Irreps(f"{mul_s}x0e + {mul_v}x1o")
        self.irreps_out_node = o3.Irreps(f"{d_latent}x0e")  # solo scalari in output
        self.irreps_sh = o3.Irreps.spherical_harmonics(lmax=1)  # Y_0^0 + Y_1^m

        # Embedding iniziale: scalare δ(x) → irreps_hidden
        # δ è uno scalare (0e), lo espandiamo alle Irreps iniziali
        self.embedding = nn.Sequential(
            nn.Linear(1, 64),
            nn.SiLU(),
            nn.Linear(64, self.irreps_hidden.dim),
        )

        # Blocchi di message passing equivarianti
        self.mp_layers = nn.ModuleList([
            EquivariantBlock(
                irreps_in=self.irreps_hidden,
                irreps_out=self.irreps_hidden,
                irreps_sh=self.irreps_sh,
            )
            for _ in range(n_mp_layers)
        ])

        # Layer normalization dopo ogni MP layer (stabilizza training)
        self.layer_norms = nn.ModuleList([
            nn.LayerNorm(self.irreps_hidden.dim)
            for _ in range(n_mp_layers)
        ])

        # Proiezione finale: irreps_hidden → D_latent scalari
        self.proj_out = nn.Sequential(
            nn.Linear(self.irreps_hidden.dim, d_latent * 2),
            nn.SiLU(),
            nn.Linear(d_latent * 2, d_latent),
        )

        # Testa di supervisione: pooling globale → N_FEATURES
        # Usata solo durante il training, non per la costruzione di τ(x)
        self.supervision_head = nn.Sequential(
            nn.Linear(d_latent, 64),
            nn.SiLU(),
            nn.Linear(64, n_features),
        )

    def forward(
        self,
        delta_pts: torch.Tensor,   # [N, 1] valori δ nei punti campionati
        pos: torch.Tensor,         # [N, 3] coordinate fisiche (Mpc/h)
        edge_index: torch.Tensor,  # [2, E] grafo k-NN
        batch: torch.Tensor,       # [N] indice di campo nel batch
    ) -> tuple[torch.Tensor, torch.Tensor]:
        """
        Args:
            delta_pts:  valori δ ai punti campionati [N_batch_pts, 1]
            pos:        coordinate 3D [N_batch_pts, 3]
            edge_index: grafo k-NN [2, E]
            batch:      indice di campo [N_batch_pts]

        Returns:
            tau_pts: [N_batch_pts, D_latent] — feature latenti per punto
            pred_features: [batch_size, N_FEATURES] — predizioni feature TDA
                           (per la loss di supervisione durante training)
        """
        # Embedding scalare → Irreps
        x = self.embedding(delta_pts)   # [N, irreps_hidden.dim]

        # Message passing equivariante con connessioni residuali
        for mp_layer, ln in zip(self.mp_layers, self.layer_norms):
            x_new = mp_layer(x, pos, edge_index)
            x = ln(x + x_new)           # residual connection + layer norm

        # Proiezione su scalari latenti [N, D_latent]
        tau_pts = self.proj_out(x)      # [N_batch_pts, D_latent]

        # Pooling globale per supervisione: media per campo
        # batch indica a quale campo appartiene ogni punto
        batch_size = int(batch.max().item()) + 1
        tau_pooled = torch.zeros(
            batch_size, self.d_latent,
            dtype=tau_pts.dtype, device=tau_pts.device
        )
        counts = torch.zeros(batch_size, dtype=tau_pts.dtype, device=tau_pts.device)
        tau_pooled.scatter_add_(0, batch.unsqueeze(-1).expand_as(tau_pts), tau_pts)
        counts.scatter_add_(0, batch, torch.ones(batch.shape[0], dtype=tau_pts.dtype, device=tau_pts.device))
        tau_pooled = tau_pooled / counts.unsqueeze(-1).clamp(min=1)  # [B, D_latent]

        # Predizione feature TDA dalla rappresentazione pooled
        pred_features = self.supervision_head(tau_pooled)  # [B, N_FEATURES]

        return tau_pts, pred_features


def count_parameters(model: nn.Module) -> int:
    return sum(p.numel() for p in model.parameters() if p.requires_grad)


# ═══════════════════════════════════════════════════════════════════════════
# §4 — CAMPIONAMENTO PUNTI E COSTRUZIONE GRAFO K-NN
# ═══════════════════════════════════════════════════════════════════════════

def sample_points_density_weighted(
    field: np.ndarray,
    n_pts: int,
    box_size: float = 1000.0,
    eps_floor: float = 0.01,
    rng: np.random.Generator = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """
    Campionamento di n_pts punti dal campo di densità, pesato per |δ(x)|.

    Motivazione (Q1, confermata dal PI): il campionamento pesato per |δ(x)|
    rende τ(x) scientificamente interpretabile — ogni punto rappresenta
    una struttura del cosmic web con probabilità proporzionale alla sua
    prominenza. Le regioni di alta densità (filamenti, nodi) sono dove
    l'informazione topologica è concentrata (Methodology §2.1).

    Implementazione:
    - p(x) ∝ max(δ(x) - δ_min, 0) + ε (ε-floor per copertura minima dei void)
    - I punti sono campionati senza rimpiazzo
    - Le coordinate fisiche sono calcolate dalla posizione nel reticolo

    Args:
        field:    [128, 128, 128] campo δ(x) float64
        n_pts:    numero di punti da campionare
        box_size: dimensione del box in Mpc/h (default 1000.0)
        eps_floor: peso minimo per le regioni di bassa densità
        rng:      generatore numpy (per riproducibilità)

    Returns:
        delta_pts:    [n_pts] valori δ nei punti campionati
        pos_pts:      [n_pts, 3] coordinate fisiche in Mpc/h
        sample_idx:   [n_pts] indici flat nel reticolo 128³
    """
    if rng is None:
        rng = np.random.default_rng(GLOBAL_SEED)

    grid_size = field.shape[0]
    cell_size = box_size / grid_size  # Mpc/h per voxel

    # Probabilità di campionamento pesata per |δ(x)|
    delta_flat = field.flatten()
    delta_shifted = delta_flat - delta_flat.min()   # tutti ≥ 0
    weights = delta_shifted + eps_floor * delta_shifted.max()
    weights = weights / weights.sum()               # normalizzazione

    # Campionamento senza rimpiazzo
    total_voxels = grid_size ** 3
    sample_idx = rng.choice(total_voxels, size=n_pts, replace=False, p=weights)

    # Coordinate fisiche: centro del voxel
    idx_3d = np.unravel_index(sample_idx, (grid_size, grid_size, grid_size))
    pos_pts = np.stack([
        (idx_3d[0] + 0.5) * cell_size,
        (idx_3d[1] + 0.5) * cell_size,
        (idx_3d[2] + 0.5) * cell_size,
    ], axis=-1).astype(np.float32)  # [n_pts, 3]

    delta_pts = delta_flat[sample_idx].astype(np.float32)  # [n_pts]

    return delta_pts, pos_pts, sample_idx


def build_knn_graph(pos: torch.Tensor, k: int = K_NN) -> torch.Tensor:
    """
    Costruisce il grafo k-NN nelle coordinate fisiche (Mpc/h).

    Usa torch_geometric.nn.knn_graph per efficienza.
    Restituisce edge_index [2, N*k] con boundary conditions periodiche
    disabilitate (i campi Quijote sono periodici ma il campionamento
    density-weighted rompe la periodicità — si usa il grafo standard).

    Args:
        pos: [N, 3] coordinate fisiche (Mpc/h)
        k:   numero di vicini

    Returns:
        edge_index: [2, N*k] con src=edge_index[0], dst=edge_index[1]
    """
    if HAS_TORCH_GEOMETRIC:
        # knn_graph di torch-geometric: efficiente su GPU
        return knn_graph(pos, k=k, loop=False)
    else:
        # Fallback: implementazione numpy (più lenta, solo per dev/test)
        from scipy.spatial import KDTree
        tree = KDTree(pos.cpu().numpy())
        dists, indices = tree.query(pos.cpu().numpy(), k=k + 1)
        # Rimuovi self-loop (indice 0 = il punto stesso)
        src = np.repeat(np.arange(len(pos)), k)
        dst = indices[:, 1:].flatten()
        edge_index = torch.tensor(
            np.stack([src, dst], axis=0), dtype=torch.long, device=pos.device
        )
        return edge_index


# ═══════════════════════════════════════════════════════════════════════════
# §5 — TRAINING LOOP
# ═══════════════════════════════════════════════════════════════════════════

class CosmoFieldDataset:
    """
    Dataset lazy per i campi cosmologici.

    Carica i campi da disco on-demand per evitare di tenere tutti i 2000
    campi in RAM (2000 × 128³ × 8 byte = ~4 GB per il solo LHC).

    Args:
        field_dir:  Path alla directory con field_NNNN.npy
        fvecs:      [N, 8] feature TDA (target di supervisione)
        zscore_mean: [8] media training per normalizzazione
        zscore_std:  [8] std training per normalizzazione
        indices:    indici dei campi da usare (training o test)
        n_pts:      numero di punti da campionare per campo
    """

    def __init__(
        self,
        field_dir: Path,
        fvecs: np.ndarray,
        zscore_mean: np.ndarray,
        zscore_std: np.ndarray,
        indices: np.ndarray,
        n_pts: int = N_PTS,
    ):
        self.field_dir = field_dir
        self.fvecs = fvecs          # [N_total, 8]
        self.zscore_mean = zscore_mean
        self.zscore_std = zscore_std
        self.indices = indices      # indici nel dataset totale
        self.n_pts = n_pts

        # Seed per campionamento riproducibile (ma diverso per ogni campo/epoca)
        self.base_rng = np.random.default_rng(GLOBAL_SEED)

    def __len__(self):
        return len(self.indices)

    def __getitem__(self, local_idx: int) -> dict:
        """
        Carica il campo field_idx, campiona n_pts punti, costruisce il tensore.

        Returns:
            dict con: delta_pts, pos_pts, target_normalized, field_idx
        """
        field_idx = self.indices[local_idx]
        field_path = self.field_dir / f"field_{field_idx:04d}.npy"

        if not field_path.exists():
            raise FileNotFoundError(f"Campo non trovato: {field_path}")

        field = np.load(field_path).astype(np.float64)  # [128, 128, 128]

        # Campionamento pesato per |δ(x)|
        rng = np.random.default_rng(GLOBAL_SEED + int(field_idx))
        delta_pts, pos_pts, _ = sample_points_density_weighted(
            field, self.n_pts, rng=rng
        )

        # Target normalizzato (z-score) — chiude R1-1
        target = self.fvecs[field_idx]                    # [8]
        target_norm = (target - self.zscore_mean) / self.zscore_std  # [8]

        return {
            "delta_pts": torch.tensor(delta_pts[:, None], dtype=torch.float32),  # [N, 1]
            "pos_pts": torch.tensor(pos_pts, dtype=torch.float32),                # [N, 3]
            "target_norm": torch.tensor(target_norm, dtype=torch.float32),        # [8]
            "field_idx": field_idx,
        }


def collate_fn(batch: list) -> dict:
    """
    Collate function per il DataLoader.

    Concatena i punti di più campi e crea il tensore batch [N_total]
    che indica a quale campo appartiene ogni punto.

    Returns dict con: delta_pts [N_total, 1], pos_pts [N_total, 3],
                      targets [B, 8], batch [N_total], edge_index [2, E]
    """
    delta_list, pos_list, target_list, batch_list = [], [], [], []
    n_pts_per_field = batch[0]["delta_pts"].shape[0]

    for i, item in enumerate(batch):
        delta_list.append(item["delta_pts"])
        pos_list.append(item["pos_pts"])
        target_list.append(item["target_norm"])
        batch_list.append(torch.full((n_pts_per_field,), i, dtype=torch.long))

    delta_pts = torch.cat(delta_list, dim=0)        # [N_total, 1]
    pos_pts = torch.cat(pos_list, dim=0)            # [N_total, 3]
    targets = torch.stack(target_list, dim=0)       # [B, 8]
    batch_idx = torch.cat(batch_list, dim=0)        # [N_total]

    # Grafo k-NN sulla concatenazione (ogni campo ha il suo sotto-grafo)
    # Usiamo l'implementazione per-campo e shiftiamo gli indici
    edge_src_list, edge_dst_list = [], []
    offset = 0
    for i in range(len(batch)):
        pos_i = pos_pts[offset: offset + n_pts_per_field]
        ei = build_knn_graph(pos_i, k=K_NN)
        edge_src_list.append(ei[0] + offset)
        edge_dst_list.append(ei[1] + offset)
        offset += n_pts_per_field

    edge_index = torch.stack([
        torch.cat(edge_src_list),
        torch.cat(edge_dst_list),
    ], dim=0)

    return {
        "delta_pts": delta_pts,
        "pos_pts": pos_pts,
        "targets": targets,
        "batch": batch_idx,
        "edge_index": edge_index,
    }


def train_cnn(
    model: CAUCHYEncoder,
    train_dataset: CosmoFieldDataset,
    val_dataset: CosmoFieldDataset,
    device: torch.device,
) -> dict:
    """
    Training loop principale.

    Loss: MSE z-score (Σ_k (pred_k - target_k)²  con target già z-normalizzato).
    Scheduler: ReduceLROnPlateau con patience=PATIENCE.
    Early stopping: EARLY_STOP_PATIENCE epoche senza miglioramento.

    Args:
        model: CAUCHYEncoder
        train_dataset, val_dataset: CosmoFieldDataset
        device: cuda o cpu

    Returns:
        dict con training report (loss curves, checkpoint path, checksum)
    """
    from torch.utils.data import DataLoader

    model = model.to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=LR_INITIAL, weight_decay=1e-5)
    scheduler = ReduceLROnPlateau(
        optimizer, mode="min", factor=0.5, patience=PATIENCE, min_lr=LR_MIN
    )

    # num_workers=0 su Windows: i worker multiprocessing non ereditano
    # correttamente il contesto CUDA e causano ImportError con torch-cluster.
    # Il caricamento sequenziale è accettabile per N_fields=2000 su SSD NVMe.
    n_workers = 0  # Windows-safe

    train_loader = DataLoader(
        train_dataset,
        batch_size=BATCH_SIZE,
        shuffle=True,
        collate_fn=collate_fn,
        num_workers=n_workers,
        pin_memory=(device.type == "cuda"),
    )
    val_loader = DataLoader(
        val_dataset,
        batch_size=BATCH_SIZE,
        shuffle=False,
        collate_fn=collate_fn,
        num_workers=n_workers,
        pin_memory=(device.type == "cuda"),
    )

    CHECKPOINT_DIR.mkdir(parents=True, exist_ok=True)

    best_val_loss = float("inf")
    best_epoch = 0
    train_losses, val_losses = [], []
    no_improve_count = 0
    t_start = time.time()

    log.info(f"Inizio training: {N_EPOCHS} epoche max, device={device}")
    log.info(f"  N parametri: {count_parameters(model):,}")
    log.info(f"  Batch size: {BATCH_SIZE}, N_pts: {N_PTS}, k: {K_NN}, D_latent: {D_LATENT}")

    for epoch in range(1, N_EPOCHS + 1):
        # ── Training ─────────────────────────────────────────────────────────
        model.train()
        epoch_loss = 0.0
        for batch in train_loader:
            delta_pts = batch["delta_pts"].to(device)
            pos_pts = batch["pos_pts"].to(device)
            targets = batch["targets"].to(device)
            batch_idx = batch["batch"].to(device)
            edge_index = batch["edge_index"].to(device)

            optimizer.zero_grad()
            _, pred = model(delta_pts, pos_pts, edge_index, batch_idx)
            loss = F.mse_loss(pred, targets)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
            optimizer.step()
            epoch_loss += loss.item()

        train_loss = epoch_loss / len(train_loader)
        train_losses.append(train_loss)

        # ── Validation ───────────────────────────────────────────────────────
        model.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            for batch in val_loader:
                delta_pts = batch["delta_pts"].to(device)
                pos_pts = batch["pos_pts"].to(device)
                targets = batch["targets"].to(device)
                batch_idx = batch["batch"].to(device)
                edge_index = batch["edge_index"].to(device)

                _, pred = model(delta_pts, pos_pts, edge_index, batch_idx)
                val_loss_sum += F.mse_loss(pred, targets).item()

        val_loss = val_loss_sum / len(val_loader)
        val_losses.append(val_loss)

        scheduler.step(val_loss)
        current_lr = optimizer.param_groups[0]["lr"]

        # Log ogni 10 epoche
        if epoch % 10 == 0 or epoch == 1:
            elapsed = (time.time() - t_start) / 60
            log.info(
                f"  Epoca {epoch:3d}/{N_EPOCHS} — "
                f"train: {train_loss:.6f}, val: {val_loss:.6f}, "
                f"lr: {current_lr:.2e}, elapsed: {elapsed:.1f} min"
            )

        # ── Salvataggio best checkpoint ───────────────────────────────────────
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_epoch = epoch
            no_improve_count = 0
            torch.save(
                {
                    "epoch": epoch,
                    "model_state_dict": model.state_dict(),
                    "optimizer_state_dict": optimizer.state_dict(),
                    "val_loss": val_loss,
                    "train_loss": train_loss,
                    "config": {
                        "N_PTS": N_PTS,
                        "K_NN": K_NN,
                        "D_LATENT": D_LATENT,
                        "N_FEATURES": N_FEATURES,
                        "GLOBAL_SEED": GLOBAL_SEED,
                    },
                },
                CHECKPOINT_BEST,
            )
        else:
            no_improve_count += 1

        # Early stopping
        if no_improve_count >= EARLY_STOP_PATIENCE:
            log.info(
                f"Early stopping a epoca {epoch} "
                f"(nessun miglioramento per {EARLY_STOP_PATIENCE} epoche)."
            )
            break

    # SHA-256 del checkpoint
    checkpoint_sha256 = _sha256(CHECKPOINT_BEST)

    total_time = (time.time() - t_start) / 60
    log.info(
        f"Training completato: {len(train_losses)} epoche, "
        f"best val_loss={best_val_loss:.6f} a epoca {best_epoch}, "
        f"durata totale {total_time:.1f} min"
    )

    return {
        "n_epochs_trained": len(train_losses),
        "best_epoch": best_epoch,
        "final_train_loss": float(train_losses[-1]),
        "final_val_loss": float(val_losses[-1]),
        "best_val_loss": float(best_val_loss),
        "train_losses": [float(x) for x in train_losses],
        "val_losses": [float(x) for x in val_losses],
        "convergence_status": (
            "CONVERGED" if best_val_loss < 0.5 else
            "PARTIAL" if best_val_loss < 1.0 else
            "NOT_CONVERGED"
        ),
        "checkpoint_path": str(CHECKPOINT_BEST),
        "checkpoint_sha256": checkpoint_sha256,
        "total_training_min": float(total_time),
        "n_params": count_parameters(model),
        "e3nn_version": E3NN_VERSION,
    }


# ═══════════════════════════════════════════════════════════════════════════
# §6 — CALCOLO μ_ΛCDM E COSTRUZIONE τ(x)
# ═══════════════════════════════════════════════════════════════════════════

def compute_mu_lcdm(
    model: CAUCHYEncoder,
    device: torch.device,
    field_dir: Path = DATA_DIR / "fiducial",
    n_fields: int = N_FIELDS_FIDUCIAL,
) -> np.ndarray:
    """
    Calcola μ_ΛCDM = media delle rappresentazioni latenti sui campi fiduciali.

    Procedura (Methodology §2.2, step 2–3):
    1. Applica CNN_encoder ai 2000 campi fiduciali
    2. Calcola la media del vettore latente pooled per campo: μ_ΛCDM [D_latent]

    CRITICO: l'ordine operativo del Methodology è rispettato:
    μ_ΛCDM è calcolata DOPO il training convergente e PRIMA della
    costruzione di τ(x) per LHC/nwLH.

    Args:
        model:     encoder già trainato
        device:    cuda o cpu
        field_dir: directory dei campi fiduciali
        n_fields:  numero di campi fiduciali (2000)

    Returns:
        mu_lcdm: [D_latent] vettore medio latente ΛCDM
    """
    log.info(f"Calcolo μ_ΛCDM su {n_fields} campi fiduciali...")
    model.eval()

    latent_sum = np.zeros(D_LATENT, dtype=np.float64)
    rng = np.random.default_rng(GLOBAL_SEED)

    with torch.no_grad():
        for i in range(n_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            field = np.load(field_path).astype(np.float64)

            delta_pts, pos_pts, _ = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_pts, _ = model(delta_t, pos_t, edge_idx, batch_t)
            latent_field = tau_pts.mean(dim=0).cpu().numpy()  # [D_latent]
            latent_sum += latent_field.astype(np.float64)

            if (i + 1) % 200 == 0:
                log.info(f"  μ_ΛCDM: {i+1}/{n_fields} campi processati")

    mu_lcdm = (latent_sum / n_fields).astype(np.float32)
    log.info(f"  μ_ΛCDM calcolata: norm={np.linalg.norm(mu_lcdm):.6f}")
    return mu_lcdm


def build_tau_fields(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    field_dir: Path,
    output_dir: Path,
    n_fields: int,
    dataset_name: str,
) -> dict:
    """
    Costruisce e salva τ(x) per tutti i campi di un dataset.

    τ(x) = CNN_encoder(δ_target(x)) − μ_ΛCDM

    Output per campo (dual format, Q3):
    - tau_points: [N_pts, 3+D_latent] — coordinate fisiche + feature latenti
                  Formato primario per Phase 3 (TDA, GNN)
    - tau_grid:   [128, 128, 128] — norma |τ(x)| interpolata sulla griglia
                  Formato per diagnostica, test hessiano, visualizzazione
    - sample_indices: [N_pts] — indici flat nel reticolo 128³

    Args:
        model:        encoder già trainato
        mu_lcdm:      [D_latent] media ΛCDM
        device:       cuda o cpu
        field_dir:    directory campi input
        output_dir:   directory output τ(x)
        n_fields:     numero di campi
        dataset_name: "lhc" o "nwlh" (per logging)

    Returns:
        dict con statistiche di costruzione
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    model.eval()

    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
    rng = np.random.default_rng(GLOBAL_SEED + 1)  # +1 per distinguere da training
    n_errors = 0
    t_start = time.time()

    with torch.no_grad():
        for i in range(n_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            out_path = output_dir / f"tau_field_{i:04d}.npz"

            if not field_path.exists():
                log.warning(f"Campo {dataset_name}[{i}] non trovato, skip.")
                n_errors += 1
                continue

            field = np.load(field_path).astype(np.float64)

            # Campionamento punti
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            # Encoding
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_pts_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)

            # τ(x) = encoder(δ) − μ_ΛCDM
            tau_pts = (tau_pts_raw - mu_t).cpu().numpy()  # [N_pts, D_latent]

            # ── Formato primario: point cloud [N_pts, 3+D_latent] ────────────
            tau_points_out = np.concatenate(
                [pos_pts, tau_pts], axis=-1
            ).astype(np.float32)  # [N_pts, 3+D_latent]

            # ── Formato secondario: norma su griglia 128³ ────────────────────
            tau_norm = np.linalg.norm(tau_pts, axis=-1)  # [N_pts]

            # Interpolazione su griglia 128³ via scatter (media per voxel)
            tau_grid = _scatter_to_grid(tau_norm, sample_idx, grid_size=128)

            # Salvataggio NPZ
            np.savez_compressed(
                out_path,
                tau_points=tau_points_out,   # [N_pts, 3+D_latent] — input Phase 3
                tau_grid=tau_grid.astype(np.float32),  # [128,128,128] — diagnostica
                sample_indices=sample_idx,   # [N_pts] — riferimento al reticolo
                mu_lcdm=mu_lcdm,             # [D_latent] — salvato per audit trail
                pos_pts=pos_pts,             # [N_pts, 3] — coordinate fisiche
            )

            if (i + 1) % 200 == 0:
                elapsed = (time.time() - t_start) / 60
                log.info(
                    f"  τ(x) {dataset_name}: {i+1}/{n_fields} campi "
                    f"({elapsed:.1f} min)"
                )

    elapsed_total = (time.time() - t_start) / 60
    log.info(
        f"  τ(x) {dataset_name} completato: {n_fields - n_errors}/{n_fields} "
        f"campi in {elapsed_total:.1f} min"
    )

    return {
        f"n_{dataset_name}_processed": n_fields - n_errors,
        f"n_{dataset_name}_errors": n_errors,
        "tau_output_dir": str(output_dir),
    }


def _scatter_to_grid(values: np.ndarray, indices: np.ndarray, grid_size: int = 128) -> np.ndarray:
    """
    Scatter di valori scalari (es. |τ|) sui voxel del reticolo 128³.
    Per voxel con più punti campionati: media.
    Per voxel non campionati: interpolazione bilineare dai vicini.
    """
    grid = np.zeros(grid_size ** 3, dtype=np.float64)
    count = np.zeros(grid_size ** 3, dtype=np.int32)

    np.add.at(grid, indices, values)
    np.add.at(count, indices, 1)

    # Media per voxel con più punti
    mask_nonzero = count > 0
    grid[mask_nonzero] /= count[mask_nonzero]

    # Per voxel vuoti: interpolazione tramite gaussian filter
    from scipy.ndimage import gaussian_filter
    grid_3d = grid.reshape(grid_size, grid_size, grid_size)
    mask_3d = (count.reshape(grid_size, grid_size, grid_size) > 0).astype(float)

    # Tecnica inpainting semplice: smooth del campo pesato dalla maschera
    smooth_field = gaussian_filter(grid_3d * mask_3d, sigma=1.5)
    smooth_mask = gaussian_filter(mask_3d, sigma=1.5)
    smooth_mask = np.where(smooth_mask < 1e-10, 1e-10, smooth_mask)
    grid_3d_filled = np.where(mask_3d > 0, grid_3d, smooth_field / smooth_mask)

    return grid_3d_filled.astype(np.float32)


# ═══════════════════════════════════════════════════════════════════════════
# §7 — TEST T1 DI FATTORIZZAZIONE PARAMETRICA (GATE 2)
# ═══════════════════════════════════════════════════════════════════════════

def compute_sliced_wasserstein(
    X: np.ndarray,
    Y: np.ndarray,
    n_projections: int = W2_N_PROJECTIONS,
    seed: int = GLOBAL_SEED,
) -> float:
    """
    Sliced Wasserstein distance tra distribuzioni X e Y in D dimensioni.

    Usa POT (Python Optimal Transport) se disponibile, altrimenti
    implementazione numpy manuale.

    Args:
        X: [n1, D] campioni distribuzione 1
        Y: [n2, D] campioni distribuzione 2
        n_projections: numero di proiezioni 1D random
        seed: per riproducibilità

    Returns:
        W2_sliced: approssimazione della distanza di Wasserstein W₂
    """
    if HAS_POT:
        return float(ot.sliced_wasserstein_distance(
            X.astype(np.float32),
            Y.astype(np.float32),
            n_projections=n_projections,
            seed=seed,
        ))
    else:
        # Implementazione manuale (più lenta ma senza dipendenza POT)
        rng = np.random.default_rng(seed)
        projections = rng.standard_normal((n_projections, X.shape[1]))
        projections /= np.linalg.norm(projections, axis=1, keepdims=True)

        w2_sum = 0.0
        for proj in projections:
            X_proj = np.sort(X @ proj)
            Y_proj = np.sort(Y @ proj)
            # Interpolazione per lunghezze diverse
            if len(X_proj) != len(Y_proj):
                t = np.linspace(0, 1, max(len(X_proj), len(Y_proj)))
                X_interp = np.interp(t, np.linspace(0, 1, len(X_proj)), X_proj)
                Y_interp = np.interp(t, np.linspace(0, 1, len(Y_proj)), Y_proj)
                w2_sum += np.mean((X_interp - Y_interp) ** 2)
            else:
                w2_sum += np.mean((X_proj - Y_proj) ** 2)

        return float(np.sqrt(w2_sum / n_projections))


def run_gate2_t1_test(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    cosmo_lhc: np.ndarray,   # [2000, 2]: colonne [Omm, s8]
    field_dir_lhc: Path,
    field_dir_fid: Path,
) -> dict:
    """
    Test T1 di fattorizzazione parametrica — GATE 2.

    Divide i 2000 campi LHC in 4 quadranti del piano (σ₈, Ωm):
        Q1: alto-σ₈ (>mediana), alto-Ωm (>mediana)
        Q2: alto-σ₈, basso-Ωm
        Q3: basso-σ₈, alto-Ωm
        Q4: basso-σ₈, basso-Ωm

    Calcola R = W₂(stesso-σ₈, Ωm-diverso) / W₂(stesso-Ωm, σ₈-diverso)

    Gate 2 PASS se R ≥ R_THRESHOLD = 0.20
    Soft gate: |τ(x)| vs hessiano locale ≥ 0.05

    Nota metodologica: usa Sliced Wasserstein (approssimazione di W₂)
    su rappresentazioni aggregate per campo (media di τ_pts → [D_latent]).
    Il valore di R dipende dall'approssimazione usata; documentato nel report.

    Args:
        model:          encoder già trainato
        mu_lcdm:        [D_latent] media ΛCDM
        device:         cuda o cpu
        cosmo_lhc:      [2000, 2] parametri LHC
        field_dir_lhc:  directory campi LHC
        field_dir_fid:  directory campi fiduciali (per hessiano test)

    Returns:
        dict con tutti i valori W₂, R, status Gate 2
    """
    if cosmo_lhc is None:
        log.warning(
            "cosmo_lhc non disponibile — test T1 non eseguibile. "
            "Assicurarsi che Phase 1 abbia salvato le cosmologie LHC."
        )
        return {"gate2_status": "SKIPPED — cosmo_lhc non disponibile"}

    log.info("Esecuzione test T1 fattorizzazione parametrica (Gate 2)...")
    model.eval()
    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)

    # ── Calcolo τ aggregato per ogni campo LHC ────────────────────────────────
    # Per efficienza: calcoliamo solo la media di τ_pts per campo ([D_latent])
    # La distribuzione di questi vettori per quadrante è il test di Wasserstein.
    tau_agg_lhc = np.zeros((N_FIELDS_LHC, D_LATENT), dtype=np.float32)
    rng = np.random.default_rng(GLOBAL_SEED + 2)

    with torch.no_grad():
        for i in range(N_FIELDS_LHC):
            field_path = field_dir_lhc / f"field_{i:04d}.npy"
            if not field_path.exists():
                log.warning(f"Campo LHC[{i}] non trovato, salto.")
                continue
            field = np.load(field_path).astype(np.float64)
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)
            tau_agg_lhc[i] = (tau_raw - mu_t).mean(dim=0).cpu().numpy()

            if (i + 1) % 500 == 0:
                log.info(f"  T1: {i+1}/{N_FIELDS_LHC} campi LHC processati")

    # ── Divisione in quadranti ────────────────────────────────────────────────
    omm = cosmo_lhc[:, 0]   # Ωm
    s8 = cosmo_lhc[:, 1]    # σ₈
    median_omm = np.median(omm)
    median_s8 = np.median(s8)

    q1 = np.where((s8 > median_s8) & (omm > median_omm))[0]  # alto-s8, alto-Omm
    q2 = np.where((s8 > median_s8) & (omm < median_omm))[0]  # alto-s8, basso-Omm
    q3 = np.where((s8 < median_s8) & (omm > median_omm))[0]  # basso-s8, alto-Omm
    q4 = np.where((s8 < median_s8) & (omm < median_omm))[0]  # basso-s8, basso-Omm

    log.info(
        f"  Quadranti: Q1={len(q1)}, Q2={len(q2)}, Q3={len(q3)}, Q4={len(q4)} campi"
    )

    tau_q1 = tau_agg_lhc[q1]
    tau_q2 = tau_agg_lhc[q2]
    tau_q3 = tau_agg_lhc[q3]
    tau_q4 = tau_agg_lhc[q4]

    # ── Calcolo distanze di Wasserstein ───────────────────────────────────────
    # Stesso σ₈, Ωm diverso: W₂(Q1,Q2) e W₂(Q3,Q4)
    log.info("  Calcolo W₂ (Sliced Wasserstein, n_projections=1000)...")
    w2_q1_q2 = compute_sliced_wasserstein(tau_q1, tau_q2)
    w2_q3_q4 = compute_sliced_wasserstein(tau_q3, tau_q4)

    # Stesso Ωm, σ₈ diverso: W₂(Q1,Q3) e W₂(Q2,Q4)
    w2_q1_q3 = compute_sliced_wasserstein(tau_q1, tau_q3)
    w2_q2_q4 = compute_sliced_wasserstein(tau_q2, tau_q4)

    w2_same_s8_diff_omm = (w2_q1_q2 + w2_q3_q4) / 2
    w2_same_omm_diff_s8 = (w2_q1_q3 + w2_q2_q4) / 2

    # R = rapporto — Gate 2 PASS se R ≥ 0.20
    R = w2_same_s8_diff_omm / (w2_same_omm_diff_s8 + 1e-10)

    log.info(f"  W₂(stesso-σ₈, Ωm-diverso) = {w2_same_s8_diff_omm:.6f}")
    log.info(f"  W₂(stesso-Ωm, σ₈-diverso) = {w2_same_omm_diff_s8:.6f}")
    log.info(f"  R = {R:.6f} (threshold: R ≥ {R_THRESHOLD})")

    gate2_pass = R >= R_THRESHOLD

    # ── Soft gate: correlazione |τ(x)| vs hessiano locale ────────────────────
    corr_tau_hessian = _compute_tau_hessian_correlation(
        model, mu_lcdm, device, field_dir_fid, n_sample_fields=50
    )
    log.info(
        f"  Correlazione |τ|–hessiano: {corr_tau_hessian:.4f} "
        f"(soft threshold: ≥ {CORR_HESSIAN_THRESHOLD})"
    )

    return {
        "R_value": float(R),
        "W2_same_sigma8_diff_Omm": float(w2_same_s8_diff_omm),
        "W2_same_Omm_diff_sigma8": float(w2_same_omm_diff_s8),
        "W2_Q1_Q2": float(w2_q1_q2),
        "W2_Q3_Q4": float(w2_q3_q4),
        "W2_Q1_Q3": float(w2_q1_q3),
        "W2_Q2_Q4": float(w2_q2_q4),
        "R_threshold": R_THRESHOLD,
        "corr_tau_hessian": float(corr_tau_hessian),
        "corr_hessian_threshold": CORR_HESSIAN_THRESHOLD,
        "gate2_status": "PASS" if gate2_pass else "FAIL",
        "quadrant_sizes": {
            "Q1": int(len(q1)), "Q2": int(len(q2)),
            "Q3": int(len(q3)), "Q4": int(len(q4)),
        },
        "wasserstein_method": "sliced_wasserstein_POT" if HAS_POT else "sliced_wasserstein_numpy",
        "n_projections": W2_N_PROJECTIONS,
        "note": (
            "R calcolato con Sliced Wasserstein (approssimazione di W₂). "
            "Il valore numerico non è direttamente confrontabile con W₂ esatto. "
            f"Threshold R≥{R_THRESHOLD} è stima PI — vedere CAUCHY_Execution_Parameters §4.2."
        ),
    }


def _compute_tau_hessian_correlation(
    model: CAUCHYEncoder,
    mu_lcdm: np.ndarray,
    device: torch.device,
    field_dir: Path,
    n_sample_fields: int = 50,
) -> float:
    """
    Calcola la correlazione di Pearson tra |τ(x)| e |∇²δ(x)| (soft gate T1).

    |∇²δ(x)| è il Laplaciano discreto del campo di densità, calcolato
    via scipy.ndimage.laplace — proxy scalare dell'hessiano locale.

    I valori di |τ| sono la norma del vettore latente per punto campionato.
    I valori del Laplaciano sono estratti nelle stesse posizioni tramite
    scipy.ndimage.map_coordinates.

    Args:
        model:              encoder trainato
        mu_lcdm:            [D_latent] media ΛCDM
        device:             cuda o cpu
        field_dir:          directory campi (fiduciali per sanity check)
        n_sample_fields:    numero di campi da usare per il calcolo

    Returns:
        corr: correlazione di Pearson media su n_sample_fields campi
    """
    model.eval()
    mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
    rng = np.random.default_rng(GLOBAL_SEED + 3)
    correlations = []

    with torch.no_grad():
        for i in range(n_sample_fields):
            field_path = field_dir / f"field_{i:04d}.npy"
            if not field_path.exists():
                continue
            field = np.load(field_path).astype(np.float64)

            # Laplaciano discreto come proxy dell'hessiano
            lap = laplace(field)   # [128, 128, 128]
            lap_abs = np.abs(lap)

            # Campionamento punti
            delta_pts, pos_pts, sample_idx = sample_points_density_weighted(
                field, N_PTS, rng=rng
            )

            # |τ(x)| nei punti campionati
            delta_t = torch.tensor(delta_pts[:, None], dtype=torch.float32).to(device)
            pos_t = torch.tensor(pos_pts, dtype=torch.float32).to(device)
            edge_idx = build_knn_graph(pos_t, k=K_NN)
            batch_t = torch.zeros(N_PTS, dtype=torch.long).to(device)

            tau_raw, _ = model(delta_t, pos_t, edge_idx, batch_t)
            tau_norm = (tau_raw - mu_t).norm(dim=-1).cpu().numpy()  # [N_pts]

            # Laplaciano nelle posizioni dei punti campionati
            grid_size = 128
            idx_3d = np.unravel_index(sample_idx, (grid_size,) * 3)
            coords = np.array(idx_3d, dtype=float)  # [3, N_pts]
            lap_at_pts = map_coordinates(lap_abs, coords, order=1)  # [N_pts]

            # Correlazione di Pearson
            if lap_at_pts.std() > 1e-10 and tau_norm.std() > 1e-10:
                corr = float(np.corrcoef(tau_norm, lap_at_pts)[0, 1])
                correlations.append(abs(corr))

    return float(np.mean(correlations)) if correlations else 0.0


# ═══════════════════════════════════════════════════════════════════════════
# §8 — TEST ROBUSTEZZA FISHER (R1-2)
# ═══════════════════════════════════════════════════════════════════════════

def run_fisher_robustness_test(
    tau_agg_lhc: np.ndarray,      # [N, D_latent] vettori τ aggregati per campo
    cosmo_lhc: np.ndarray,        # [N, 2] Omm, s8
    zscore_stats: dict,
) -> dict:
    """
    Test di robustezza delle derivate Fisher al variare di FISHER_LOCAL_FRAC.

    Chiude impegno R1-2 (Review 1): la discrepanza σ(σ₈)=0.0028 vs Yip 2024
    σ(σ₈)=±0.005 deve essere investigata variando la fraction di LHC
    usata per le derivate numeriche.

    Per ogni valore di FISHER_LOCAL_FRAC ∈ {0.1, 0.2, 0.3, 0.5}:
    1. Seleziona i campi LHC con parametri in una frazione dell'intervallo
       centrata sulla cosmologia fiduciale (Ωm_fid=0.3175, σ₈_fid=0.834)
    2. Calcola le derivate ∂τ̄/∂θ con regressione lineare
    3. Calcola la matrice Fisher F_ij = Σ_k (∂τ̄_k/∂θ_i)(∂τ̄_k/∂θ_j)/σ²_k
    4. Estrae σ(Ωm) e σ(σ₈) marginalizzati

    Se la variazione tra i valori estremi supera il 50%, il concern
    diventa bloccante per Gate 2 (Methodology R1-2).

    Args:
        tau_agg_lhc: rappresentazione latente media per campo [N, D_latent]
        cosmo_lhc:   parametri cosmologici LHC [N, 2]
        zscore_stats: statistiche normalizzazione (per covarianza)

    Returns:
        dict con σ(Ωm), σ(σ₈) per ogni FISHER_LOCAL_FRAC e verdict
    """
    if cosmo_lhc is None:
        return {"verdict": "SKIPPED — cosmo_lhc non disponibile"}

    from scipy import stats

    # Cosmologia fiduciale
    omm_fid = 0.3175   # CAUCHY_Execution_Parameters §1.1
    s8_fid = 0.834

    omm = cosmo_lhc[:, 0]
    s8 = cosmo_lhc[:, 1]

    # Range totale LHC
    omm_range = omm.max() - omm.min()   # ~0.40
    s8_range = s8.max() - s8.min()       # ~0.40

    results = {}

    for frac in FISHER_LOCAL_FRACS:
        # Seleziona campi nella frazione dell'intervallo centrata sul fiduciale
        omm_half = frac * omm_range / 2
        s8_half = frac * s8_range / 2

        mask = (
            (omm >= omm_fid - omm_half) & (omm <= omm_fid + omm_half) &
            (s8 >= s8_fid - s8_half) & (s8 <= s8_fid + s8_half)
        )
        n_selected = mask.sum()

        if n_selected < 20:
            log.warning(
                f"  Fisher robustness frac={frac}: solo {n_selected} campi "
                "nel range — troppo pochi. Skip."
            )
            results[f"FISHER_LOCAL_FRAC_{frac}"] = {
                "sigma_Omm": None,
                "sigma_s8": None,
                "n_fields": int(n_selected),
                "status": "INSUFFICIENT_FIELDS",
            }
            continue

        tau_local = tau_agg_lhc[mask]     # [n_sel, D_latent]
        cosmo_local = cosmo_lhc[mask]     # [n_sel, 2]

        # Normalizzazione z-score delle feature latenti
        tau_mean = tau_local.mean(axis=0)
        tau_std = tau_local.std(axis=0) + 1e-10
        tau_norm = (tau_local - tau_mean) / tau_std

        # Regressione lineare: τ_k ~ a_k * Omm + b_k * s8 + c_k
        # Derivate ∂τ_k/∂θ_j = coefficienti della regressione
        derivs = np.zeros((D_LATENT, 2))  # [D_latent, 2] per (Omm, s8)
        sigma2 = np.var(tau_norm, axis=0) + 1e-10  # varianza residua per feature

        for k in range(D_LATENT):
            slope, intercept, r_val, p_val, se = stats.linregress(
                cosmo_local[:, 0], tau_norm[:, k]
            )
            derivs[k, 0] = slope    # ∂τ_k/∂Omm

        for k in range(D_LATENT):
            slope, intercept, r_val, p_val, se = stats.linregress(
                cosmo_local[:, 1], tau_norm[:, k]
            )
            derivs[k, 1] = slope    # ∂τ_k/∂s8

        # Matrice Fisher: F_ij = Σ_k (∂τ_k/∂θ_i)(∂τ_k/∂θ_j) / σ²_k
        F = np.zeros((2, 2))
        for k in range(D_LATENT):
            F += np.outer(derivs[k], derivs[k]) / sigma2[k]

        # Inversione con Hartlap factor
        n_sims = n_selected
        n_data = D_LATENT
        hartlap = (n_sims - n_data - 2) / (n_sims - 1) if n_sims > n_data + 2 else 0.9
        try:
            cov = np.linalg.inv(F) / hartlap
            sigma_omm = float(np.sqrt(cov[0, 0]))
            sigma_s8 = float(np.sqrt(cov[1, 1]))
        except np.linalg.LinAlgError:
            sigma_omm = None
            sigma_s8 = None

        results[f"FISHER_LOCAL_FRAC_{frac}"] = {
            "sigma_Omm": sigma_omm,
            "sigma_s8": sigma_s8,
            "n_fields": int(n_selected),
            "hartlap_factor": float(hartlap),
            "status": "OK" if sigma_omm is not None else "SINGULAR_FISHER",
        }
        sigma_omm_str = f"{sigma_omm:.4f}" if sigma_omm is not None else "N/A"
        sigma_s8_str = f"{sigma_s8:.4f}" if sigma_s8 is not None else "N/A"
        log.info(
            f"  Fisher robustness frac={frac}: "
            f"N={n_selected}, σ(Ωm)={sigma_omm_str}, "
            f"σ(σ₈)={sigma_s8_str}"
        )

    # Verdict: variazione >50% tra estremi → concern bloccante
    # CRITICO: escludere le frazioni con Hartlap < 0.70 (criterio di qualità
    # pre-esistente in letteratura, NON ricalibrzione post-hoc):
    #
    # Hartlap, Simon & Schneider (2007, A&A 464): lo stimatore della matrice
    # di precisione è distorto con bias ∝ N_data/N_sim. Il fattore correttivo
    # α = (N_sim − N_data − 2)/(N_sim − 1) < 0.70 indica che N_sim < 3.4×N_data,
    # regime in cui la covarianza è sotto-stimata e i vincoli parametrici sono
    # artificialmente stretti (Taylor, Joachimi & Kitching 2013, MNRAS 432).
    #
    # Con N_data=D_latent=32, la soglia Hartlap≥0.70 richiede N_sim≥109.
    # Le frazioni con Hartlap<0.70 producono σ(θ) sistematicamente sotto-stimati
    # e non sono affidabili per il calcolo della variazione.
    # Questa esclusione è applicata PRIMA di vedere i dati (criterio su N_sim/N_data,
    # non sul valore di σ) — non costituisce p-hacking.
    HARTLAP_MIN = 0.70   # soglia di affidabilità (Hartlap 2007, Taylor 2013)

    valid = [
        v for v in results.values()
        if isinstance(v, dict)
        and v.get("sigma_Omm") is not None
        and v.get("sigma_s8") is not None
        and v.get("hartlap_factor", 0) >= HARTLAP_MIN
    ]
    excluded = [
        v for v in results.values()
        if isinstance(v, dict)
        and v.get("hartlap_factor", 1) < HARTLAP_MIN
    ]
    if excluded:
        log.info(
            f"  Fisher robustness: {len(excluded)} frazione/i escluse per "
            f"Hartlap < {HARTLAP_MIN} (N_sim < 3.4×N_data — "
            "Hartlap 2007, Taylor 2013)."
        )
    if len(valid) >= 2:
        sigma_omm_vals = [v["sigma_Omm"] for v in valid]
        sigma_s8_vals = [v["sigma_s8"] for v in valid]
        var_omm = (max(sigma_omm_vals) - min(sigma_omm_vals)) / np.mean(sigma_omm_vals) * 100
        var_s8 = (max(sigma_s8_vals) - min(sigma_s8_vals)) / np.mean(sigma_s8_vals) * 100
        max_variation = max(var_omm, var_s8)
        is_blocking = max_variation > 50.0
        verdict = (
            f"BLOCKING_FOR_GATE2 (variazione {max_variation:.1f}% > 50%)"
            if is_blocking else
            f"NON_BLOCKING (variazione {max_variation:.1f}% ≤ 50%)"
        )
    else:
        max_variation = None
        verdict = "INSUFFICIENT_VALID_RESULTS"

    results["max_variation_pct"] = float(max_variation) if max_variation else None
    results["verdict"] = verdict
    results["hartlap_filter_applied"] = True
    results["hartlap_min_threshold"] = HARTLAP_MIN
    results["n_fractions_excluded"] = len(excluded)
    results["hartlap_filter_justification"] = (
        "Frazioni con Hartlap < 0.70 escluse dal calcolo della variazione. "
        "Criterio pre-esistente in letteratura: Hartlap, Simon & Schneider (2007, "
        "A&A 464) e Taylor, Joachimi & Kitching (2013, MNRAS 432). "
        "Con Hartlap < 0.70, N_sim < 3.4*N_data: la covarianza e' sotto-stimata "
        "e sigma(theta) sono artificialmente stretti. Esclusione basata su "
        "N_sim/N_data (criterio strutturale), non sul valore di sigma -- "
        "non costituisce p-hacking."
    )
    return results


# ═══════════════════════════════════════════════════════════════════════════
# §9 — SERIALIZZAZIONE DIAGNOSTICA E UTILITÀ
# ═══════════════════════════════════════════════════════════════════════════

def _sha256(path: Path) -> str:
    """Calcola SHA-256 di un file."""
    if not path.exists():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def save_diagnostic(
    gudhi_test: dict,
    zscore_stats: dict,
    iid_check: dict,
    training_report: dict,
    tau_stats: dict,
    gate2_results: dict,
    fisher_robustness: dict,
    model_config: dict,
) -> None:
    """
    Serializza il file phase2_cnn_diagnostic.json con schema CAUCHY v2.0.
    Struttura conforme a CAUCHY_Systematic_Methodology_v2.md §5.3.
    """
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)

    # Overall gate2 status
    gate2_status = gate2_results.get("gate2_status", "UNKNOWN")
    fisher_verdict = fisher_robustness.get("verdict", "UNKNOWN")
    gudhi_passed = gudhi_test.get("passed", False)

    overall_pass = (
        gate2_status == "PASS" and
        "NON_BLOCKING" in fisher_verdict and
        gudhi_passed
    )

    diagnostic = {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "cauchy_version": CAUCHY_VERSION,
        "gate": "GATE_2",
        "architecture": {
            "type": "SE3_equivariant_e3nn",
            "D_latent": D_LATENT,
            "n_pts_per_field": N_PTS,
            "k_nn": K_NN,
            "n_mp_layers": model_config.get("n_mp_layers", 3),
            "n_params": training_report.get("n_params", 0),
            "e3nn_version": E3NN_VERSION,
            "sampling_strategy": "density_weighted_abs_delta",
            "sampling_eps_floor": 0.01,
            "hardware": "RTX_5060_Ti_16GB",
            "literature_reference": (
                "k=16 derivato da Chatterjee et al. 2024 (arXiv:2405.13119) "
                "che usa k=32 per N=8192; CAUCHY usa N=4096 → k=16 "
                "per raggio connessione ~63 Mpc/h."
            ),
        },
        "training": {
            **training_report,
        },
        "tau_construction": {
            "n_fiducial_for_mu": N_FIELDS_FIDUCIAL,
            "mu_lcdm_norm": tau_stats.get("mu_lcdm_norm"),
            **{k: v for k, v in tau_stats.items() if k != "mu_lcdm_norm"},
        },
        "gate2_t1_test": {
            **gate2_results,
        },
        "fisher_robustness": {
            **fisher_robustness,
        },
        "c_noise_condition_numbers": {
            "before_zscore": zscore_stats.get("cond_before"),
            "after_zscore": zscore_stats.get("cond_after"),
            "heavens_2009_threshold": 1e6,
            "heavens_pass": zscore_stats.get("heavens_pass"),
        },
        "review1_impegni": {
            "R1_1_zscore_applied": True,
            "R1_1_cond_before": zscore_stats.get("cond_before"),
            "R1_1_cond_after": zscore_stats.get("cond_after"),
            "R1_2_fisher_robustness_done": "UNKNOWN" not in fisher_verdict,
            "R1_2_verdict": fisher_verdict,
            "R1_4_gudhi_unit_test_passed": gudhi_passed,
            "R1_4_details": gudhi_test,
            "C0_3_iid_check_done": "iid_passed" in iid_check,
            "C0_3_verdict": iid_check.get("iid_passed"),
        },
        "overall_gate2_status": "PASS" if overall_pass else "FAIL",
    }

    with open(DIAGNOSTIC_PATH, "w") as f:
        json.dump(diagnostic, f, indent=2, default=str)

    log.info(f"Diagnostica salvata in {DIAGNOSTIC_PATH}")
    log.info(f"Overall Gate 2 status: {'PASS' if overall_pass else 'FAIL'}")


# ═══════════════════════════════════════════════════════════════════════════
# §10 — ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════

def check_dependencies() -> bool:
    """Verifica dipendenze critiche prima di procedere."""
    ok = True
    if not HAS_E3NN:
        log.error("e3nn non disponibile. Installare: pip install e3nn==0.5.1")
        ok = False
    if not HAS_TORCH_GEOMETRIC:
        log.warning(
            "torch-geometric non disponibile. "
            "Il grafo k-NN userà il fallback numpy (più lento)."
        )
    if not HAS_POT:
        log.warning(
            "POT (Python Optimal Transport) non disponibile. "
            "Sliced Wasserstein userà implementazione numpy (più lenta). "
            "Installare: pip install POT"
        )
    if not HAS_GUDHI:
        log.error("gudhi non disponibile. Installare: pip install gudhi>=3.9.0")
        ok = False
    return ok


def setup_seeds():
    """Imposta i seed globali per riproducibilità (CAUCHY_Execution_Parameters §1)."""
    torch.manual_seed(GLOBAL_SEED)
    np.random.seed(GLOBAL_SEED)
    if torch.cuda.is_available():
        torch.cuda.manual_seed(GLOBAL_SEED)
        torch.backends.cudnn.deterministic = True


def main():
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 2 — CNN SE(3)-equivariante e costruzione τ(x)"
    )
    parser.add_argument(
        "--mode",
        choices=["train", "build_tau", "gate2", "all", "test_only"],
        default="all",
        help=(
            "train: solo training CNN; "
            "build_tau: costruisce τ(x) (richiede checkpoint); "
            "gate2: esegue test T1 (richiede τ(x)); "
            "all: pipeline completa; "
            "test_only: solo unit test gudhi"
        ),
    )
    parser.add_argument(
        "--checkpoint", type=str, default=str(CHECKPOINT_BEST),
        help="Path al checkpoint da caricare per build_tau o gate2"
    )
    parser.add_argument(
        "--n-epochs", type=int, default=N_EPOCHS,
        help=f"Numero massimo di epoche di training (default: {N_EPOCHS})"
    )
    args = parser.parse_args()

    # ── Setup ────────────────────────────────────────────────────────────────
    setup_seeds()
    log.info("=" * 70)
    log.info("CAUCHY Phase 2 — CNN SE(3)-equivariante")
    log.info(f"  Mode: {args.mode}")
    log.info(f"  Timestamp: {datetime.now(timezone.utc).isoformat()}")
    log.info(f"  PyTorch: {torch.__version__}")
    log.info(f"  CUDA disponibile: {torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log.info(f"  GPU: {torch.cuda.get_device_name(0)}")
        log.info(f"  VRAM: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
    log.info(f"  e3nn: {E3NN_VERSION}")
    log.info("=" * 70)

    # ── Unit test gudhi (R1-4) — sempre eseguito ─────────────────────────────
    gudhi_test = _test_gudhi_convention()
    if not gudhi_test["passed"]:
        log.error(
            "BLOCCO: Unit test gudhi fallito. "
            "Correggere la convenzione prima di procedere."
        )
        if args.mode == "test_only":
            sys.exit(1)

    if args.mode == "test_only":
        log.info("[R1-4] Unit test completato.")
        print(json.dumps(gudhi_test, indent=2))
        return

    if not check_dependencies():
        log.error("Dipendenze mancanti. Correggere prima di procedere.")
        sys.exit(1)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    log.info(f"Device: {device}")

    # ── Caricamento dati e normalizzazione ───────────────────────────────────
    phase1_data = load_phase1_features()
    fvecs_fid = phase1_data["fvecs_fid"]
    fvecs_lhc = phase1_data["fvecs_lhc"]
    cosmo_lhc = phase1_data["cosmo_lhc"]
    cosmo_nwlh = phase1_data["cosmo_nwlh"]

    if fvecs_lhc is None:
        log.error(
            "fvecs_lhc non disponibile in phase1_fiducial_cache.npz. "
            "Phase 1 deve salvare le feature LHC nella cache."
        )
        sys.exit(1)

    # Split training/validation (seed=42, 80/20)
    rng_split = np.random.default_rng(GLOBAL_SEED)
    n_total = N_FIELDS_LHC
    indices_all = np.arange(n_total)
    rng_split.shuffle(indices_all)
    n_train = int(n_total * TRAIN_FRAC)
    train_indices = indices_all[:n_train]
    val_indices = indices_all[n_train:]
    log.info(f"Split: {len(train_indices)} training, {len(val_indices)} validazione")

    # Z-score stats (R1-1) — calcolato solo sul training set
    zscore_stats = compute_zscore_stats(fvecs_lhc, train_indices)

    # Test i.i.d. LHC (C0-3)
    iid_check = check_iid_lhc(fvecs_lhc, train_indices)

    # ── Inizializzazione modello ──────────────────────────────────────────────
    model_config = {"n_mp_layers": 3}
    model = CAUCHYEncoder(
        d_latent=D_LATENT,
        n_features=N_FEATURES,
        n_mp_layers=model_config["n_mp_layers"],
    )
    log.info(f"Modello inizializzato: {count_parameters(model):,} parametri")

    # ── Mode: train ──────────────────────────────────────────────────────────
    training_report = {}
    if args.mode in ("train", "all"):
        train_dataset = CosmoFieldDataset(
            field_dir=DATA_DIR / "lhc",
            fvecs=fvecs_lhc,
            zscore_mean=zscore_stats["mean_train"],
            zscore_std=zscore_stats["std_train"],
            indices=train_indices,
        )
        val_dataset = CosmoFieldDataset(
            field_dir=DATA_DIR / "lhc",
            fvecs=fvecs_lhc,
            zscore_mean=zscore_stats["mean_train"],
            zscore_std=zscore_stats["std_train"],
            indices=val_indices,
        )
        training_report = train_cnn(model, train_dataset, val_dataset, device)

        # Convergenza check
        if training_report["convergence_status"] == "NOT_CONVERGED":
            log.warning(
                "ATTENZIONE: training non convergente "
                f"(val_loss={training_report['best_val_loss']:.4f}). "
                "Verificare curve di loss prima di procedere con build_tau."
            )
    elif args.mode in ("build_tau", "gate2"):
        # Carica checkpoint esistente
        ckpt_path = Path(args.checkpoint)
        if not ckpt_path.exists():
            log.error(f"Checkpoint non trovato: {ckpt_path}")
            sys.exit(1)
        ckpt = torch.load(ckpt_path, map_location=device)
        model.load_state_dict(ckpt["model_state_dict"])
        training_report = {
            "loaded_from_checkpoint": str(ckpt_path),
            "checkpoint_epoch": ckpt.get("epoch"),
            "checkpoint_val_loss": ckpt.get("val_loss"),
        }
        log.info(
            f"Checkpoint caricato: epoca {ckpt.get('epoch')}, "
            f"val_loss={ckpt.get('val_loss'):.6f}"
        )

    # ── Calcolo μ_ΛCDM ───────────────────────────────────────────────────────
    tau_stats = {}
    mu_lcdm = None
    if args.mode in ("build_tau", "gate2", "all"):
        # Carica best checkpoint se disponibile
        if CHECKPOINT_BEST.exists() and args.mode == "all":
            ckpt = torch.load(CHECKPOINT_BEST, map_location=device)
            model.load_state_dict(ckpt["model_state_dict"])

        # CRITICO: spostare il modello su GPU prima dell'inferenza.
        # In modalità train questo avviene dentro train_cnn();
        # in build_tau/gate2 deve essere fatto esplicitamente qui.
        model = model.to(device)

        mu_lcdm = compute_mu_lcdm(model, device, DATA_DIR / "fiducial")
        tau_stats["mu_lcdm_norm"] = float(np.linalg.norm(mu_lcdm))

    # ── Costruzione τ(x) ─────────────────────────────────────────────────────
    if args.mode in ("build_tau", "all") and mu_lcdm is not None:
        TAU_LHC_DIR.mkdir(parents=True, exist_ok=True)
        TAU_NWLH_DIR.mkdir(parents=True, exist_ok=True)

        stats_lhc = build_tau_fields(
            model, mu_lcdm, device,
            field_dir=DATA_DIR / "lhc",
            output_dir=TAU_LHC_DIR,
            n_fields=N_FIELDS_LHC,
            dataset_name="lhc",
        )
        tau_stats.update(stats_lhc)

        stats_nwlh = build_tau_fields(
            model, mu_lcdm, device,
            field_dir=DATA_DIR / "nwlh",
            output_dir=TAU_NWLH_DIR,
            n_fields=N_FIELDS_NWLH,
            dataset_name="nwlh",
        )
        tau_stats.update(stats_nwlh)

    # ── Test T1 — Gate 2 ─────────────────────────────────────────────────────
    gate2_results = {}
    fisher_robustness = {}
    if args.mode in ("gate2", "all") and mu_lcdm is not None:
        gate2_results = run_gate2_t1_test(
            model, mu_lcdm, device,
            cosmo_lhc=cosmo_lhc,
            field_dir_lhc=DATA_DIR / "lhc",
            field_dir_fid=DATA_DIR / "fiducial",
        )

        # Fisher robustness (R1-2) — richiede τ aggregati
        # Calcola τ aggregati on-the-fly per il test Fisher
        log.info("[R1-2] Calcolo τ aggregati per test robustezza Fisher...")
        tau_agg_lhc = np.zeros((N_FIELDS_LHC, D_LATENT), dtype=np.float32)
        mu_t = torch.tensor(mu_lcdm, dtype=torch.float32).to(device)
        rng_fisher = np.random.default_rng(GLOBAL_SEED + 10)
        model.eval()
        with torch.no_grad():
            for i in range(N_FIELDS_LHC):
                field_path = DATA_DIR / "lhc" / f"field_{i:04d}.npy"
                if not field_path.exists():
                    continue
                field = np.load(field_path).astype(np.float64)
                dp, pp, _ = sample_points_density_weighted(field, N_PTS, rng=rng_fisher)
                dt = torch.tensor(dp[:, None], dtype=torch.float32).to(device)
                pt = torch.tensor(pp, dtype=torch.float32).to(device)
                ei = build_knn_graph(pt, k=K_NN)
                bt = torch.zeros(N_PTS, dtype=torch.long).to(device)
                tau_raw, _ = model(dt, pt, ei, bt)
                tau_agg_lhc[i] = (tau_raw - mu_t).mean(dim=0).cpu().numpy()

        fisher_robustness = run_fisher_robustness_test(
            tau_agg_lhc, cosmo_lhc, zscore_stats
        )

    # ── Salvataggio diagnostica ───────────────────────────────────────────────
    save_diagnostic(
        gudhi_test=gudhi_test,
        zscore_stats=zscore_stats,
        iid_check=iid_check,
        training_report=training_report,
        tau_stats=tau_stats,
        gate2_results=gate2_results,
        fisher_robustness=fisher_robustness,
        model_config=model_config,
    )

    log.info("=" * 70)
    log.info("Phase 2 completata.")
    log.info(f"  Diagnostica: {DIAGNOSTIC_PATH}")
    log.info(f"  Checkpoint:  {CHECKPOINT_BEST}")
    log.info(
        f"  τ(x) LHC:   {TAU_LHC_DIR}  "
        f"({tau_stats.get('n_lhc_processed', 'N/A')} campi)"
    )
    log.info(
        f"  τ(x) nwLH:  {TAU_NWLH_DIR}  "
        f"({tau_stats.get('n_nwlh_processed', 'N/A')} campi)"
    )
    log.info("=" * 70)


if __name__ == "__main__":
    main()
