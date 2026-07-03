"""
CAUCHY — Phase 8, diagnostic
src/phase8_field_diagnostic.py

Isolate why <pers1>_DESI (0.459) sits 3.5x BELOW the cut-sky mocks (1.64) at
matched sigma_px and matched density. Suspected cause: delta_FKP amplitude
mismatch (field std), not galaxy density.

Prints, for the DESI canonical field and 3 cut-sky mocks, on the SAME mask:
  - delta_std_in_survey        (amplitude of the field)
  - mean CIC data count / voxel (shot-noise regime)
  - nu_min / nu_max            (1st / 99th percentile -> filtration range)
  - N H1 generators, <pers1>, beta1_max

If mock delta_std >> DESI delta_std (~0.53), the <pers1> gap is amplitude, and
the comparison must standardize amplitude before it means anything.

Reuses functions from phase8_cutsky_mocks.py (must be in the same src/ dir).

Usage:
  python src\\phase8_field_diagnostic.py --project_root D:\\projects\\cauchy
"""

import argparse
import sys
from pathlib import Path
import numpy as np

# import the machinery already written and validated
sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M


def field_stats(delta, mask, label):
    din = delta[mask]
    nu_min = float(np.percentile(din, 1))
    nu_max = float(np.percentile(din, 99))
    feats = M.compute_tda_features(delta, mask, M.N_THRESH)
    print(f"  [{label}]")
    print(f"      delta_std_in_survey = {din.std():.4f}")
    print(f"      delta_mean_in_survey= {din.mean():+.4f}")
    print(f"      nu_min / nu_max     = {nu_min:+.4f} / {nu_max:+.4f}  (range {nu_max-nu_min:.4f})")
    print(f"      beta1_max (N H1)    = {feats[4]:.0f}")
    print(f"      <pers1>             = {feats[5]:.4f}")
    return {"std": float(din.std()), "nu_range": nu_max - nu_min,
            "beta1_max": float(feats[4]), "pers1": float(feats[5])}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_mock", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    M.ROOT = Path(args.project_root)   # not strictly needed; paths already absolute in M

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("Phase 8 field diagnostic — DESI vs cut-sky mock amplitude")
    print("=" * 70)
    print(f"  mask fill {100*mask.mean():.1f}%  ({mask.sum():,} voxel)")
    print(f"  mean data count/voxel target: 217614 / {mask.sum()} = "
          f"{217614/mask.sum():.3f} gal/voxel\n")

    print("\n[1/3] Campo random DESI + rebuild DESI (log-transform)...")
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    # DESI, rebuilt from FITS through the shared build_field (log included)
    print("\nDESI field (rebuilt from FITS, log-transform):")
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
    d_desi = field_stats(nu_desi, mask, "DESI")

    # Cut-sky mocks (built through the same build_field)
    print("\nCut-sky mocks (rebuilt on the fly, same build_field):")
    mock_stats = []
    for i in range(args.n_mock):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, 3)
        pos_gal, vel_gal = M.populate_halos_hod_with_vel(pos_h, mass_h, vel_h,
                                                         M.HOD_MEDIAN, rng)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        delta_s = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        print(f"  mock {i}: N_sel={len(pos_sel):,}")
        mock_stats.append(field_stats(delta_s, mask, f"mock_{i}"))

    # Verdict
    print("\n" + "=" * 70)
    std_ratio = np.mean([m["std"] for m in mock_stats]) / d_desi["std"]
    print(f"  delta_std ratio (mock/DESI) = {std_ratio:.2f}x")
    if std_ratio > 1.5:
        print("  -> AMPLITUDE MISMATCH confirmed. The <pers1> gap is field std, not")
        print("     cosmology/geometry. compute_tda_features(<pers1>) scales with")
        print("     amplitude; a like-for-like test must standardize the field")
        print("     (e.g. divide delta by its in-survey std, or log-transform) on")
        print("     BOTH sides before extracting persistence.")
    elif std_ratio < 0.67:
        print("  -> DESI amplitude HIGHER than mocks — investigate FKP weighting.")
    else:
        print("  -> Amplitudes comparable; the <pers1> gap is NOT primarily amplitude.")
        print("     Look elsewhere (nu range, shot noise, mask boundary).")


if __name__ == "__main__":
    main()
