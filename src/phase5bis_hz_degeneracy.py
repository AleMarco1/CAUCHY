"""
CAUCHY Phase 5bis — O5b-1: H(z) Degeneracy Map
================================================
Computes H(z) for all 2000 nwLH cosmologies and builds the pairwise
max|ΔH/H| degeneracy matrix. Identifies degenerate pairs below tolerance.

Usage
-----
    python phase5bis_hz_degeneracy.py \\
        --project_root D:\\projects\\cauchy \\
        --tol_pct 0.5 \\
        --seed 42

Output
------
    results/phase5bis_Hz_degeneracy.json   (canonical schema O5b-1)

Runtime estimate
----------------
    ~2000^2 / 2 = 2M pair comparisons on a 200-point z-grid.
    Vectorised numpy operations; expect 10–30 min on a modern CPU.
    Memory: 200 floats × 2000 cosmologies = 400K floats ~ 3 MB peak.

References
----------
    Neumann, Videla & Araya 2026, arXiv:2604.22970
    CAUCHY_Execution_Design_v2.md §5.6bis
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np

# ---------------------------------------------------------------------------
# Import IDE analytics module (must be in src/ or same directory)
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
# Support both src/ and project-root invocation
for candidate in [SCRIPT_DIR, os.path.join(SCRIPT_DIR, '..', 'src')]:
    if os.path.exists(os.path.join(candidate, 'phase5bis_ide_analytics.py')):
        sys.path.insert(0, candidate)
        break

from phase5bis_ide_analytics import hz_cpl


# ---------------------------------------------------------------------------
# Parameter file loading
# ---------------------------------------------------------------------------

def load_nwlh_params(project_root, params_path_override=None):
    """
    Load latin_hypercube_nwLH_params.txt.
    Columns (0-indexed): Omm Omb h ns s8 Mnu w0
    Returns array of shape (N, 7).
    """
    if params_path_override:
        params_path = os.path.join(project_root, params_path_override) \
                      if not os.path.isabs(params_path_override) \
                      else params_path_override
    else:
        params_path = os.path.join(
            project_root, 'data', 'raw', 'quijote',
            'latin_hypercube_nwLH', 'latin_hypercube_nwLH_params.txt'
        )
    if not os.path.exists(params_path):
        raise FileNotFoundError(
            f"Parameter file not found: {params_path}\n"
            "Check --project_root and ensure nwLH data is present."
        )

    # Load, skipping comment lines starting with #
    params = np.loadtxt(params_path, comments='#')
    assert params.ndim == 2 and params.shape[1] == 7, (
        f"Expected 2000×7 array, got {params.shape}"
    )
    print(f"[I] Loaded {params.shape[0]} cosmologies from {params_path}")
    print(f"[I] Column check: Omm∈[{params[:,0].min():.3f},{params[:,0].max():.3f}]  "
          f"h∈[{params[:,2].min():.3f},{params[:,2].max():.3f}]  "
          f"w0∈[{params[:,6].min():.3f},{params[:,6].max():.3f}]")
    return params


# ---------------------------------------------------------------------------
# Core degeneracy computation
# ---------------------------------------------------------------------------

def compute_Hz_grid(params, z_grid):
    """
    Compute E(z) = H(z)/H0 for all cosmologies on z_grid.

    Parameters
    ----------
    params  : (N, 7) array — nwLH cosmological parameters
    z_grid  : (M,) array  — redshift grid

    Returns
    -------
    E_matrix : (N, M) array — E(z) for each cosmology
    """
    N = params.shape[0]
    M = len(z_grid)
    E_matrix = np.zeros((N, M), dtype=np.float32)

    print(f"[I] Computing H(z) for {N} cosmologies on {M} z-points...")
    t0 = time.time()

    for i in range(N):
        Omm = params[i, 0]
        h   = params[i, 2]
        w0  = params[i, 6]
        wa  = 0.0   # nwLH suite: wa fixed to 0

        E_matrix[i, :] = hz_cpl(z_grid, w0, wa, Omm, h).astype(np.float32)

        if (i + 1) % 500 == 0:
            elapsed = time.time() - t0
            eta = elapsed / (i + 1) * (N - i - 1)
            print(f"[I]   {i+1}/{N}  elapsed={elapsed:.1f}s  ETA={eta:.1f}s")

    print(f"[I] H(z) grid complete in {time.time()-t0:.1f}s")
    return E_matrix


def compute_degeneracy_matrix(E_matrix, tol_frac, batch_size=200):
    """
    Compute pairwise max|ΔH/H| and identify degenerate pairs.

    Memory-efficient: processes in row batches to avoid N×N full matrix.

    Parameters
    ----------
    E_matrix   : (N, M) float32 array — E(z) for each cosmology
    tol_frac   : float — degeneracy tolerance as fraction (e.g. 0.005 for 0.5%)
    batch_size : int   — number of rows processed per batch

    Returns
    -------
    degenerate_pairs : list of dicts with keys i, j, max_DH_over_H
    max_DH_matrix_stats : dict with mean, p50, p95 of the full upper-triangle values
    """
    N, M = E_matrix.shape
    degenerate_pairs = []

    # For statistics we accumulate a sample of upper-triangle values
    stats_sample = []
    n_sample_target = 200_000
    sample_every = max(1, N * (N - 1) // 2 // n_sample_target)
    sample_counter = 0

    print(f"[I] Computing pairwise degeneracy matrix ({N}×{N}/2 pairs)...")
    t0 = time.time()
    total_pairs = 0

    for i_start in range(0, N, batch_size):
        i_end = min(i_start + batch_size, N)
        batch_i = E_matrix[i_start:i_end].astype(np.float64)  # (batch, M)

        for j in range(i_end, N):
            Ej = E_matrix[j].astype(np.float64)  # (M,)

            # Relative difference for each i in batch vs j
            # shape: (batch_i_size,)
            max_rel = np.max(np.abs(batch_i - Ej[np.newaxis, :]) /
                             Ej[np.newaxis, :], axis=1)

            for k, i in enumerate(range(i_start, i_end)):
                if i >= j:
                    continue
                val = float(max_rel[k])
                total_pairs += 1

                sample_counter += 1
                if sample_counter % sample_every == 0:
                    stats_sample.append(val)

                if val <= tol_frac:
                    degenerate_pairs.append({
                        "i": int(i),
                        "j": int(j),
                        "max_DH_over_H": round(val, 6)
                    })

        if (i_end % 500 == 0) or (i_end == N):
            elapsed = time.time() - t0
            pct = i_end / N * 100
            print(f"[I]   outer-i={i_end}/{N} ({pct:.0f}%)  "
                  f"pairs_so_far={total_pairs:,}  degenerate={len(degenerate_pairs):,}  "
                  f"elapsed={elapsed:.1f}s")

    print(f"[I] Degeneracy computation complete. Total pairs: {total_pairs:,}")
    print(f"[I] Degenerate pairs (tol={tol_frac*100:.2f}%): {len(degenerate_pairs):,}")

    # Summary statistics from sample
    if stats_sample:
        arr = np.array(stats_sample)
        stats = {
            "mean": float(np.mean(arr)),
            "p50":  float(np.median(arr)),
            "p95":  float(np.percentile(arr, 95)),
        }
    else:
        stats = {"mean": None, "p50": None, "p95": None}

    return degenerate_pairs, stats


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CAUCHY Phase 5bis O5b-1 — H(z) Degeneracy Map"
    )
    parser.add_argument("--project_root", default=".",
                        help="Project root directory (default: .)")
    parser.add_argument("--tol_pct", type=float, default=0.5,
                        help="Degeneracy tolerance in percent (default: 0.5)")
    parser.add_argument("--seed", type=int, default=42,
                        help="Random seed (for reproducibility metadata)")
    parser.add_argument("--z_min", type=float, default=0.01,
                        help="Minimum redshift for H(z) grid (default: 0.01)")
    parser.add_argument("--z_max", type=float, default=3.0,
                        help="Maximum redshift for H(z) grid (default: 3.0)")
    parser.add_argument("--n_z", type=int, default=200,
                        help="Number of z grid points (default: 200)")
    parser.add_argument("--batch_size", type=int, default=200,
                        help="Batch size for pairwise loop (default: 200)")
    parser.add_argument("--params_path", default=None,
                        help="Override path to nwLH params file "
                             "(absolute, or relative to project_root)")
    args = parser.parse_args()

    np.random.seed(args.seed)
    project_root = os.path.abspath(args.project_root)
    tol_frac = args.tol_pct / 100.0

    # --- Early path validation ---
    print("[I] === CAUCHY Phase 5bis O5b-1 — H(z) Degeneracy Map ===")
    print(f"[I] Project root : {project_root}")
    print(f"[I] Tolerance    : {args.tol_pct:.2f}% ({tol_frac:.5f})")

    # Load parameters
    params = load_nwlh_params(project_root, params_path_override=args.params_path)
    N = params.shape[0]

    # Build z grid (z_min > 0 to avoid trivial H(0)/H(0) = 1 comparison)
    z_grid = np.linspace(args.z_min, args.z_max, args.n_z)
    print(f"[I] z grid       : [{args.z_min}, {args.z_max}], {args.n_z} points")

    # Compute H(z) for all cosmologies
    E_matrix = compute_Hz_grid(params, z_grid)

    # Compute degeneracy pairs
    degenerate_pairs, max_DH_stats = compute_degeneracy_matrix(
        E_matrix, tol_frac, batch_size=args.batch_size
    )

    # w0 range from params
    w0_values = params[:, 6]
    w0_range = [float(np.min(w0_values)), float(np.max(w0_values))]

    # Canonical output schema O5b-1
    output = {
        "schema_version": "1.0",
        "n_cosmo": N,
        "tol_pct": args.tol_pct,
        "n_degenerate_pairs": len(degenerate_pairs),
        "fraction_degenerate": round(
            len(degenerate_pairs) / (N * (N - 1) / 2), 6
        ),
        "max_DH_H_matrix_stats": max_DH_stats,
        "w0_range_covered": w0_range,
        "wa_fixed": 0.0,
        "z_grid_params": {
            "z_min": args.z_min,
            "z_max": args.z_max,
            "n_z": args.n_z,
        },
        "note": (
            "Quijote nwLH: w0 variabile, wa=0 fisso. "
            "CPL piena (wa libero) non coperta. "
            "Tolleranza applicata su max|DeltaH(z)/H(z)| per z in [z_min, z_max]."
        ),
        "degenerate_pairs": degenerate_pairs,
        "metadata": {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": args.seed,
            "script": "phase5bis_hz_degeneracy.py",
            "reference": "Neumann, Videla & Araya 2026, arXiv:2604.22970",
        }
    }

    # Save output
    out_dir = os.path.join(project_root, 'results')
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, 'phase5bis_Hz_degeneracy.json')

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2)

    print(f"\n[I] Output saved: {out_path}")
    print(f"[I] n_degenerate_pairs : {output['n_degenerate_pairs']:,}")
    print(f"[I] fraction_degenerate: {output['fraction_degenerate']:.4f}")
    print(f"[I] max_DH_stats       : {max_DH_stats}")
    print("[I] === O5b-1 COMPLETE ===")


if __name__ == "__main__":
    main()
