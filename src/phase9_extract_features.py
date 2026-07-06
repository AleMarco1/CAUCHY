#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, prerequisite for Script 1
src/phase9_extract_features.py

Why this exists:
    The definitive N=2000 like-for-like run (Test 2, masked) saved the 2000
    masked fields as results/phase8_test2_fields/test2_XXXX.npz (key 'delta'),
    and froze summary stats + ranks in results/phase8_test2_masked.json, but the
    per-mock table (phase8_test2_permock.csv) only holds the N=200 pilot. The
    empirical histogram (Script 1) needs the raw 2000 values.

What it does:
    Re-runs Phase 8's OWN compute_tda_features(delta, mask, N_THRESH, masked=True)
    on each of the 2000 frozen cubes -> identical filtration by construction, so
    the resulting distribution is consistent with the frozen ranks. Merges w0/Om/s8
    from the pilot CSV by mock index (available for the 200 pilot indices; NaN
    otherwise -> Script 3 uses whatever is present). Freezes everything to
    results/phase9_likeforlike_arrays.npz.

    beta1_max = feats[4], pers1 = feats[5]  (same indices Phase 8 uses).

Sanity: prints mock mean/std and compares to phase8_test2_masked.json
    (beta1_max 35436.7 +/- 313.0 ; pers1 0.62985 +/- 0.04394). A large drift means
    the mask or the masked=True path differs from the frozen run -> stop and check.

Run (Windows, env cauchy):
    python src\\phase9_extract_features.py --project_root D:\\projects\\cauchy
"""

import argparse
import csv
import json
import sys
import time
from pathlib import Path
import numpy as np


def find_mask(root, M):
    """Resolve the DESI mask path. Prefer Phase 8's own constant, else glob."""
    try:
        p = Path(M.DESI_MASK_FILE)
        if p.exists():
            return p
    except Exception:
        pass
    hits = list(root.rglob("bgs_ngc_mask_128.npy"))
    if hits:
        return hits[0]
    sys.exit("[FATAL] bgs_ngc_mask_128.npy not found under project root. "
             "Pass the correct --project_root or place the mask there.")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--n_expected", type=int, default=2000)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    fields_dir = res_dir / "phase8_test2_fields"
    masked_json = res_dir / "phase8_test2_masked.json"
    pilot_csv = res_dir / "phase8_test2_permock.csv"
    out_npz = res_dir / "phase9_likeforlike_arrays.npz"

    # --- import Phase 8's own feature extractor (identical filtration) ---------
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
    except Exception as e:
        sys.exit(f"[FATAL] cannot import phase8_cutsky_mocks from {root/'src'}: {e}")

    n_thresh = getattr(M, "N_THRESH", 100)
    mask_path = find_mask(root, M)
    mask = np.load(mask_path)
    print("=" * 70)
    print("CAUCHY Phase 9 - extract per-mock features from frozen masked cubes")
    print("=" * 70)
    print(f"  mask: {mask_path}  fill={100*float(mask.mean()):.1f}%  N_THRESH={n_thresh}")

    # --- DESI reference (already recomputed masked in Phase 8) -----------------
    with open(masked_json, "r", encoding="utf-8") as f:
        mj = json.load(f)
    desi_beta1max = float(mj["desi_reference_masked"]["beta1_max"])
    desi_pers1 = float(mj["desi_reference_masked"]["pers1"])
    ref_b_mean = float(mj["mock_beta1_max"]["mean"])
    ref_b_std = float(mj["mock_beta1_max"]["std"])
    ref_p_mean = float(mj["mock_pers1"]["mean"])
    ref_p_std = float(mj["mock_pers1"]["std"])
    print(f"  DESI (masked): beta1_max={desi_beta1max:.0f}  pers1={desi_pers1:.5f}")

    # --- w0/Om/s8 from the pilot CSV, keyed by mock index ----------------------
    params = {}
    if pilot_csv.exists():
        with open(pilot_csv, newline="") as f:
            for row in csv.DictReader(f):
                try:
                    params[int(row["index"])] = (
                        float(row["w0"]), float(row["Om"]), float(row["s8"]))
                except (ValueError, KeyError):
                    continue
        print(f"  pilot CSV: {len(params)} indices with (w0,Om,s8)")
    else:
        print("  [warn] pilot CSV not found -> w0/Om/s8 will be NaN.")

    # --- loop over the frozen cubes -------------------------------------------
    files = sorted(fields_dir.glob("test2_*.npz"))
    if not files:
        sys.exit(f"[FATAL] no test2_*.npz in {fields_dir}")
    print(f"\n  {len(files)} cubes found. Recomputing masked TDA...")

    idx_list, b1_list, p1_list, w0_list, om_list, s8_list = [], [], [], [], [], []
    t0 = time.time()
    for k, fp in enumerate(files):
        try:
            i = int(fp.stem.split("_")[1])
        except (IndexError, ValueError):
            i = k
        delta = np.load(fp)["delta"]
        feats = M.compute_tda_features(delta, mask, n_thresh, masked=True)
        b1_list.append(float(feats[4]))
        p1_list.append(float(feats[5]))
        idx_list.append(i)
        w0, om, s8 = params.get(i, (np.nan, np.nan, np.nan))
        w0_list.append(w0); om_list.append(om); s8_list.append(s8)
        if (k + 1) % 100 == 0 or k == 0:
            eta = (time.time() - t0) / (k + 1) * (len(files) - k - 1) / 60
            print(f"  [{k+1}/{len(files)}] beta1_max~{np.mean(b1_list):.0f} "
                  f"pers1~{np.mean(p1_list):.4f} ETA={eta:.1f}min")

    beta1 = np.array(b1_list, float)
    pers1 = np.array(p1_list, float)
    index = np.array(idx_list, int)
    w0 = np.array(w0_list, float)
    om = np.array(om_list, float)
    s8 = np.array(s8_list, float)
    N = beta1.size

    # --- sanity vs frozen summary ---------------------------------------------
    b_mean, b_std = float(beta1.mean()), float(beta1.std(ddof=1))
    p_mean, p_std = float(pers1.mean()), float(pers1.std(ddof=1))
    print(f"\n  recomputed  beta1_max: mean={b_mean:.1f} std={b_std:.1f}  "
          f"(frozen {ref_b_mean:.1f} +/- {ref_b_std:.1f})")
    print(f"  recomputed  pers1    : mean={p_mean:.5f} std={p_std:.5f}  "
          f"(frozen {ref_p_mean:.5f} +/- {ref_p_std:.5f})")
    drift_b = abs(b_mean - ref_b_mean) / ref_b_std
    drift_p = abs(p_mean - ref_p_mean) / ref_p_std
    if drift_b > 0.5 or drift_p > 0.5:
        print(f"  [WARN] drift vs frozen > 0.5 sigma (beta1 {drift_b:.2f}, "
              f"pers1 {drift_p:.2f}). Investigate before using the histogram.")
    else:
        print(f"  [ok] consistent with frozen run (drift beta1 {drift_b:.2f}, "
              f"pers1 {drift_p:.2f} in units of frozen std).")

    # --- freeze ----------------------------------------------------------------
    np.savez(
        out_npz,
        beta1_max=beta1, pers1_mean=pers1, index=index,
        w0=w0, Om=om, s8=s8,
        desi_beta1max=np.array(desi_beta1max),
        desi_pers1=np.array(desi_pers1),
        n_mocks=np.array(N),
    )
    print(f"\n[SAVED] {out_npz}  (N={N})")
    print("Report the two 'recomputed' lines and the [ok]/[WARN] status.")


if __name__ == "__main__":
    main()
