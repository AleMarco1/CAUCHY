#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 4
src/phase9_rsd_satellite_sensitivity.py

Isolated-referee Concern 2: BGS data carry the true redshift-space velocities
(real Fingers-of-God), while the Test 2 mocks use a FIRST-ORDER virial dispersion
for satellites (sigma1d_virial, eta_vel=1). Munari et al. 2013 show the sigma_v-M
relation can differ by ~tens of percent for massive halos. The paper declares this
but does not quantify it. This script bounds it.

Method: regenerate a K-mock subsample varying eta_vel (the satellite dispersion
multiplier in populate_with_virial) over a Munari-plausible range, recompute
beta1_max, and measure how far the mock distribution mean and DESI's rank move.
If beta1_max shifts by << the DESI deficit (~7000), the residual RSD asymmetry is
sub-dominant and cannot account for the anomaly.

Consumes only the DESI reference (phase8_test2_masked.json) + frozen baseline for a
sanity check. Regenerates fields on the fly.

Run pilot then scale:
  python src\\phase9_rsd_satellite_sensitivity.py --project_root D:\\projects\\cauchy --k 3
  python src\\phase9_rsd_satellite_sensitivity.py --project_root D:\\projects\\cauchy --k 20
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np

ETA_VEL_SCAN = [0.8, 1.0, 1.2]   # Munari-plausible +/- ~20% on satellite dispersion
FROZEN_BASELINE_MEAN = 35424.8
FROZEN_BASELINE_STD = 444.8


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

    print("=" * 70)
    print(f"CAUCHY Phase 9 - Script 4: RSD satellite sensitivity (K={args.k})")
    print("=" * 70)
    print(f"  DESI beta1_max (masked) = {desi_b:.0f}")
    print(f"  eta_vel scan = {ETA_VEL_SCAN}  (1.0 = Test 2 baseline)")

    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    base_hod = np.array(M.HOD_MEDIAN, float)
    eta_vel_idx = 7   # position of eta_vel in the HOD vector (see populate_with_virial)

    def beta1_for_eta(k, eta):
        rng = np.random.default_rng(args.seed + k)
        pos_h, mass_h, vel_h = M.read_halo_catalog(k, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            return None
        hod = base_hod.copy()
        hod[eta_vel_idx] = eta
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pos_gal) < 100:
            return None
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:
            return None
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            return None
        return float(M.compute_tda_features(nu, mask, n_thresh, masked=True)[4])

    per_eta = {f"{e:.1f}": [] for e in ETA_VEL_SCAN}
    t0 = time.time()
    for k in range(args.k):
        vals = {}
        for e in ETA_VEL_SCAN:
            b = beta1_for_eta(k, e)
            if b is not None:
                per_eta[f"{e:.1f}"].append(b)
                vals[e] = b
        if len(vals) == len(ETA_VEL_SCAN):
            eta = (time.time() - t0) / (k + 1) * (args.k - k - 1) / 60
            print(f"  [mock {k}] " + " ".join(f"eta{e}:{vals[e]:.0f}" for e in ETA_VEL_SCAN)
                  + f"  ETA={eta:.1f}min")

    # aggregate
    print("\n  per-eta_vel aggregate:")
    agg = {}
    for e in ETA_VEL_SCAN:
        arr = np.array(per_eta[f"{e:.1f}"], float)
        if arr.size == 0:
            continue
        agg[f"{e:.1f}"] = {"n": int(arr.size), "mean": float(arr.mean()),
                           "std": float(arr.std(ddof=1)) if arr.size > 1 else 0.0}
        print(f"    eta={e:.1f}: beta1_max mean={arr.mean():.0f} +/- "
              f"{agg[f'{e:.1f}']['std']:.0f}  (n={arr.size})  "
              f"gap vs DESI = {arr.mean()-desi_b:+.0f}")

    # sanity: eta=1.0 should reproduce frozen baseline
    if "1.0" in agg:
        drift = abs(agg["1.0"]["mean"] - FROZEN_BASELINE_MEAN) / FROZEN_BASELINE_STD
        status = "[ok]" if drift < 1.0 else "[WARN]"
        print(f"\n  eta=1.0 baseline vs frozen: drift {drift:.2f} sigma {status}")
    else:
        drift = float("nan")

    # systematic span = max shift in mock mean across eta_vel range
    means = np.array([agg[f"{e:.1f}"]["mean"] for e in ETA_VEL_SCAN if f"{e:.1f}" in agg])
    span = float(means.max() - means.min()) if means.size else float("nan")
    deficit = float(np.mean(means) - desi_b) if means.size else float("nan")
    frac = span / abs(deficit) if deficit else float("nan")
    print(f"\n  RSD-satellite systematic span on beta1_max = {span:.0f} loops "
          f"across eta_vel in [{min(ETA_VEL_SCAN)}, {max(ETA_VEL_SCAN)}]")
    print(f"  DESI deficit = {deficit:.0f} loops  ->  systematic is {100*frac:.1f}% of the deficit")
    subdominant = frac < 0.2
    verdict = "SUBDOMINANT" if subdominant else "NON_NEGLIGIBLE"
    print(f"  >>> VERDICT: RSD satellite asymmetry {verdict} "
          f"({'cannot' if subdominant else 'could'} account for the anomaly)")

    out = {
        "schema_version": "2.0",
        "script": "phase9_rsd_satellite_sensitivity.py",
        "phase": "9",
        "concern_addressed": "isolated-referee Concern 2 (satellite RSD asymmetry, Munari 2013)",
        "timestamp": _now_iso(),
        "k_mocks": args.k,
        "eta_vel_scan": ETA_VEL_SCAN,
        "desi_beta1_max": desi_b,
        "aggregate": agg,
        "baseline_drift_sigma_vs_frozen": drift,
        "systematic_span_loops": span,
        "desi_deficit_loops": deficit,
        "systematic_fraction_of_deficit": frac,
        "verdict": verdict,
        "notes": ("eta_vel multiplies the satellite virial dispersion (sigma1d_virial). "
                  "Munari-plausible +/-20%. The span of the mock mean over this range bounds "
                  "the residual RSD asymmetry; compared to the DESI deficit to judge dominance."),
    }
    outp = res_dir / "phase9_rsd_satellite.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the per-eta aggregate, the baseline drift, the systematic span line, and the VERDICT.")


if __name__ == "__main__":
    main()
