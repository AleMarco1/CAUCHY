#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 5
src/phase9_hod_concentrated_grid.py

OC-3: the HOD fit minimum sat at the grid EDGE in log M1 (best fit log_M1=13.8);
"the more concentrated region of HOD space was not fully explored." More
concentrated = LOWER log_M1 (satellites appear in lower-mass halos -> more
satellites per halo -> denser small-scale structure). This script extends the
grid BELOW 13.8 and tests whether any concentrated HOD drives beta1_max to DESI.

Because carve_cutsky re-downsamples to the BGS n(z) target, N is matched across
all log_M1 -> this isolates the HOD SHAPE (concentration) from the density.

Verdict HOD_EXCLUDED if even the most concentrated HOD leaves beta1_max well above
DESI (deficit persists) -> strengthens the result. HOD_CANDIDATE if some
concentrated HOD reaches DESI (concern stands).

Consumes phase8_hod_bestfit.json (fitted HOD) + phase8_test2_masked.json (DESI ref).
Sanity: log_M1=13.8 should reproduce the fitted-HOD baseline (~35304, from
phase8_test2_hodfit.json, N=200).

Run pilot then scale:
  python src\\phase9_hod_concentrated_grid.py --project_root D:\\projects\\cauchy --k 3
  python src\\phase9_hod_concentrated_grid.py --project_root D:\\projects\\cauchy --k 20
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np

# log_M1 scan: below the fitted edge (13.8) = more concentrated, incl. baseline.
LOG_M1_SCAN = [13.3, 13.4, 13.5, 13.6, 13.7, 13.8]
LOG_M1_INDEX = 3            # position of log_M1 in the HOD vector
FITTED_BASELINE_MEAN = 35304.6   # phase8_test2_hodfit.json (log_M1=13.8, N=200)
FITTED_BASELINE_STD = 1033.0


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=20)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import phase8_test2_masked as T2
    except Exception as e:
        sys.exit(f"[FATAL] import failed: {e}")

    n_thresh = getattr(M, "N_THRESH", 100)
    mask = np.load(M.DESI_MASK_FILE) if Path(M.DESI_MASK_FILE).exists() \
        else np.load(next(root.rglob("bgs_ngc_mask_128.npy")))

    with open(res_dir / "phase8_test2_masked.json") as f:
        desi_b = float(json.load(f)["desi_reference_masked"]["beta1_max"])
    with open(res_dir / "phase8_hod_bestfit.json") as f:
        base_hod = np.array(json.load(f)["best_fit"]["hod_vector"], float)

    print("=" * 70)
    print(f"CAUCHY Phase 9 - Script 5: HOD concentrated grid (K={args.k})")
    print("=" * 70)
    print(f"  DESI beta1_max (masked) = {desi_b:.0f}")
    print(f"  fitted HOD = {base_hod.tolist()}")
    print(f"  log_M1 scan = {LOG_M1_SCAN}  (13.8 = fitted edge; lower = more concentrated)")

    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    def beta1_for_logM1(k, logM1):
        rng = np.random.default_rng(args.seed + k)
        pos_h, mass_h, vel_h = M.read_halo_catalog(k, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            return None, None
        hod = base_hod.copy()
        hod[LOG_M1_INDEX] = logM1
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pos_gal) < 100:
            return None, None
        n_pre = len(pos_gal)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:
            return None, None
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            return None, None
        return float(M.compute_tda_features(nu, mask, n_thresh, masked=True)[4]), n_pre

    per_m1 = {f"{m:.1f}": [] for m in LOG_M1_SCAN}
    npre_m1 = {f"{m:.1f}": [] for m in LOG_M1_SCAN}
    t0 = time.time()
    for k in range(args.k):
        vals = {}
        for m1 in LOG_M1_SCAN:
            b, npre = beta1_for_logM1(k, m1)
            if b is not None:
                per_m1[f"{m1:.1f}"].append(b)
                npre_m1[f"{m1:.1f}"].append(npre)
                vals[m1] = b
        if vals:
            eta = (time.time() - t0) / (k + 1) * (args.k - k - 1) / 60
            print(f"  [mock {k}] " + " ".join(f"M1_{m}:{vals[m]:.0f}" for m in LOG_M1_SCAN if m in vals)
                  + f"  ETA={eta:.1f}min")

    print("\n  per-log_M1 aggregate (more concentrated = lower M1):")
    agg = {}
    for m1 in LOG_M1_SCAN:
        arr = np.array(per_m1[f"{m1:.1f}"], float)
        if arr.size == 0:
            continue
        npre = np.array(npre_m1[f"{m1:.1f}"], float)
        agg[f"{m1:.1f}"] = {
            "n": int(arr.size), "mean": float(arr.mean()),
            "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0,
            "n_gal_pre_carve_median": float(np.median(npre)),
            "gap_to_desi": float(arr.mean() - desi_b),
        }
        print(f"    log_M1={m1:.1f}: beta1_max={arr.mean():.0f} +/- "
              f"{agg[f'{m1:.1f}']['std']:.0f}  (n={arr.size})  "
              f"N_gal(pre-carve)~{np.median(npre):.0f}  gap vs DESI={arr.mean()-desi_b:+.0f}")

    # sanity: log_M1=13.8 vs fitted baseline
    if "13.8" in agg:
        drift = abs(agg["13.8"]["mean"] - FITTED_BASELINE_MEAN) / FITTED_BASELINE_STD
        status = "[ok]" if drift < 1.0 else "[WARN]"
        print(f"\n  log_M1=13.8 vs fitted baseline: drift {drift:.2f} sigma {status}")
    else:
        drift = float("nan")

    # verdict: does the most concentrated HOD reach DESI?
    gaps = {m1: agg[f"{m1:.1f}"]["gap_to_desi"] for m1 in LOG_M1_SCAN if f"{m1:.1f}" in agg}
    min_gap = min(gaps.values()) if gaps else float("nan")
    best_m1 = min(gaps, key=gaps.get) if gaps else None
    reaches = min_gap <= 0
    # also report the trend: does lowering M1 move toward DESI at all?
    m1_sorted = sorted(gaps)
    trend = (gaps[m1_sorted[0]] - gaps[m1_sorted[-1]]) if len(m1_sorted) > 1 else float("nan")
    verdict = "HOD_CANDIDATE" if reaches else "HOD_EXCLUDED"
    print(f"\n  smallest gap to DESI = {min_gap:+.0f} at log_M1={best_m1}")
    print(f"  trend (gap at lowest M1 - gap at highest M1) = {trend:+.0f} "
          f"({'toward' if trend < 0 else 'away from'} DESI as HOD concentrates)")
    print(f"  >>> VERDICT: {verdict} "
          f"({'a concentrated HOD reaches DESI' if reaches else 'deficit persists even at the most concentrated HOD'})")

    out = {
        "schema_version": "2.0",
        "script": "phase9_hod_concentrated_grid.py",
        "phase": "9",
        "concern_addressed": "OC-3 (HOD fit minimum at log_M1 grid edge; concentrated region unexplored)",
        "timestamp": _now_iso(),
        "k_mocks": args.k,
        "log_M1_scan": LOG_M1_SCAN,
        "fitted_hod_vector": base_hod.tolist(),
        "desi_beta1_max": desi_b,
        "aggregate": agg,
        "baseline_drift_sigma_vs_fitted": drift,
        "smallest_gap_to_desi": min_gap,
        "best_log_M1": best_m1,
        "trend_gap_low_minus_high_M1": trend,
        "verdict": verdict,
        "notes": ("log_M1 lowered below the fitted edge (13.8) = more concentrated HOD. "
                  "N matched to BGS by carve downsampling, so this isolates HOD shape. "
                  "HOD_EXCLUDED strengthens the deficit; the anomaly is not an HOD artifact."),
    }
    outp = res_dir / "phase9_hod_concentrated.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the per-log_M1 aggregate, the baseline drift, and the VERDICT.")


if __name__ == "__main__":
    main()
