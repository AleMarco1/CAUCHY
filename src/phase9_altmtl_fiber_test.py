#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 3
src/phase9_altmtl_fiber_test.py

Isolated-referee Concern 4 (the heaviest): the Phase 8 incompleteness surrogate
was density-dependent on the LOCAL 3D voxel density and gave the wrong sign. Real
DESI fiber assignment removes targets in ANGULARLY crowded regions (fiber-collision
groups within ~62"), tracking PROJECTED angular density, not 3D local density.
altmtl (the official DESI fiber-assignment realizations) is the gold standard and
is not available here; this is the physically-motivated angular surrogate.

Test design (isolates the fiber PATTERN from the pure count loss):
  For each of K regenerated mocks (same Test 2 virial-velocity populate + cut-sky):
    baseline beta1_max                    (no decimation)
    fiber-decimated beta1_max             (remove preferentially in angular density,
                                           62" collision radius, target fraction f)
    random-decimated beta1_max (x R reps) (remove the SAME count uniformly at random)
  Fiber assignment can explain DESI's deficit ONLY IF fiber decimation drives
  beta1_max toward DESI (28256) BEYOND the random-count-loss null.

Verdict FIBER_EXCLUDED if, across mocks, the mean fiber-driven drop does NOT exceed
the random-null drop by a margin that would reach DESI (i.e. fiber is not the cause).

Consumes nothing frozen except the DESI reference (phase8_test2_masked.json) and the
frozen baseline mean for a sanity check. Regenerates fields on the fly.

Run a pilot first, then scale:
  python src\\phase9_altmtl_fiber_test.py --project_root D:\\projects\\cauchy --k 3
  python src\\phase9_altmtl_fiber_test.py --project_root D:\\projects\\cauchy --k 20
"""

import argparse
import datetime
import json
import sys
import time
from pathlib import Path
import numpy as np

FIBER_ARCSEC = 62.0          # DESI fiber-collision radius
F_TARGETS = [0.05, 0.10, 0.20]   # target overall removal fractions to scan
N_RANDOM_REPS = 3
FROZEN_BASELINE_MEAN = 35424.8   # from phase9 extraction (sanity check)
FROZEN_BASELINE_STD = 444.8


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def angular_neighbor_counts(pos, chord_r):
    """Neighbors within angular chord radius on the unit sphere, per galaxy."""
    from scipy.spatial import cKDTree
    norm = np.linalg.norm(pos, axis=1, keepdims=True)
    norm[norm == 0] = 1.0
    unit = pos / norm
    tree = cKDTree(unit)
    # return_length gives count within radius (includes self -> subtract 1)
    counts = tree.query_ball_point(unit, r=chord_r, return_length=True) - 1
    return np.asarray(counts, float)


def fiber_decimate(pos, f_target, chord_r, rng):
    """Remove galaxies with probability proportional to local angular density,
    scaled so the expected overall removal fraction ~ f_target."""
    counts = angular_neighbor_counts(pos, chord_r)
    mean_c = counts.mean()
    if mean_c <= 0:
        # no collisions at all -> fall back to uniform f_target
        keep = rng.random(len(pos)) >= f_target
        return pos[keep], int((~keep).sum())
    p_rem = np.clip(f_target * counts / mean_c, 0.0, 1.0)
    keep = rng.random(len(pos)) >= p_rem
    return pos[keep], int((~keep).sum())


def random_decimate(pos, n_remove, rng):
    if n_remove <= 0:
        return pos
    idx = rng.choice(len(pos), size=len(pos) - n_remove, replace=False)
    return pos[idx]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=20, help="number of mocks to regenerate")
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
    chord_r = 2.0 * np.sin(np.radians(FIBER_ARCSEC / 3600.0) / 2.0)

    with open(res_dir / "phase8_test2_masked.json") as f:
        desi_b = float(json.load(f)["desi_reference_masked"]["beta1_max"])

    print("=" * 70)
    print(f"CAUCHY Phase 9 - Script 3: angular fiber surrogate (K={args.k})")
    print("=" * 70)
    print(f"  DESI beta1_max (masked) = {desi_b:.0f}")
    print(f"  fiber collision radius  = {FIBER_ARCSEC}\"  (chord {chord_r:.3e})")
    print(f"  f_target scan = {F_TARGETS}, random reps = {N_RANDOM_REPS}")

    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN

    def beta1_of(pos_sel):
        nu = M.voxelize_mock(pos_sel, field_r, sum_wr, mask)
        if nu is None:
            return None
        feats = M.compute_tda_features(nu, mask, n_thresh, masked=True)
        return float(feats[4])

    rows = []
    base_list = []
    t0 = time.time()
    for k in range(args.k):
        rng = np.random.default_rng(args.seed + k)
        pos_h, mass_h, vel_h = M.read_halo_catalog(k, args.snapnum)
        if pos_h is None or len(pos_h) < 50:
            continue
        pos_gal, vel_gal = T2.populate_with_virial(pos_h, mass_h, vel_h, hod, rng)
        if len(pos_gal) < 100:
            continue
        pos_sel = M.carve_cutsky(pos_gal, vel_gal, mask, nz_z, nz_target, rng)
        if pos_sel is None or len(pos_sel) < 100:
            continue
        M_sel = len(pos_sel)
        b_base = beta1_of(pos_sel)
        if b_base is None:
            continue
        base_list.append(b_base)

        row = {"mock": k, "n_sel": M_sel, "beta1_base": b_base,
               "fiber": {}, "random": {}}
        for f in F_TARGETS:
            pos_fib, n_rem = fiber_decimate(pos_sel, f, chord_r, rng)
            b_fib = beta1_of(pos_fib)
            # random null: same count removed, R reps
            b_rand = []
            for r in range(N_RANDOM_REPS):
                pos_rnd = random_decimate(pos_sel, n_rem, rng)
                br = beta1_of(pos_rnd)
                if br is not None:
                    b_rand.append(br)
            row["fiber"][f"{f:.2f}"] = {"n_removed": n_rem, "beta1": b_fib}
            row["random"][f"{f:.2f}"] = {"beta1_mean": float(np.mean(b_rand)),
                                         "beta1_std": float(np.std(b_rand))}
        rows.append(row)
        eta = (time.time() - t0) / len(rows) * (args.k - len(rows)) / 60
        print(f"  [mock {k}] N={M_sel} base={b_base:.0f} "
              + " ".join(f"f{f}:fib={row['fiber'][f'{f:.2f}']['beta1']:.0f}/"
                         f"rnd={row['random'][f'{f:.2f}']['beta1_mean']:.0f}"
                         for f in F_TARGETS)
              + f"  ETA={eta:.1f}min")

    if not rows:
        sys.exit("[FATAL] no valid mocks.")

    # sanity: baseline mean vs frozen
    base_mean = float(np.mean(base_list))
    drift = abs(base_mean - FROZEN_BASELINE_MEAN) / FROZEN_BASELINE_STD
    print(f"\n  baseline mean beta1_max = {base_mean:.0f} "
          f"(frozen {FROZEN_BASELINE_MEAN:.0f}; drift {drift:.2f} sigma) "
          f"{'[ok]' if drift < 1.0 else '[WARN]'}")

    # aggregate per f_target: mean fiber drop vs mean random drop, and gap to DESI
    print("\n  per-f_target aggregate (drop = base - decimated):")
    agg = {}
    for f in F_TARGETS:
        fk = f"{f:.2f}"
        d_fib = np.array([r["beta1_base"] - r["fiber"][fk]["beta1"] for r in rows])
        d_rnd = np.array([r["beta1_base"] - r["random"][fk]["beta1_mean"] for r in rows])
        fib_beta = np.array([r["fiber"][fk]["beta1"] for r in rows])
        # fiber-specific extra drop beyond random count loss
        extra = d_fib - d_rnd
        # how far the fiber-decimated mocks still sit above DESI
        gap_to_desi = float(np.mean(fib_beta) - desi_b)
        agg[fk] = {
            "fiber_drop_mean": float(d_fib.mean()),
            "random_drop_mean": float(d_rnd.mean()),
            "fiber_extra_drop_mean": float(extra.mean()),
            "fiber_extra_drop_sem": float(extra.std(ddof=1) / np.sqrt(len(extra))) if len(extra) > 1 else 0.0,
            "fiber_beta1_mean": float(fib_beta.mean()),
            "gap_to_desi": gap_to_desi,
        }
        print(f"    f={f:.2f}: fiber_drop={d_fib.mean():6.0f}  random_drop={d_rnd.mean():6.0f}  "
              f"extra={extra.mean():+6.0f}+/-{agg[fk]['fiber_extra_drop_sem']:.0f}  "
              f"fiber_beta1={fib_beta.mean():.0f} (still {gap_to_desi:+.0f} vs DESI)")

    # verdict: fiber explains deficit only if at some f the fiber-decimated beta1
    # reaches DESI AND the extra drop (beyond random) is what gets it there.
    reaches = any(agg[f"{f:.2f}"]["gap_to_desi"] <= 0 for f in F_TARGETS)
    extra_significant = any(
        agg[f"{f:.2f}"]["fiber_extra_drop_mean"] > 2 * agg[f"{f:.2f}"]["fiber_extra_drop_sem"]
        and agg[f"{f:.2f}"]["fiber_extra_drop_mean"] > 0
        for f in F_TARGETS)
    if reaches and extra_significant:
        verdict = "FIBER_CANDIDATE"  # concern stands; fiber can plausibly drive the deficit
    else:
        verdict = "FIBER_EXCLUDED"   # fiber incompleteness cannot explain the deficit
    print(f"\n  >>> VERDICT: {verdict}")
    print(f"      (reaches DESI at some f: {reaches}; fiber-specific extra drop "
          f"significant: {extra_significant})")

    out = {
        "schema_version": "2.0",
        "script": "phase9_altmtl_fiber_test.py",
        "phase": "9",
        "concern_addressed": "isolated-referee Concern 4 (fiber assignment, angular surrogate)",
        "timestamp": _now_iso(),
        "k_mocks": len(rows),
        "fiber_arcsec": FIBER_ARCSEC,
        "f_targets": F_TARGETS,
        "n_random_reps": N_RANDOM_REPS,
        "desi_beta1_max": desi_b,
        "baseline_mean": base_mean,
        "baseline_drift_sigma_vs_frozen": drift,
        "aggregate": agg,
        "per_mock": rows,
        "verdict": verdict,
        "verdict_note": ("FIBER_EXCLUDED = angular fiber incompleteness does not drive "
                         "beta1_max to DESI beyond random count loss. altmtl remains the "
                         "gold-standard follow-up; this is a physically-motivated surrogate."),
        "notes": ("Removal probability proportional to local angular neighbor count "
                  "within 62\", scaled to target fraction f; random null removes the same "
                  "count uniformly to isolate the fiber pattern from pure N loss."),
    }
    outp = res_dir / "phase9_fiber_surrogate.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print("Report the baseline sanity line, the per-f_target aggregate block, and the VERDICT.")


if __name__ == "__main__":
    main()
