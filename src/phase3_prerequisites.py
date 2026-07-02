#!/usr/bin/env python3
"""
CAUCHY — Phase 3 Prerequisites
================================
Verifica obbligatoria degli impegni R2-3 e R2-4 prima di Gate 3.
Autorità: gate2_prior_v1.0.json, CAUCHY_Execution_Parameters.md §5.1

Prerequisiti (da gate2_prior_v1.0.json):
  R2-3: test KS distribuzione persistenza TDA(tau) vs GRF — obbligatorio prima di Gate 3
  R2-4: varianza spaziale |tau(x)| > 5% varianza inter-campo — obbligatorio prima di Gate 3

Esito:
  results/phase3_prerequisites.json — schema_version 2.0

Uso:
  python src/phase3_prerequisites.py --repo-root /path/to/repo [--n-sample 50] [--seed 42]

Nota operativa: lancia PRIMA di qualsiasi script GNN. Se overall_prerequisites=BLOCKING,
il Ramo B è bloccato e Phase 3 non può procedere. Comunicare esito al PI per decisione.
"""

import argparse
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("phase3_prerequisites")


# ---------------------------------------------------------------------------
# Gate 2 Prior Verification (obbligatoria — misura preventiva da Reviewer Phase 2)
# ---------------------------------------------------------------------------
EXPECTED_SHA256 = "302771fcd8656d4626bd923e87c8778cd5e64fc91210cc60c05fcd0b44cd6505"


def verify_gate2_prior(repo_root: Path) -> dict:
    """
    Verifica consistenza con gate2_prior_v1.0.json.
    Se un assert fallisce: STOP — i tau(x) su disco potrebbero non corrispondere
    alla configurazione dichiarata.
    Autorità: phase3_prompt.md §Specifica Tecnica — Assert parametri frozen.
    """
    prior_path = repo_root / "prior" / "gate2_prior_v1_0.json"
    if not prior_path.exists():
        # Fallback: prova nella root del repo (come nel progetto Claude)
        prior_path = repo_root / "gate2_prior_v1_0.json"

    log.info(f"Lettura gate2_prior da: {prior_path}")
    with open(prior_path) as f:
        gate2_prior = json.load(f)

    arch = gate2_prior["frozen_architecture"]
    training = gate2_prior["frozen_training"]
    tau = gate2_prior["frozen_tau_construction"]

    assert arch["n_pts_per_field"] == 8192, (
        f"MISMATCH n_pts_per_field: atteso 8192, trovato {arch['n_pts_per_field']}. "
        "STOP — i tau(x) su disco potrebbero non corrispondere alla configurazione dichiarata."
    )
    assert arch["D_latent"] == 32, (
        f"MISMATCH D_latent: atteso 32, trovato {arch['D_latent']}. "
        "STOP — configurazione architetturale inconsistente."
    )
    assert training["checkpoint_sha256"] == EXPECTED_SHA256, (
        f"MISMATCH checkpoint_sha256:\n"
        f"  atteso:  {EXPECTED_SHA256}\n"
        f"  trovato: {training['checkpoint_sha256']}\n"
        "STOP — checkpoint non corrisponde al prior congelato."
    )

    log.info("✓ gate2_prior verificato: n_pts=8192, D_latent=32, checkpoint SHA-256 OK")
    return {
        "prior_path": str(prior_path),
        "n_pts_per_field": arch["n_pts_per_field"],
        "D_latent": arch["D_latent"],
        "checkpoint_sha256": training["checkpoint_sha256"],
        "mu_lcdm_norm": tau["mu_lcdm_norm"],
        "tau_lhc_dir": tau["tau_lhc_dir"],
        "tau_nwlh_dir": tau["tau_nwlh_dir"],
    }


# ---------------------------------------------------------------------------
# Caricamento campi tau
# ---------------------------------------------------------------------------

def load_tau_norm_field(npz_path: Path) -> np.ndarray:
    """
    Carica un campo tau e restituisce |tau(x)| = norma L2 del vettore latente per punto.
    Input: tau_points [8192, 35] — col 0:3 = coord fisiche, col 3:35 = vettore latente.
    Output: array [8192] di norme.
    Autorità: gate2_prior_v1.0.json frozen_tau_construction.tau_format_primary
    """
    data = np.load(npz_path)
    tau_pts = data["tau_points"]           # [8192, 35]
    latent = tau_pts[:, 3:]                # [8192, 32]
    tau_norm = np.linalg.norm(latent, axis=1)  # [8192]
    return tau_norm.astype(np.float64)


def load_tau_grid(npz_path: Path) -> np.ndarray:
    """
    Carica tau_grid [128,128,128] — norma |tau(x)| su griglia originale.
    Usata solo come diagnostica secondaria se disponibile.
    """
    data = np.load(npz_path)
    return data["tau_grid"].astype(np.float64)


def sample_tau_files(lhc_dir: Path, nwlh_dir: Path,
                     n_per_cosmology: int, rng: np.random.Generator):
    """
    Campiona n_per_cosmology file da ciascuna cosmologia (LHC e nwLH).
    Seed controllato da rng (seed=42 per coerenza con Phase 2).
    Autorità: phase3_prompt.md — "25 LHC + 25 nwLH campionati (seed=42)"
    """
    lhc_files = sorted(lhc_dir.glob("tau_field_*.npz"))
    nwlh_files = sorted(nwlh_dir.glob("tau_field_*.npz"))

    if len(lhc_files) < n_per_cosmology:
        raise ValueError(f"LHC: trovati {len(lhc_files)} file, richiesti {n_per_cosmology}")
    if len(nwlh_files) < n_per_cosmology:
        raise ValueError(f"nwLH: trovati {len(nwlh_files)} file, richiesti {n_per_cosmology}")

    lhc_idx = rng.choice(len(lhc_files), size=n_per_cosmology, replace=False)
    nwlh_idx = rng.choice(len(nwlh_files), size=n_per_cosmology, replace=False)

    selected_lhc = [lhc_files[i] for i in sorted(lhc_idx)]
    selected_nwlh = [nwlh_files[i] for i in sorted(nwlh_idx)]

    log.info(f"Campionati {len(selected_lhc)} campi LHC + {len(selected_nwlh)} campi nwLH")
    return selected_lhc, selected_nwlh


# ---------------------------------------------------------------------------
# TDA utility: persistence diagram via gudhi CubicalComplex
# ---------------------------------------------------------------------------

def compute_persistence_diagram_1d(tau_norm: np.ndarray, dim: int) -> np.ndarray:
    """
    Calcola il diagramma di persistenza di beta_dim su |tau| come campo 1D
    (distribuzione empirica dei valori).

    Strategia: usiamo gudhi CubicalComplex sulla distribuzione ordinata dei valori
    di |tau| — equivalente a filtrazione di superlevel sulla distribuzione empirica.
    Restituisce le persistenze (birth - death) per la dimensione specificata.

    Nota: per dati point-cloud con 8192 punti senza griglia spaziale esplicita,
    usiamo il CubicalComplex 1D sulla CDF empirica come proxy della struttura
    topologica della distribuzione scalare. Per beta_1 e beta_2 sul campo 3D
    spaziale si richiederebbe tau_grid — si usa qui l'approccio distributivo
    che è sufficiente per il test KS contro GRF (confronto delle distribuzioni
    di persistenza, non della topologia spaziale assoluta).

    Alternativa più robusta: se tau_grid [128,128,128] è disponibile, usare
    quella. Vedi note nello script — la funzione è parametrizzata per farlo.
    """
    import gudhi

    # Ordina i valori di |tau| — costruisce la filtrazione di superlevel
    # come CubicalComplex 1D sulla sequenza ordinata
    sorted_vals = np.sort(tau_norm)[::-1]  # superlevel: dal massimo al minimo

    cc = gudhi.CubicalComplex(
        dimensions=[len(sorted_vals)],
        top_dimensional_cells=sorted_vals,
    )
    cc.compute_persistence()

    pairs = cc.persistence()
    # Filtra per dimensione richiesta
    pers_dim = [(b, d) for (dim_, (b, d)) in pairs if dim_ == dim and not np.isinf(d)]
    if not pers_dim:
        return np.array([], dtype=np.float64)

    births, deaths = zip(*pers_dim)
    persistences = np.array(births, dtype=np.float64) - np.array(deaths, dtype=np.float64)
    return persistences[persistences > 0]


def compute_persistence_diagram_3d(tau_grid: np.ndarray, dim: int) -> np.ndarray:
    """
    Calcola il diagramma di persistenza di beta_dim su tau_grid [128,128,128].
    Filtrazione di superlevel (negazione del campo per gudhi).
    Usata se tau_grid è disponibile nel file NPZ.
    Autorità: Methodology §3.1 — filtrazione di superlevel su |tau(x)|
    """
    import gudhi

    # gudhi CubicalComplex usa filtrazione di sublevel; per superlevel neghiamo
    neg_grid = -tau_grid.ravel()

    cc = gudhi.CubicalComplex(
        dimensions=list(tau_grid.shape),
        top_dimensional_cells=neg_grid,
    )
    cc.compute_persistence()

    pairs = cc.persistence()
    pers_dim = [(b, d) for (dim_, (b, d)) in pairs if dim_ == dim and not np.isinf(d)]
    if not pers_dim:
        return np.array([], dtype=np.float64)

    births, deaths = zip(*pers_dim)
    # Per superlevel negato: persistenza = |birth - death| (entrambi negati)
    persistences = np.array(deaths, dtype=np.float64) - np.array(births, dtype=np.float64)
    return persistences[persistences > 0]


def get_persistences_for_field(npz_path: Path, dim: int,
                               use_3d: bool = True) -> np.ndarray:
    """
    Calcola le persistenze beta_dim per un campo tau.
    Preferisce tau_grid 3D se disponibile (più fedele alla topologia spaziale).
    Fallback: CubicalComplex 1D sulla distribuzione di |tau|.
    """
    data = np.load(npz_path)

    if use_3d and "tau_grid" in data:
        tau_grid = data["tau_grid"].astype(np.float64)
        return compute_persistence_diagram_3d(tau_grid, dim)
    else:
        tau_norm = np.linalg.norm(data["tau_points"][:, 3:], axis=1).astype(np.float64)
        return compute_persistence_diagram_1d(tau_norm, dim)


# ---------------------------------------------------------------------------
# R2-3: Test KS struttura topologica di tau vs GRF
# ---------------------------------------------------------------------------

def generate_grf_tau_grid(tau_grid: np.ndarray, rng: np.random.Generator) -> np.ndarray:
    """
    Genera un GRF sintetico con la stessa varianza di tau_grid.
    Il GRF è gaussiano isotropo — se tau(x) porta struttura topologica non-gaussiana,
    il test KS lo rileverà comparando le distribuzioni di persistenza.
    Autorità: R2-3 — "GRF sintetici con stessa varianza"
    """
    sigma = np.std(tau_grid)
    grf = rng.standard_normal(size=tau_grid.shape) * sigma
    return grf.astype(np.float64)


def compute_r2_3_ks_test(
    selected_lhc: list,
    selected_nwlh: list,
    rng: np.random.Generator,
    use_3d: bool = True,
) -> dict:
    """
    R2-3: Test KS distribuzione persistenza TDA(tau) vs GRF con stessa varianza.
    Calcola beta1 e beta2 per i 50 campi campione e li confronta con GRF sintetici.

    Criterio (Execution Parameters §5.1, phase3_prompt.md):
      Se p > 0.05 per beta1 E beta2: distribuzioni indistinguibili da GRF → BLOCKING
      Se almeno una ha p <= 0.05: struttura topologica genuina presente → PASS

    Output: dict con statistiche KS per beta1 e beta2, e verdict PASS/BLOCKING.
    """
    from scipy.stats import ks_2samp

    log.info("=== R2-3: Test KS struttura topologica tau vs GRF ===")
    all_files = selected_lhc + selected_nwlh
    n_fields = len(all_files)

    tau_pers_beta1 = []
    tau_pers_beta2 = []
    grf_pers_beta1 = []
    grf_pers_beta2 = []

    for i, npz_path in enumerate(all_files):
        log.info(f"  Campo {i+1}/{n_fields}: {npz_path.name}")
        data = np.load(npz_path)

        # --- Persistenze tau ---
        if use_3d and "tau_grid" in data:
            tau_grid = data["tau_grid"].astype(np.float64)
            p_b1 = compute_persistence_diagram_3d(tau_grid, dim=1)
            p_b2 = compute_persistence_diagram_3d(tau_grid, dim=2)

            # GRF con stessa varianza di tau_grid
            grf = generate_grf_tau_grid(tau_grid, rng)
            g_b1 = compute_persistence_diagram_3d(grf, dim=1)
            g_b2 = compute_persistence_diagram_3d(grf, dim=2)
        else:
            # Fallback 1D
            tau_norm = np.linalg.norm(data["tau_points"][:, 3:], axis=1).astype(np.float64)
            p_b1 = compute_persistence_diagram_1d(tau_norm, dim=1)
            p_b2 = compute_persistence_diagram_1d(tau_norm, dim=2)

            sigma = np.std(tau_norm)
            grf_1d = rng.standard_normal(size=len(tau_norm)) * sigma
            g_b1 = compute_persistence_diagram_1d(grf_1d, dim=1)
            g_b2 = compute_persistence_diagram_1d(grf_1d, dim=2)

        tau_pers_beta1.extend(p_b1.tolist())
        tau_pers_beta2.extend(p_b2.tolist())
        grf_pers_beta1.extend(g_b1.tolist())
        grf_pers_beta2.extend(g_b2.tolist())

    tau_b1 = np.array(tau_pers_beta1)
    tau_b2 = np.array(tau_pers_beta2)
    grf_b1 = np.array(grf_pers_beta1)
    grf_b2 = np.array(grf_pers_beta2)

    log.info(f"  beta1 — tau: {len(tau_b1)} persistenze, GRF: {len(grf_b1)} persistenze")
    log.info(f"  beta2 — tau: {len(tau_b2)} persistenze, GRF: {len(grf_b2)} persistenze")

    # Test KS a due campioni: distribuzione tau vs distribuzione GRF
    if len(tau_b1) == 0 or len(grf_b1) == 0:
        log.warning("  beta1: nessuna persistenza trovata — impossibile eseguire KS")
        ks1_stat, ks1_pval = float("nan"), float("nan")
    else:
        ks1_stat, ks1_pval = ks_2samp(tau_b1, grf_b1)

    if len(tau_b2) == 0 or len(grf_b2) == 0:
        log.warning("  beta2: nessuna persistenza trovata — impossibile eseguire KS")
        ks2_stat, ks2_pval = float("nan"), float("nan")
    else:
        ks2_stat, ks2_pval = ks_2samp(tau_b2, grf_b2)

    log.info(f"  KS beta1: stat={ks1_stat:.4f}, p={ks1_pval:.4e}")
    log.info(f"  KS beta2: stat={ks2_stat:.4f}, p={ks2_pval:.4e}")

    # Criterio R2-3:
    # p > 0.05 su ENTRAMBI beta1 e beta2 → tau indistinguibile da GRF → BLOCKING
    # Se almeno uno ha p <= 0.05 → struttura topologica non gaussiana → PASS
    # NaN trattato come fallimento del test (non abbastanza dati topologici)
    b1_distinguishable = (not np.isnan(ks1_pval)) and (ks1_pval <= 0.05)
    b2_distinguishable = (not np.isnan(ks2_pval)) and (ks2_pval <= 0.05)

    if b1_distinguishable or b2_distinguishable:
        verdict = "PASS"
        log.info("  R2-3 verdict: PASS — tau ha struttura topologica non gaussiana")
    else:
        verdict = "BLOCKING"
        log.warning("  R2-3 verdict: BLOCKING — tau indistinguibile da GRF → Ramo B bloccato")

    return {
        "n_fields_sampled": n_fields,
        "n_tau_beta1_persistences": len(tau_b1),
        "n_tau_beta2_persistences": len(tau_b2),
        "n_grf_beta1_persistences": len(grf_b1),
        "n_grf_beta2_persistences": len(grf_b2),
        "beta1_ks_stat": float(ks1_stat),
        "beta1_ks_pval": float(ks1_pval),
        "beta2_ks_stat": float(ks2_stat),
        "beta2_ks_pval": float(ks2_pval),
        "verdict": verdict,
        "note": (
            "Criterio (Execution Parameters §5.1): p>0.05 su ENTRAMBI beta1 e beta2 → BLOCKING. "
            "Anche un solo p<=0.05 implica struttura topologica genuina → PASS."
        ),
    }


# ---------------------------------------------------------------------------
# R2-4: Varianza spaziale di |tau(x)|
# ---------------------------------------------------------------------------

def compute_r2_4_spatial_variance(
    selected_lhc: list,
    selected_nwlh: list,
) -> dict:
    """
    R2-4: Varianza spaziale vs inter-campo di |tau(x)|.

    Criterio (phase3_prompt.md, Execution Parameters §5.1):
      rapporto = media(var_spaziale_per_campo) / var(norma_media_inter-campo)
      Se rapporto > 5%: tau ha struttura spaziale → PASS
      Se rapporto <= 5%: tau è sostanzialmente piatto → BLOCKING

    La varianza spaziale cattura quanto |tau(x)| varia DENTRO un singolo campo.
    La varianza inter-campo cattura quanto la norma media varia TRA campi diversi.
    Se la varianza intra-campo è trascurabile rispetto a quella inter-campo,
    la TDA su tau produce risultati equivalenti a statistiche globali.
    Autorità: R2-4 — "varianza spaziale media > 5% della varianza inter-campo"
    """
    log.info("=== R2-4: Varianza spaziale |tau(x)| vs varianza inter-campo ===")
    all_files = selected_lhc + selected_nwlh
    n_fields = len(all_files)

    spatial_variances = []
    mean_norms = []

    for i, npz_path in enumerate(all_files):
        log.info(f"  Campo {i+1}/{n_fields}: {npz_path.name}")
        data = np.load(npz_path)
        tau_pts = data["tau_points"]        # [8192, 35]
        latent = tau_pts[:, 3:]             # [8192, 32]
        tau_norm = np.linalg.norm(latent, axis=1)  # [8192]

        # Varianza spaziale: varianza di |tau(x)| all'interno di questo campo
        var_spatial = float(np.var(tau_norm))
        mean_norm = float(np.mean(tau_norm))

        spatial_variances.append(var_spatial)
        mean_norms.append(mean_norm)

        log.info(f"    var_spatial={var_spatial:.6f}, mean_norm={mean_norm:.6f}")

    spatial_variances = np.array(spatial_variances)
    mean_norms = np.array(mean_norms)

    mean_spatial_var = float(np.mean(spatial_variances))
    interfield_var = float(np.var(mean_norms))

    if interfield_var < 1e-12:
        log.error("  Varianza inter-campo quasi zero — impossibile calcolare rapporto")
        ratio_pct = float("nan")
        verdict = "BLOCKING"
    else:
        ratio_pct = float(mean_spatial_var / interfield_var * 100.0)
        verdict = "PASS" if ratio_pct > 5.0 else "BLOCKING"

    log.info(f"  mean_spatial_var = {mean_spatial_var:.6f}")
    log.info(f"  interfield_var   = {interfield_var:.6f}")
    log.info(f"  rapporto         = {ratio_pct:.2f}%")
    log.info(f"  R2-4 verdict: {verdict}")

    # Per campo: rapporto individuale (var_spaziale_campo / var_inter-campo)
    per_field_ratios = [
        float(sv / interfield_var * 100.0) if interfield_var > 1e-12 else float("nan")
        for sv in spatial_variances
    ]

    return {
        "n_fields_sampled": n_fields,
        "mean_spatial_var": mean_spatial_var,
        "interfield_var_of_mean_norm": interfield_var,
        "mean_ratio_pct": ratio_pct,
        "per_field_spatial_variances": spatial_variances.tolist(),
        "per_field_mean_norms": mean_norms.tolist(),
        "per_field_ratios_pct": per_field_ratios,
        "verdict": verdict,
        "note": (
            "Criterio (Execution Parameters §5.1): rapporto > 5% → PASS. "
            "rapporto = mean(var_spaziale_per_campo) / var(mean_norm_inter-campo) * 100."
        ),
    }


# ---------------------------------------------------------------------------
# Persistence threshold (percentile 90° sui campi fiduciali)
# ---------------------------------------------------------------------------

def compute_persistence_threshold_p90(
    repo_root: Path,
    prior_info: dict,
    rng: np.random.Generator,
    n_fiducial_sample: int = 200,
    use_3d: bool = True,
) -> float:
    """
    Calcola la soglia di persistenza come percentile 90° della distribuzione di
    persistenza sui campi fiduciali (tau≈0, persistenze brevi = rumore).
    La soglia è frozen prima del training GNN.
    Autorità: Methodology §3.1 — "calcolata prima del training GNN e congelata"
    phase3_prompt.md — "percentile 90° della distribuzione di persistenza sui campi fiduciali"

    Nota: usa i file tau dei campi nwLH come proxy per campi con tau≈0 non disponibili
    (i campi fiduciali ΛCDM potrebbero non avere file tau separati se non prodotti
    in Phase 2). Se disponibili, usa la directory specifica.

    Strategia: campiona n_fiducial_sample campi dalla directory tau_lhc (che include
    cosmologie vicine alla fiduciale), calcola le persistenze e prende il p90.
    IMPORTANTE: nella pratica, se esistono tau fiduciali separati, usarli è preferibile.
    La threshold calcolata qui è quella da congelare in gate3_prior.
    """
    log.info("=== Calcolo soglia persistenza (percentile 90° campi fiduciali) ===")

    tau_lhc_dir = repo_root / prior_info["tau_lhc_dir"]
    lhc_files = sorted(tau_lhc_dir.glob("tau_field_*.npz"))

    if len(lhc_files) == 0:
        log.warning(f"Nessun file trovato in {tau_lhc_dir}. Soglia = NaN.")
        return float("nan")

    n_sample = min(n_fiducial_sample, len(lhc_files))
    selected_idx = rng.choice(len(lhc_files), size=n_sample, replace=False)
    selected_files = [lhc_files[i] for i in sorted(selected_idx)]

    all_persistences = []
    for i, npz_path in enumerate(selected_files):
        log.info(f"  Fiduciale proxy {i+1}/{n_sample}: {npz_path.name}")
        data = np.load(npz_path)

        if use_3d and "tau_grid" in data:
            tau_grid = data["tau_grid"].astype(np.float64)
            p1 = compute_persistence_diagram_3d(tau_grid, dim=1)
            p2 = compute_persistence_diagram_3d(tau_grid, dim=2)
        else:
            tau_norm = np.linalg.norm(data["tau_points"][:, 3:], axis=1).astype(np.float64)
            p1 = compute_persistence_diagram_1d(tau_norm, dim=1)
            p2 = compute_persistence_diagram_1d(tau_norm, dim=2)

        all_persistences.extend(p1.tolist())
        all_persistences.extend(p2.tolist())

    if len(all_persistences) == 0:
        log.warning("Nessuna persistenza trovata nei campi fiduciali. Soglia = NaN.")
        return float("nan")

    threshold_p90 = float(np.percentile(all_persistences, 90))
    log.info(f"  Totale persistenze campionate: {len(all_persistences)}")
    log.info(f"  Soglia p90 = {threshold_p90:.6f}")
    log.info(f"  (da congelare in gate3_prior prima del training GNN)")
    return threshold_p90


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 3 Prerequisites — R2-3 e R2-4"
    )
    parser.add_argument(
        "--repo-root", type=Path, required=True,
        help="Root del repository CAUCHY"
    )
    parser.add_argument(
        "--n-sample", type=int, default=50,
        help="Numero totale di campi campione (metà LHC, metà nwLH). Default: 50"
    )
    parser.add_argument(
        "--seed", type=int, default=42,
        help="Seed RNG (coerente con Phase 2). Default: 42"
    )
    parser.add_argument(
        "--n-fiducial-sample", type=int, default=200,
        help="Numero di campi per calcolo soglia persistenza p90. Default: 200"
    )
    parser.add_argument(
        "--use-3d", action="store_true", default=True,
        help="Usa tau_grid 3D per TDA (default True). Fallback 1D se non disponibile."
    )
    parser.add_argument(
        "--output", type=Path, default=None,
        help="Path output JSON. Default: <repo-root>/results/phase3_prerequisites.json"
    )
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = args.repo_root.resolve()
    rng = np.random.default_rng(args.seed)

    log.info("=" * 60)
    log.info("CAUCHY — Phase 3 Prerequisites")
    log.info(f"  repo_root   : {repo_root}")
    log.info(f"  n_sample    : {args.n_sample}")
    log.info(f"  seed        : {args.seed}")
    log.info(f"  use_3d      : {args.use_3d}")
    log.info("=" * 60)

    # 0. Verifica gate2_prior (obbligatoria)
    try:
        prior_info = verify_gate2_prior(repo_root)
    except (AssertionError, FileNotFoundError) as e:
        log.error(f"VERIFICA GATE2 PRIOR FALLITA: {e}")
        sys.exit(1)

    # 1. Campionamento file
    tau_lhc_dir = repo_root / prior_info["tau_lhc_dir"]
    tau_nwlh_dir = repo_root / prior_info["tau_nwlh_dir"]

    if args.n_sample % 2 != 0:
        log.warning(f"n_sample={args.n_sample} dispari — uso {args.n_sample // 2 * 2}")
    n_per_cosmology = args.n_sample // 2  # 25 LHC + 25 nwLH = 50

    try:
        selected_lhc, selected_nwlh = sample_tau_files(
            tau_lhc_dir, tau_nwlh_dir, n_per_cosmology, rng
        )
    except (ValueError, FileNotFoundError) as e:
        log.error(f"Errore nel campionamento dei file: {e}")
        sys.exit(1)

    t_start = time.time()

    # 2. R2-3: Test KS
    log.info("")
    result_r2_3 = compute_r2_3_ks_test(selected_lhc, selected_nwlh, rng, args.use_3d)
    t_r2_3 = time.time() - t_start

    # 3. R2-4: Varianza spaziale
    log.info("")
    # Ricampiona con seed diverso per R2-4 (ma stesso insieme — stessi file)
    result_r2_4 = compute_r2_4_spatial_variance(selected_lhc, selected_nwlh)
    t_r2_4 = time.time() - t_start - t_r2_3

    # 4. Soglia persistenza p90
    log.info("")
    # Nuovo seed per campionamento fiduciali — indipendente dai precedenti
    rng_p90 = np.random.default_rng(args.seed + 1000)
    persistence_threshold_p90 = compute_persistence_threshold_p90(
        repo_root, prior_info, rng_p90, args.n_fiducial_sample, args.use_3d
    )

    # 5. Overall verdict
    overall = (
        "PASS"
        if result_r2_3["verdict"] == "PASS" and result_r2_4["verdict"] == "PASS"
        else "BLOCKING"
    )

    t_total = time.time() - t_start

    log.info("")
    log.info("=" * 60)
    log.info(f"  R2-3 verdict            : {result_r2_3['verdict']}")
    log.info(f"  R2-4 verdict            : {result_r2_4['verdict']}")
    log.info(f"  Soglia p90              : {persistence_threshold_p90:.6f}")
    log.info(f"  OVERALL PREREQUISITES   : {overall}")
    if overall == "BLOCKING":
        log.warning("  → RAMO B BLOCCATO. Comunicare al PI prima di procedere.")
    else:
        log.info("  → PASS. Procedere con architettura GNN (Sessione 1 Fase B).")
    log.info(f"  Tempo totale            : {t_total:.1f}s")
    log.info("=" * 60)

    # 6. Serializzazione output
    output_path = args.output or repo_root / "results" / "phase3_prerequisites.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    result = {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "GATE_3_apertura",
        "script_version": "phase3_prerequisites.py v1.0",
        "config": {
            "seed": args.seed,
            "n_sample_total": args.n_sample,
            "n_per_cosmology": n_per_cosmology,
            "use_3d_tda": args.use_3d,
            "n_fiducial_sample_p90": args.n_fiducial_sample,
        },
        "gate2_prior_verified": {
            "n_pts_per_field": prior_info["n_pts_per_field"],
            "D_latent": prior_info["D_latent"],
            "checkpoint_sha256": prior_info["checkpoint_sha256"],
            "status": "OK",
        },
        "R2_3_ks_test": {
            "n_fields_sampled": result_r2_3["n_fields_sampled"],
            "beta1_ks_stat": result_r2_3["beta1_ks_stat"],
            "beta1_ks_pval": result_r2_3["beta1_ks_pval"],
            "beta2_ks_stat": result_r2_3["beta2_ks_stat"],
            "beta2_ks_pval": result_r2_3["beta2_ks_pval"],
            "n_tau_beta1_persistences": result_r2_3["n_tau_beta1_persistences"],
            "n_tau_beta2_persistences": result_r2_3["n_tau_beta2_persistences"],
            "n_grf_beta1_persistences": result_r2_3["n_grf_beta1_persistences"],
            "n_grf_beta2_persistences": result_r2_3["n_grf_beta2_persistences"],
            "verdict": result_r2_3["verdict"],
            "note": result_r2_3["note"],
        },
        "R2_4_spatial_variance": {
            "n_fields_sampled": result_r2_4["n_fields_sampled"],
            "mean_spatial_var": result_r2_4["mean_spatial_var"],
            "interfield_var_of_mean_norm": result_r2_4["interfield_var_of_mean_norm"],
            "mean_ratio_pct": result_r2_4["mean_ratio_pct"],
            "per_field_ratios_pct": result_r2_4["per_field_ratios_pct"],
            "verdict": result_r2_4["verdict"],
            "note": result_r2_4["note"],
        },
        "overall_prerequisites": overall,
        "persistence_threshold_p90": persistence_threshold_p90,
        "timing": {
            "r2_3_seconds": round(t_r2_3, 1),
            "r2_4_seconds": round(t_r2_4, 1),
            "total_seconds": round(t_total, 1),
        },
    }

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2)

    log.info(f"Output scritto: {output_path}")

    # Exit code non-zero se BLOCKING — utile per automazione CI/CD
    if overall == "BLOCKING":
        sys.exit(2)


if __name__ == "__main__":
    main()
