"""
CAUCHY — Phase 8, A/B resolution (weights explain the deficit?)
src/phase8_weight_smoothness.py

The smoothness check found DESI differs from cut-sky mocks in its ONE-POINT
statistics: less small-scale power (z=-15) but MORE high-density excursion
(z=+7) and higher gradient variance (z=+3). This is not simple 'DESI smoother';
it is a different density distribution — concentrated structure, fewer diffuse
small-scale fluctuations, hence fewer H1 loops (beta1_max z=-25).

Two readings:
  A (mundane): the mismatch is our imperfect model of the DATA field — chiefly
    that DESI is FKP-WEIGHTED (WEIGHT*WEIGHT_FKP) while the mocks are unweighted.
    Weights redistribute density (raise the dense tail) without creating loops.
  B (genuine): the real galaxy field truly has a density distribution LCDM+HOD
    does not reproduce.

Test: rebuild N mocks WITH an FKP-like per-galaxy weight and re-measure BOTH
beta1_max AND the three smoothness metrics. If the weighted mocks move TOWARD
DESI on all of them, reading A wins and the beta1_max anomaly deflates. If they
do not, reading B stands and N=2000 is warranted.

Decision rule (frozen): reading A (deflate) IF weighting moves the mock toward
DESI by > 50% of the unweighted gap on beta1_max AND on smallscale_power AND on
exc(>1). Otherwise reading B (proceed to N=2000).

Usage:
  python src\\phase8_weight_smoothness.py --n_mock 40 --project_root D:\\projects\\cauchy
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M
from phase8_weight_check import fkp_weight_at, voxelize_mock_weighted
from phase8_smoothness_check import gradient_var, small_scale_power, excursion_fraction


def metrics(nu, mask):
    return (gradient_var(nu, mask), small_scale_power(nu, mask),
            excursion_fraction(nu, mask))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_mock", type=int, default=40)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("Phase 8 — A/B resolution: do FKP weights explain the deficit?")
    print("=" * 70)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    # DESI (weighted, as in the paper) — masked TDA for beta1_max
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
    fD = M.compute_tda_features(nu_desi, mask, M.N_THRESH, masked=True)
    dgrad, dpow, dexc = metrics(nu_desi, mask)
    d_beta1 = float(fD[4])
    print(f"\nDESI (weighted): beta1_max={d_beta1:.0f}  grad={dgrad:.4g}  "
          f"power={dpow:.4g}  exc={dexc:.4g}")

    print(f"\nMocks (N={args.n_mock}): unweighted vs FKP-weighted...")
    b_u, g_u, p_u, e_u = [], [], [], []
    b_w, g_w, p_w, e_w = [], [], [], []
    for i in range(args.n_mock):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, 3)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = M.populate_halos_hod_with_vel(pos_h, mass_h, vel_h, M.HOD_MEDIAN, rng)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if len(pos_sel) < 100:
            continue
        # unweighted
        nu0 = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        f0 = M.compute_tda_features(nu0, mask, M.N_THRESH, masked=True)
        b_u.append(float(f0[4])); gg, pp, ee = metrics(nu0, mask)
        g_u.append(gg); p_u.append(pp); e_u.append(ee)
        # FKP-weighted
        alpha0 = len(pos_sel) / sum_wr
        w_sel = fkp_weight_at(pos_sel, field_r, alpha0)
        nu1 = voxelize_mock_weighted(pos_sel, w_sel, field_r, sum_wr, mask)
        f1 = M.compute_tda_features(nu1, mask, M.N_THRESH, masked=True)
        b_w.append(float(f1[4])); gg, pp, ee = metrics(nu1, mask)
        g_w.append(gg); p_w.append(pp); e_w.append(ee)
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}] beta1_max unw={np.mean(b_u):.0f} wt={np.mean(b_w):.0f} | "
                  f"power unw={np.mean(p_u):.4g} wt={np.mean(p_w):.4g} | "
                  f"exc unw={np.mean(e_u):.3g} wt={np.mean(e_w):.3g}")

    def m(x): return float(np.mean(x))

    print("\n" + "=" * 70)
    print("  metric        DESI      mock_unw   mock_wt    -> moves toward DESI?")
    def row(name, dval, uval, wval, lower_is_desi):
        gap = dval - uval
        moved = (wval - uval)
        frac = (moved / gap) if abs(gap) > 1e-12 else 0.0
        arrow = "YES" if frac > 0.5 else ("partial" if frac > 0.15 else "no")
        print(f"  {name:12s} {dval:9.4g} {uval:9.4g} {wval:9.4g}   frac={frac:+.2f}  [{arrow}]")
        return frac
    f_b = row("beta1_max", d_beta1, m(b_u), m(b_w), True)
    f_p = row("power(k>)", dpow, m(p_u), m(p_w), True)
    f_e = row("exc(>1)", dexc, m(e_u), m(e_w), False)
    f_g = row("grad_var", dgrad, m(g_u), m(g_w), False)

    print("\n" + "-" * 70)
    reading_A = (f_b > 0.5) and (f_p > 0.5) and (f_e > 0.5)
    if reading_A:
        print("  >>> READING A: FKP weights explain the deficit. The mock moves >50% of")
        print("      the way to DESI on beta1_max, small-scale power AND excursion once")
        print("      weighted like the data. The beta1_max anomaly is largely a weighting")
        print("      mismatch (data weighted, mocks not). DEFLATE — do NOT run N=2000 as")
        print("      an anomaly; pivot to the methodological paper.")
    else:
        print("  >>> READING B: FKP weights do NOT close the gap. The density-distribution")
        print("      difference (fewer loops, more concentrated structure) survives matching")
        print("      the data weighting. Proceed to N=2000 for the robust beta1_max rank.")
    print("      (frac = fraction of the unweighted DESI-mock gap closed by weighting)")


if __name__ == "__main__":
    main()
