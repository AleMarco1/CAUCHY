"""
CAUCHY — MN-26-2100-P revision, referee point R1.1 (pilot)
src/rev1_r11_pilot.py

"Tiling doesn't provide new information and artificially deflates the variance."

rev1_r11_tiling.py measures how much volume the tiling repeats. This pilot
measures the consequence: it regenerates mocks with every box replica mapped
through a random signed permutation of the axes before tiling -- which
decorrelates the replicas from one another -- and compares the
realisation-to-realisation scatter of beta1_max against the standard tiling on
the SAME cosmologies, the SAME HOD realisation and the SAME downsampling
stream. The only difference between the two arms is the orientation of the
replicas.

A signed permutation sends the cubic periodic box to itself, so it is an exact
symmetry of the simulation: the field is the same field, only its replicas no
longer repeat one another. Velocities are transformed by the same matrix.

WHAT IS COPIED, AND THE GATE THAT MAKES IT SAFE
  carve_cutsky_rot below is P8.carve_cutsky copied verbatim with exactly one
  block added (marked in the body). Copying pipeline code is the main risk in
  this script, so it opens with a NULL GATE: with randomise=False the copy must
  return an array bit-identical to P8.carve_cutsky started from the same
  generator state. The permutations are drawn from a separate generator, so
  with randomise=False nothing at all is consumed from `rng` and the two calls
  see identical random streams. If the gate fails the script stops and writes
  nothing.

WHAT THIS DOES NOT MEASURE
  Modes larger than the 1000 h^-1 Mpc periodic box are absent from the mocks,
  not duplicated. Randomising the replicas cannot restore them. The pilot
  bounds the repetition term only, and the paper says so.

  python src\\rev1_r11_pilot.py --n_mocks 100

Output: results/revision/rev1_r11_pilot.json
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

ROOT = Path.cwd()
SRC = ROOT / "src"
OUT_DIR = ROOT / "results" / "revision"

parser = argparse.ArgumentParser()
parser.add_argument("--n_mocks", type=int, default=100)
parser.add_argument("--snapnum", type=int, default=3)
parser.add_argument("--seed", type=int, default=0,
                    help="Base seed of the mock loop, following the convention "
                         "rng = default_rng(seed + i) of the production runs.")
parser.add_argument("--rot_seed", type=int, default=20260822,
                    help="Base seed of the SEPARATE generator that draws the "
                         "replica orientations.")
parser.add_argument("--frozen", type=str,
                    default="results/phase9_ngc_clean_beta1.npz")
parser.add_argument("--frozen_key", type=str, default="beta1_max")
parser.add_argument("--skip_gate", action="store_true",
                    help="Diagnostic only. Never for a number that enters the paper.")
ARGS = parser.parse_args()

OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))
import phase8_cutsky_mocks as P8      # noqa: E402
import phase8_test2_masked as T2      # noqa: E402  (populate_with_virial)

_IDENTITY = np.eye(3)
_PERMS = [(0, 1, 2), (0, 2, 1), (1, 0, 2), (1, 2, 0), (2, 0, 1), (2, 1, 0)]


def _signed_permutation(rng):
    """One of the 48 elements of the cube's symmetry group, drawn uniformly."""
    perm = _PERMS[rng.integers(len(_PERMS))]
    signs = rng.integers(0, 2, size=3) * 2 - 1
    S = np.zeros((3, 3))
    for i, j in enumerate(perm):
        S[i, j] = signs[i]
    return S


def _rng_at(state):
    r = np.random.default_rng()
    r.bit_generator.state = state
    return r


def carve_cutsky_rot(pos_gal, vel_gal, mask, nz_z, nz_target, rng,
                     randomise=False, rot_rng=None):
    """Map periodic-box galaxies into the DESI embedding cube, apply RSD, carve
    by mask + z range, downsample to BGS n(z). Returns selected embedding-frame
    Cartesian positions [M,3] (redshift-space)."""
    # Tile offsets covering the embedding cube along each axis
    def offsets(axis):
        lo, hi = P8.BOX_MIN[axis], P8.BOX_MIN[axis] + P8.BOX_SIZE
        k_lo = int(np.floor(lo / P8.BOXSIZE_MOCK))
        k_hi = int(np.floor(hi / P8.BOXSIZE_MOCK))
        return list(range(k_lo, k_hi + 1))
    ox, oy, oz = offsets(0), offsets(1), offsets(2)

    # Pass 1: collect ALL in-survey candidates (mask + z range), no downsampling.
    cand_P, cand_z = [], []
    for kx in ox:
        for ky in oy:
            for kz in oz:
                # --- the only modification w.r.t. P8.carve_cutsky ---------
                # Each replica is mapped through a random signed permutation of
                # the axes before being shifted. A signed permutation sends the
                # cubic periodic box to itself, so it is an exact symmetry of
                # the simulation and leaves the field statistics unchanged; the
                # velocities are transformed by the same matrix so that the
                # redshift-space treatment stays consistent. The permutations
                # are drawn from a SEPARATE generator, so with randomise=False
                # not a single value is consumed from `rng` and this block is a
                # no-op -- which is what the null gate checks.
                S = _signed_permutation(rot_rng) if randomise else _IDENTITY
                pos_rep = np.mod(pos_gal @ S.T, P8.BOXSIZE_MOCK)
                vel_rep = vel_gal @ S.T
                # ----------------------------------------------------------
                shift = np.array([kx, ky, kz]) * P8.BOXSIZE_MOCK
                P = pos_rep + shift[None, :]
                inb = np.all((P >= P8.BOX_MIN[None, :]) &
                             (P < (P8.BOX_MIN + P8.BOX_SIZE)[None, :]), axis=1)
                if not inb.any():
                    continue
                P = P[inb]
                V = vel_rep[inb]
                # Real-space distance & LOS
                dC = np.linalg.norm(P, axis=1)
                good = (dC > 1e-6) & (dC >= P8.D_C_ZMIN - 50) & (dC <= P8.D_C_ZMAX + 50)
                if not good.any():
                    continue
                P, V, dC = P[good], V[good], dC[good]
                rhat = P / dC[:, None]
                z_cosmo = P8.z_of_dc(dC)
                v_los = np.sum(V * rhat, axis=1)                 # km/s
                z_obs = z_cosmo + (1.0 + z_cosmo) * v_los / P8.C_KMS
                dC_rsd = np.interp(np.clip(z_obs, 0.0, 0.6), P8._Z_TAB, P8._DC_TAB)
                P_rsd = rhat * dC_rsd[:, None]
                zsel = (z_obs >= P8.ZMIN) & (z_obs <= P8.ZMAX)
                if not zsel.any():
                    continue
                P_rsd, z_obs_s = P_rsd[zsel], z_obs[zsel]
                ijk = np.clip(((P_rsd - P8.BOX_MIN[None, :]) / P8.CELL).astype(np.int32),
                              0, P8.NGRID - 1)
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
    desired = shape / shape.sum() * float(P8.N_TARGET_BGS)
    with np.errstate(divide='ignore', invalid='ignore'):
        p_bin = np.where(n_cand_bin > 0, desired / n_cand_bin, 0.0)
    p_bin = np.minimum(p_bin, 1.0)
    p = p_bin[which]
    keep = rng.random(len(z_cand)) < p
    return P_cand[keep]


# ---------------------------------------------------------------------------
def beta1(pos_sel, field_r, sum_wr, mask):
    if pos_sel is None or len(pos_sel) < 100:
        return None
    nu = P8.voxelize_mock(pos_sel, field_r, sum_wr, mask)
    if nu is None:
        return None
    return int(P8.compute_tda_features(nu, mask, P8.N_THRESH, masked=True)[4])


def populate(pos_h, mass_h, vel_h, rng):
    """The final masked pipeline populates satellites WITH the virial
    dispersion (T2.populate_with_virial), not with the bulk-velocity-only
    option of P8.populate_halos_hod_with_vel. Using the wrong one here would
    silently break the like-for-like with the frozen ensemble."""
    return T2.populate_with_virial(pos_h, mass_h, vel_h, P8.HOD_MEDIAN, rng)


def main():
    print("=" * 72)
    print("R1.1 — PILOTA: REPLICHE RANDOMIZZATE CONTRO TILING STANDARD")
    print("=" * 72)
    mask = np.load(P8.DESI_MASK_FILE)
    field_r, sum_wr = P8.load_desi_random_field()
    nz_z, nz_target = P8.load_bgs_nz()
    print(f"    HOD baseline (P8.HOD_MEDIAN): {list(P8.HOD_MEDIAN)}")
    print(f"    popolazione satelliti: T2.populate_with_virial")

    frozen = None
    try:
        fz = np.load(ARGS.frozen)
        frozen = np.asarray(fz[ARGS.frozen_key], dtype=float)
        print(f"    ensemble congelato: {ARGS.frozen} "
              f"(N={frozen.size}, media {frozen.mean():.1f})")
    except Exception as e:  # noqa: BLE001
        print(f"    [nota] ensemble congelato non leggibile ({e}); "
              f"il confronto per indice sara' saltato")

    # ---------------- null gate ----------------
    print("\n[1/2] Null gate sulla copia di carve_cutsky...")
    rng = np.random.default_rng(ARGS.seed)
    pos_h, mass_h, vel_h = P8.read_halo_catalog(0, ARGS.snapnum)
    if pos_h is None:
        sys.exit("[ERRORE] catalogo aloni 0 non leggibile.")
    pg, vg = populate(pos_h, mass_h, vel_h, rng)
    state = rng.bit_generator.state
    a = P8.carve_cutsky(pg, vg, mask, nz_z, nz_target, _rng_at(state))
    b = carve_cutsky_rot(pg, vg, mask, nz_z, nz_target, _rng_at(state),
                         randomise=False)
    same = (a.shape == b.shape) and bool(np.array_equal(a, b))
    print(f"      copia == originale: {same}   "
          f"({a.shape[0]} vs {b.shape[0]} galassie selezionate)")
    if not same and not ARGS.skip_gate:
        sys.exit("[STOP] la copia non riproduce P8.carve_cutsky. "
                 "Non usare nulla di questo run.")

    # ---------------- pilot ----------------
    print(f"\n[2/2] {ARGS.n_mocks} mock, due carving ciascuno...")
    std, rot, idx_ok, frz = [], [], [], []
    t0 = time.time()
    for i in range(ARGS.n_mocks):
        rng = np.random.default_rng(ARGS.seed + i)
        pos_h, mass_h, vel_h = P8.read_halo_catalog(i, ARGS.snapnum)
        if pos_h is None or len(pos_h) < 50:
            print(f"      [{i+1}] catalogo assente o troppo piccolo, saltato")
            continue
        pg, vg = populate(pos_h, mass_h, vel_h, rng)
        if len(pg) < 100:
            print(f"      [{i+1}] popolazione vuota, saltato")
            continue
        state = rng.bit_generator.state
        a = beta1(carve_cutsky_rot(pg, vg, mask, nz_z, nz_target,
                                   _rng_at(state), randomise=False),
                  field_r, sum_wr, mask)
        b = beta1(carve_cutsky_rot(pg, vg, mask, nz_z, nz_target,
                                   _rng_at(state), randomise=True,
                                   rot_rng=np.random.default_rng(ARGS.rot_seed + i)),
                  field_r, sum_wr, mask)
        if a is None or b is None:
            print(f"      [{i+1}] campo vuoto, saltato")
            continue
        std.append(a); rot.append(b); idx_ok.append(i)
        f = float(frozen[i]) if (frozen is not None and i < frozen.size) else float("nan")
        frz.append(f)
        el = time.time() - t0
        print(f"      [{i+1}/{ARGS.n_mocks}] sim {i}: standard {a}  "
              f"randomizzato {b}  (congelato {f:.0f})  ({el/len(std):.0f}s/mock)")

    std = np.array(std, float); rot = np.array(rot, float); frz = np.array(frz, float)
    n = len(std)
    if n < 10:
        sys.exit(f"[STOP] solo {n} mock riusciti: troppo pochi per uno scatter.")

    s_std, s_rot = float(std.std(ddof=1)), float(rot.std(ddof=1))
    ratio = s_rot / s_std
    r = np.random.default_rng(12345)
    boot = [rot[k].std(ddof=1) / std[k].std(ddof=1)
            for k in (r.integers(0, n, n) for _ in range(5000))]
    lo, hi = np.percentile(boot, [2.5, 97.5])
    n_match = int(np.sum(std == frz)) if np.isfinite(frz).any() else 0

    print("\n" + "-" * 72)
    print(f"    N = {n}")
    print(f"    standard      media {std.mean():9.1f}  sigma {s_std:7.1f}")
    print(f"    randomizzato  media {rot.mean():9.1f}  sigma {s_rot:7.1f}")
    print(f"    sigma_rand / sigma_std = {ratio:.3f}  [95% {lo:.3f}, {hi:.3f}]")
    print(f"    atteso se var ~ 1/V_indip: sqrt(1.437) = 1.199")
    print(f"    spostamento della media: {rot.mean()-std.mean():+.1f} generatori")
    print(f"    mock in cui il braccio standard riproduce l'ensemble "
          f"congelato: {n_match}/{n}")
    if n_match == 0:
        print("      (atteso se --seed non e' quello del run di produzione; "
              "il confronto appaiato resta valido)")

    out = {"n_mocks_used": n, "sim_indices": idx_ok, "snapnum": ARGS.snapnum,
           "seed": ARGS.seed, "rot_seed": ARGS.rot_seed,
           "hod_baseline": [float(x) for x in P8.HOD_MEDIAN],
           "satellite_population": "T2.populate_with_virial",
           "null_gate_passed": bool(same),
           "standard": {"beta1_max": std.tolist(), "mean": float(std.mean()),
                        "std": s_std},
           "randomised": {"beta1_max": rot.tolist(), "mean": float(rot.mean()),
                          "std": s_rot},
           "frozen_reference": frz.tolist(),
           "n_standard_matching_frozen": n_match,
           "sigma_ratio": ratio, "sigma_ratio_ci95": [float(lo), float(hi)],
           "mean_shift": float(rot.mean() - std.mean()),
           "geometric_expectation_if_var_scales_as_inverse_volume": 1.199,
           "caveat": "bounds the repetition term only; modes larger than the "
                     "periodic box are absent, not duplicated",
           "timestamp": datetime.now(timezone.utc).isoformat(),
           "script": "src/rev1_r11_pilot.py"}
    p = OUT_DIR / "rev1_r11_pilot.json"
    p.write_text(json.dumps(out, indent=2), encoding="utf-8")
    print(f"\n[OUT] {p}")


if __name__ == "__main__":
    if not SRC.exists():
        sys.exit(f"[ERRORE] Lancia dalla root del progetto. Cwd: {ROOT}")
    main()
