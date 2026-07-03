"""
CAUCHY — Phase 8, fiber-assignment surrogate
src/phase8_fiber_surrogate.py

Last untested mundane explanation for the beta1_max deficit: DESI fiber-assignment
incompleteness. Fibers cannot be placed on all galaxies in angularly crowded
regions, so DESI preferentially LOSES galaxies where they are densest — a
density-dependent decimation that could suppress small-scale structure and loops.

We do NOT have the DESI altmtl / fast-fiberassign mocks (the proper test). This is
a SURROGATE: apply a density-dependent decimation to the cut-sky mocks and see if
it moves beta1_max toward DESI. Decimation model: a galaxy is dropped with
probability p_drop(local_density) that rises with the local projected galaxy count,
controlled by a strength f (mean drop fraction). We scan f from mild (BGS-like,
~2-5%) to aggressive (~30%).

Reading:
  - If even aggressive density-dependent decimation does NOT move the mock
    beta1_max toward DESI, fiber-assignment is unlikely to explain the deficit;
    report as a passed surrogate check (full altmtl test = future work).
  - If mild decimation moves the mock substantially toward DESI, fiber-assignment
    is a serious candidate; download altmtl and run the real test.

Note: DESI data already carry completeness weights (WEIGHT_COMP in WEIGHT), and the
weight check showed beta1_max is robust to weighting — an independent hint that
incompleteness (as captured by weights) does not drive the deficit. The surrogate
tests the residual topological effect of the decimation itself.

Usage:
  python src\\phase8_fiber_surrogate.py --n_mock 60 --project_root D:\\projects\\cauchy
"""

import argparse, json, sys
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M
from phase8_test2_masked import populate_with_virial, recompute_desi_reference_masked

DROP_STRENGTHS = [0.0, 0.05, 0.15, 0.30]   # mean drop fraction (0 = baseline)


def local_density(pos_sel, mask, smooth_vox=2.0):
    """Local projected galaxy density at each galaxy, from a coarse CIC count of
    the selected galaxies smoothed on the embedding grid. Returns per-galaxy density."""
    from scipy.ndimage import gaussian_filter
    cnt = M.cic_3d(pos_sel, np.ones(len(pos_sel)), M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    cnt = gaussian_filter(cnt, sigma=smooth_vox)
    ijk = np.clip(((pos_sel - M.BOX_MIN[None, :]) / M.CELL).astype(np.int32), 0, M.NGRID - 1)
    return cnt[ijk[:, 0], ijk[:, 1], ijk[:, 2]]


def decimate(pos_sel, mask, f_drop, rng):
    """Density-dependent decimation: drop probability increases with local density,
    normalised so the MEAN drop fraction equals f_drop. p_i = f_drop * d_i / <d>,
    clipped to [0,1]."""
    if f_drop <= 0:
        return pos_sel
    d = local_density(pos_sel, mask)
    dm = d.mean()
    if dm <= 0:
        return pos_sel
    p = np.clip(f_drop * d / dm, 0.0, 1.0)
    keep = rng.random(len(pos_sel)) >= p
    return pos_sel[keep]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_mock", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("Phase 8 — fiber-assignment SURROGATE (density-dependent decimation)")
    print("=" * 70)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    desi_pers1, desi_beta1 = recompute_desi_reference_masked(mask, field_r, sum_wr)
    print(f"  DESI (masked): beta1_max={desi_beta1:.0f}")
    print(f"  drop strengths f = {DROP_STRENGTHS}")

    # per strength: list of beta1_max across mocks
    res = {f: [] for f in DROP_STRENGTHS}
    for i in range(args.n_mock):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, 3)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = populate_with_virial(pos_h, mass_h, vel_h, M.HOD_MEDIAN, rng)
        pos_sel_full = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if len(pos_sel_full) < 100:
            continue
        for f in DROP_STRENGTHS:
            pos_dec = decimate(pos_sel_full, mask, f, np.random.default_rng(args.seed + i + int(f*1000)))
            nu = M.voxelize_mock(pos_dec, field_r, sum_wr, mask)
            if nu is None:
                res[f].append(np.nan); continue
            feats = M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)
            res[f].append(float(feats[4]))
        if (i + 1) % 10 == 0:
            line = f"  [{i+1}]"
            for f in DROP_STRENGTHS:
                v = np.array(res[f]); v = v[np.isfinite(v)]
                line += f"  f={f}:{v.mean():.0f}"
            print(line)

    print("\n" + "=" * 70)
    print(f"  DESI beta1_max = {desi_beta1:.0f}")
    base = np.array(res[0.0]); base = base[np.isfinite(base)]
    base_mean = base.mean()
    print(f"  {'f_drop':>8} {'mock_beta1':>12} {'std':>8} {'gap_to_DESI':>12} {'frac_closed':>12}")
    verdict_move = False
    summary = {}
    for f in DROP_STRENGTHS:
        v = np.array(res[f]); v = v[np.isfinite(v)]
        gap0 = base_mean - desi_beta1
        frac = (base_mean - v.mean()) / gap0 if abs(gap0) > 1 else 0.0
        print(f"  {f:>8} {v.mean():>12.0f} {v.std(ddof=1):>8.0f} "
              f"{v.mean()-desi_beta1:>12.0f} {frac:>12.2f}")
        summary[str(f)] = {"mean": float(v.mean()), "std": float(v.std(ddof=1)),
                           "frac_gap_closed": float(frac)}
        if f > 0 and frac > 0.5:
            verdict_move = True

    print("\n" + "-" * 70)
    if verdict_move:
        print("  >>> SURROGATE MOVES the deficit: density-dependent decimation brings")
        print("      the mock toward DESI. Fiber-assignment is a serious candidate —")
        print("      download DESI altmtl mocks and run the proper test before claiming.")
    else:
        print("  >>> SURROGATE does NOT close the gap: even aggressive density-dependent")
        print("      decimation (up to 30%) does not move mock beta1_max to DESI. Fiber-")
        print("      assignment is unlikely to explain the deficit. Report as a passed")
        print("      surrogate check; full altmtl test remains future work.")

    out = {
        "output_id": "phase8_fiber_surrogate",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "desi_beta1_max_masked": desi_beta1,
        "baseline_mock_beta1_max": float(base_mean),
        "by_strength": summary,
        "verdict": "MOVES_toward_DESI" if verdict_move else "does_NOT_close_gap",
        "caveat": "Surrogate decimation model, not DESI altmtl. Full test = future work.",
    }
    json.dump(out, open(M.RES_DIR / "phase8_fiber_surrogate.json", "w"), indent=2)
    print(f"\n[SAVED] {M.RES_DIR / 'phase8_fiber_surrogate.json'}")


if __name__ == "__main__":
    main()
