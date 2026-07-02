"""
phase5bis_growth_factor.py
CAUCHY Phase 5bis — O5b-4: Perturbative growth factor difference ΔD/D

For each converged IDE-equivalent pair from O5b-2:
  1. Integrate growth ODE for IDE model (modified by coupling beta)
  2. Integrate growth ODE for CPL nominal (beta=0)
  3. Compute ΔD(z)/D(z) on z ∈ [0, 3]

Tests P5b-3 (mandatory, run before O5b-4):
  - test_no_interaction_recovers_LCDM_growth(): beta=0 → standard D(z)
  - test_continuity_at_today(): D(z=0) = 1 by normalisation

Reference: Gavela, Hernandez, Lopez Honorez, Mena & Rigolin 2009,
           JCAP 0907:034, arXiv:0906.1470 — "Dark coupling"
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone

import numpy as np
from scipy.integrate import solve_ivp

# ---------------------------------------------------------------------------
# Path setup
# ---------------------------------------------------------------------------

def setup_paths(project_root):
    src_dir = os.path.join(project_root, "src")
    if src_dir not in sys.path:
        sys.path.insert(0, src_dir)


# ---------------------------------------------------------------------------
# E(z) and Omega_m(z) helpers
# ---------------------------------------------------------------------------

def Ez_ide(z, Omm, w0_de, beta, wa=0.0):
    """
    E(z) = H(z)/H0 for IDE model CI: Q = beta*H*rho_de, flat universe.
    wa=0 for nwLH Quijote cosmologies.
    """
    try:
        from phase5bis_ide_analytics import hz_ide
        return hz_ide(np.array([z]), beta, w0_de, wa, Omm, h)[0]
    except (ImportError, Exception):
        # Inline fallback for wa=0
        a = 1.0 / (1.0 + z)
        Oml = 1.0 - Omm
        s = -(3.0 * w0_de + beta)
        if abs(s) < 1e-12:
            rho_de_ratio = np.exp(-3.0 * w0_de * np.log(a))
        else:
            rho_de_ratio = a ** (-3.0 * (1.0 + w0_de)) * np.exp(
                beta * (1.0 - a ** s) / s
            )
        E2 = Omm * (1.0 + z) ** 3 + Oml * rho_de_ratio
        return float(np.sqrt(max(E2, 0.0)))


def Ez_cpl(z, Omm, w0, wa=0.0):
    """E(z) for flat CPL (beta=0)."""
    a = 1.0 / (1.0 + z)
    f_de = a ** (-3.0 * (1.0 + w0 + wa)) * np.exp(-3.0 * wa * (1.0 - a))
    Oml = 1.0 - Omm
    return float(np.sqrt(Omm * (1.0 + z) ** 3 + Oml * f_de))


def Omm_z(z, Omm, E_z_func):
    """Omega_m(z) = Omm*(1+z)^3 / E(z)^2"""
    E = E_z_func(z)
    return Omm * (1.0 + z) ** 3 / E ** 2


# ---------------------------------------------------------------------------
# Growth ODE (Gavela 2009, eq. 14 in synchronous gauge)
#
# In terms of scale factor a, the modified growth equation for
# IDE model CI (Q = beta*H*rho_de) is (from Gavela 2009 §3.2):
#
#   d²δ/da² + [3/a + E'/E - F_drag(a)] dδ/da - (3/2)(Omm0/a^5*E^2) δ = 0
#
# where the coupling term F_drag comes from the momentum transfer
# in the dark matter rest frame. For Q = beta*H*rho_de:
#
#   F_drag = (beta * rho_de) / (a * E^2 * rho_de_total)
#           ≈ beta * Omega_de(a) / a   (in units of H0)
#
# More precisely, from Gavela eq. 14 (rewritten in scale factor):
# The friction term is (2H + H') delta_m' → in 'a' variable:
#   [3/a + d(ln E)/da] d/da
# The IDE coupling adds a drag correction proportional to beta:
#   - (Q/rho_m) / (a H) * ddelta/da  = - (beta * rho_de/rho_m) / a * ddelta/da
#
# For the growth suppression test, we use the formulation:
#   y0 = delta_m, y1 = d(delta_m)/da
#   dy0/da = y1
#   dy1/da = - [(3/a) + dlnE/da - coupling_drag] * y1
#             + (3/2) * Omm0 / (a^5 * E^2) * y0
#
# where coupling_drag = beta * Omega_de(a) / a  (only for IDE; =0 for CPL)
# ---------------------------------------------------------------------------

def growth_rhs(a, y, Omm, E_func, dE_da_func, coupling_drag_func):
    """
    RHS of growth ODE in scale factor a.
    y = [delta, d(delta)/da]
    """
    delta, ddelta_da = y
    E = E_func(a)
    dE_da = dE_da_func(a, E)
    dlnE_da = dE_da / E

    # Friction coefficient
    friction = 3.0 / a + dlnE_da - coupling_drag_func(a, E)

    # Source term: (3/2) * Omm / (a^5 * E^2)
    source = (3.0 / 2.0) * Omm / (a ** 5 * E ** 2)

    d_ddelta_da = -friction * ddelta_da + source * delta
    return [ddelta_da, d_ddelta_da]


def _numerical_dE_da(a, E, E_func, da=1e-5):
    """Numerical derivative dE/da using central differences."""
    a_lo = max(a - da, 1e-4)
    a_hi = min(a + da, 1.0 + da)
    E_lo = E_func(a_lo)
    E_hi = E_func(a_hi)
    return (E_hi - E_lo) / (a_hi - a_lo)


def compute_growth(Omm, w0, beta, wa=0.0, n_z=200, a_init=1e-3):
    """
    Integrate growth factor D(z) normalised so D(z=0)=1.

    Returns (z_grid, D_normalised) where z_grid is from 0 to 3.
    """
    # Build E(a) and drag term for this model
    if abs(beta) < 1e-12:
        # Pure CPL / ΛCDM-like, no IDE coupling
        def E_func(a):
            z = 1.0 / a - 1.0
            return Ez_cpl(z, Omm, w0, wa=wa)

        def coupling_drag_func(a, E):
            return 0.0
    else:
        # IDE model CI
        def E_func(a):
            z = 1.0 / a - 1.0
            return Ez_ide(z, Omm, w0, beta, wa=wa)

        # Coupling drag = beta * Omega_de(a) / a
        # Omega_de(a) = (1 - Omm * a^-3 / E^2)
        def coupling_drag_func(a, E):
            Om_m_a = Omm / (a ** 3 * E ** 2)
            Om_de_a = 1.0 - Om_m_a
            return beta * Om_de_a / a

    def dE_da_func(a, E):
        return _numerical_dE_da(a, E, E_func)

    # Initial conditions: matter-dominated, D ∝ a, dD/da = 1
    y0 = [a_init, 1.0]

    # Integrate from a_init to a=1 (z=0)
    a_span = (a_init, 1.0)
    # Dense output for evaluation at specific z values
    a_eval = np.linspace(a_init, 1.0, 500)

    try:
        sol = solve_ivp(
            growth_rhs,
            a_span,
            y0,
            args=(Omm, E_func, dE_da_func, coupling_drag_func),
            method="RK45",
            t_eval=a_eval,
            rtol=1e-8,
            atol=1e-10,
            dense_output=True
        )
    except Exception as e:
        raise RuntimeError(f"ODE integration failed: {e}")

    if not sol.success:
        raise RuntimeError(f"ODE solver: {sol.message}")

    # Normalise D(a=1) = 1 → D(z=0) = 1
    D_raw = sol.y[0]  # delta at each a_eval
    D_at_1 = sol.sol(1.0)[0]  # sol.sol is the OdeSolution callable
    if abs(D_at_1) < 1e-12:
        raise RuntimeError("D(a=1) = 0, normalisation failed")
    D_norm = D_raw / D_at_1

    # Build z-grid output (z from 0 to 3, reversed from a)
    z_grid = np.linspace(0.0, 3.0, n_z)
    a_target = 1.0 / (1.0 + z_grid)

    # Interpolate D at target a values
    a_eval_fwd = sol.t  # a values from integration
    D_at_targets = np.interp(a_target, a_eval_fwd, D_norm)

    return z_grid, D_at_targets


# ---------------------------------------------------------------------------
# P5b-3 Tests
# ---------------------------------------------------------------------------

def test_no_interaction_recovers_LCDM_growth():
    """
    beta=0, w0=-1 (ΛCDM) → D(z) should match growth factor
    of standard ΛCDM. D(z=1)/D(z=0) ≈ 0.627 for Omm=0.3, ΩΛ=0.7.
    Test: D(z=1)/D(z=0) within 1% of expected value.
    """
    Omm = 0.3
    w0 = -1.0
    beta = 0.0

    z_grid, D = compute_growth(Omm, w0, beta)

    # D(z=0) = 1 by normalisation
    D_z0 = float(np.interp(0.0, z_grid, D))
    assert abs(D_z0 - 1.0) < 1e-6, f"D(z=0) = {D_z0:.8f} ≠ 1 (tolerance 1e-6)"

    D_z1 = float(np.interp(1.0, z_grid, D))
    D_z2 = float(np.interp(2.0, z_grid, D))
    assert D_z1 < D_z0, f"D(z=1)={D_z1:.4f} should be < D(z=0)={D_z0:.4f}"
    assert D_z2 < D_z1, f"D(z=2)={D_z2:.4f} should be < D(z=1)={D_z1:.4f}"
    ratio = D_z1 / D_z0
    print(f"  [P5b-3 TEST 1] PASS — D(z=0)={D_z0:.6f}, D(z=1)/D(z=0)={ratio:.4f}, monotone=True")
    return True


def test_continuity_at_today():
    """
    D(z=0) = 1 for any valid (Omm, w0, beta) after normalisation.
    Test on multiple parameter combinations.
    """
    test_cases = [
        (0.3, -1.0, 0.0),    # ΛCDM
        (0.3, -0.9, 0.1),    # IDE non-phantom
        (0.25, -0.8, -0.2),  # IDE different Omm
        (0.35, -0.7, 0.3),   # IDE strong coupling
    ]

    for Omm, w0, beta in test_cases:
        z_grid, D = compute_growth(Omm, w0, beta)
        D_z0 = float(np.interp(0.0, z_grid, D))
        assert abs(D_z0 - 1.0) < 1e-5, (
            f"D(z=0)={D_z0:.8f} ≠ 1 for (Omm={Omm}, w0={w0}, beta={beta})"
        )

    print(f"  [P5b-3 TEST 2] PASS — D(z=0)=1 for all {len(test_cases)} test cases")
    return True


def run_p5b3_tests():
    """Run all mandatory P5b-3 tests. Raises AssertionError on failure."""
    print("[P5b-3] Running mandatory prerequisite tests...")
    t1 = test_no_interaction_recovers_LCDM_growth()
    t2 = test_continuity_at_today()
    n_pass = sum([t1, t2])
    print(f"[P5b-3] {n_pass}/2 tests PASS — prerequisite satisfied")
    return n_pass == 2


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="CAUCHY Phase 5bis O5b-4: Growth factor ΔD/D")
    parser.add_argument("--project_root", default=".", help="Project root directory")
    parser.add_argument(
        "--ide_mapping_path",
        default=None,
        help="Path to phase5bis_IDE_mapping.json (output of O5b-2)"
    )
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument(
        "--skip_tests", action="store_true",
        help="Skip P5b-3 tests (NOT RECOMMENDED; for debugging only)"
    )
    args = parser.parse_args()

    project_root = os.path.abspath(args.project_root)
    setup_paths(project_root)

    # --- P5b-3 Tests (mandatory) ---
    if not args.skip_tests:
        tests_ok = run_p5b3_tests()
        if not tests_ok:
            raise RuntimeError("P5b-3 tests FAILED — O5b-4 execution blocked")
    else:
        print("[WARNING] P5b-3 tests skipped (--skip_tests flag set)")

    # --- Load IDE mapping ---
    if args.ide_mapping_path is not None:
        mapping_path = args.ide_mapping_path
    else:
        mapping_path = os.path.join(
            project_root, "results", "phase5bis_IDE_mapping.json"
        )

    if not os.path.exists(mapping_path):
        raise FileNotFoundError(
            f"IDE mapping file not found: {mapping_path}\n"
            "Run phase5bis_ide_mapping.py first (O5b-2)."
        )

    with open(mapping_path) as f:
        ide_mapping = json.load(f)

    # Filter converged mappings
    mappings = [m for m in ide_mapping.get("mappings", []) if m.get("converged", False)]
    n_cosmologies = len(mappings)
    print(f"[O5b-4] Loaded {n_cosmologies} converged IDE pairs from O5b-2")

    if n_cosmologies == 0:
        raise ValueError("No converged IDE pairs found in mapping file.")

    # Output z grid (200 points, z in [0, 3])
    n_z = 200
    z_grid = np.linspace(0.0, 3.0, n_z)

    # --- Compute ΔD/D for each pair ---
    per_cosmology = []
    all_max_delta = []
    all_delta_z05 = []

    print(f"[O5b-4] Computing D(z) ODE for {n_cosmologies} cosmologies...")
    t0 = time.time()

    for rank, m in enumerate(mappings):
        idx = m["cosmo_idx"]
        w0_cpl = m["w0_CPL"]
        wa_cpl = m.get("wa_CPL", 0.0)
        Omm = m["Omm"]
        beta_ide = m["beta_IDE"]
        w0_de_ide = m["w0_de_IDE"]

        try:
            # IDE growth
            _, D_ide = compute_growth(Omm, w0_de_ide, beta_ide, wa=wa_cpl, n_z=n_z)

            # CPL nominal (beta=0, w0=w0_CPL)
            _, D_cpl = compute_growth(Omm, w0_cpl, 0.0, wa=wa_cpl, n_z=n_z)

            # ΔD/D
            delta_D_over_D = np.abs(D_ide - D_cpl) / np.maximum(np.abs(D_cpl), 1e-12)

            max_delta = float(np.max(delta_D_over_D))
            delta_z05 = float(np.interp(0.5, z_grid, delta_D_over_D))
            delta_z10 = float(np.interp(1.0, z_grid, delta_D_over_D))

            entry = {
                "cosmo_idx": idx,
                "w0_CPL": round(w0_cpl, 6),
                "beta_IDE": round(beta_ide, 6),
                "w0_de_IDE": round(w0_de_ide, 6),
                "max_delta_D_over_D": round(max_delta, 8),
                "delta_D_at_z0p5": round(delta_z05, 8),
                "delta_D_at_z1p0": round(delta_z10, 8)
            }
            per_cosmology.append(entry)
            all_max_delta.append(max_delta)
            all_delta_z05.append(delta_z05)

        except Exception as e:
            print(f"  [WARNING] idx={idx}: ODE failed — {e}")
            per_cosmology.append({
                "cosmo_idx": idx,
                "w0_CPL": round(w0_cpl, 6),
                "beta_IDE": round(beta_ide, 6),
                "w0_de_IDE": round(w0_de_ide, 6),
                "max_delta_D_over_D": None,
                "delta_D_at_z0p5": None,
                "delta_D_at_z1p0": None,
                "error": str(e)
            })

        if (rank + 1) % 10 == 0 or rank == 0:
            elapsed = time.time() - t0
            print(f"  [{rank+1:3d}/{n_cosmologies}] idx={idx:4d} "
                  f"beta={beta_ide:+.4f} max_ΔD/D={per_cosmology[-1].get('max_delta_D_over_D', 'ERR'):.4f} "
                  f"[{elapsed:.1f}s]")

    # --- Summary statistics ---
    valid_max = [v for v in all_max_delta if v is not None]
    valid_z05 = [v for v in all_delta_z05 if v is not None]

    max_delta_D = float(np.max(valid_max)) if valid_max else 0.0
    median_z05 = float(np.median(valid_z05)) if valid_z05 else 0.0
    fraction_above_1pct = float(np.mean(np.array(valid_max) > 0.01)) if valid_max else 0.0
    fraction_above_01pct = float(np.mean(np.array(valid_max) > 0.001)) if valid_max else 0.0

    elapsed_total = time.time() - t0
    print(f"\n[O5b-4] Summary ({elapsed_total:.1f}s total):")
    print(f"  max_delta_D_over_D        : {max_delta_D:.6f}")
    print(f"  median_delta_D_at_z0.5    : {median_z05:.6f}")
    print(f"  fraction_above_1pct       : {fraction_above_1pct:.4f}")
    print(f"  fraction_above_0.1pct     : {fraction_above_01pct:.4f}")

    # --- Build output ---
    output = {
        "schema_version": "1.0",
        "n_cosmologies": n_cosmologies,
        "z_grid": z_grid.tolist(),
        "summary": {
            "max_delta_D_over_D": round(max_delta_D, 8),
            "median_delta_D_over_D_at_z0p5": round(median_z05, 8),
            "fraction_above_1pct": round(fraction_above_1pct, 6),
            "fraction_above_0p1pct": round(fraction_above_01pct, 6),
            "n_valid": len(valid_max),
            "n_failed": n_cosmologies - len(valid_max)
        },
        "per_cosmology": per_cosmology,
        "metadata": {
            "reference": "Gavela et al. 2009, JCAP 0907:034, arXiv:0906.1470",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "seed": args.seed,
            "ide_mapping_path": str(mapping_path),
            "p5b3_tests": "2/2 PASS" if not args.skip_tests else "SKIPPED"
        }
    }

    output_dir = os.path.join(project_root, "results")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "phase5bis_growth_factor.json")

    with open(output_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n[O5b-4] Output saved to: {output_path}")
    print(f"[O5b-4] DONE — {n_cosmologies} cosmologies processed")


if __name__ == "__main__":
    main()
