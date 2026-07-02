"""
phase5bis_ide_mapping.py
CAUCHY Phase 5bis — O5b-2: IDE-equivalent mapping

For each of 100 uniformly sampled nwLH cosmologies (uniform over w0),
find (beta, w0_de) IDE parameters with w0_de > -1 (non-phantom)
that reproduce H(z) within 0.5% tolerance.

Reference: Neumann, Videla & Araya 2026, arXiv:2604.22970 §2.2
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
from scipy.optimize import minimize

# ---------------------------------------------------------------------------
# Path setup — allows import of phase5bis_ide_analytics from src/
# ---------------------------------------------------------------------------

def setup_paths(project_root):
    src_dir = os.path.join(project_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)

# ---------------------------------------------------------------------------
# IDE forward model (duplicated inline for safety; canonical is ide_analytics)
# ---------------------------------------------------------------------------

def hz_ide_local(z_arr, Omm, h, w0_de, beta, wa=0.0):
    """
    Compute E(z) = H(z)/H0 for IDE model CI: Q = beta*H*rho_de
    with CPL dark energy w(a) = w0_de + wa*(1-a).
    For wa=0 (nwLH Quijote case), uses closed-form solution.

    Delegates to phase5bis_ide_analytics.hz_ide when available.
    """
    try:
        from phase5bis_ide_analytics import hz_ide
        return hz_ide(z_arr, beta, w0_de, wa, Omm, h)
    except ImportError:
        # Inline fallback for wa=0
        if wa != 0.0:
            raise ValueError("Inline fallback only valid for wa=0")
        a_arr = 1.0 / (1.0 + np.asarray(z_arr, dtype=float))
        Oml_eff = 1.0 - Omm  # flat ΛCDM-like structure; dark energy ≠ Λ

        def _rho_de_over_rho_de0(a_val):
            # rho_de(a)/rho_de(a=1) for IDE CI with wa=0
            # From Neumann 2026 §2.2: integral I(a) = (1 - a^s)/s
            # s = -(3*w0_de + beta)
            s = -(3.0 * w0_de + beta)
            if abs(s) < 1e-12:
                log_term = -3.0 * w0_de * np.log(a_val)
                return np.exp(log_term)
            return a_val ** (-3.0 * (1.0 + w0_de)) * np.exp(
                beta * (1.0 - a_val ** s) / s
            )

        E2 = np.array([
            Omm * a ** (-3) + Oml_eff * _rho_de_over_rho_de0(a)
            for a in a_arr
        ])
        return np.sqrt(np.maximum(E2, 0.0))


def hz_cpl(z_arr, Omm, w0, wa=0.0):
    """E(z) for flat CPL (no interaction, beta=0)."""
    z = np.asarray(z_arr, dtype=float)
    a = 1.0 / (1.0 + z)
    f_de = a ** (-3.0 * (1.0 + w0 + wa)) * np.exp(-3.0 * wa * (1.0 - a))
    Oml = 1.0 - Omm
    return np.sqrt(Omm * (1.0 + z) ** 3 + Oml * f_de)


# ---------------------------------------------------------------------------
# Optimisation helpers
# ---------------------------------------------------------------------------

def loss_fn(params, z_grid, Omm, h, w0_cpl, wa_cpl, tol_abs):
    """
    Loss = max|Delta H/H| between IDE(beta, w0_de) and CPL(w0_cpl, wa_cpl).
    Returns large value if physically invalid.
    """
    beta, w0_de = params
    # Physical bounds enforcement (soft walls)
    if w0_de >= 0.0 or w0_de <= -1.0:
        return 1e6
    if abs(beta) > 0.5:
        return 1e6
    try:
        E_ide = hz_ide_local(z_grid, Omm, h, w0_de, beta, wa=wa_cpl)
        E_cpl = hz_cpl(z_grid, Omm, w0_cpl, wa=wa_cpl)
        if np.any(E_ide <= 0):
            return 1e6
        return float(np.max(np.abs(E_ide - E_cpl) / E_cpl))
    except Exception:
        return 1e6


def find_ide_equivalent(Omm, h, w0_cpl, wa_cpl, tol_pct, seed_offset=0):
    """
    Find (beta, w0_de) minimising max|Delta H/H| subject to w0_de in (-1, 0).
    Returns (beta, w0_de, residual, converged).
    """
    tol_abs = tol_pct / 100.0
    z_grid = np.linspace(0.01, 3.0, 200)

    # Multi-start grid to avoid local minima
    rng = np.random.default_rng(42 + seed_offset)
    best_result = None
    best_loss = 1e9

    # Grid of starting points
    beta_starts = [-0.3, -0.1, 0.0, 0.1, 0.3]
    w0_starts = [-0.9, -0.7, -0.5, -0.3]

    for b0 in beta_starts:
        for w0_start in w0_starts:
            x0 = [b0, w0_start]
            bounds = [(-0.5, 0.5), (-0.999, -0.001)]
            try:
                res = minimize(
                    loss_fn,
                    x0,
                    args=(z_grid, Omm, h, w0_cpl, wa_cpl, tol_abs),
                    method="L-BFGS-B",
                    bounds=bounds,
                    options={"maxiter": 500, "ftol": 1e-12, "gtol": 1e-8}
                )
                if res.fun < best_loss:
                    best_loss = res.fun
                    best_result = res
            except Exception:
                continue

    # Also try Nelder-Mead for robustness
    for b0 in [-0.2, 0.0, 0.2]:
        for w0_start in [-0.8, -0.5, -0.2]:
            x0 = [b0, w0_start]
            try:
                res = minimize(
                    loss_fn,
                    x0,
                    args=(z_grid, Omm, h, w0_cpl, wa_cpl, tol_abs),
                    method="Nelder-Mead",
                    options={"maxiter": 2000, "xatol": 1e-8, "fatol": 1e-10}
                )
                # Clip to bounds for Nelder-Mead
                b_opt = float(np.clip(res.x[0], -0.5, 0.5))
                w0_opt = float(np.clip(res.x[1], -0.999, -0.001))
                loss_clipped = loss_fn(
                    [b_opt, w0_opt], z_grid, Omm, h, w0_cpl, wa_cpl, tol_abs
                )
                if loss_clipped < best_loss:
                    best_loss = loss_clipped
                    best_result = type('R', (), {'x': [b_opt, w0_opt], 'fun': loss_clipped})()
            except Exception:
                continue

    if best_result is None:
        return 0.0, -0.5, 1.0, False

    beta_opt = float(np.clip(best_result.x[0], -0.5, 0.5))
    w0_opt = float(np.clip(best_result.x[1], -0.999, -0.001))
    # Recompute loss at clipped values
    final_loss = loss_fn([beta_opt, w0_opt], z_grid, Omm, h, w0_cpl, wa_cpl, tol_abs)
    converged = final_loss <= tol_abs

    return beta_opt, w0_opt, final_loss, converged


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CAUCHY Phase 5bis O5b-2: IDE mapping")
    parser.add_argument("--project_root", default=".", help="Project root directory")
    parser.add_argument(
        "--params_path",
        default=None,
        help="Path to latin_hypercube_nwLH_params.txt (7-column, header #Omega_m...w0)"
    )
    parser.add_argument("--n_sample", type=int, default=100,
                        help="Number of cosmologies to map (uniform over w0)")
    parser.add_argument("--tol_pct", type=float, default=0.5,
                        help="Tolerance in percent for H(z) matching")
    parser.add_argument("--w0_near_lcdm_thr", type=float, default=0.01,
                        help="Exclude cosmologies with |w0+1| < this threshold")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    setup_paths(project_root)

    # --- Path resolution ---
    if args.params_path is not None:
        params_path = args.params_path
    else:
        params_path = os.path.join(
            project_root,
            "data", "raw", "quijote", "3D_cubes",
            "latin_hypercube_nwLH",
            "latin_hypercube_nwLH_params.txt"
        )

    # Early path validation
    if not os.path.exists(params_path):
        raise FileNotFoundError(
            f"Parameters file not found: {params_path}\n"
            "Use --params_path to specify the correct path."
        )

    output_dir = os.path.join(project_root, "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "phase5bis_IDE_mapping.json")

    print(f"[O5b-2] Loading parameters from: {params_path}")

    # --- Load nwLH parameters ---
    # Columns: Omm(0), Omb(1), h(2), ns(3), s8(4), Mnu(5), w0(6)
    params = np.loadtxt(params_path)
    n_total = len(params)
    print(f"[O5b-2] Loaded {n_total} cosmologies")

    # Validate column count
    if params.ndim != 2 or params.shape[1] < 7:
        raise ValueError(f"Expected 7 columns, got shape {params.shape}")

    w0_all = params[:, 6]
    Omm_all = params[:, 0]
    h_all = params[:, 2]

    w0_min, w0_max = w0_all.min(), w0_all.max()
    print(f"[O5b-2] w0 range in dataset: [{w0_min:.3f}, {w0_max:.3f}]")

    # --- Select 100 cosmologies uniformly over w0 ---
    rng = np.random.default_rng(args.seed)

    # Sort by w0, then take uniform stride
    sorted_idx = np.argsort(w0_all)
    stride = n_total // args.n_sample
    candidate_indices = sorted_idx[::stride][:args.n_sample]

    # Ensure exactly n_sample
    if len(candidate_indices) < args.n_sample:
        # Fill remaining with random draw from unused
        used = set(candidate_indices.tolist())
        remaining = [i for i in range(n_total) if i not in used]
        extra = rng.choice(remaining, args.n_sample - len(candidate_indices), replace=False)
        candidate_indices = np.concatenate([candidate_indices, extra])

    candidate_indices = candidate_indices[:args.n_sample]
    print(f"[O5b-2] Selected {len(candidate_indices)} candidate cosmologies")

    # --- Classify: near-ΛCDM vs mappable ---
    mappings = []
    unmapped = []
    near_lcdm_count = 0

    wa_fixed = 0.0  # nwLH has wa = 0 by construction

    for rank, idx in enumerate(candidate_indices):
        idx = int(idx)
        w0_cpl = float(w0_all[idx])
        Omm = float(Omm_all[idx])
        h_val = float(h_all[idx])

        # Exclude near-ΛCDM
        if abs(w0_cpl + 1.0) < args.w0_near_lcdm_thr:
            near_lcdm_count += 1
            unmapped.append({
                "cosmo_idx": idx,
                "w0_CPL": round(w0_cpl, 6),
                "reason": "w0_near_LCDM"
            })
            if (rank + 1) % 10 == 0 or rank == 0:
                print(f"  [{rank+1:3d}/{args.n_sample}] idx={idx:4d} w0={w0_cpl:.3f} → EXCLUDED (near ΛCDM)")
            continue

        # Run optimisation
        beta_opt, w0_de_opt, residual, converged = find_ide_equivalent(
            Omm, h_val, w0_cpl, wa_fixed, args.tol_pct, seed_offset=idx
        )

        entry = {
            "cosmo_idx": idx,
            "w0_CPL": round(w0_cpl, 6),
            "wa_CPL": 0.0,
            "Omm": round(Omm, 6),
            "h": round(h_val, 6),
            "beta_IDE": round(beta_opt, 6),
            "w0_de_IDE": round(w0_de_opt, 6),
            "max_DH_over_H_residual": round(residual, 8),
            "converged": converged
        }
        mappings.append(entry)

        status = "CONVERGED" if converged else "NOT_CONVERGED"
        if (rank + 1) % 10 == 0 or rank == 0:
            print(f"  [{rank+1:3d}/{args.n_sample}] idx={idx:4d} "
                  f"w0={w0_cpl:.3f} → beta={beta_opt:+.4f} "
                  f"w0_de={w0_de_opt:.4f} res={residual:.4f} {status}")

    # Unmapped: not-converged entries
    for entry in mappings:
        if not entry["converged"]:
            unmapped.append({
                "cosmo_idx": entry["cosmo_idx"],
                "w0_CPL": entry["w0_CPL"],
                "reason": "optimization_not_converged"
            })

    n_ide_found = sum(1 for e in mappings if e["converged"])
    n_total_attempted = len(candidate_indices)
    fraction_ide_mappable = n_ide_found / n_total_attempted if n_total_attempted > 0 else 0.0

    print(f"\n[O5b-2] Summary:")
    print(f"  Cosmologies attempted : {n_total_attempted}")
    print(f"  Near-ΛCDM excluded    : {near_lcdm_count}")
    print(f"  IDE found (converged) : {n_ide_found}")
    print(f"  Fraction mappable     : {fraction_ide_mappable:.3f}")
    print(f"  Not converged         : {len([e for e in mappings if not e['converged']])}")

    # --- Build output ---
    output = {
        "schema_version": "1.0",
        "n_cosmo_mapped": len(mappings),
        "n_ide_found": n_ide_found,
        "fraction_ide_mappable": round(fraction_ide_mappable, 4),
        "tol_pct": args.tol_pct,
        "w0_de_nonphantom_constraint": "w0_de > -1",
        "beta_bounds": [-0.5, 0.5],
        "w0_de_bounds": [-0.999, -0.001],
        "mappings": mappings,
        "unmapped": unmapped,
        "metadata": {
            "reference": "Neumann, Videla & Araya 2026, arXiv:2604.22970 §2.2",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": args.seed,
            "n_sample_requested": args.n_sample,
            "w0_near_lcdm_thr": args.w0_near_lcdm_thr,
            "wa_fixed": wa_fixed,
            "params_path": params_path
        }
    }

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[O5b-2] Output saved to: {output_path}")
    print(f"[O5b-2] DONE — {n_ide_found}/{n_total_attempted} IDE equivalents found")


if __name__ == "__main__":
    main()
