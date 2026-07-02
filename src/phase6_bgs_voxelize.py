"""
CAUCHY — Phase 6
src/phase6_bgs_voxelize.py

Converte catalogo BGS DESI DR1 (FITS) in campo di densita 128^3 su griglia
cartesiana comovente, con correzione FKP per la geometria survey.

Design decisions (phase6_design_decisions.md):
  - D3: FKP standard dai randoms, nessun file maschera separato
  - D1: z_eff BGS ~0.2, brackettato da calibrazioni a z=0 e z=0.5
  - Cosmologia fiduciale: Planck 2018 (Omm=0.3175, h=0.6711)
  - Smoothing: R=5 Mpc/h (sigma=0.64 px su 128^3), identico Phase 0/5
  - NGRID=128, BOXSIZE determinato dal volume BGS

Colonne FITS usate (da BGS_BRIGHT-21.5 LSS catalog):
  RA, DEC, Z, WEIGHT, WEIGHT_FKP, WEIGHT_COMP

Input:
  data/raw/desi_dr1/BGS_BRIGHT-21.5_NGC_clustering.dat.fits
  data/raw/desi_dr1/BGS_BRIGHT-21.5_NGC_0_clustering.ran.fits
  data/raw/desi_dr1/BGS_BRIGHT-21.5_SGC_clustering.dat.fits
  data/raw/desi_dr1/BGS_BRIGHT-21.5_SGC_0_clustering.ran.fits

Output:
  data/processed/phase6_fields/bgs_ngc_delta_128.npy   [128,128,128] float32
  data/processed/phase6_fields/bgs_sgc_delta_128.npy
  data/processed/phase6_fields/bgs_ngc_mask_128.npy    [128,128,128] bool
  data/processed/phase6_fields/bgs_sgc_mask_128.npy
  results/phase6_voxelize_diagnostics.json

Uso:
  python src/phase6_bgs_voxelize.py [--region NGC|SGC|both] [--project_root .]
"""

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from scipy.ndimage import gaussian_filter

parser = argparse.ArgumentParser()
parser.add_argument("--region", choices=["NGC", "SGC", "both"], default="both")
parser.add_argument("--project_root", type=str, default=".")
parser.add_argument("--ngrid", type=int, default=128)
parser.add_argument("--zmin", type=float, default=0.1)
parser.add_argument("--zmax", type=float, default=0.4)
parser.add_argument("--R_smooth", type=float, default=5.0,
                    help="Smoothing in Mpc/h (default 5.0, identico Phase 5)")
args = parser.parse_args()

ROOT     = Path(args.project_root)
NGRID    = args.ngrid
DATA_DIR = ROOT / "data" / "raw" / "desi_dr1"
OUT_DIR  = ROOT / "data" / "processed" / "phase6_fields"
RES_DIR  = ROOT / "results"
OUT_DIR.mkdir(parents=True, exist_ok=True)
RES_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Cosmologia fiduciale Planck 2018 (tutto in unita h)
# ---------------------------------------------------------------------------
OMM = 0.3175
OML = 1.0 - OMM
C_OVER_H0 = 2997.92  # Mpc/h  (c / 100 km/s/Mpc)


def comoving_distance(z_arr, n_steps=500):
    """Distanza comovente in Mpc/h via integrazione numerica."""
    z_arr = np.atleast_1d(np.asarray(z_arr, dtype=np.float64))
    result = np.zeros(len(z_arr))
    for i, zi in enumerate(z_arr):
        zz = np.linspace(0.0, zi, n_steps)
        EE = np.sqrt(OMM * (1 + zz)**3 + OML)
        result[i] = C_OVER_H0 * np.trapezoid(1.0 / EE, zz)
    return result if len(result) > 1 else float(result[0])


def radec_z_to_xyz(ra_deg, dec_deg, z):
    """RA, Dec [deg] + z -> coordinate cartesiane comoventi [Mpc/h]."""
    d_C = comoving_distance(z)
    ra  = np.radians(ra_deg)
    dec = np.radians(dec_deg)
    x = d_C * np.cos(dec) * np.cos(ra)
    y = d_C * np.cos(dec) * np.sin(ra)
    z_c = d_C * np.sin(dec)
    return x, y, z_c


# ---------------------------------------------------------------------------
# CIC 3D vettorizzato (identico Phase 5)
# ---------------------------------------------------------------------------
def cic_3d(pos, weights, ngrid, box_min, box_size):
    cell  = box_size / ngrid
    xyz   = np.clip((pos - box_min[None, :]) / cell, 0.0, ngrid - 1e-6)
    ijk   = xyz.astype(np.int32)
    d     = (xyz - ijk).astype(np.float32)
    w     = weights.astype(np.float32)
    flat  = np.zeros(ngrid**3, dtype=np.float32)
    for di in range(2):
        wx = (1.0 - d[:, 0]) if di == 0 else d[:, 0]
        ii = np.clip(ijk[:, 0] + di, 0, ngrid - 1)
        for dj in range(2):
            wy = (1.0 - d[:, 1]) if dj == 0 else d[:, 1]
            jj = np.clip(ijk[:, 1] + dj, 0, ngrid - 1)
            for dk in range(2):
                wz = (1.0 - d[:, 2]) if dk == 0 else d[:, 2]
                kk = np.clip(ijk[:, 2] + dk, 0, ngrid - 1)
                idx = ii * ngrid**2 + jj * ngrid + kk
                flat += np.bincount(idx, weights=wx * wy * wz * w,
                                    minlength=ngrid**3).astype(np.float32)
    return flat.reshape(ngrid, ngrid, ngrid)


# ---------------------------------------------------------------------------
# Voxelizzazione di una regione
# ---------------------------------------------------------------------------
def voxelize_region(region):
    from astropy.io import fits

    dat_f = DATA_DIR / f"BGS_BRIGHT-21.5_{region}_clustering.dat.fits"
    ran_f = DATA_DIR / f"BGS_BRIGHT-21.5_{region}_0_clustering.ran.fits"
    assert dat_f.exists(), f"Mancante: {dat_f}"
    assert ran_f.exists(), f"Mancante: {ran_f}"

    print(f"\n{'='*60}")
    print(f"BGS {region}")
    print(f"{'='*60}")
    t0 = time.time()

    # Dati
    print(f"  Caricamento {dat_f.name}...")
    with fits.open(dat_f) as h:
        d = h['LSS'].data
        mask_z = (d['Z'] >= args.zmin) & (d['Z'] <= args.zmax)
        ra_d   = d['RA'][mask_z].astype(np.float64)
        dec_d  = d['DEC'][mask_z].astype(np.float64)
        z_d    = d['Z'][mask_z].astype(np.float64)
        w_d    = (d['WEIGHT'][mask_z] * d['WEIGHT_FKP'][mask_z]).astype(np.float64)
    print(f"  Galassie: {len(ra_d):,}")

    # Randoms
    print(f"  Caricamento {ran_f.name} ({ran_f.stat().st_size/1e6:.0f} MB)...")
    with fits.open(ran_f) as h:
        r = h['LSS'].data
        mask_z = (r['Z'] >= args.zmin) & (r['Z'] <= args.zmax)
        ra_r   = r['RA'][mask_z].astype(np.float64)
        dec_r  = r['DEC'][mask_z].astype(np.float64)
        z_r    = r['Z'][mask_z].astype(np.float64)
        w_r    = r['WEIGHT_FKP'][mask_z].astype(np.float64)
    print(f"  Randoms: {len(ra_r):,}  (ratio {len(ra_r)/len(ra_d):.0f}x)")

    alpha = np.sum(w_d) / np.sum(w_r)
    print(f"  Alpha = {alpha:.6f}")

    # Coordinate cartesiane comoventi
    print("  Conversione coordinate...")
    x_d, y_d, zc_d = radec_z_to_xyz(ra_d, dec_d, z_d)
    x_r, y_r, zc_r = radec_z_to_xyz(ra_r, dec_r, z_r)
    pos_d = np.column_stack([x_d, y_d, zc_d])
    pos_r = np.column_stack([x_r, y_r, zc_r])

    # Box cartesiano dai randoms (+ margine 5 Mpc/h)
    box_min  = pos_r.min(axis=0) - 5.0
    box_max  = pos_r.max(axis=0) + 5.0
    box_size = float((box_max - box_min).max())  # box cubico
    cell_size = box_size / NGRID

    print(f"  Box: {box_size:.1f} Mpc/h  |  cella: {cell_size:.1f} Mpc/h")
    sigma_smooth_px = args.R_smooth / cell_size
    print(f"  R_smooth = {args.R_smooth:.1f} Mpc/h -> sigma = {sigma_smooth_px:.4f} px")

    # CIC
    print("  CIC dati...")
    field_d = cic_3d(pos_d, w_d, NGRID, box_min, box_size)
    print("  CIC randoms...")
    field_r = cic_3d(pos_r, w_r, NGRID, box_min, box_size)

    # Maschera survey: celle con copertura random > 1% della media
    rand_threshold = 0.01 * field_r.mean()
    mask = field_r > rand_threshold

    # Delta FKP
    delta = np.zeros((NGRID, NGRID, NGRID), dtype=np.float32)
    denom = alpha * field_r
    valid = denom > 0
    delta[valid] = (field_d[valid] - denom[valid]) / denom[valid]
    delta[~mask] = 0.0

    print(f"  Survey fill: {100*mask.mean():.1f}%  |  "
          f"delta_std={delta[mask].std():.4f}")

    # Smoothing
    print(f"  Smoothing R={args.R_smooth:.1f} Mpc/h (sigma={sigma_smooth_px:.4f}px)...")
    delta_s = gaussian_filter(delta.astype(np.float64),
                              sigma=sigma_smooth_px).astype(np.float32)
    delta_s[~mask] = 0.0
    delta_s -= delta_s[mask].mean()  # media zero dentro la survey

    elapsed = time.time() - t0
    print(f"  Completato in {elapsed:.0f}s")

    # Diagnostica n(z)
    bins = np.linspace(args.zmin, args.zmax, 31)
    nz_d, _ = np.histogram(z_d, bins=bins, weights=w_d)
    nz_r, _ = np.histogram(z_r, bins=bins, weights=w_r * alpha)
    nz_ratio = np.where(nz_r > 0, nz_d / nz_r, 0.0)

    # Salva
    np.save(OUT_DIR / f"bgs_{region.lower()}_delta_128.npy", delta_s)
    np.save(OUT_DIR / f"bgs_{region.lower()}_mask_128.npy",  mask)
    print(f"  -> bgs_{region.lower()}_delta_128.npy")
    print(f"  -> bgs_{region.lower()}_mask_128.npy")

    return {
        "region": region,
        "N_data": int(len(ra_d)),
        "N_rand": int(len(ra_r)),
        "alpha": float(alpha),
        "box_size_mpc_h": float(box_size),
        "cell_size_mpc_h": float(cell_size),
        "box_min": box_min.tolist(),
        "n_valid_voxels": int(mask.sum()),
        "survey_fill_fraction": float(mask.mean()),
        "delta_std_in_survey": float(delta_s[mask].std()),
        "nz_ratio_mean": float(nz_ratio.mean()),
        "nz_ratio_std":  float(nz_ratio.std()),
        "R_smooth_mpc_h": float(args.R_smooth),
        "sigma_smooth_px": float(sigma_smooth_px),
        "elapsed_s": float(elapsed),
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
print("=" * 70)
print("CAUCHY Phase 6 — BGS Voxelization")
print(f"NGRID={NGRID}, z=[{args.zmin},{args.zmax}], R_smooth={args.R_smooth} Mpc/h")
print(f"Cosmologia: Planck2018 Omm={OMM}")
print("=" * 70)

D_MIN = comoving_distance(args.zmin)
D_MAX = comoving_distance(args.zmax)
print(f"d_C(z={args.zmin}) = {D_MIN:.1f} Mpc/h")
print(f"d_C(z={args.zmax}) = {D_MAX:.1f} Mpc/h")

diagnostics = {
    "schema_version": "2.0",
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "ngrid": NGRID,
    "zmin": args.zmin,
    "zmax": args.zmax,
    "R_smooth_mpc_h": args.R_smooth,
    "sigma_smooth_note": "sigma_px = R_smooth / cell_size, calcolato per regione",
    "d_C_zmin_mpc_h": float(D_MIN),
    "d_C_zmax_mpc_h": float(D_MAX),
    "cosmology": {"Omm": OMM, "OmL": OML, "units": "h=1"},
    "regions": {}
}

regions = ["NGC", "SGC"] if args.region == "both" else [args.region]
for region in regions:
    diagnostics["regions"][region] = voxelize_region(region)

with open(RES_DIR / "phase6_voxelize_diagnostics.json", "w") as f:
    json.dump(diagnostics, f, indent=2)

print(f"\n{'='*70}")
print("RIEPILOGO")
print(f"{'='*70}")
for region, info in diagnostics["regions"].items():
    print(f"\n  {region}: {info['N_data']:,} gal | "
          f"fill={100*info['survey_fill_fraction']:.1f}% | "
          f"box={info['box_size_mpc_h']:.0f} Mpc/h | "
          f"delta_std={info['delta_std_in_survey']:.4f}")

print(f"\n  Output: {OUT_DIR}")
print(f"  Diagnostiche: {RES_DIR}/phase6_voxelize_diagnostics.json")
print(f"\nProssimo: python src/phase6_bgs_tda.py")
print(f"{'='*70}")
