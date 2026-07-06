#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9b, combined light majors
src/phase9b_majors.py

Four second-round major points, run in sequence (one launch, four JSON):

  A. Redshift split (R1.2): is the deficit present in BOTH halves of the z shell?
     DESI split at the median z; mocks re-carved and split at the same z_obs cut.

  B. Scatter decomposition (R2.2): fix ONE fiducial cosmology (nwLH idx 1805,
     Om=0.329 s8=0.811 w0=-0.98, near Planck) and run 50 HOD/downsampling seeds
     to measure the STOCHASTIC scatter, vs the cosmological scatter across the
     suite. Reports r(beta1,Om/s8/w0) too.

  C. Filtration-convention stability (R2.3): recompute beta1_max under the
     ALTERNATIVE masked convention (retain sentinel-touching generators as
     relative cycles) and check the deficit is stable.

  D. Imaging split (R3.1b): split the NGC DATA by PHOTSYS (N=BASS+MzLS,
     S=DECaLS) and by Dec at +32.4, and check the deficit against the mock
     distribution in each angular region.

Run:
  python src\\phase9b_majors.py --project_root D:\\projects\\cauchy --k 30 --nseed 50
  (use --only A|B|C|D to run a single block)
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


# ---------------------------------------------------------------------------
# Local carve that ALSO returns z_obs (module version discards it)
# ---------------------------------------------------------------------------
def carve_with_z(M, pos_gal, vel_gal, mask, nz_z, nz_target, rng):
    def offsets(axis):
        lo, hi = M.BOX_MIN[axis], M.BOX_MIN[axis] + M.BOX_SIZE
        return list(range(int(np.floor(lo / M.BOXSIZE_MOCK)),
                          int(np.floor(hi / M.BOXSIZE_MOCK)) + 1))
    ox, oy, oz = offsets(0), offsets(1), offsets(2)
    cand_P, cand_z = [], []
    for kx in ox:
        for ky in oy:
            for kz in oz:
                shift = np.array([kx, ky, kz]) * M.BOXSIZE_MOCK
                P = pos_gal + shift[None, :]
                inb = np.all((P >= M.BOX_MIN[None, :]) &
                             (P < (M.BOX_MIN + M.BOX_SIZE)[None, :]), axis=1)
                if not inb.any():
                    continue
                P = P[inb]; V = vel_gal[inb]
                dC = np.linalg.norm(P, axis=1)
                good = (dC > 1e-6) & (dC >= M.D_C_ZMIN - 50) & (dC <= M.D_C_ZMAX + 50)
                if not good.any():
                    continue
                P, V, dC = P[good], V[good], dC[good]
                rhat = P / dC[:, None]
                z_cosmo = M.z_of_dc(dC)
                v_los = np.sum(V * rhat, axis=1)
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / M.C_KMS
                dC_rsd = np.interp(np.clip(z_obs, 0.0, 0.6), M._Z_TAB, M._DC_TAB)
                P_rsd = rhat * dC_rsd[:, None]
                zsel = (z_obs >= M.ZMIN) & (z_obs <= M.ZMAX)
                if not zsel.any():
                    continue
                P_rsd, z_obs_s = P_rsd[zsel], z_obs[zsel]
                ijk = np.clip(((P_rsd - M.BOX_MIN[None, :]) / M.CELL).astype(np.int32), 0, M.NGRID - 1)
                inmask = mask[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
                if not inmask.any():
                    continue
                cand_P.append(P_rsd[inmask]); cand_z.append(z_obs_s[inmask])
    if not cand_P:
        return np.zeros((0, 3)), np.zeros(0)
    P_cand = np.vstack(cand_P); z_cand = np.concatenate(cand_z)
    edges = np.concatenate([[nz_z[0] - 0.5 * (nz_z[1] - nz_z[0])],
                            0.5 * (nz_z[:-1] + nz_z[1:]),
                            [nz_z[-1] + 0.5 * (nz_z[-1] - nz_z[-2])]])
    which = np.clip(np.digitize(z_cand, edges) - 1, 0, len(nz_z) - 1)
    n_cand_bin = np.bincount(which, minlength=len(nz_z)).astype(float)
    shape = np.clip(nz_target, 0.0, None).astype(float)
    if shape.sum() <= 0:
        return np.zeros((0, 3)), np.zeros(0)
    desired = shape / shape.sum() * float(M.N_TARGET_BGS)
    with np.errstate(divide='ignore', invalid='ignore'):
        p_bin = np.where(n_cand_bin > 0, desired / n_cand_bin, 0.0)
    p = np.minimum(p_bin, 1.0)[which]
    keep = rng.random(len(z_cand)) < p
    return P_cand[keep], z_cand[keep]


# ---------------------------------------------------------------------------
# beta1_max with selectable masked convention (standard vs relative-cycle)
# ---------------------------------------------------------------------------
def beta1_conv(M, delta_field, mask, n_thresh, convention="standard"):
    import gudhi
    field = delta_field.astype(np.float64)
    field_in = field[mask]
    thr = np.linspace(np.percentile(field_in, 1), np.percentile(field_in, 99), n_thresh)
    SENT = 1.0e6
    field_work = field.copy(); field_work[~mask] = -SENT
    field_neg = -field_work
    cutoff = (SENT / 2.0) if convention == "standard" else np.inf
    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                              top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()
    d1 = cc.persistence_intervals_in_dimension(1)
    if len(d1) == 0:
        return 0
    d = np.array(d1)
    keep = np.isfinite(d[:, 1]) & (d[:, 0] < cutoff) & (d[:, 1] < cutoff)
    df = d[keep]
    b1, dth1 = -df[:, 0], -df[:, 1]
    curve = np.array([np.sum((b1 >= nu) & (dth1 < nu)) for nu in thr])
    return int(curve.max())


def voxelize_positions(M, pos, field_r, sum_wr, mask):
    if len(pos) < 100:
        return None
    field_d = M.cic_3d(pos, np.ones(len(pos)), M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    return M.build_field(field_d, field_r, float(len(pos)) / sum_wr, mask)


# ===========================================================================
def block_A_redshift_split(M, T2, mask, field_r, sum_wr, nz_z, nz_target, args, desi_dir, res_dir):
    print("\n" + "=" * 60 + "\n[A] Redshift split (R1.2)\n" + "=" * 60)
    from astropy.io import fits
    # DESI: split data by median z, voxelize each half, deficit ref
    dat = desi_dir / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        t = h["LSS"].data
        mz = (t["Z"] >= M.ZMIN) & (t["Z"] <= M.ZMAX)
        ra, dec, z = t["RA"][mz], t["DEC"][mz], t["Z"][mz]
        w = (t["WEIGHT"][mz] * t["WEIGHT_FKP"][mz]).astype(np.float64)
    zmed = float(np.median(z))
    dC = M.comoving_distance(z.astype(np.float64))
    rar, decr = np.radians(ra.astype(np.float64)), np.radians(dec.astype(np.float64))
    pos = np.column_stack([dC*np.cos(decr)*np.cos(rar), dC*np.cos(decr)*np.sin(rar), dC*np.sin(decr)])
    print(f"  median z = {zmed:.3f}")
    out = {"median_z": zmed, "halves": {}}
    for name, sel in [("low", z <= zmed), ("high", z > zmed)]:
        fd = M.cic_3d(pos[sel], w[sel], M.NGRID, M.BOX_MIN, M.BOX_SIZE)
        nu = M.build_field(fd, field_r, float(w[sel].sum())/sum_wr, mask)
        desi_b = float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4])
        # mocks: re-carve, keep only galaxies in this z-half, voxelize
        mb = []
        for kk in range(args.k):
            rng = np.random.default_rng(args.seed + kk)
            ph, mh, vh = M.read_halo_catalog(kk, args.snapnum)
            if ph is None or len(ph) < 50: continue
            pg, vg = T2.populate_with_virial(ph, mh, vh, M.HOD_MEDIAN, rng)
            if len(pg) < 100: continue
            ps, zs = carve_with_z(M, pg, vg, mask, nz_z, nz_target, rng)
            half = ps[zs <= zmed] if name == "low" else ps[zs > zmed]
            nuh = voxelize_positions(M, half, field_r, sum_wr, mask)
            if nuh is None: continue
            mb.append(float(M.compute_tda_features(nuh, mask, M.N_THRESH, masked=True)[4]))
        mb = np.array(mb); mean, std = float(mb.mean()), float(mb.std(ddof=1))
        z_s = (desi_b - mean)/std; frac = (mean-desi_b)/mean
        out["halves"][name] = {"desi": desi_b, "mock_mean": mean, "mock_std": std,
                               "z": z_s, "frac_deficit": frac, "n_mock": int(mb.size)}
        print(f"  {name:4s} z: DESI={desi_b:.0f} mock={mean:.0f}+/-{std:.0f} "
              f"z={z_s:+.1f} frac={100*frac:.1f}% (n={mb.size})")
    both = all(out["halves"][h]["z"] < -3 for h in out["halves"])
    out["verdict"] = "DEFICIT_IN_BOTH_HALVES" if both else "REDSHIFT_LOCALISED"
    print(f"  >>> {out['verdict']}")
    json.dump(out, open(res_dir/"phase9b_redshift_split.json","w"), indent=2)
    return out


def block_B_scatter(M, T2, mask, field_r, sum_wr, nz_z, nz_target, args, res_dir):
    print("\n" + "=" * 60 + "\n[B] Scatter decomposition, fixed cosmology (R2.2)\n" + "=" * 60)
    FID = 1805
    ph, mh, vh = M.read_halo_catalog(FID, args.snapnum)
    if ph is None:
        print("  [skip] fiducial halo catalog not available"); return None
    vals = []
    t0 = time.time()
    for s in range(args.nseed):
        rng = np.random.default_rng(10000 + s)   # vary HOD+downsampling seed only
        pg, vg = T2.populate_with_virial(ph, mh, vh, M.HOD_MEDIAN, rng)
        if len(pg) < 100: continue
        ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
        nu = M.voxelize_mock(ps, field_r, sum_wr, mask)
        if nu is None: continue
        vals.append(float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4]))
        if len(vals) % 10 == 0:
            eta=(time.time()-t0)/len(vals)*(args.nseed-len(vals))/60
            print(f"  [{len(vals)}/{args.nseed}] mean={np.mean(vals):.0f} std={np.std(vals,ddof=1):.0f} ETA={eta:.1f}min")
    vals = np.array(vals)
    stoch = float(vals.std(ddof=1))
    # cosmological scatter from the frozen suite
    d = np.load(Path(args.project_root)/"results"/"phase9_likeforlike_arrays.npz")
    b = np.asarray(d["beta1_max"], float); total = float(b.std(ddof=1))
    Om, s8, w0 = (np.asarray(d[k], float) for k in ("Om","s8","w0"))
    ok = np.isfinite(Om)
    r = lambda x: float(np.corrcoef(b[ok], x[ok])[0,1])
    out = {"fiducial_idx": FID, "nseed": int(vals.size),
           "fiducial_mean": float(vals.mean()), "stochastic_std": stoch,
           "suite_total_std": total,
           "stochastic_fraction_of_total_var": (stoch**2)/(total**2) if total>0 else None,
           "r_beta1_Om": r(Om), "r_beta1_s8": r(s8), "r_beta1_w0": r(w0)}
    print(f"  stochastic std (fixed cosmology, {vals.size} seeds) = {stoch:.0f}")
    print(f"  suite total std = {total:.0f}  -> stochastic is {100*out['stochastic_fraction_of_total_var']:.0f}% of the variance")
    print(f"  r(beta1,Om)={out['r_beta1_Om']:+.3f}  r(s8)={out['r_beta1_s8']:+.3f}  r(w0)={out['r_beta1_w0']:+.3f}")
    json.dump(out, open(res_dir/"phase9b_scatter_decomp.json","w"), indent=2)
    return out


def block_C_convention(M, mask, args, res_dir):
    print("\n" + "=" * 60 + "\n[C] Filtration-convention stability (R2.3)\n" + "=" * 60)
    fields_dir = Path(args.project_root)/"results"/"phase8_test2_fields"
    files = sorted(fields_dir.glob("test2_*.npz"))[:args.k]
    # DESI field
    field_r, sum_wr = M.load_desi_random_field()
    field_d, sum_wd = M.load_desi_data_field()
    nu_desi = M.build_field(field_d, field_r, sum_wd/sum_wr, mask)
    out = {"conventions": {}}
    for conv in ("standard", "relative"):
        desi_b = beta1_conv(M, nu_desi, mask, M.N_THRESH, conv)
        mb = np.array([beta1_conv(M, np.load(fp)["delta"], mask, M.N_THRESH, conv) for fp in files])
        mean, std = float(mb.mean()), float(mb.std(ddof=1))
        z = (desi_b-mean)/std; nb = int((mb <= desi_b).sum())
        out["conventions"][conv] = {"desi": desi_b, "mock_mean": mean, "mock_std": std,
                                    "z": z, "rank": f"{nb}/{len(mb)}", "frac": (mean-desi_b)/mean}
        print(f"  {conv:9s}: DESI={desi_b} mock={mean:.0f}+/-{std:.0f} z={z:+.1f} rank={nb}/{len(mb)} frac={100*(mean-desi_b)/mean:.1f}%")
    stable = all(out["conventions"][c]["z"] < -3 for c in out["conventions"])
    out["verdict"] = "CONVENTION_STABLE" if stable else "CONVENTION_SENSITIVE"
    print(f"  >>> {out['verdict']}")
    json.dump(out, open(res_dir/"phase9b_filtration_convention.json","w"), indent=2)
    return out


def block_D_imaging(M, mask, field_r, sum_wr, args, desi_dir, res_dir):
    print("\n" + "=" * 60 + "\n[D] Imaging split (R3.1b)\n" + "=" * 60)
    from astropy.io import fits
    dat = desi_dir / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        t = h["LSS"].data
        mz = (t["Z"] >= M.ZMIN) & (t["Z"] <= M.ZMAX)
        ra, dec, z = t["RA"][mz], t["DEC"][mz], t["Z"][mz]
        w = (t["WEIGHT"][mz] * t["WEIGHT_FKP"][mz]).astype(np.float64)
        photsys = np.array(t["PHOTSYS"][mz]).astype(str)
    dC = M.comoving_distance(z.astype(np.float64))
    rar, decr = np.radians(ra.astype(np.float64)), np.radians(dec.astype(np.float64))
    pos = np.column_stack([dC*np.cos(decr)*np.cos(rar), dC*np.cos(decr)*np.sin(rar), dC*np.sin(decr)])
    splits = {"PHOTSYS_N": photsys == "N", "PHOTSYS_S": photsys == "S",
              "DEC_gt_32.4": dec > 32.4, "DEC_le_32.4": dec <= 32.4}
    # reference DESI full deficit under this mask
    nu_full = M.build_field(M.cic_3d(pos, w, M.NGRID, M.BOX_MIN, M.BOX_SIZE), field_r, float(w.sum())/sum_wr, mask)
    desi_full = float(M.compute_tda_features(nu_full, mask, M.N_THRESH, masked=True)[4])
    out = {"desi_full": desi_full, "regions": {}}
    for name, sel in splits.items():
        if sel.sum() < 1000:
            print(f"  {name}: only {int(sel.sum())} gals, skipped"); continue
        nu = M.build_field(M.cic_3d(pos[sel], w[sel], M.NGRID, M.BOX_MIN, M.BOX_SIZE), field_r, float(w[sel].sum())/sum_wr, mask)
        db = float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4])
        out["regions"][name] = {"n_gal": int(sel.sum()), "desi_beta1": db,
                                "ratio_to_full": db/desi_full}
        print(f"  {name:12s}: n={int(sel.sum()):6d}  beta1_max={db:.0f}  (ratio to full {db/desi_full:.3f})")
    n = out["regions"].get("PHOTSYS_N", {}).get("desi_beta1")
    s = out["regions"].get("PHOTSYS_S", {}).get("desi_beta1")
    if n and s:
        out["imaging_consistent"] = abs(n - s) / ((n + s) / 2) < 0.15
        print(f"  PHOTSYS N vs S: {n:.0f} vs {s:.0f}  -> "
              f"{'consistent' if out['imaging_consistent'] else 'DIFFERENT (imaging systematic suspected)'}")
    json.dump(out, open(res_dir/"phase9b_imaging_split.json","w"), indent=2)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=30)
    ap.add_argument("--nseed", type=int, default=50)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--only", type=str, default=None, help="A|B|C|D")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res_dir = root / "results"; desi_dir = root / "data" / "raw" / "desi_dr1"
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    mask = (np.load(M.DESI_MASK_FILE) if Path(M.DESI_MASK_FILE).exists()
            else np.load(next(root.rglob("bgs_ngc_mask_128.npy")))).astype(bool)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    print("=" * 70 + f"\nCAUCHY Phase 9b majors (k={args.k}, nseed={args.nseed})\n" + "=" * 70)
    do = (lambda x: (args.only is None) or (args.only.upper() == x))
    if do("A"): block_A_redshift_split(M, T2, mask, field_r, sum_wr, nz_z, nz_target, args, desi_dir, res_dir)
    if do("B"): block_B_scatter(M, T2, mask, field_r, sum_wr, nz_z, nz_target, args, res_dir)
    if do("C"): block_C_convention(M, mask, args, res_dir)
    if do("D"): block_D_imaging(M, mask, field_r, sum_wr, args, desi_dir, res_dir)
    print("\n[done] Report the [A]/[B]/[C]/[D] blocks and their verdicts.")


if __name__ == "__main__":
    main()
