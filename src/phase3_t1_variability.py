#!/usr/bin/env python3
"""
CAUCHY — Phase 3 T1 Variability
=================================
Quantificazione empirica della varianza stocastica del test T1 (Gate 2).
Esegue ≥10 run indipendenti sullo stesso checkpoint Phase 2 (SHA-256 frozen)
con seed diversi e calcola media, std, min, max di R.

Motivazione: il Reviewer Phase 2 ha registrato una riserva perché la stima
±0.05 della dispersione run-to-run non era supportata dai dati (dispersione
osservata Δ=0.121 su 3 run). Questo script fornisce la quantificazione
empirica richiesta dalla riserva Reviewer (≥10 run).

Autorità: phase2_gate_result.json T1_variability_observed.nota,
          phase2_review.json review_closure.riserva_reviewer.

Output: aggiorna il campo t1_variability_empirical in
        results/phase3_gnn_correlations.json (o crea
        results/phase3_t1_variability.json separato).

Uso:
  python src/phase3_t1_variability.py --repo-root /path/to/repo \\
      [--n-runs 15] [--base-seed 42]
      [--output-json results/phase3_t1_variability.json]

Nota: richiede il checkpoint phase2_cnn_best.pt e i tau(x) di Phase 2 su disco.
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
log = logging.getLogger("phase3_t1_variability")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
EXPECTED_SHA256 = "302771fcd8656d4626bd923e87c8778cd5e64fc91210cc60c05fcd0b44cd6505"
N_PTS_PER_FIELD = 8192
D_LATENT = 32
N_RUNS_MIN = 10
# Autorità: phase2_gate_result.json impegno_paper


# ---------------------------------------------------------------------------
# Gate 2 Prior Verification
# ---------------------------------------------------------------------------

def verify_gate2_prior(repo_root: Path) -> dict:
    prior_path = repo_root / "prior" / "gate2_prior_v1_0.json"
    if not prior_path.exists():
        prior_path = repo_root / "gate2_prior_v1_0.json"

    with open(prior_path) as f:
        gate2_prior = json.load(f)

    arch = gate2_prior["frozen_architecture"]
    training = gate2_prior["frozen_training"]

    assert arch["n_pts_per_field"] == N_PTS_PER_FIELD
    assert arch["D_latent"] == D_LATENT
    assert training["checkpoint_sha256"] == EXPECTED_SHA256, (
        f"checkpoint SHA-256 mismatch: {training['checkpoint_sha256']}"
    )
    log.info("✓ gate2_prior verificato")
    return gate2_prior


# ---------------------------------------------------------------------------
# Test T1 — singolo run con seed specifico
# ---------------------------------------------------------------------------

def run_single_t1_test(
    checkpoint_path: Path,
    tau_lhc_dir: Path,
    tau_nwlh_dir: Path,
    cosmo_lhc: np.ndarray,
    seed: int,
    n_pts: int = N_PTS_PER_FIELD,
    n_projections: int = 1000,
    k_nn: int = 16,
) -> dict:
    """
    Singolo run del test T1 (Gate 2) con seed specificato.

    Il test T1 misura R = W₂(stesso-σ₈, Ωm-diverso) / W₂(stesso-Ωm, σ₈-diverso)
    dove W₂ è la distanza di Wasserstein del 2° ordine tra distribuzioni di τ
    in quadranti del piano (σ₈, Ωm).

    La stocasticità proviene da:
    - Campionamento del sotto-insieme di campi per formare i quadranti
    - Proiezioni random nello Sliced Wasserstein

    Autorità: phase2_cnn_diagnostic.json + phase2_gate_result.json §gate2_t1_test.
    """
    import torch

    rng = np.random.default_rng(seed)

    # Carica checkpoint CNN
    log.info(f"  [seed={seed}] Caricamento checkpoint...")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    # Importa CAUCHYEncoder da phase2_cnn.py — nome classe verificato sul sorgente reale.
    # Il caricamento del checkpoint è usato solo per verificare che il modello
    # riproduca gli stessi tau(x): in questo script usiamo i tau già costruiti
    # su disco (tau_lhc_dir), quindi il modello NON è strettamente necessario.
    # Se l'import fallisce, lo script procede con i tau su disco (comportamento
    # identico al run canonico di Gate 2).
    try:
        src_dir = checkpoint_path.parent.parent / "src"
        if str(src_dir) not in sys.path:
            sys.path.insert(0, str(src_dir))
        from phase2_cnn import CAUCHYEncoder  # nome classe verificato su phase2_cnn.py
        model = CAUCHYEncoder(d_latent=D_LATENT, n_features=8, n_mp_layers=3)
        checkpoint = torch.load(checkpoint_path, map_location=device, weights_only=False)
        state_dict = checkpoint.get("model_state_dict", checkpoint)
        model.load_state_dict(state_dict)
        model = model.to(device)
        model.eval()
        model_loaded = True
        log.info(f"  [seed={seed}] CAUCHYEncoder caricato da checkpoint OK")
    except Exception as e:
        log.warning(f"  [seed={seed}] Impossibile caricare CAUCHYEncoder: {e}")
        log.warning(f"  [seed={seed}] Fallback: tau(x) letti dal disco (nessuna rielaborazione)")
        model_loaded = False

    # Campiona 200 campi LHC (100 per quadrante — subset casuale)
    n_lhc = len(cosmo_lhc)
    sample_idx = rng.choice(n_lhc, size=min(200, n_lhc), replace=False)
    cosmo_sample = cosmo_lhc[sample_idx]

    # Divide in quadranti del piano (σ₈, Ωm)
    omm_median = np.median(cosmo_sample[:, 0])
    s8_median = np.median(cosmo_sample[:, 1])

    mask_lo_omm_lo_s8 = (cosmo_sample[:, 0] < omm_median) & (cosmo_sample[:, 1] < s8_median)
    mask_lo_omm_hi_s8 = (cosmo_sample[:, 0] < omm_median) & (cosmo_sample[:, 1] >= s8_median)
    mask_hi_omm_lo_s8 = (cosmo_sample[:, 0] >= omm_median) & (cosmo_sample[:, 1] < s8_median)
    mask_hi_omm_hi_s8 = (cosmo_sample[:, 0] >= omm_median) & (cosmo_sample[:, 1] >= s8_median)

    quadrant_masks = [mask_lo_omm_lo_s8, mask_lo_omm_hi_s8, mask_hi_omm_lo_s8, mask_hi_omm_hi_s8]

    # Carica tau(x) dal disco per i campi campionati
    lhc_files_all = sorted(tau_lhc_dir.glob("tau_field_*.npz"))
    if len(lhc_files_all) < n_lhc:
        raise FileNotFoundError(f"Trovati {len(lhc_files_all)} file tau LHC, attesi {n_lhc}")

    log.info(f"  [seed={seed}] Caricamento {len(sample_idx)} campi tau...")
    tau_latents = []
    for i in sample_idx:
        npz = np.load(lhc_files_all[i])
        latent = npz["tau_points"][:, 3:]   # [8192, 32]
        # Mean-pool per ottenere un vettore per campo
        tau_latents.append(latent.mean(axis=0))  # [32]

    tau_latents = np.array(tau_latents)  # [N_sample, 32]

    # Calcola W₂ sliced (POT) tra distribuzioni di τ nei quadranti
    try:
        import ot
        rng_proj = np.random.default_rng(seed + 10000)

        def sliced_w2(X: np.ndarray, Y: np.ndarray, n_proj: int) -> float:
            """Sliced Wasserstein distance W₂."""
            if len(X) == 0 or len(Y) == 0:
                return float("nan")
            d = X.shape[1]
            projs = rng_proj.standard_normal((n_proj, d))
            projs /= np.linalg.norm(projs, axis=1, keepdims=True) + 1e-12
            X_proj = X @ projs.T  # [N, n_proj]
            Y_proj = Y @ projs.T  # [M, n_proj]
            sw = 0.0
            for j in range(n_proj):
                xp = np.sort(X_proj[:, j])
                yp = np.sort(Y_proj[:, j])
                # Interpolazione per campioni di dimensioni diverse
                t = np.linspace(0, 1, max(len(xp), len(yp)))
                xp_i = np.interp(t, np.linspace(0, 1, len(xp)), xp)
                yp_i = np.interp(t, np.linspace(0, 1, len(yp)), yp)
                sw += np.mean((xp_i - yp_i) ** 2)
            return float(np.sqrt(sw / n_proj))

        # W₂ tra (stesso σ₈ diverso Ωm): quadrante lo-σ₈ vs hi-Ωm lo-σ₈
        tau_lo_s8_lo_omm = tau_latents[mask_lo_omm_lo_s8]
        tau_lo_s8_hi_omm = tau_latents[mask_hi_omm_lo_s8]
        tau_hi_s8_lo_omm = tau_latents[mask_lo_omm_hi_s8]
        tau_hi_s8_hi_omm = tau_latents[mask_hi_omm_hi_s8]

        # W₂(stesso-σ₈, diverso-Ωm): distanza tra quadranti con σ₈ simile ma Ωm diverso
        w2_same_s8_diff_omm = (
            sliced_w2(tau_lo_s8_lo_omm, tau_lo_s8_hi_omm, n_projections) +
            sliced_w2(tau_hi_s8_lo_omm, tau_hi_s8_hi_omm, n_projections)
        ) / 2.0

        # W₂(stesso-Ωm, diverso-σ₈): distanza tra quadranti con Ωm simile ma σ₈ diverso
        w2_same_omm_diff_s8 = (
            sliced_w2(tau_lo_s8_lo_omm, tau_hi_s8_lo_omm, n_projections) +
            sliced_w2(tau_lo_s8_hi_omm, tau_hi_s8_hi_omm, n_projections)
        ) / 2.0

        if w2_same_omm_diff_s8 < 1e-12:
            R = float("nan")
            log.warning(f"  [seed={seed}] W₂(stesso-Ωm) ≈ 0 — R non calcolabile")
        else:
            R = w2_same_s8_diff_omm / w2_same_omm_diff_s8

        log.info(f"  [seed={seed}] W₂(same_s8)={w2_same_s8_diff_omm:.4f}, "
                 f"W₂(same_omm)={w2_same_omm_diff_s8:.4f}, R={R:.4f}")

        return {
            "seed": seed,
            "R": float(R),
            "W2_same_s8_diff_omm": float(w2_same_s8_diff_omm),
            "W2_same_omm_diff_s8": float(w2_same_omm_diff_s8),
            "n_fields_sampled": int(len(sample_idx)),
            "model_loaded": model_loaded,
            "ot_backend": "POT_sliced",
        }

    except ImportError:
        log.warning("  POT non disponibile — calcolo R approssimato con distanza L2 tra medie")
        # Approssimazione: distanza tra medie dei quadranti
        mu_lo_s8_lo_omm = tau_latents[mask_lo_omm_lo_s8].mean(axis=0)
        mu_lo_s8_hi_omm = tau_latents[mask_hi_omm_lo_s8].mean(axis=0)
        mu_hi_s8_lo_omm = tau_latents[mask_lo_omm_hi_s8].mean(axis=0)
        mu_hi_s8_hi_omm = tau_latents[mask_hi_omm_hi_s8].mean(axis=0)

        d_same_s8 = (np.linalg.norm(mu_lo_s8_lo_omm - mu_lo_s8_hi_omm) +
                     np.linalg.norm(mu_hi_s8_lo_omm - mu_hi_s8_hi_omm)) / 2.0
        d_same_omm = (np.linalg.norm(mu_lo_s8_lo_omm - mu_hi_s8_lo_omm) +
                      np.linalg.norm(mu_lo_s8_hi_omm - mu_hi_s8_hi_omm)) / 2.0

        R = float(d_same_s8 / d_same_omm) if d_same_omm > 1e-12 else float("nan")
        log.info(f"  [seed={seed}] R(approx_L2)={R:.4f}")
        return {
            "seed": seed,
            "R": R,
            "W2_same_s8_diff_omm": float(d_same_s8),
            "W2_same_omm_diff_s8": float(d_same_omm),
            "n_fields_sampled": int(len(sample_idx)),
            "model_loaded": model_loaded,
            "ot_backend": "approx_L2_fallback",
        }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    parser = argparse.ArgumentParser(description="CAUCHY Phase 3 T1 Variability")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--n-runs", type=int, default=15,
                        help=f"Numero di run (min {N_RUNS_MIN}). Default: 15")
    parser.add_argument("--base-seed", type=int, default=42,
                        help="Seed base — run i usa seed base+i*100. Default: 42")
    parser.add_argument("--n-projections", type=int, default=1000,
                        help="Numero proiezioni Sliced Wasserstein. Default: 1000")
    parser.add_argument("--output-json", type=Path, default=None,
                        help="Output JSON separato. Default: results/phase3_t1_variability.json")
    parser.add_argument("--merge-into", type=Path, default=None,
                        help="Se specificato, aggiorna t1_variability_empirical in questo JSON")
    return parser.parse_args()


def main():
    args = parse_args()
    repo_root = args.repo_root.resolve()

    if args.n_runs < N_RUNS_MIN:
        log.error(f"--n-runs={args.n_runs} < {N_RUNS_MIN} (minimo richiesto dalla riserva Reviewer)")
        sys.exit(1)

    log.info("=" * 60)
    log.info("CAUCHY — Phase 3 T1 Variability")
    log.info(f"  repo_root   : {repo_root}")
    log.info(f"  n_runs      : {args.n_runs}")
    log.info(f"  base_seed   : {args.base_seed}")
    log.info("=" * 60)

    # Assert gate2_prior
    try:
        gate2_prior = verify_gate2_prior(repo_root)
    except (AssertionError, FileNotFoundError) as e:
        log.error(f"VERIFICA GATE2 PRIOR FALLITA: {e}")
        sys.exit(1)

    checkpoint_path = repo_root / gate2_prior["frozen_training"]["checkpoint_path"]
    tau_lhc_dir = repo_root / gate2_prior["frozen_tau_construction"]["tau_lhc_dir"]
    tau_nwlh_dir = repo_root / gate2_prior["frozen_tau_construction"]["tau_nwlh_dir"]

    # Carica cosmologie LHC
    cache_path = repo_root / "results" / "phase1_fiducial_cache.npz"
    cosmo_cache = np.load(cache_path)
    cosmo_lhc = cosmo_cache["cosmo_lhc"]  # [2000, 2]

    # Esegue n_runs test T1
    run_results = []
    R_values = []
    t_start = time.time()

    for run_i in range(args.n_runs):
        seed_i = args.base_seed + run_i * 100
        log.info(f"\n--- Run {run_i+1}/{args.n_runs} (seed={seed_i}) ---")
        try:
            result = run_single_t1_test(
                checkpoint_path=checkpoint_path,
                tau_lhc_dir=tau_lhc_dir,
                tau_nwlh_dir=tau_nwlh_dir,
                cosmo_lhc=cosmo_lhc,
                seed=seed_i,
                n_projections=args.n_projections,
            )
            run_results.append(result)
            if not np.isnan(result["R"]):
                R_values.append(result["R"])
        except Exception as e:
            log.error(f"  Run {run_i+1} fallito: {e}")
            run_results.append({"seed": seed_i, "R": float("nan"), "error": str(e)})

    t_total = time.time() - t_start

    # Statistiche
    R_arr = np.array([r for r in R_values if not np.isnan(r)])
    if len(R_arr) == 0:
        log.error("Nessun run completato con successo.")
        sys.exit(1)

    R_mean = float(np.mean(R_arr))
    R_std = float(np.std(R_arr))
    R_min = float(np.min(R_arr))
    R_max = float(np.max(R_arr))
    R_delta = R_max - R_min

    log.info("\n" + "=" * 60)
    log.info(f"  Run completati: {len(R_arr)}/{args.n_runs}")
    log.info(f"  R_mean = {R_mean:.4f}")
    log.info(f"  R_std  = {R_std:.4f}")
    log.info(f"  R_min  = {R_min:.4f}")
    log.info(f"  R_max  = {R_max:.4f}")
    log.info(f"  Δ(max-min) = {R_delta:.4f}")
    log.info(f"  Confronto Gate 2 canonical: R=0.862, threshold=0.20")
    log.info(f"  Margine sul threshold: {R_mean - 0.20:.4f}")
    log.info("=" * 60)

    variability_result = {
        "n_runs": len(R_arr),
        "n_runs_requested": args.n_runs,
        "n_runs_failed": args.n_runs - len(R_arr),
        "R_mean": R_mean,
        "R_std": R_std,
        "R_min": R_min,
        "R_max": R_max,
        "R_delta_max_min": R_delta,
        "R_canonical_gate2": 0.862,
        "R_threshold_gate2": 0.20,
        "margin_above_threshold": R_mean - 0.20,
        "note": (
            "Quantificazione empirica della varianza stocastica del test T1. "
            "Richiesta dalla riserva Reviewer Phase 2 (phase2_gate_result.json). "
            "Da includere nella sezione metodi del paper come stima dell'incertezza del gate criterion."
        ),
        "per_run_results": run_results,
        "base_seed": args.base_seed,
        "seeds_used": [args.base_seed + i * 100 for i in range(args.n_runs)],
    }

    # Output JSON separato
    output_path = args.output_json or repo_root / "results" / "phase3_t1_variability.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_doc = {
        "schema_version": "2.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "gate": "GATE_3",
        "authority": "phase2_gate_result.json T1_variability_observed.impegno_paper",
        "script_version": "phase3_t1_variability.py v1.0",
        "gate2_prior_verified": {
            "checkpoint_sha256": EXPECTED_SHA256,
            "status": "OK",
        },
        "t1_variability_empirical": variability_result,
        "timing": {"total_seconds": round(t_total, 1)},
    }

    with open(output_path, "w") as f:
        json.dump(output_doc, f, indent=2)
    log.info(f"Output scritto: {output_path}")

    # Merge opzionale in phase3_gnn_correlations.json
    if args.merge_into and args.merge_into.exists():
        log.info(f"Aggiornamento t1_variability_empirical in: {args.merge_into}")
        with open(args.merge_into) as f:
            gnn_result = json.load(f)
        gnn_result["t1_variability_empirical"] = variability_result
        with open(args.merge_into, "w") as f:
            json.dump(gnn_result, f, indent=2)
        log.info(f"✓ Aggiornato {args.merge_into}")


if __name__ == "__main__":
    main()
