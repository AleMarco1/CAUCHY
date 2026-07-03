"""
CAUCHY — Phase 8, Script 1
src/phase8_cutsky_mocks.py

TEST 1 (diagnostic, exact-replica): does the DESI topological anomaly survive
survey geometry?

Rationale (gate8_prior_v1_0.json):
  The canonical DESI TDA (phase6_bgs_tda.py) runs gudhi CubicalComplex on the
  FULL 128^3 embedding cube with ~85% of voxels set to 0.0 (exterior). The mask
  is used only for thresholds/mean, NOT to exclude the exterior from the
  filtration. Mocks (phase6_smoothing_sensitivity.compute_b2_full) are periodic
  boxes with no mask and mode='wrap' smoothing. The two <pers1> statistics are
  therefore NOT computed on comparable geometries.

  This script rebuilds the mock reference distribution by applying the SAME
  construction as DESI: cut-sky carving with the DESI NGC mask + n(z) + FKP,
  zero-exterior embedding, and the identical UNMASKED compute_tda_features.

  DESI values are UNCHANGED (0.45886, 29683). Only the mock side is rebuilt.

Construction (option (a): satellites at halo bulk velocity, no intra-halo disp):
  1. Read FoF halos from groups_003 (z=0.5), WITH group velocities.
  2. HOD populate (B3 median), assign per-galaxy velocity = parent halo velocity.
  3. Tile the periodic 1000 Mpc/h box into the DESI embedding cube.
  4. Observer at Cartesian origin; per galaxy -> (RA, Dec, z_cosmo).
  5. RSD: z_obs = z_cosmo + (1+z_cosmo) * v_los / c.
  6. Carve: keep galaxies whose embedding voxel is in the DESI NGC mask AND
     z_obs in [0.1, 0.4].
  7. Radial downsample to match BGS NGC n(z).
  8. delta_FKP against the DESI random field, exterior = 0.0, smoothing R=5.
  9. compute_tda_features UNMASKED (identical to phase6_bgs_tda.py).
 10. Collect <pers1> and beta1_max per mock; empirical rank of DESI.

Output:
  results/phase8_cutsky_test1.json
  results/phase8_cutsky_fields/cutsky_{i:04d}.npz   (delta field per mock, optional)

Usage:
  python src/phase8_cutsky_mocks.py --n_pilot 200 --project_root D:\projects\cauchy

VERIFY BEFORE TREATING AS FINAL (see gate8 declared_limitations):
  - GADGET_VEL_SQRT_A: whether Quijote group_tab velocities need the sqrt(a) factor.
  - FoF GroupVel byte offset (validated by --check_fof on one file).
  - Random-catalogue column names (WEIGHT_FKP).
"""

import argparse
import json
import time
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

# ---------------------------------------------------------------------------
# CLI — only parse the real command line when run as the main program. When this
# module is IMPORTED (e.g. by phase8_weight_check.py / phase8_field_diagnostic.py),
# parse an empty list so those scripts keep their own argparse.
# ---------------------------------------------------------------------------
parser = argparse.ArgumentParser()
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--n_pilot", type=int, default=200)
parser.add_argument("--snapnum", type=int, default=3, help="3 = z=0.5")
parser.add_argument("--seed", type=int, default=42)
parser.add_argument("--save_fields", action="store_true",
                    help="Save per-mock delta fields (large; off by default)")
parser.add_argument("--check_fof", action="store_true",
                    help="Validate FoF velocity offset on sim 0 and exit")
args = parser.parse_args() if __name__ == "__main__" else parser.parse_args([])

ROOT = Path(args.project_root)
np.random.seed(args.seed)

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
HOD_CATALOG_DIR = ROOT / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH_hod"
DESI_DIR        = ROOT / "data" / "raw" / "desi_dr1"
RAN_FITS        = DESI_DIR / "BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits"
NZ_FILE         = DESI_DIR / "BGS_BRIGHT-21.5_NGC_nz.txt"
FLD_DIR         = ROOT / "data" / "processed" / "phase6_fields"
DESI_MASK_FILE  = FLD_DIR / "bgs_ngc_mask_128.npy"
RES_DIR         = ROOT / "results"
OUT_FIELDS_DIR  = RES_DIR / "phase8_cutsky_fields"
OUTPUT_JSON     = RES_DIR / "phase8_cutsky_test1.json"
RES_DIR.mkdir(parents=True, exist_ok=True)
if args.save_fields:
    OUT_FIELDS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Frozen geometry (phase6_voxelize_diagnostics.json, region NGC) and constants
# ---------------------------------------------------------------------------
BOXSIZE_MOCK = 1000.0          # Mpc/h, Quijote periodic box
NGRID        = 128
N_PART_MIN   = 20

# DESI NGC embedding cube (must match phase6_bgs_voxelize output exactly)
BOX_MIN  = np.array([-1085.5836039835003, -1059.3513403117618, -194.44091723978792])
BOX_SIZE = 1997.3629167166155
CELL     = BOX_SIZE / NGRID     # 15.6044 Mpc/h
D_C_ZMIN = 292.535950750378
D_C_ZMAX = 1080.7298534541035
ZMIN, ZMAX = 0.1, 0.4

R_SMOOTH = 5.0
SIGMA_PX = R_SMOOTH / CELL      # 0.3204 (matches DESI canonical sigma_px)

# Cosmology (Planck 2018 fiducial, h=1 units) — identical to phase6_bgs_voxelize
OMM = 0.3175
OML = 1.0 - OMM
C_OVER_H0 = 2997.92             # Mpc/h
C_KMS     = 299792.458          # km/s

# HOD B3 median (gate8 frozen)
HOD_MEDIAN = np.array([12.5, 0.55, 12.25, 13.5, 1.0, 0.0, 0.0, 1.0, 1.0])

# Gadget velocity convention: Quijote group velocities. If True, multiply by
# sqrt(a) to obtain peculiar velocity in km/s. VERIFY against Quijote docs.
GADGET_VEL_SQRT_A = True
SCALE_A = 1.0 / (1.0 + 0.5)     # z=0.5

# DESI reference is RECOMPUTED on the native grid at sigma_px=0.3204 (see main),
# NOT taken from the canonical 0.459 (which was sigma_px=0.216). This makes the
# comparison like-for-like: mock and DESI on the same physical grid, same R.
DESI_FIELD_R5 = FLD_DIR / "bgs_ngc_delta_128.npy"   # canonical R=5 native grid
PERS1_DESI = None        # filled in main() by recompute_desi_reference()
BETA1_MAX_DESI = None

# Density target: nominal BGS NGC count (abstract / all tables). Used to scale
# the radial downsampling so N_sel ~ N_TARGET_BGS instead of ~1.6x.
N_TARGET_BGS = 217614

N_THRESH = 100

# ---------------------------------------------------------------------------
# Cosmology helpers (comoving distance + inverse), consistent w/ voxelizer
# ---------------------------------------------------------------------------
def comoving_distance(z_arr, n_steps=500):
    z_arr = np.atleast_1d(np.asarray(z_arr, dtype=np.float64))
    out = np.zeros(len(z_arr))
    for i, zi in enumerate(z_arr):
        zz = np.linspace(0.0, zi, n_steps)
        EE = np.sqrt(OMM * (1 + zz) ** 3 + OML)
        out[i] = C_OVER_H0 * np.trapezoid(1.0 / EE, zz)
    return out

# Inverse table r -> z over a generous range
_Z_TAB = np.linspace(0.0, 0.6, 4001)
_DC_TAB = comoving_distance(_Z_TAB)
def z_of_dc(dc):
    return np.interp(dc, _DC_TAB, _Z_TAB)

# ---------------------------------------------------------------------------
# FoF reader WITH velocities (extends phase5_hod_b3.FoF_catalog)
# Layout (from phase5_hod_b3.py header comment, verified SOA nwLH):
#   header 24 bytes; N = first int32
#   GroupLen  @ 24            (int32,  N*4)
#   GroupMass @ 24 + N*8      (float32,N*4)
#   Pos  x @ 24+N*12, y @ 24+N*16, z @ 24+N*20
#   Vel vx @ 24+N*24, vy @ 24+N*28, vz @ 24+N*32
# ---------------------------------------------------------------------------
class FoF_catalog:
    def __init__(self, snapdir, snapnum):
        fname = Path(snapdir) / f"groups_{snapnum:03d}" / f"group_tab_{snapnum:03d}.0"
        assert fname.exists(), f"Catalogo non trovato: {fname}"
        raw = fname.read_bytes()
        N = int(np.frombuffer(raw[:4], dtype=np.int32)[0])
        self.Ngroups = N
        if N == 0 or len(raw) < 24 + N * 84:
            self.GroupLen  = np.array([], dtype=np.int32)
            self.GroupMass = np.array([], dtype=np.float32)
            self.GroupPos  = np.zeros((0, 3), dtype=np.float32)
            self.GroupVel  = np.zeros((0, 3), dtype=np.float32)
            return
        def rd_i(off): return np.frombuffer(raw[off:off + N * 4], dtype=np.int32).copy()
        def rd_f(off): return np.frombuffer(raw[off:off + N * 4], dtype=np.float32).copy()
        self.GroupLen  = rd_i(24)
        self.GroupMass = rd_f(24 + N * 8)
        self.GroupPos  = np.column_stack([rd_f(24 + N * 12),
                                          rd_f(24 + N * 16),
                                          rd_f(24 + N * 20)])
        self.GroupVel  = np.column_stack([rd_f(24 + N * 24),
                                          rd_f(24 + N * 28),
                                          rd_f(24 + N * 32)])


def read_halo_catalog(sim_idx, snapnum):
    snapdir = HOD_CATALOG_DIR / str(sim_idx)
    FoF = FoF_catalog(snapdir, snapnum)
    if FoF.Ngroups == 0:
        return None, None, None
    mask   = FoF.GroupLen >= N_PART_MIN
    pos_h  = (FoF.GroupPos[mask] / 1e3) % BOXSIZE_MOCK      # kpc/h -> Mpc/h
    mass_h = FoF.GroupMass[mask] * 1e10                     # 1e10 Msun/h -> Msun/h
    vel_h  = FoF.GroupVel[mask].astype(np.float64)          # km/s (see GADGET_VEL_SQRT_A)
    if GADGET_VEL_SQRT_A:
        vel_h = vel_h * np.sqrt(SCALE_A)
    return pos_h, mass_h, vel_h


# ---------------------------------------------------------------------------
# HOD (identical mean occupation to phase5_hod_b3.py) + velocities (option a)
# ---------------------------------------------------------------------------
def mean_Ncen(mass_h, log_Mmin, sigma_logM):
    from scipy.special import erf
    return 0.5 * (1.0 + erf((np.log10(mass_h) - log_Mmin) / (sigma_logM + 1e-10)))

def mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin):
    M0, M1 = 10 ** log_M0, 10 ** log_M1
    N_sat = np.zeros(len(mass_h))
    m = mass_h > M0
    ratio = np.where(m, (mass_h - M0) / (M1 + 1e-30), 0.0)
    N_sat[m] = ratio[m] ** alpha
    N_sat *= mean_Ncen(mass_h, log_Mmin, 0.2)
    return N_sat

def populate_halos_hod_with_vel(pos_h, mass_h, vel_h, hod_params, rng):
    """Return (pos_gal [N,3] Mpc/h, vel_gal [N,3] km/s). Option (a): satellites
    inherit the parent halo bulk velocity, no intra-halo dispersion."""
    log_Mmin, sigma_logM, log_M0, log_M1, alpha, A_cen, A_sat, eta_vel, eta_conc = hod_params
    N_h = len(mass_h)
    if N_h == 0:
        return np.zeros((0, 3)), np.zeros((0, 3))

    p_cen = np.clip(mean_Ncen(mass_h, log_Mmin, sigma_logM), 0.0, 1.0)
    is_central = rng.random(N_h) < p_cen
    lam_sat = np.clip(mean_Nsat(mass_h, log_M0, log_M1, alpha, log_Mmin), 0.0, 1e4)
    n_sat = rng.poisson(lam_sat)

    pos_list, vel_list = [], []
    if is_central.any():
        pos_list.append(pos_h[is_central])
        vel_list.append(vel_h[is_central])

    rho_crit = 2.775e11 * OMM
    for i in range(N_h):
        ns = int(n_sat[i])
        if ns <= 0:
            continue
        r_vir = np.clip((3.0 * mass_h[i] / (4.0 * np.pi * 200.0 * rho_crit)) ** (1.0 / 3.0),
                        0.01, 5.0) * eta_conc
        u = rng.random(ns)
        r = r_vir * u ** (1.0 / 3.0)
        theta = np.arccos(1.0 - 2.0 * rng.random(ns))
        phi = 2.0 * np.pi * rng.random(ns)
        dxyz = np.column_stack([r * np.sin(theta) * np.cos(phi),
                                r * np.sin(theta) * np.sin(phi),
                                r * np.cos(theta)])
        pos_list.append((pos_h[i] + dxyz) % BOXSIZE_MOCK)
        vel_list.append(np.tile(vel_h[i], (ns, 1)))   # option (a): halo bulk vel

    if not pos_list:
        return np.zeros((0, 3)), np.zeros((0, 3))
    return np.vstack(pos_list), np.vstack(vel_list)


# ---------------------------------------------------------------------------
# CIC (identical to phase6_bgs_voxelize.cic_3d)
# ---------------------------------------------------------------------------
def cic_3d(pos, weights, ngrid, box_min, box_size):
    cell = box_size / ngrid
    xyz  = np.clip((pos - box_min[None, :]) / cell, 0.0, ngrid - 1e-6)
    ijk  = xyz.astype(np.int32)
    d    = (xyz - ijk).astype(np.float32)
    w    = weights.astype(np.float32)
    flat = np.zeros(ngrid ** 3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = np.clip(ijk[:, 0] + di, 0, ngrid - 1)
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = np.clip(ijk[:, 1] + dj, 0, ngrid - 1)
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = np.clip(ijk[:, 2] + dk, 0, ngrid - 1)
                idx = ii * ngrid ** 2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz * w,
                                    minlength=ngrid ** 3).astype(np.float32)
    return flat.reshape(ngrid, ngrid, ngrid)


# ---------------------------------------------------------------------------
# UNMASKED TDA — byte-for-byte the DESI canonical (phase6_bgs_tda.compute_tda_features)
# The CubicalComplex runs on the FULL -field (exterior zeros included). mask is
# used only for thresholds and the b0 mean level — identical to DESI.
# ---------------------------------------------------------------------------
def compute_tda_features(delta_field, mask, n_thresh=100, masked=False):
    import gudhi
    # The log-transform is applied upstream in build_field (on the RAW delta).
    # compute_tda_features works on the field as-is.
    #
    # masked=False (Test 1): CubicalComplex on the FULL -field, exterior zeros
    #   included in the filtration — identical to the (broken) DESI canonical.
    # masked=True (Test 2): exterior EXCLUDED from the filtration. Exterior cells
    #   are set to a high sentinel in -field so they enter the sublevel filtration
    #   LAST; any H1 loop that would need the exterior to close is cut (its birth
    #   or death touches the sentinel and is removed). Applied identically to DESI
    #   and mocks — the only correct like-for-like treatment for a bounded survey.
    field = delta_field.astype(np.float64)
    field_in = field[mask]
    nu_min = float(np.percentile(field_in, 1))
    nu_max = float(np.percentile(field_in, 99))
    thresholds = np.linspace(nu_min, nu_max, n_thresh)

    SENT = 1.0e6
    if masked:
        field_work = field.copy()
        field_work[~mask] = -SENT          # exterior very low in field ...
        field_neg = -field_work            # ... => +SENT in -field (enters last)
        cutoff = SENT / 2.0
    else:
        field_neg = -field
        cutoff = np.inf

    cc = gudhi.CubicalComplex(dimensions=list(field_neg.shape),
                              top_dimensional_cells=field_neg.flatten())
    cc.compute_persistence()
    diag_0 = cc.persistence_intervals_in_dimension(0)
    diag_1 = cc.persistence_intervals_in_dimension(1)

    def proc(diag):
        if len(diag) == 0:
            return np.array([]), np.array([]), np.array([])
        d = np.array(diag)
        keep = np.isfinite(d[:, 1]) & (d[:, 0] < cutoff) & (d[:, 1] < cutoff)
        df = d[keep]
        b, dth = -df[:, 0], -df[:, 1]
        return b, dth, b - dth

    b0, d0, _   = proc(diag_0)
    b1, d1, p1  = proc(diag_1)

    b1_curve = np.zeros(n_thresh)
    b0_curve = np.zeros(n_thresh)
    for k, nu in enumerate(thresholds):
        if len(b0):
            b0_curve[k] = np.sum((b0 >= nu) & (d0 < nu))
        if len(b1):
            b1_curve[k] = np.sum((b1 >= nu) & (d1 < nu))

    feats = np.zeros(8, dtype=np.float64)
    if b1_curve.max() > 0:
        pk = np.argmax(b1_curve)
        feats[0] = thresholds[pk]
        feats[1] = b1_curve[pk]
        half = b1_curve.max() / 2.0
        above = np.where(b1_curve >= half)[0]
        feats[2] = (thresholds[above[-1]] - thresholds[above[0]]) if len(above) > 1 else 0.0
        feats[3] = np.trapezoid(b1_curve, thresholds)
    if len(p1) > 0:
        feats[4] = len(p1)
        feats[5] = float(np.mean(p1))
        feats[6] = float(np.sum(p1 >= np.percentile(p1, 90)))
    mean_val = float(field[mask].mean())
    feats[7] = b0_curve[np.argmin(np.abs(thresholds - mean_val))]
    # feats[4] = beta1_max (n loops), feats[5] = <pers1>
    return feats


# ---------------------------------------------------------------------------
# Load DESI random field once (denominator of delta_FKP) + n(z) target
# ---------------------------------------------------------------------------
def load_desi_random_field():
    from astropy.io import fits
    with fits.open(RAN_FITS) as h:
        r = h['LSS'].data
        mz = (r['Z'] >= ZMIN) & (r['Z'] <= ZMAX)
        ra, dec, z = r['RA'][mz].astype(np.float64), r['DEC'][mz].astype(np.float64), r['Z'][mz].astype(np.float64)
        w = r['WEIGHT_FKP'][mz].astype(np.float64)
    dC = comoving_distance(z)
    ra_r, dec_r = np.radians(ra), np.radians(dec)
    x = dC * np.cos(dec_r) * np.cos(ra_r)
    y = dC * np.cos(dec_r) * np.sin(ra_r)
    zc = dC * np.sin(dec_r)
    pos_r = np.column_stack([x, y, zc])
    field_r = cic_3d(pos_r, w, NGRID, BOX_MIN, BOX_SIZE)
    sum_wr = float(w.sum())
    return field_r, sum_wr

def load_desi_data_field():
    """CIC of the DESI BGS NGC data catalogue with w = WEIGHT * WEIGHT_FKP,
    same coordinates/geometry as the random loader. Returns (field_d, sum_wd)."""
    from astropy.io import fits
    dat = DESI_DIR / "BGS_BRIGHT-21.5_NGC_clustering.dat.fits"
    with fits.open(dat) as h:
        d = h['LSS'].data
        mz = (d['Z'] >= ZMIN) & (d['Z'] <= ZMAX)
        ra, dec, z = d['RA'][mz].astype(np.float64), d['DEC'][mz].astype(np.float64), d['Z'][mz].astype(np.float64)
        w = (d['WEIGHT'][mz] * d['WEIGHT_FKP'][mz]).astype(np.float64)
    dC = comoving_distance(z)
    ra_r, dec_r = np.radians(ra), np.radians(dec)
    x = dC * np.cos(dec_r) * np.cos(ra_r)
    y = dC * np.cos(dec_r) * np.sin(ra_r)
    zc = dC * np.sin(dec_r)
    pos_d = np.column_stack([x, y, zc])
    field_d = cic_3d(pos_d, w, NGRID, BOX_MIN, BOX_SIZE)
    return field_d, float(w.sum())


def load_bgs_nz():
    """Return (z_centres, nz) from the BGS n(z) file. Robust to column layout:
    uses the first column as z and the last numeric column as n(z)."""
    tab = np.loadtxt(NZ_FILE, comments='#')
    if tab.ndim == 1:
        tab = tab.reshape(1, -1)
    return tab[:, 0], tab[:, -1]


# ---------------------------------------------------------------------------
# Cut-sky carving of one mock (tiling + observer + RSD + mask + n(z))
# ---------------------------------------------------------------------------
_MASK = None  # loaded in main

def carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng):
    """Map periodic-box galaxies into the DESI embedding cube, apply RSD, carve
    by mask + z range, downsample to BGS n(z). Returns selected embedding-frame
    Cartesian positions [M,3] (redshift-space)."""
    # Tile offsets covering the embedding cube along each axis
    def offsets(axis):
        lo, hi = BOX_MIN[axis], BOX_MIN[axis] + BOX_SIZE
        k_lo = int(np.floor(lo / BOXSIZE_MOCK))
        k_hi = int(np.floor(hi / BOXSIZE_MOCK))
        return list(range(k_lo, k_hi + 1))
    ox, oy, oz = offsets(0), offsets(1), offsets(2)

    # Pass 1: collect ALL in-survey candidates (mask + z range), no downsampling.
    cand_P, cand_z = [], []
    for kx in ox:
        for ky in oy:
            for kz in oz:
                shift = np.array([kx, ky, kz]) * BOXSIZE_MOCK
                P = pos_gal + shift[None, :]
                inb = np.all((P >= BOX_MIN[None, :]) &
                             (P < (BOX_MIN + BOX_SIZE)[None, :]), axis=1)
                if not inb.any():
                    continue
                P = P[inb]
                V = vel_gal[inb]
                # Real-space distance & LOS
                dC = np.linalg.norm(P, axis=1)
                good = (dC > 1e-6) & (dC >= D_C_ZMIN - 50) & (dC <= D_C_ZMAX + 50)
                if not good.any():
                    continue
                P, V, dC = P[good], V[good], dC[good]
                rhat = P / dC[:, None]
                z_cosmo = z_of_dc(dC)
                v_los = np.sum(V * rhat, axis=1)                 # km/s
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / C_KMS
                dC_rsd = np.interp(np.clip(z_obs, 0.0, 0.6), _Z_TAB, _DC_TAB)
                P_rsd = rhat * dC_rsd[:, None]
                zsel = (z_obs >= ZMIN) & (z_obs <= ZMAX)
                if not zsel.any():
                    continue
                P_rsd, z_obs_s = P_rsd[zsel], z_obs[zsel]
                ijk = np.clip(((P_rsd - BOX_MIN[None, :]) / CELL).astype(np.int32),
                              0, NGRID - 1)
                inmask = mask[ijk[:, 0], ijk[:, 1], ijk[:, 2]]
                if not inmask.any():
                    continue
                cand_P.append(P_rsd[inmask])
                cand_z.append(z_obs_s[inmask])
    if not cand_P:
        return np.zeros((0, 3))
    P_cand = np.vstack(cand_P)
    z_cand = np.concatenate(cand_z)

    # Pass 2: global n(z)-shaped downsampling to hit N_TARGET_BGS.
    # Desired count per z-bin ∝ BGS n(z); acceptance = desired/available, capped 1.
    edges = np.concatenate([[nz_z[0] - 0.5 * (nz_z[1] - nz_z[0])],
                            0.5 * (nz_z[:-1] + nz_z[1:]),
                            [nz_z[-1] + 0.5 * (nz_z[-1] - nz_z[-2])]])
    which = np.clip(np.digitize(z_cand, edges) - 1, 0, len(nz_z) - 1)
    n_cand_bin = np.bincount(which, minlength=len(nz_z)).astype(float)
    shape = np.clip(nz_target, 0.0, None).astype(float)
    if shape.sum() <= 0:
        return np.zeros((0, 3))
    desired = shape / shape.sum() * float(N_TARGET_BGS)
    with np.errstate(divide='ignore', invalid='ignore'):
        p_bin = np.where(n_cand_bin > 0, desired / n_cand_bin, 0.0)
    p_bin = np.minimum(p_bin, 1.0)
    p = p_bin[which]
    keep = rng.random(len(z_cand)) < p
    return P_cand[keep]


def build_field(field_d, field_r, alpha, mask):
    """Shared field construction for DESI and cut-sky mocks. Identical byte-for-byte
    on both sides. Pipeline (as STATED in the paper):
      raw delta_FKP (>= -1)  ->  nu = log(1 + clip(delta, -1))  ->  smooth  ->  mean-sub.
    The log on the RAW delta bounds the FKP shot-noise positive tail (delta up to
    +150 -> log(151)=5.0, matching DESI's raw range) without a spurious negative
    spike. Exterior/invalid voxels are 0 (= log(1)), preserving the zero exterior."""
    delta = np.zeros((NGRID, NGRID, NGRID), dtype=np.float64)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0
    nu = np.zeros_like(delta)
    nu[mask] = np.log(1.0 + np.clip(delta[mask], -1.0 + 1e-3, None))
    nu = gaussian_filter(nu, sigma=SIGMA_PX)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


def voxelize_mock(pos_sel, field_r, sum_wr, mask):
    """Cut-sky mock field via the shared build_field (log-transform included)."""
    if len(pos_sel) < 100:
        return None
    w_d = np.ones(len(pos_sel))
    field_d = cic_3d(pos_sel, w_d, NGRID, BOX_MIN, BOX_SIZE)
    alpha = float(w_d.sum()) / sum_wr
    return build_field(field_d, field_r, alpha, mask)


# ---------------------------------------------------------------------------
# FoF offset self-check
# ---------------------------------------------------------------------------
def check_fof():
    pos_h, mass_h, vel_h = read_halo_catalog(0, args.snapnum)
    print("[CHECK_FOF] sim 0, snapnum", args.snapnum)
    print(f"  N halos (>=20 part): {len(mass_h)}")
    print(f"  pos_h  range Mpc/h : [{pos_h.min():.1f}, {pos_h.max():.1f}] (expect ~[0,1000])")
    print(f"  mass_h range Msun/h: [{mass_h.min():.2e}, {mass_h.max():.2e}]")
    print(f"  |vel_h| km/s       : mean={np.linalg.norm(vel_h,axis=1).mean():.1f} "
          f"max={np.linalg.norm(vel_h,axis=1).max():.1f} (expect ~few 100s)")
    print("  If |vel| is ~0 or ~1e5, the GroupVel offset or sqrt(a) factor is wrong.")


# ---------------------------------------------------------------------------
# Recompute the DESI reference on the NATIVE grid at sigma_px=0.3204.
# The canonical bgs_ngc_delta_128.npy was voxelized at R=5 on the DESI cell
# (15.6 Mpc/h) -> sigma_px = 5/15.6 = 0.3204. This is ALREADY the mock cut-sky
# sigma_px. So <pers1>_DESI at matched sigma_px is simply compute_tda_features
# on the canonical field. (The 0.459 canonical was reported at sigma_px=0.216,
# i.e. R=5 on a 23.14 Mpc/h reference cell — a different grid. We do NOT use it.)
# ---------------------------------------------------------------------------
def recompute_desi_reference(mask, field_r, sum_wr):
    """Rebuild the DESI NGC field from the FITS catalogues through the SHARED
    build_field (log-transform included), so the DESI reference is consistent
    with the cut-sky mocks. This does NOT use the canonical 0.459 (built without
    log): every paper number moves as a result, by design."""
    field_d, sum_wd = load_desi_data_field()
    alpha = sum_wd / sum_wr
    nu_desi = build_field(field_d, field_r, alpha, mask)
    feats = compute_tda_features(nu_desi, mask, N_THRESH)
    return float(feats[5]), float(feats[4]), float(nu_desi[mask].std())


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    global PERS1_DESI, BETA1_MAX_DESI
    print("=" * 70)
    print("CAUCHY Phase 8 — Script 1: Cut-sky mocks, TEST 1 (diagnostic)")
    print("=" * 70)
    print(f"  snapnum={args.snapnum} (z=0.5), n_pilot={args.n_pilot}")
    print(f"  embedding cell={CELL:.3f} Mpc/h, sigma_px={SIGMA_PX:.4f}")
    print(f"  density target N_sel ~ {N_TARGET_BGS:,} (BGS NGC nominal)")

    for p, lbl in [(DESI_MASK_FILE, "mask"), (RAN_FITS, "random FITS"),
                   (NZ_FILE, "n(z)"), (HOD_CATALOG_DIR, "HOD halo dir")]:
        if not p.exists():
            print(f"[ERRORE] Mancante ({lbl}): {p}"); sys.exit(1)

    if args.check_fof:
        check_fof(); return

    mask = np.load(DESI_MASK_FILE)
    print(f"  mask fill: {100*mask.mean():.1f}%  ({mask.sum():,} voxel)")

    print("\n[1/3] Costruzione campo random DESI (denominatore FKP)...")
    field_r, sum_wr = load_desi_random_field()
    nz_z, nz_target = load_bgs_nz()
    print(f"  random field pronto; n(z) target su {len(nz_z)} bin")

    print("\n[0/3] Ricostruzione DESI reference dai FITS con log-transform "
          "(build_field condiviso)...")
    PERS1_DESI, BETA1_MAX_DESI, std_desi = recompute_desi_reference(mask, field_r, sum_wr)
    print(f"  nu_std_in_survey (DESI)      = {std_desi:.4f}  "
          f"(era 1.65 senza log — deve scendere)")
    print(f"  <pers1>_DESI (log, sigma_px=0.3204) = {PERS1_DESI:.5f}  "
          f"[canonico senza-log 0.45886 NON usato]")
    print(f"  beta1_max_DESI               = {BETA1_MAX_DESI:.0f}")

    print(f"\n[2/3] Loop su {args.n_pilot} mock cut-sky...")
    pers1_list, beta1_list, ngal_list = [], [], []
    t0 = time.time()
    for i in range(args.n_pilot):
        rng = np.random.default_rng(args.seed + i)
        pos_h, mass_h, vel_h = read_halo_catalog(i, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = populate_halos_hod_with_vel(pos_h, mass_h, vel_h,
                                                       HOD_MEDIAN, rng)
        if len(pos_gal) < 100:
            continue
        pos_sel = carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        delta_s = voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if delta_s is None:
            continue
        feats = compute_tda_features(delta_s, mask, N_THRESH)
        beta1_list.append(float(feats[4]))
        pers1_list.append(float(feats[5]))
        ngal_list.append(int(len(pos_sel)))
        if args.save_fields:
            np.savez(OUT_FIELDS_DIR / f"cutsky_{i:04d}.npz", delta=delta_s)
        if (i + 1) % 20 == 0 or i == 0:
            eta = (time.time() - t0) / (i + 1) * (args.n_pilot - i - 1) / 60
            print(f"  [{i+1}/{args.n_pilot}] N_sel~{np.median(ngal_list):.0f} "
                  f"<pers1>={np.mean(pers1_list):.4f} "
                  f"beta1_max={np.mean(beta1_list):.0f}  ETA={eta:.1f}min")

    pers1 = np.array(pers1_list)
    beta1 = np.array(beta1_list)
    n_ok = len(pers1)
    if n_ok < 20:
        print(f"[ERRORE] Solo {n_ok} mock validi — insufficiente."); sys.exit(1)

    print(f"\n[3/3] Verdetto (N={n_ok} mock validi)...")
    # <pers1>
    p_mean, p_std = float(pers1.mean()), float(pers1.std(ddof=1))
    z_pers1 = (PERS1_DESI - p_mean) / p_std
    rank_pers1 = float(np.mean(pers1 < PERS1_DESI))            # fraction of mocks below DESI
    # beta1_max
    b_mean, b_std = float(beta1.mean()), float(beta1.std(ddof=1))
    z_beta1 = (BETA1_MAX_DESI - b_mean) / b_std
    rank_beta1 = float(np.mean(beta1 < BETA1_MAX_DESI))

    # Frozen gate1 decision
    dissolved = (abs(z_pers1) < 3.0) and (abs(z_beta1) < 3.0)
    survives  = (z_pers1 >= 3.0) and (z_beta1 <= -3.0)
    verdict = "DISSOLVED" if dissolved else ("SURVIVES" if survives else "PARTIAL")

    print(f"  <pers1>: DESI={PERS1_DESI:.4f}  mock={p_mean:.4f}±{p_std:.4f}  "
          f"z={z_pers1:+.2f}  rank={rank_pers1*100:.1f}%")
    print(f"  beta1_max: DESI={BETA1_MAX_DESI:.0f}  mock={b_mean:.0f}±{b_std:.0f}  "
          f"z={z_beta1:+.2f}  rank={rank_beta1*100:.1f}%")
    print(f"\n  >>> VERDETTO GATE 1: {verdict}")
    if verdict == "DISSOLVED":
        print("      L'anomalia era la geometria. Pivot a paper metodologico.")
    elif verdict == "SURVIVES":
        print("      Geometria non spiega. Procedere a Test 2 e N=2000.")
    else:
        print("      Esito parziale. Realistico: paper metodologico con residuo.")

    out = {
        "schema_version": "1.0",
        "output_id": "phase8_cutsky_test1",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "authority": "gate8_prior_v1_0.json",
        "n_pilot_requested": args.n_pilot,
        "n_mock_valid": n_ok,
        "snapnum": args.snapnum,
        "sigma_px": SIGMA_PX,
        "hod_params_b3_median": HOD_MEDIAN.tolist(),
        "satellite_velocity": "option_a_no_intrahalo_dispersion",
        "gadget_vel_sqrt_a": GADGET_VEL_SQRT_A,
        "density_target_bgs": N_TARGET_BGS,
        "desi_reference": {
            "pers1": PERS1_DESI, "beta1_max": BETA1_MAX_DESI,
            "sigma_px": SIGMA_PX,
            "note": ("Recomputed on the native DESI grid (R=5, cell 15.6 Mpc/h -> "
                     "sigma_px=0.3204), matched to the cut-sky mocks. The canonical "
                     "0.45886 (sigma_px=0.216) is NOT used here.")
        },
        "cutsky_mock_pers1": {"mean": p_mean, "std": p_std,
                              "z_desi": z_pers1, "rank_desi": rank_pers1},
        "cutsky_mock_beta1_max": {"mean": b_mean, "std": b_std,
                                  "z_desi": z_beta1, "rank_desi": rank_beta1},
        "median_ngal_selected": float(np.median(ngal_list)),
        "verdict": verdict,
        "n_floor_note": ("With N=%d the empirical p-floor is ~1/%d; z-scores are "
                         "auxiliary tail extrapolations, ranks are primary."
                         % (n_ok, n_ok + 1)),
    }
    with open(OUTPUT_JSON, "w") as f:
        json.dump(out, f, indent=2)
    print(f"\n[SAVED] {OUTPUT_JSON}")
    print("[COMPLETATO] Test 1 terminato.")


if __name__ == "__main__":
    main()
