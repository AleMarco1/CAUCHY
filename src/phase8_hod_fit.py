"""
CAUCHY — Phase 8, HOD fit (R5-1: the #1 mundane explanation)
src/phase8_hod_fit.py

The robust beta1_max deficit (DESI below all 2000 cut-sky LCDM mocks) is not w0
(excluded). The highest-prior mundane explanation is HOD: B3 median (log_Mmin=12.5)
was never fit to the DESI clustering. A more concentrated HOD (more satellites in
massive halos) produces fewer diffuse loops for a mundane reason. R3 noted we
compute wp(rp) 'for HOD calibration' and never fit it. This script fits it.

Stages:
  1. DESI wp(rp) via TreeCorr (Landy-Szalay) from the BGS NGC data+random.
  2. Fit Zheng HOD (log_Mmin, log_M1, alpha; sigma_logM, log_M0 fixed at B3) to
     wp(rp) + n_bar on N_fid fiducial-cosmology Quijote z=0.5 boxes, by coarse
     grid + local refine. chi2 = chi2(wp) + chi2(n_bar).
  3. Save best-fit HOD to results/phase8_hod_bestfit.json.

Then run Test 2 with --hod_json results/phase8_hod_bestfit.json to regenerate the
cut-sky mocks with the CLUSTERING-CALIBRATED HOD and recompute beta1_max. If the
deficit survives a data-calibrated HOD, the #1 mundane explanation is excluded.
If it dissolves, the anomaly was HOD and the paper pivots to methodological.

Dependencies: TreeCorr (DESI wp, Landy-Szalay with randoms). Mock wp is a
self-contained periodic pair-counter in numpy/scipy (no Corrfunc/halotools).

CAVEAT: mocks are z=0.5, DESI zeff~0.2 — absolute wp amplitude differs by growth.
This is a robustness calibration, not a precision fit; the question is whether a
clustering-matched HOD changes the deficit, not the exact best-fit values.

Usage:
  python src\\phase8_hod_fit.py --n_fid 8 --project_root D:\\projects\\cauchy
"""

import argparse, json, sys, time
from pathlib import Path
from datetime import datetime, timezone
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M

# rp bins for wp(rp)
RP_BINS = np.logspace(np.log10(0.5), np.log10(30.0), 12)   # Mpc/h
RP_MID  = np.sqrt(RP_BINS[:-1] * RP_BINS[1:])
PI_MAX  = 40.0   # Mpc/h


# ---------------------------------------------------------------------------
# DESI wp(rp) via TreeCorr (Landy-Szalay)
# ---------------------------------------------------------------------------
def desi_wp(field_root):
    import treecorr
    from astropy.io import fits
    def load(fn, is_ran):
        with fits.open(fn) as h:
            d = h['LSS'].data
            mz = (d['Z'] >= M.ZMIN) & (d['Z'] <= M.ZMAX)
            ra, dec, z = d['RA'][mz], d['DEC'][mz], d['Z'][mz]
            if is_ran:
                w = d['WEIGHT_FKP'][mz]
            else:
                w = d['WEIGHT'][mz] * d['WEIGHT_FKP'][mz]
        r = M.comoving_distance(np.asarray(z, float))
        return (np.asarray(ra, float), np.asarray(dec, float), r, np.asarray(w, float))
    ddir = M.DESI_DIR
    ra_d, dec_d, r_d, w_d = load(ddir / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits", False)
    ra_r, dec_r, r_r, w_r = load(ddir / "BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits", True)
    cat_d = treecorr.Catalog(ra=ra_d, dec=dec_d, r=r_d, w=w_d, ra_units='deg', dec_units='deg')
    cat_r = treecorr.Catalog(ra=ra_r, dec=dec_r, r=r_r, w=w_r, ra_units='deg', dec_units='deg')
    cfg = dict(min_sep=RP_BINS[0], max_sep=RP_BINS[-1], nbins=len(RP_BINS)-1,
               metric='Rperp', min_rpar=-PI_MAX, max_rpar=PI_MAX, bin_slop=0.1)
    dd = treecorr.NNCorrelation(**cfg); dd.process(cat_d)
    dr = treecorr.NNCorrelation(**cfg); dr.process(cat_d, cat_r)
    rr = treecorr.NNCorrelation(**cfg); rr.process(cat_r)
    xi, _ = dd.calculateXi(rr=rr, dr=dr)
    # wp ~ 2 * PI_MAX * xi(rp) integrated over pi already via rpar limits
    wp = 2.0 * PI_MAX * xi
    return RP_MID, wp


# ---------------------------------------------------------------------------
# Mock wp(rp) on a periodic box
# ---------------------------------------------------------------------------
def mock_wp(pos, box, n_sub=150000, n_pi=20, seed=0):
    """Correct projected correlation wp(rp) on a periodic box, dependency-free.
    Counts galaxy pairs in (rp, pi) bins with a periodic cKDTree, forms xi(rp,pi)
    via the natural estimator against the analytic random expectation, and
    integrates over pi: wp(rp) = 2 * sum_pi xi(rp,pi) * dpi.

    Subsamples to n_sub for tractability; pi in [0, PI_MAX] with n_pi linear bins.
    """
    from scipy.spatial import cKDTree
    rng = np.random.default_rng(seed)
    n = min(len(pos), n_sub)
    if len(pos) > n:
        pos = pos[rng.choice(len(pos), n, replace=False)]
    nbar = n / box**3
    tree = cKDTree(pos, boxsize=box)

    pi_edges = np.linspace(0.0, PI_MAX, n_pi + 1)
    dpi = pi_edges[1] - pi_edges[0]

    # Count pairs in cylinders of radius rp up to each rp edge and |dz| slabs.
    # Strategy: for each pi slab, count pairs with transverse sep < rp_edge AND
    # line-of-sight sep in the slab. We approximate LOS as the z-axis (box is a
    # snapshot; plane-parallel), transverse = sqrt(dx^2+dy^2).
    # Efficient approach: query pairs within max 3D sep = sqrt(rp_max^2+pi_max^2).
    rmax3d = np.sqrt(RP_BINS[-1]**2 + PI_MAX**2)
    pairs = tree.query_pairs(r=rmax3d, output_type='ndarray')
    if len(pairs) == 0:
        return np.full(len(RP_MID), np.nan)
    d = pos[pairs[:, 0]] - pos[pairs[:, 1]]
    # periodic minimum image
    d -= box * np.round(d / box)
    rp = np.sqrt(d[:, 0]**2 + d[:, 1]**2)
    pi = np.abs(d[:, 2])
    sel = (rp >= RP_BINS[0]) & (rp < RP_BINS[-1]) & (pi < PI_MAX)
    rp, pi = rp[sel], pi[sel]
    # 2D histogram of DD (each unordered pair counted once -> multiply by 2 for
    # ordered convention consistency with RR expectation below)
    DD, _, _ = np.histogram2d(rp, pi, bins=[RP_BINS, pi_edges])
    DD = DD * 2.0
    # analytic RR for a uniform box: expected ordered pairs in annulus x pi slab
    area = np.pi * np.diff(RP_BINS**2)                 # per rp bin (transverse)
    RR = nbar * n * area[:, None] * (2.0 * dpi)         # x2 for +-pi symmetry
    xi = DD / RR - 1.0
    wp = 2.0 * np.nansum(xi, axis=1) * dpi
    return wp


# ---------------------------------------------------------------------------
# HOD populate at fiducial cosmology (positions only; fit uses clustering+nbar)
# ---------------------------------------------------------------------------
def populate_positions(pos_h, mass_h, hod, rng):
    log_Mmin, sigma_logM, log_M0, log_M1, alpha = hod
    p_cen = np.clip(M.mean_Ncen(mass_h, log_Mmin, sigma_logM), 0, 1)
    is_cen = rng.random(len(mass_h)) < p_cen
    lam = np.clip(M.mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin), 0, 1e4)
    n_sat = rng.poisson(lam)
    out = [pos_h[is_cen]]
    rho = 2.775e11 * M.OMM
    for i in np.where(n_sat > 0)[0]:
        ns = int(n_sat[i])
        rv = np.clip((3*mass_h[i]/(4*np.pi*200*rho))**(1/3), 0.01, 5.0)
        u = rng.random(ns); r = rv*u**(1/3)
        th = np.arccos(1-2*rng.random(ns)); ph = 2*np.pi*rng.random(ns)
        d = np.column_stack([r*np.sin(th)*np.cos(ph), r*np.sin(th)*np.sin(ph), r*np.cos(th)])
        out.append((pos_h[i]+d) % M.BOXSIZE_MOCK)
    return np.vstack(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--n_fid", type=int, default=8, help="fiducial boxes for the fit")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    print("=" * 70)
    print("Phase 8 — HOD fit to DESI wp(rp)+nbar (R5-1)")
    print("=" * 70)

    print("\n[1] DESI wp(rp) via TreeCorr...")
    rp, wp_desi = desi_wp(M.ROOT)
    nbar_desi = M.N_TARGET_BGS / (1000.0**3)   # target number density on box scale
    print("  rp[Mpc/h]:", np.round(rp, 2))
    print("  wp_desi  :", np.round(wp_desi, 1))

    # fiducial-cosmology Quijote boxes (|w0+1|<0.08) for the fit
    params = np.loadtxt(M.ROOT / "data/raw/quijote/3D_cubes/latin_hypercube_nwLH/latin_hypercube_nwLH_params.txt")
    w0_all = params[:, 6]; Om_all = params[:, 0]
    fid_idx = np.where((np.abs(w0_all + 1.0) < 0.08) & (Om_all > 0.28) & (Om_all < 0.35))[0][:args.n_fid]
    print(f"\n[2] Fit su {len(fid_idx)} box fiduciali: {list(fid_idx)}")

    # Coarse grid over (log_Mmin, log_M1, alpha); sigma_logM, log_M0 fixed at B3
    grid_Mmin = [12.5, 12.8, 13.1, 13.4]
    grid_M1   = [13.2, 13.5, 13.8]
    grid_alpha= [0.8, 1.0, 1.2]
    best = None
    t0 = time.time()
    halos = []
    for idx in fid_idx:
        ph, mh, _ = M.read_halo_catalog(int(idx), 3)
        halos.append((ph, mh))

    for lm in grid_Mmin:
        for l1 in grid_M1:
            for al in grid_alpha:
                hod = (lm, 0.55, 12.25, l1, al)
                wps, nbars = [], []
                for (ph, mh) in halos:
                    rng = np.random.default_rng(args.seed)
                    pos = populate_positions(ph, mh, hod, rng)
                    nbars.append(len(pos) / M.BOXSIZE_MOCK**3)
                    wps.append(mock_wp(pos, M.BOXSIZE_MOCK))
                wp_m = np.nanmean(wps, axis=0)
                nb_m = np.mean(nbars)
                # chi2: relative wp residual + nbar residual
                mwp = np.isfinite(wp_m) & np.isfinite(wp_desi) & (wp_desi != 0)
                chi2_wp = np.mean(((wp_m[mwp] - wp_desi[mwp]) / (np.abs(wp_desi[mwp]) + 1e-6))**2)
                chi2_nb = ((nb_m - nbar_desi) / nbar_desi)**2
                chi2 = chi2_wp + chi2_nb
                if best is None or chi2 < best["chi2"]:
                    best = dict(hod=hod, chi2=float(chi2), chi2_wp=float(chi2_wp),
                                chi2_nb=float(chi2_nb), nbar=float(nb_m),
                                wp=[float(x) for x in wp_m])
                print(f"  Mmin={lm} M1={l1} a={al}: chi2={chi2:.3f} "
                      f"(wp={chi2_wp:.3f}, nb={chi2_nb:.3f}, nbar={nb_m:.2e})")

    print(f"\n[3] Best-fit HOD: log_Mmin={best['hod'][0]}, log_M1={best['hod'][3]}, "
          f"alpha={best['hod'][4]}  chi2={best['chi2']:.3f}")
    print(f"    (B3 baseline was log_Mmin=12.5, log_M1=13.5, alpha=1.0)")
    print(f"    elapsed {(time.time()-t0)/60:.1f} min")

    out = {
        "output_id": "phase8_hod_fit",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "rp_mid": [float(x) for x in rp],
        "wp_desi": [float(x) for x in wp_desi],
        "nbar_desi_box": float(nbar_desi),
        "best_fit": {
            "log_Mmin": best["hod"][0], "sigma_logM": 0.55, "log_M0": 12.25,
            "log_M1": best["hod"][3], "alpha": best["hod"][4],
            # full 9-vector for Test 2 HOD override (A_cen,A_sat,eta_vel,eta_conc=defaults)
            "hod_vector": [best["hod"][0], 0.55, 12.25, best["hod"][3], best["hod"][4],
                           0.0, 0.0, 1.0, 1.0],
        },
        "chi2": best["chi2"], "chi2_wp": best["chi2_wp"], "chi2_nbar": best["chi2_nb"],
        "nbar_bestfit_box": best["nbar"],
        "note": "z=0.5 fit; DESI zeff~0.2 growth caveat. Robustness calibration for the beta1_max deficit test.",
    }
    outp = M.RES_DIR / "phase8_hod_bestfit.json"
    json.dump(out, open(outp, "w"), indent=2)
    print(f"\n[SAVED] {outp}")
    print("\nProssimo: Test 2 con l'HOD calibrato:")
    print("  python src\\phase8_test2_masked.py --n_pilot 200 --save_fields \\")
    print("      --hod_json results\\phase8_hod_bestfit.json --project_root D:\\projects\\cauchy")


if __name__ == "__main__":
    main()
