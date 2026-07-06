#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9b, Script 7
src/phase9_sgc_likeforlike.py

Referee R3.1 (mandatory, most informative): the SGC result under the like-for-
like framework is promised but never delivered. The SGC has its own mask,
randoms, n(z), and partially different imaging. If it shows a compatible ~20%
beta1_max deficit, the anomaly gains more support than any surrogate; if it does
not, the NGC deficit points to a hemisphere/imaging systematic.

This runs the Test 2 cut-sky masked pipeline on the SGC footprint. It is self-
consistent: the SGC embedding box, cell size, sigma_px, and mask are recomputed
from the SGC randoms (Phase 6 logic: min-5 / max+5, cubic), then INJECTED into
the phase8_cutsky_mocks module globals before its functions are used. This matters
because sigma_px = R_smooth/cell is the dominant systematic and cell_SGC != cell_NGC.

Density target: the SGC BGS sample is ~82k galaxies (not the ~217k NGC); we set the
density target from the SGC data count so the mock downsampling matches the SGC.

Run pilot then scale:
  python src\\phase9_sgc_likeforlike.py --project_root D:\\projects\\cauchy --k 3
  python src\\phase9_sgc_likeforlike.py --project_root D:\\projects\\cauchy --k 200
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def sgc_positions(fits_path, ra_key="RA", dec_key="DEC", z_key="Z",
                  wkeys=("WEIGHT_FKP",), zmin=0.1, zmax=0.4, M=None):
    """Comoving Cartesian positions + weights from an SGC clustering FITS."""
    from astropy.io import fits
    with fits.open(fits_path) as h:
        t = h["LSS"].data
        mz = (t[z_key] >= zmin) & (t[z_key] <= zmax)
        ra = t[ra_key][mz].astype(np.float64)
        dec = t[dec_key][mz].astype(np.float64)
        z = t[z_key][mz].astype(np.float64)
        w = np.ones(mz.sum(), dtype=np.float64)
        for k in wkeys:
            w *= t[k][mz].astype(np.float64)
    dC = M.comoving_distance(z)
    ra_r, dec_r = np.radians(ra), np.radians(dec)
    x = dC * np.cos(dec_r) * np.cos(ra_r)
    y = dC * np.cos(dec_r) * np.sin(ra_r)
    zc = dC * np.sin(dec_r)
    return np.column_stack([x, y, zc]), w


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=200)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    desi_dir = root / "data" / "raw" / "desi_dr1"
    fld_dir = root / "data" / "processed" / "phase6_fields"
    sys.path.insert(0, str(root / "src"))
    try:
        import phase8_cutsky_mocks as M
        import phase8_test2_masked as T2
    except Exception as e:
        sys.exit(f"[FATAL] import failed: {e}")

    ran_sgc = desi_dir / "BGS_BRIGHT-21.5_SGC_0_clustering.ran.fits"
    dat_sgc = desi_dir / "BGS_BRIGHT-21.5_SGC_clustering.dat.fits"
    nz_sgc = desi_dir / "BGS_BRIGHT-21.5_SGC_nz.txt"
    mask_sgc_path = fld_dir / "bgs_sgc_mask_128.npy"
    for p in (ran_sgc, dat_sgc, nz_sgc):
        if not p.exists():
            sys.exit(f"[FATAL] missing {p}")

    print("=" * 70)
    print(f"CAUCHY Phase 9b - Script 7: SGC like-for-like (K={args.k})")
    print("=" * 70)

    # --- SGC geometry from the SGC randoms (Phase 6 logic: min-5/max+5, cubic) --
    pos_r, w_r = sgc_positions(ran_sgc, wkeys=("WEIGHT_FKP",), M=M)
    box_min = pos_r.min(axis=0) - 5.0
    box_max = pos_r.max(axis=0) + 5.0
    box_size = float((box_max - box_min).max())
    ngrid = M.NGRID
    cell = box_size / ngrid
    sigma_px = M.R_SMOOTH / cell
    print(f"  SGC box_size = {box_size:.1f} Mpc/h  cell = {cell:.3f}  "
          f"sigma_px = {sigma_px:.4f}  (NGC was cell {M.CELL:.3f}, sigma_px {M.SIGMA_PX:.4f})")

    # --- INJECT SGC globals into the module (before using its functions) --------
    M.BOX_MIN = box_min
    M.BOX_SIZE = box_size
    M.CELL = cell
    M.SIGMA_PX = sigma_px
    M.RAN_FITS = ran_sgc
    M.NZ_FILE = nz_sgc

    # --- SGC random + data fields (own loaders; module's data loader is NGC-hardcoded)
    field_r = M.cic_3d(pos_r, w_r, ngrid, box_min, box_size)
    sum_wr = float(w_r.sum())
    pos_d, w_d = sgc_positions(dat_sgc, wkeys=("WEIGHT", "WEIGHT_FKP"), M=M)
    field_d = M.cic_3d(pos_d, w_d, ngrid, box_min, box_size)
    sum_wd = float(w_d.sum())
    n_data_sgc = int(len(pos_d))
    print(f"  SGC data galaxies (z in [{M.ZMIN},{M.ZMAX}]) = {n_data_sgc}")

    # --- SGC mask: prefer the frozen Phase 6 mask IF its geometry matches --------
    mask = None
    if mask_sgc_path.exists():
        m0 = np.load(mask_sgc_path).astype(bool)
        # coherence check: fraction of SGC data landing inside the frozen mask
        ijk = np.clip(((pos_d - box_min[None, :]) / cell).astype(int), 0, ngrid - 1)
        inside = m0[ijk[:, 0], ijk[:, 1], ijk[:, 2]].mean()
        print(f"  frozen SGC mask: fill {100*m0.mean():.2f}%; "
              f"{100*inside:.1f}% of SGC data fall inside it")
        if inside > 0.90:
            mask = m0
            print("  -> using frozen SGC mask (geometry consistent).")
        else:
            print("  -> frozen SGC mask INCONSISTENT with recomputed box; rebuilding.")
    if mask is None:
        ref = field_r[field_r > 0].mean()
        mask = field_r > 0.01 * ref
        print(f"  rebuilt SGC mask from randoms (1% threshold): fill {100*mask.mean():.2f}%")

    M.DESI_MASK_FILE = mask_sgc_path  # for any downstream reference

    # --- density target from SGC data (not the NGC 217k) ------------------------
    M.N_TARGET_BGS = n_data_sgc
    nz_z, nz_target = M.load_bgs_nz()
    print(f"  n(z) target bins: {len(nz_z)};  density target N_sel ~ {n_data_sgc}")

    # --- DESI-SGC reference (masked filtration), same build_field ---------------
    nu_desi = M.build_field(field_d, field_r, sum_wd / sum_wr, mask)
    feats = M.compute_tda_features(nu_desi, mask, M.N_THRESH, masked=True)
    desi_pers1, desi_b = float(feats[5]), float(feats[4])
    print(f"  DESI-SGC (masked): beta1_max = {desi_b:.0f}   <pers1> = {desi_pers1:.5f}")

    # --- K cut-sky masked mocks on the SGC footprint ----------------------------
    hod = M.HOD_MEDIAN
    b1_list = []
    t0 = time.time()
    for kk in range(args.k):
        rng = np.random.default_rng(args.seed + kk)
        pos_h, mass_h, vel_h = M.read_halo_catalog(kk, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pos_gal) < 100:
            continue
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:
            continue
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            continue
        b1_list.append(float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4]))
        if len(b1_list) % 20 == 0 or len(b1_list) == 1:
            eta = (time.time() - t0) / len(b1_list) * (args.k - len(b1_list)) / 60
            print(f"  [{len(b1_list)}/{args.k}] mock beta1_max~{np.mean(b1_list):.0f}  ETA={eta:.1f}min")

    b1 = np.array(b1_list)
    n_ok = b1.size
    if n_ok < 10:
        sys.exit(f"[FATAL] only {n_ok} valid SGC mocks.")

    mean, std = float(b1.mean()), float(b1.std(ddof=1))
    z = (desi_b - mean) / std
    n_below = int((b1 <= desi_b).sum())
    rank = (n_below + 1) / (n_ok + 1)
    frac_deficit = (mean - desi_b) / mean

    print(f"\n  SGC result (N={n_ok} mocks):")
    print(f"    DESI-SGC beta1_max = {desi_b:.0f}")
    print(f"    mock beta1_max     = {mean:.0f} +/- {std:.0f}")
    print(f"    z = {z:+.2f}   rank = {n_below}/{n_ok}   frac deficit = {100*frac_deficit:.1f}%")

    # verdict: does the SGC show a compatible deficit?
    confirms = (z < -3.0) and (frac_deficit > 0.10)
    verdict = "SGC_CONFIRMS" if confirms else "SGC_NULL"
    print(f"\n  >>> VERDICT: {verdict} "
          f"({'compatible deficit -> anomaly reinforced' if confirms else 'no/weak deficit -> hemisphere/imaging systematic suspected'})")
    print(f"      (NGC reference: ~20% deficit, z ~ -16, rank 1/2000)")

    out = {
        "schema_version": "2.0",
        "script": "phase9_sgc_likeforlike.py",
        "phase": "9b",
        "concern_addressed": "referee R3.1 (SGC like-for-like result, mandatory)",
        "timestamp": _now_iso(),
        "sgc_geometry": {"box_size_mpc_h": box_size, "cell_mpc_h": cell,
                         "sigma_px": sigma_px, "mask_fill_pct": 100 * float(mask.mean()),
                         "box_min": box_min.tolist()},
        "sgc_data_galaxies": n_data_sgc,
        "k_mocks": n_ok,
        "desi_sgc_beta1_max": desi_b,
        "desi_sgc_pers1": desi_pers1,
        "mock_beta1_mean": mean,
        "mock_beta1_std": std,
        "z": z,
        "rank": f"{n_below}/{n_ok}",
        "empirical_p_one_sided": rank,
        "fractional_deficit": frac_deficit,
        "verdict": verdict,
        "ngc_reference": {"frac_deficit": 0.20, "z_gaussian": -16.1, "rank": "1/2000"},
        "notes": ("SGC embedding box, cell, sigma_px, and density target recomputed from "
                  "the SGC catalogues; sigma_px matched between DESI-SGC and mocks (dominant "
                  "systematic). Same populate_with_virial, masked filtration, and build_field "
                  "as the NGC Test 2. A SGC_CONFIRMS reinforces the anomaly independently of "
                  "NGC imaging; a SGC_NULL localises it to a hemisphere/imaging systematic."),
    }
    outp = res_dir / "phase9_sgc_likeforlike.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the SGC result block and the VERDICT.")


if __name__ == "__main__":
    main()
