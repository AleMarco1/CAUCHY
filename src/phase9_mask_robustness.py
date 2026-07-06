#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9b, Script 8
src/phase9_mask_robustness.py

Referee R3.2 (mandatory, cheap): the mask admits low-coverage edge voxels where
the FKP contrast is noisiest. Two one-parameter tests, applied IDENTICALLY to data
and mocks: (i) raise the coverage threshold (1% -> 5% -> 20% of the mean random
density); (ii) erode the mask by 1 and 2 voxels (15.6 and 31.2 h^-1 Mpc). The
deficit is a bulk claim; it should be indifferent to the skin of the volume.

Method (reuses the frozen fields; no regeneration):
  - DESI field nu_desi is built ONCE with the fiducial mask; the mock delta fields
    are the frozen test2 cubes. For each mask variant we recompute only the MASKED
    FILTRATION (compute_tda_features(field, variant_mask, masked=True)) on those
    same fields, for DESI and for a mock subsample. Data and mocks are treated
    identically (same frozen field, same variant filtration), so the comparison
    stays like-for-like. The mean-subtraction region is the fiducial interior for
    both sides; we note this as an approximation that preserves like-for-like.

Verdict MASK_ROBUST if the deficit (mock_mean - DESI) and DESI's rank/z stay
essentially unchanged across all variants; MASK_SENSITIVE if the 20% deficit moves
materially under erosion (boundary not fully controlled).

Run pilot then scale the mock subsample:
  python src\\phase9_mask_robustness.py --project_root D:\\projects\\cauchy --k 50
  python src\\phase9_mask_robustness.py --project_root D:\\projects\\cauchy --k 300
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np
from scipy import ndimage

THRESH_FRACS = [0.05, 0.20]   # raised coverage thresholds (fiducial ~ 0.01)
ERODE_ITERS = [1, 2]          # voxels
FROZEN_DESI = 28256.0
FROZEN_MOCK_MEAN = 35424.8
FROZEN_MOCK_STD = 444.8


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def build_variants(fiducial, field_r):
    """Return dict name -> boolean mask. Threshold variants are subsets of the
    fiducial interior (nested), so the frozen delta values remain valid there."""
    fid = fiducial.astype(bool)
    ref = float(field_r[fid].mean()) if fid.any() else 1.0
    variants = {"fiducial": fid}
    for frac in THRESH_FRACS:
        variants[f"thresh{int(frac*100)}"] = fid & (field_r > frac * ref)
    for it in ERODE_ITERS:
        variants[f"erode{it}"] = ndimage.binary_erosion(fid, iterations=it)
    return variants


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=300, help="mock subsample size")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    fields_dir = res_dir / "phase8_test2_fields"
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
    except Exception as e:
        sys.exit(f"[FATAL] import failed: {e}")

    n_thresh = getattr(M, "N_THRESH", 100)
    fiducial = (np.load(M.DESI_MASK_FILE) if Path(M.DESI_MASK_FILE).exists()
                else np.load(next(root.rglob("bgs_ngc_mask_128.npy")))).astype(bool)

    print("=" * 70)
    print(f"CAUCHY Phase 9b - Script 8: mask-edge robustness (mock k={args.k})")
    print("=" * 70)

    # random field (for thresholds) + DESI field built ONCE with the fiducial mask
    field_r, sum_wr = M.load_desi_random_field()
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, fiducial)

    variants = build_variants(fiducial, field_r)
    for name, m in variants.items():
        print(f"  mask '{name}': fill {100*m.mean():.2f}%  ({int(m.sum())} voxels)")

    # mock subsample (frozen cubes)
    files = sorted(fields_dir.glob("test2_*.npz"))[: args.k]
    if not files:
        sys.exit(f"[FATAL] no cubes in {fields_dir}")
    print(f"\n  {len(files)} mock cubes; recomputing TDA under {len(variants)} masks...")

    def beta1(field, mask):
        return float(M.compute_tda_features(field, mask, n_thresh, masked=True)[4])

    results = {}
    t0 = time.time()
    for vi, (name, m) in enumerate(variants.items()):
        desi_b = beta1(nu_desi, m)
        mock_vals = []
        for fp in files:
            mock_vals.append(beta1(np.load(fp)["delta"], m))
        mock = np.array(mock_vals)
        mean, std = float(mock.mean()), float(mock.std(ddof=1))
        z = (desi_b - mean) / std
        n_below = int((mock <= desi_b).sum())
        deficit = mean - desi_b
        results[name] = {
            "fill_pct": 100 * float(m.mean()),
            "desi_beta1": desi_b, "mock_mean": mean, "mock_std": std,
            "z": z, "n_below": n_below, "k": len(files),
            "deficit": deficit,
        }
        eta = (time.time() - t0) / (vi + 1) * (len(variants) - vi - 1) / 60
        print(f"  [{name:9s}] DESI={desi_b:.0f}  mock={mean:.0f}+/-{std:.0f}  "
              f"z={z:+.1f}  below={n_below}/{len(files)}  deficit={deficit:+.0f}  "
              f"ETA={eta:.1f}min")

    # sanity vs frozen (fiducial)
    fid = results["fiducial"]
    drift_d = abs(fid["desi_beta1"] - FROZEN_DESI)
    drift_m = abs(fid["mock_mean"] - FROZEN_MOCK_MEAN) / FROZEN_MOCK_STD
    status = "[ok]" if (drift_d < 50 and drift_m < 1.0) else "[WARN]"
    print(f"\n  fiducial sanity: DESI {fid['desi_beta1']:.0f} (frozen {FROZEN_DESI:.0f}, "
          f"d={drift_d:.0f})  mock drift {drift_m:.2f} sigma {status}")

    # verdict: deficit stability across variants
    deficits = np.array([results[n]["deficit"] for n in results])
    fid_def = fid["deficit"]
    max_swing = float(np.max(np.abs(deficits - fid_def)))
    frac_swing = max_swing / abs(fid_def) if fid_def else float("nan")
    print(f"\n  deficit across variants: fiducial {fid_def:+.0f}, "
          f"max swing {max_swing:.0f} ({100*frac_swing:.1f}% of fiducial)")
    robust = frac_swing < 0.20 and all(results[n]["z"] < -3 for n in results)
    verdict = "MASK_ROBUST" if robust else "MASK_SENSITIVE"
    print(f"  >>> VERDICT: {verdict} "
          f"(deficit {'indifferent to' if robust else 'moves with'} the volume skin)")

    out = {
        "schema_version": "2.0",
        "script": "phase9_mask_robustness.py",
        "phase": "9b",
        "concern_addressed": "referee R3.2 (mask-edge robustness: threshold + erosion)",
        "timestamp": _now_iso(),
        "mock_k": len(files),
        "thresholds": THRESH_FRACS,
        "erode_iters": ERODE_ITERS,
        "variants": results,
        "fiducial_deficit": fid_def,
        "max_deficit_swing": max_swing,
        "max_swing_fraction": frac_swing,
        "verdict": verdict,
        "notes": ("DESI field and mock cubes are frozen (fiducial build); only the "
                  "filtration mask varies, identically on both sides. Threshold variants "
                  "are nested subsets of the fiducial interior; mean-subtraction region is "
                  "the fiducial interior for both, preserving like-for-like. A full rebuild "
                  "per mask would additionally re-center each field; declared as a "
                  "second-order effect."),
    }
    outp = res_dir / "phase9_mask_robustness.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the per-variant table, the fiducial sanity line, and the VERDICT.")


if __name__ == "__main__":
    main()
