#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 6
src/phase9_growth_mismatch.py

Referee R1.c (the leading remaining physical candidate): the mocks use z=0.5
snapshots (snapnum=3) while the DESI BGS data sit at z in [0.1, 0.4]
(z_eff ~ 0.2-0.3). Structure grows between these redshifts, so the mock
beta1_max is measured at the wrong epoch. This script bounds the induced offset.

Method: for K nwLH realizations, regenerate the IDENTICAL cut-sky masked mock
(same HOD, mask, n(z), FKP, filtration) at snapnum=4 (z=0) and snapnum=3 (z=0.5),
using the same rng seed per realization so the ONLY difference is the snapshot.
Take the PAIRED difference Delta = beta1_max(z=0) - beta1_max(z=0.5) per
realization, form the per-unit-z rate Delta / Delta z_snap (Delta z_snap = 0.5),
and scale to the data offset Delta z_data = z_snap_mock(0.5) - z_eff_data.

Interpretation: if the growth offset over Delta z_data accounts for << the DESI
deficit (~7200 generators), the snapshot-vs-lightcone mismatch is sub-dominant and
cannot explain the anomaly; the Section 5.2 claim stands. If it accounts for a
large fraction, Section 5.2 must be rewritten.

Caveats (frozen in gate):
  - nwLH has per-realization cosmology; pairing z=0 vs z=0.5 on the SAME
    realization isolates growth (same halos, same cosmology, same seed) and
    samples it across the prior. It is not a fixed-cosmology fiducial, by design.
  - The Gadget sqrt(a) velocity convention differs between snapshots; we inherit
    read_halo_catalog's handling (it takes snapnum), so RSD is treated
    self-consistently at each z. We report beta1_max WITH RSD (as in the paper);
    an optional --real_space run isolates the pure density-growth part.
  - Linear extrapolation in z is a first-order estimate; the measured rate is
    quoted with its scatter, not a point value.

Run pilot then scale:
  python src\\phase9_growth_mismatch.py --project_root D:\\projects\\cauchy --k 3
  python src\\phase9_growth_mismatch.py --project_root D:\\projects\\cauchy --k 30
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np

# Snapshot redshifts (Quijote standard): snap 3 -> z=0.5, snap 4 -> z=0.
Z_SNAP = {3: 0.5, 4: 0.0}
SNAP_HI = 3   # z = 0.5 (the mock baseline used in the paper)
SNAP_LO = 4   # z = 0.0
Z_EFF_DATA = 0.25   # BGS effective redshift for z in [0.1, 0.4]; scanned below too
FROZEN_BASELINE_MEAN = 35424.8   # z=0.5, B3, from phase9 extraction (sanity)
FROZEN_BASELINE_STD = 444.8


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--real_space", action="store_true",
                    help="isolate density growth by disabling RSD (if supported)")
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
    print(f"CAUCHY Phase 9 - Script 6: growth mismatch z=0 vs z=0.5 (K={args.k})")
    print("=" * 70)
    print(f"  DESI beta1_max (masked) = {desi_b:.0f}   z_eff(data) = {Z_EFF_DATA}")
    print(f"  snapshots: {SNAP_HI} (z={Z_SNAP[SNAP_HI]}) vs {SNAP_LO} (z={Z_SNAP[SNAP_LO]})")
    if args.real_space:
        print("  [mode] real-space requested (RSD disabled if pipeline supports it)")

    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN

    def beta1_at(realization, snapnum, rng):
        pos_h, mass_h, vel_h = M.read_halo_catalog(realization, snapnum)
        if pos_h is None or len(pos_h) < 50:
            return None
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pos_gal) < 100:
            return None
        if args.real_space:
            vel_gal = np.zeros_like(vel_gal)   # kills RSD -> pure density growth
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:
            return None
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            return None
        return float(M.compute_tda_features(nu, mask, n_thresh, masked=True)[4])

    rows = []
    t0 = time.time()
    for k in range(args.k):
        # SAME seed for both snapshots so only the snapshot differs
        b_hi = beta1_at(k, SNAP_HI, np.random.default_rng(args.seed + k))
        b_lo = beta1_at(k, SNAP_LO, np.random.default_rng(args.seed + k))
        if b_hi is None or b_lo is None:
            continue
        rows.append({"realization": k, "beta1_z0.5": b_hi, "beta1_z0.0": b_lo,
                     "delta_lo_minus_hi": b_lo - b_hi})
        eta = (time.time() - t0) / len(rows) * (args.k - len(rows)) / 60
        print(f"  [{k}] z0.5={b_hi:.0f}  z0.0={b_lo:.0f}  "
              f"Delta(z0-z0.5)={b_lo-b_hi:+.0f}  ETA={eta:.1f}min")

    if len(rows) < 3:
        sys.exit(f"[FATAL] only {len(rows)} valid pairs.")

    b_hi_arr = np.array([r["beta1_z0.5"] for r in rows])
    b_lo_arr = np.array([r["beta1_z0.0"] for r in rows])
    dz_snap = Z_SNAP[SNAP_HI] - Z_SNAP[SNAP_LO]        # 0.5
    delta = b_lo_arr - b_hi_arr                         # beta1(z=0) - beta1(z=0.5)

    # sanity: z=0.5 mean vs frozen baseline
    drift = abs(b_hi_arr.mean() - FROZEN_BASELINE_MEAN) / FROZEN_BASELINE_STD
    status = "[ok]" if drift < 1.0 else "[WARN]"
    print(f"\n  z=0.5 baseline mean = {b_hi_arr.mean():.0f} "
          f"(frozen {FROZEN_BASELINE_MEAN:.0f}; drift {drift:.2f} sigma) {status}")

    # per-unit-z rate (beta1 per unit z), paired
    rate = delta / dz_snap                              # generators per unit z
    rate_mean = float(rate.mean())
    rate_sem = float(rate.std(ddof=1) / np.sqrt(len(rate)))
    print(f"\n  paired Delta beta1_max (z=0 minus z=0.5): mean {delta.mean():+.0f} "
          f"+/- {delta.std(ddof=1)/np.sqrt(len(delta)):.0f}  over Delta z = {dz_snap}")
    print(f"  growth rate d(beta1_max)/dz = {rate_mean:+.0f} +/- {rate_sem:.0f} per unit z")
    print(f"  (sign: {'more' if rate_mean>0 else 'fewer'} generators at LOWER z, "
          f"i.e. as structure grows)")

    # scale to the data offset and compare to the deficit
    deficit = float(b_hi_arr.mean() - desi_b)          # z=0.5 mock mean above DESI
    print(f"\n  deficit at z=0.5 (mock mean - DESI) = {deficit:+.0f} generators")
    scan = {}
    for zeff in (0.20, 0.25, 0.30):
        dz_data = Z_SNAP[SNAP_HI] - zeff               # mock at 0.5 -> data at zeff
        growth_offset = rate_mean * dz_data            # expected beta1 change over dz_data
        frac = growth_offset / deficit if deficit else float("nan")
        scan[f"{zeff:.2f}"] = {"dz_data": dz_data, "growth_offset": growth_offset,
                               "fraction_of_deficit": frac}
        print(f"    z_eff={zeff:.2f}: dz={dz_data:.2f}  growth offset={growth_offset:+.0f}  "
              f"= {100*frac:+.1f}% of the deficit")

    frac_ref = scan[f"{Z_EFF_DATA:.2f}"]["fraction_of_deficit"]
    subdominant = abs(frac_ref) < 0.20
    verdict = "GROWTH_SUBDOMINANT" if subdominant else "GROWTH_SIGNIFICANT"
    print(f"\n  >>> VERDICT (z_eff={Z_EFF_DATA}): {verdict} "
          f"({'cannot' if subdominant else 'could'} account for the deficit; "
          f"{100*frac_ref:+.1f}%)")

    out = {
        "schema_version": "2.0",
        "script": "phase9_growth_mismatch.py",
        "phase": "9",
        "concern_addressed": "referee R1.c (growth mismatch z=0.5 snapshot vs z_eff data)",
        "timestamp": _now_iso(),
        "mode": "real_space" if args.real_space else "redshift_space",
        "k_pairs": len(rows),
        "snap_hi": {"snapnum": SNAP_HI, "z": Z_SNAP[SNAP_HI]},
        "snap_lo": {"snapnum": SNAP_LO, "z": Z_SNAP[SNAP_LO]},
        "desi_beta1_max": desi_b,
        "z0.5_baseline_mean": float(b_hi_arr.mean()),
        "z0.5_baseline_drift_sigma": drift,
        "paired_delta_z0_minus_z05_mean": float(delta.mean()),
        "growth_rate_per_unit_z": rate_mean,
        "growth_rate_sem": rate_sem,
        "deficit_at_z05": deficit,
        "z_eff_scan": scan,
        "z_eff_reference": Z_EFF_DATA,
        "fraction_of_deficit_reference": frac_ref,
        "verdict": verdict,
        "per_realization": rows,
        "notes": ("Paired same-seed z=0 vs z=0.5 on each nwLH realization isolates growth. "
                  "Rate scaled linearly to the data offset; first-order estimate quoted with "
                  "scatter. real_space mode isolates pure density growth from the RSD part."),
    }
    outp = res_dir / "phase9_growth_mismatch.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the growth-rate line, the z_eff scan block, and the VERDICT.")


if __name__ == "__main__":
    main()
