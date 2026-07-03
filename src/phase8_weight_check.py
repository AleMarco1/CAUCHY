"""
CAUCHY — Phase 8, weight-asymmetry check
src/phase8_weight_check.py

The only remaining construction asymmetry between DESI and the cut-sky mocks is
the per-galaxy weight: DESI data are CIC-assigned with w = WEIGHT * WEIGHT_FKP,
the mocks with w = 1. This script bounds the effect of that asymmetry on
<pers1> and beta1_max, so we know whether the Test-1 residual (SURVIVES) is
robust to weighting or partly an artefact of it.

Two complementary bounds, both cheap:

  (A) MOCK gets an FKP-like weight.
      Assign each mock galaxy the FKP weight of the DESI random field at its
      voxel: w_FKP(x) = (alpha * field_r(x)) evaluated per galaxy, normalised.
      This mimics giving the mock the same radial/positional weighting the data
      carry, without a full n(z) FKP model. Rebuild N=n_mock cut-sky mocks with
      this weight; compare the mock <pers1>/beta1_max distribution to the
      unweighted one and to DESI.

  (B) DESI gets w = 1.
      Rebuild the DESI reference with unit weights (drop WEIGHT*WEIGHT_FKP),
      through the same build_field. If DESI <pers1>/beta1_max barely move, the
      weighting is not what drives the anomaly.

Decision rule (frozen here, consistent with gate8 spirit):
  The residual is robust to weighting IF, after both (A) and (B), DESI still
  sits >3 sigma ABOVE the mock <pers1> distribution AND >3 sigma BELOW the mock
  beta1_max distribution. Otherwise the weight asymmetry is a candidate
  explanation and must be modelled properly before Test 2.

Reuses phase8_cutsky_mocks.py machinery.

Usage:
  python src\\phase8_weight_check.py --n_mock 60 --project_root D:\\projects\\cauchy
"""

import argparse
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M


# --- build_field variant that accepts a per-galaxy weight for the mock data ---
def voxelize_mock_weighted(pos_sel, w_sel, field_r, sum_wr, mask):
    if len(pos_sel) < 100:
        return None
    field_d = M.cic_3d(pos_sel, w_sel, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    alpha = float(w_sel.sum()) / sum_wr
    return M.build_field(field_d, field_r, alpha, mask)


def fkp_weight_at(pos, field_r, alpha):
    """FKP-like per-galaxy weight = local expected density (alpha*field_r) at the
    galaxy voxel, normalised to mean 1. Mimics the data weighting positionally."""
    ijk = np.clip(((pos - M.BOX_MIN[None, :]) / M.CELL).astype(np.int32), 0, M.NGRID - 1)
    w = alpha * field_r[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
    w = np.where(w > 0, w, np.nan)
    wmean = np.nanmean(w)
    w = np.where(np.isfinite(w), w / wmean, 1.0)
    return w


def stats(vals):
    a = np.array(vals, dtype=float)
    return float(a.mean()), float(a.std(ddof=1))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_mock", type=int, default=60)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    mask = np.load(M.DESI_MASK_FILE)
    print("=" * 70)
    print("Phase 8 — weight-asymmetry check")
    print("=" * 70)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()

    # --- (B) DESI reference: w=1 vs w=WEIGHT*WEIGHT_FKP ---
    print("\n(B) DESI reference sensitivity to weights:")
    # weighted (canonical Phase 8 build)
    p_w, b_w, _ = M.recompute_desi_reference(mask, field_r, sum_wr)
    # unweighted: rebuild data field with w=1
    from astropy.io import fits
    dat = M.DESI_DIR / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        d = h['LSS'].data
        mz = (d['Z'] >= M.ZMIN) & (d['Z'] <= M.ZMAX)
        ra, dec, z = d['RA'][mz].astype(float), d['DEC'][mz].astype(float), d['Z'][mz].astype(float)
    dC = M.comoving_distance(z)
    rr, dd = np.radians(ra), np.radians(dec)
    pos_d = np.column_stack([dC*np.cos(dd)*np.cos(rr), dC*np.cos(dd)*np.sin(rr), dC*np.sin(dd)])
    field_d1 = M.cic_3d(pos_d, np.ones(len(pos_d)), M.NGRID, M.BOX_MIN, M.BOX_SIZE)
    nu_desi1 = M.build_field(field_d1, field_r, len(pos_d)/sum_wr, mask)
    f1 = M.compute_tda_features(nu_desi1, mask, M.N_THRESH)
    p_u, b_u = float(f1[5]), float(f1[4])
    print(f"    <pers1>_DESI:  weighted={p_w:.4f}  unweighted={p_u:.4f}  d={p_u-p_w:+.4f}")
    print(f"    beta1_max_DESI: weighted={b_w:.0f}  unweighted={b_u:.0f}  d={b_u-b_w:+.0f}")

    # --- (A) MOCK with FKP-like weight vs unweighted ---
    print(f"\n(A) MOCK weighting sensitivity (N={args.n_mock}):")
    p_unw, b_unw, p_wt, b_wt = [], [], [], []
    for i in range(args.n_mock):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = M.read_halo_catalog(i, 3)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = M.populate_halos_hod_with_vel(pos_h, mass_h, vel_h, M.HOD_MEDIAN, rng)
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if len(pos_sel) < 100:
            continue
        # unweighted (Test 1 baseline)
        nu0 = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        f0 = M.compute_tda_features(nu0, mask, M.N_THRESH)
        p_unw.append(float(f0[5])); b_unw.append(float(f0[4]))
        # weighted
        alpha0 = len(pos_sel) / sum_wr
        w_sel = fkp_weight_at(pos_sel, field_r, alpha0)
        nu1 = voxelize_mock_weighted(pos_sel, w_sel, field_r, sum_wr, mask)
        f1m = M.compute_tda_features(nu1, mask, M.N_THRESH)
        p_wt.append(float(f1m[5])); b_wt.append(float(f1m[4]))
        if (i + 1) % 10 == 0:
            print(f"    [{i+1}] <pers1> unw={np.mean(p_unw):.4f} wt={np.mean(p_wt):.4f} | "
                  f"beta1_max unw={np.mean(b_unw):.0f} wt={np.mean(b_wt):.0f}")

    pu_m, pu_s = stats(p_unw); pw_m, pw_s = stats(p_wt)
    bu_m, bu_s = stats(b_unw); bw_m, bw_s = stats(b_wt)

    print("\n  MOCK <pers1>:   unweighted %.4f±%.4f | weighted %.4f±%.4f" % (pu_m, pu_s, pw_m, pw_s))
    print("  MOCK beta1_max: unweighted %.0f±%.0f | weighted %.0f±%.0f" % (bu_m, bu_s, bw_m, bw_s))

    # --- Verdict: worst-case DESI-vs-mock separation across weighting choices ---
    print("\n" + "=" * 70)
    # <pers1>: DESI should sit ABOVE mocks. Use the weighting combo LEAST favourable
    # (smallest DESI, largest mock mean).
    desi_pers1_lo = min(p_w, p_u)
    mock_pers1_hi_mean = max(pu_m, pw_m); mock_pers1_hi_std = pw_s if pw_m >= pu_m else pu_s
    z_pers1_worst = (desi_pers1_lo - mock_pers1_hi_mean) / mock_pers1_hi_std
    # beta1_max: DESI should sit BELOW mocks. Least favourable = largest DESI, smallest mock.
    desi_b_hi = max(b_w, b_u)
    mock_b_lo_mean = min(bu_m, bw_m); mock_b_lo_std = bw_s if bw_m <= bu_m else bu_s
    z_beta1_worst = (desi_b_hi - mock_b_lo_mean) / mock_b_lo_std

    print(f"  WORST-CASE <pers1>   separation: z = {z_pers1_worst:+.2f}  (want > +3)")
    print(f"  WORST-CASE beta1_max separation: z = {z_beta1_worst:+.2f}  (want < -3)")
    robust = (z_pers1_worst > 3.0) and (z_beta1_worst < -3.0)
    print(f"\n  >>> WEIGHT ASYMMETRY: {'ROBUST — residual survives weighting' if robust else 'NOT ROBUST — model weights before Test 2'}")


if __name__ == "__main__":
    main()
