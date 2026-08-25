"""
CAUCHY — MN-26-2100-P revision, referee point R1.1
src/rev1_r11_tiling.py

"Tiling doesn't provide new information and artificially deflates the variance.
Could part of the 20% deficit simply be explained by a wider true cosmic
variance?"

Two measurements, neither of which runs a filtration, so this takes seconds.

  (A) How much information does the tiling actually repeat?
      Every in-survey voxel centre maps back to a cell of the periodic box
      through x mod L_box. Counting how many in-survey voxels share a box cell
      turns "tiling doesn't provide new information" into a number: the fraction
      of the survey volume that corresponds to distinct simulation volume.

  (B) How much wider would the distribution have to be?
      The deficit is an offset between one observation and the ensemble mean; a
      wider variance widens the distribution without moving its centre, so it
      can only make the observation a plausible draw, not create the offset.
      That is a quantitative question, and the ensemble scatter is already
      decomposed in Section 5.5 into cosmology, HOD/downsampling and
      realisation terms. Tiling can deflate the realisation term only. We
      therefore ask how large the realisation term would have to be, with the
      other two held at their measured values, for the observation to sit at
      3 sigma and at 2 sigma.

All inputs are read from the frozen records or from the pipeline module; none
are typed in here except the three variance shares of Section 5.5, which are
passed as arguments so they are visible in the output.

  python src\\rev1_r11_tiling.py

Output: results/revision/rev1_r11_tiling.json
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path.cwd()
SRC = ROOT / "src"
OUT_DIR = ROOT / "results" / "revision"

parser = argparse.ArgumentParser()
parser.add_argument("--frozen", type=str,
                    default="results/phase9_ngc_clean_beta1.npz")
parser.add_argument("--frozen_key", type=str, default="beta1_max")
# Variance decomposition of Section 5.5 (fractions of the total variance).
parser.add_argument("--share_cosmology", type=float, default=0.698)
parser.add_argument("--share_hod", type=float, default=0.168)
parser.add_argument("--share_realisation", type=float, default=0.134)
ARGS = parser.parse_args()

OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))
import phase8_cutsky_mocks as P8  # noqa: E402

print("=" * 72)
print("R1.1 — TILING: DUPLICAZIONE E BOUND SULLA VARIANZA")
print("=" * 72)

# --------------------------------------------------------------------------
# (A) Geometry of the tiling
# --------------------------------------------------------------------------
print("\n[A] Quanta struttura ripete il tiling")
mask = np.load(P8.DESI_MASK_FILE)
n_in = int(mask.sum())
L_box = float(P8.BOXSIZE_MOCK)
cell = float(P8.CELL)
box_min = np.asarray(P8.BOX_MIN, dtype=float)
print(f"    box periodico {L_box:.1f} h^-1 Mpc, cubo {P8.BOX_SIZE:.1f}, "
      f"cella {cell:.4f}")
print(f"    voxel in-survey: {n_in:,}")

idx = np.argwhere(mask)                       # (n_in, 3) integer voxel indices
centres = box_min[None, :] + (idx + 0.5) * cell
pos_box = np.mod(centres, L_box)              # back to the periodic box

# Bin the box at the closest integer number of survey cells, so that one bin is
# one resolution element of the analysis grid.
nb = int(round(L_box / cell))
bw = L_box / nb
j = np.floor(pos_box / bw).astype(np.int64)
np.clip(j, 0, nb - 1, out=j)
flat = (j[:, 0] * nb + j[:, 1]) * nb + j[:, 2]

uniq, counts = np.unique(flat, return_counts=True)
n_cells_box = nb ** 3
n_distinct = int(uniq.size)
frac_distinct = n_distinct / n_in
mult = counts[np.searchsorted(uniq, flat)]    # multiplicity of each voxel's cell
frac_voxels_duplicated = float((mult > 1).mean())
hist = {int(k): int((counts == k).sum()) for k in np.unique(counts)}
vox_by_mult = {int(k): int((mult == k).sum()) for k in np.unique(counts)}

print(f"    griglia del box: {nb}^3 = {n_cells_box:,} celle di {bw:.4f} h^-1 Mpc")
print(f"    celle del box effettivamente usate: {n_distinct:,} "
      f"({100*n_distinct/n_cells_box:.1f}% del box)")
print(f"    volume indipendente / volume del survey = {frac_distinct:.4f}")
print(f"    voxel in-survey su celle usate piu' di una volta: "
      f"{100*frac_voxels_duplicated:.1f}%")
print(f"    molteplicita' media delle celle usate: {counts.mean():.3f} "
      f"(massima {counts.max()})")
print("    ripartizione dei voxel per molteplicita' della loro cella:")
for k in sorted(vox_by_mult):
    print(f"      x{k}: {vox_by_mult[k]:,} voxel "
          f"({100*vox_by_mult[k]/n_in:.1f}%)")

# --------------------------------------------------------------------------
# (B) How wide would the distribution have to be?
# --------------------------------------------------------------------------
print("\n[B] Quanto dovrebbe allargarsi la distribuzione")
fz = np.load(ARGS.frozen)
arr = np.asarray(fz[ARGS.frozen_key], dtype=float)
desi = float(fz["desi_beta1max"])
mean, sd = float(arr.mean()), float(arr.std(ddof=1))
deficit = mean - desi
n_below = int((arr < desi).sum())
gap_to_min = float(arr.min() - desi)
print(f"    ensemble N={arr.size}: media {mean:.3f}, sigma {sd:.1f}, "
      f"minimo {arr.min():.0f}")
print(f"    DESI {desi:.0f}: deficit {deficit:.1f} ({100*deficit/mean:.1f}%), "
      f"z = {-deficit/sd:.2f}")
print(f"    mock sotto il dato: {n_below}; il minimo sta {gap_to_min:.0f} "
      f"generatori sopra")

shares = {"cosmology": ARGS.share_cosmology, "hod": ARGS.share_hod,
          "realisation": ARGS.share_realisation}
tot_share = sum(shares.values())
sig = {k: sd * np.sqrt(v) for k, v in shares.items()}
print(f"    quote di varianza (Sez. 5.5): {shares}, somma {tot_share:.3f}")
for k, v in sig.items():
    print(f"      sigma_{k:12s} = {v:7.1f}")

bounds = {}
for nsig in (3.0, 2.0):
    sd_need = deficit / nsig
    fixed_var = sig["cosmology"] ** 2 + sig["hod"] ** 2
    need_var = sd_need ** 2 - fixed_var
    if need_var <= 0:
        bounds[f"{nsig:g}sigma"] = {"sigma_total_required": sd_need,
                                    "feasible_without_growth": True}
        continue
    sr = float(np.sqrt(need_var))
    bounds[f"{nsig:g}sigma"] = {
        "sigma_total_required": sd_need,
        "sigma_total_growth_factor": sd_need / sd,
        "sigma_realisation_required": sr,
        "sigma_realisation_growth_factor": sr / sig["realisation"],
        "variance_realisation_growth_factor": (sr / sig["realisation"]) ** 2}
    print(f"    per portare il dato a {nsig:g} sigma: sigma totale "
          f"{sd_need:.0f} (x{sd_need/sd:.2f}); tenendo fisse cosmologia e HOD, "
          f"il termine di realizzazione dovrebbe passare da "
          f"{sig['realisation']:.1f} a {sr:.0f} (x{sr/sig['realisation']:.1f}, "
          f"cioe' x{(sr/sig['realisation'])**2:.0f} in varianza)")

# --------------------------------------------------------------------------
# (C) Putting the two together: the tiling correction actually implied
# --------------------------------------------------------------------------
print("\n[C] Correzione implicata dalla duplicazione misurata")
# First-order argument: the realisation variance of a count statistic scales
# inversely with the independent volume. The tiling reduces the independent
# volume by the factor measured in (A), so it deflates the realisation variance
# by that same factor and no more.
infl_var = 1.0 / frac_distinct
sig_real_corr = sig["realisation"] * np.sqrt(infl_var)
sd_corr = float(np.sqrt(sig["cosmology"] ** 2 + sig["hod"] ** 2
                        + sig_real_corr ** 2))
print(f"    varianza di realizzazione deflazionata di x{infl_var:.3f}")
print(f"    sigma_realisation {sig['realisation']:.1f} -> {sig_real_corr:.1f}")
print(f"    sigma totale {sd:.1f} -> {sd_corr:.1f} (x{sd_corr/sd:.3f})")
print(f"    z {-deficit/sd:.2f} -> {-deficit/sd_corr:.2f}")
print(f"    da confrontare con il x{bounds['3sigma']['variance_realisation_growth_factor']:.0f} "
      f"in varianza che servirebbe per arrivare a 3 sigma")

out = {
    "tiling_correction": {
        "assumption": "realisation variance inversely proportional to the "
                      "independent volume; does not account for modes larger "
                      "than the periodic box, which are absent rather than "
                      "duplicated",
        "variance_inflation_factor": float(infl_var),
        "sigma_realisation_corrected": float(sig_real_corr),
        "sigma_total_corrected": sd_corr,
        "sigma_total_growth_factor": sd_corr / sd,
        "z_corrected": -deficit / sd_corr},
    "tiling_geometry": {
        "box_size_mock": L_box, "cube_size": float(P8.BOX_SIZE), "cell": cell,
        "n_voxels_in_survey": n_in,
        "box_grid_n": nb, "box_bin_width": bw,
        "n_box_cells_total": n_cells_box, "n_box_cells_used": n_distinct,
        "frac_box_covered": n_distinct / n_cells_box,
        "independent_volume_fraction": frac_distinct,
        "frac_voxels_on_reused_cells": frac_voxels_duplicated,
        "mean_multiplicity_of_used_cells": float(counts.mean()),
        "max_multiplicity": int(counts.max()),
        "cells_by_multiplicity": hist,
        "voxels_by_multiplicity": vox_by_mult},
    "ensemble": {"n": int(arr.size), "mean": mean, "std": sd,
                 "min": float(arr.min()), "desi": desi, "deficit": deficit,
                 "deficit_fraction": deficit / mean, "z": -deficit / sd,
                 "n_mocks_below_desi": n_below,
                 "gap_min_to_desi": gap_to_min},
    "variance_shares_section_5_5": shares,
    "sigma_components": {k: float(v) for k, v in sig.items()},
    "width_required": bounds,
    "timestamp": datetime.now(timezone.utc).isoformat(),
    "script": "src/rev1_r11_tiling.py"}
p = OUT_DIR / "rev1_r11_tiling.json"
p.write_text(json.dumps(out, indent=2), encoding="utf-8")
print(f"\n[OUT] {p}")
