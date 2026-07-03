"""
CAUCHY — Phase 8, w0 exclusion
src/phase8_w0_exclusion.py

Thesis-defining test. The robust result is a beta1_max DEFICIT in DESI vs cut-sky
LCDM mocks. This script asks: can ANY w0CDM model with wa=0, w0 in [-1.30,-0.70],
reproduce it? If not, we EXCLUDE w0CDM(wa=0) as the explanation — the honest,
falsifiable claim (as opposed to 'we detect phantom', which we cannot support).

Inputs (in priority order):
  1. results/phase8_test2_permock.csv   (index,w0,Om,s8,pers1,beta1_max)  [preferred]
  2. results/phase8_test2_fields/*.npz + nwLH params  [recompute beta1_max]
DESI reference (masked beta1_max) from results/phase8_test2_masked.json.

Analyses:
  A. Partial correlation r(beta1_max, w0 | Om, s8) and its permutation significance.
     Compare mean beta1_max of phantom (w0<-1.10) vs quintessence (w0>-0.90) mocks,
     and where DESI sits relative to BOTH — if DESI is far below even the phantom
     subset, no w0 in range helps.
  B. Linear model beta1_max ~ a*Om + b*s8 + c*w0 + d. Solve for the w0 that would
     bring a fiducial mock to DESI's beta1_max (holding Om,s8 at fiducial). If that
     w0 is far outside [-1.30,-0.70] (or the sign is wrong), w0CDM(wa=0) is excluded.

Verdict (frozen): EXCLUDE w0CDM(wa=0) IF DESI beta1_max lies below the minimum of
the phantom subset AND the extrapolated w0-to-DESI is outside [-2.0, -0.5] or has
the wrong sign. Otherwise: cannot exclude (phantom remains a candidate).

CAVEAT printed in output: this excludes w0CDM with wa=0 only. CPL with wa!=0 is
NOT testable here (no wa!=0 mocks) and the exclusion does not extend to it.

Usage:
  python src\\phase8_w0_exclusion.py --project_root D:\\projects\\cauchy
"""

import argparse
import json
import sys
from pathlib import Path
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import phase8_cutsky_mocks as M


def partial_corr(x, y, Z):
    """Partial correlation of x,y controlling for columns of Z (add intercept)."""
    Z1 = np.column_stack([np.ones(len(x)), Z])
    bx, *_ = np.linalg.lstsq(Z1, x, rcond=None)
    by, *_ = np.linalg.lstsq(Z1, y, rcond=None)
    rx = x - Z1 @ bx
    ry = y - Z1 @ by
    return float(np.corrcoef(rx, ry)[0, 1])


def perm_sig(x, y, Z, r_obs, n=2000, seed=0):
    rng = np.random.default_rng(seed)
    null = np.empty(n)
    for i in range(n):
        null[i] = partial_corr(x, rng.permutation(y), Z)
    # two-sided z relative to null
    return float((r_obs - null.mean()) / (null.std(ddof=1) + 1e-12))


def _load_params_map(root):
    """dict index -> (Om, s8, w0) from the nwLH params file (7 cols, w0=col6)."""
    candidates = [
        root / "data" / "raw" / "quijote" / "3D_cubes" / "latin_hypercube_nwLH" / "latin_hypercube_nwLH_params.txt",
        root / "data" / "raw" / "quijote" / "latin_hypercube_nwLH_params.txt",
    ]
    path = next((p for p in candidates if p.exists()), None)
    if path is None:
        return None
    t = np.loadtxt(path)
    return {i: (float(t[i, 0]), float(t[i, 4]), float(t[i, 6])) for i in range(len(t))}


def load_table(res_dir, root):
    """Prefer the per-mock CSV; otherwise reconstruct beta1_max from saved
    test2_fields/*.npz (current running job) joined with nwLH params."""
    csv = res_dir / "phase8_test2_permock.csv"
    if csv.exists():
        d = np.genfromtxt(csv, delimiter=",", names=True)
        return (np.asarray(d["w0"], float), np.asarray(d["Om"], float),
                np.asarray(d["s8"], float), np.asarray(d["beta1_max"], float),
                np.asarray(d["pers1"], float))
    # Fallback: recompute from saved fields
    fdir = res_dir / "phase8_test2_fields"
    files = sorted(fdir.glob("test2_*.npz")) if fdir.exists() else []
    if not files:
        return None
    params = _load_params_map(root)
    if params is None:
        print("[ERRORE] params nwLH non trovato per il fallback dai campi.")
        return None
    mask = np.load(M.DESI_MASK_FILE)
    print(f"  [fallback] ricostruzione beta1_max da {len(files)} campi salvati "
          f"(TDA mascherata)...")
    w0L, OmL, s8L, bL, pL = [], [], [], [], []
    for k, f in enumerate(files):
        idx = int(f.stem.split("_")[1])
        if idx not in params:
            continue
        nu = np.load(f)["delta"]
        feats = M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)
        om, s8, w0 = params[idx]
        OmL.append(om); s8L.append(s8); w0L.append(w0)
        bL.append(float(feats[4])); pL.append(float(feats[5]))
        if (k + 1) % 200 == 0:
            print(f"    [{k+1}/{len(files)}]")
    return (np.array(w0L), np.array(OmL), np.array(s8L), np.array(bL), np.array(pL))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default=".")
    ap.add_argument("--project_root_dummy", action="store_true")
    args = ap.parse_args()

    res = M.RES_DIR
    ref_json = res / "phase8_test2_masked.json"
    if not ref_json.exists():
        print("[ERRORE] phase8_test2_masked.json mancante — esegui prima Test 2.")
        sys.exit(1)
    ref = json.load(open(ref_json))
    desi_beta1 = ref["desi_reference_masked"]["beta1_max"]
    desi_pers1 = ref["desi_reference_masked"]["pers1"]
    print("=" * 70)
    print("Phase 8 — w0 exclusion (can any w0CDM wa=0 reproduce the deficit?)")
    print("=" * 70)
    print(f"  DESI (masked): beta1_max={desi_beta1:.0f}  pers1={desi_pers1:.4f}")

    tbl = load_table(res, M.ROOT)
    if tbl is None:
        print("[ERRORE] Nessuna sorgente per-mock: manca sia phase8_test2_permock.csv")
        print("         sia la cartella phase8_test2_fields/ con i campi salvati.")
        print("         Attendi che Test 2 (--save_fields) finisca, poi rilancia.")
        sys.exit(1)
    w0, Om, s8, beta1, pers1 = tbl
    ok = np.isfinite(w0) & np.isfinite(beta1)
    w0, Om, s8, beta1, pers1 = w0[ok], Om[ok], s8[ok], beta1[ok], pers1[ok]
    print(f"  mocks with valid params: N={len(w0)}, "
          f"w0 range [{w0.min():.3f}, {w0.max():.3f}]")

    # ---- Analysis A ----
    print("\n[A] Partial correlation and phantom vs quintessence")
    Z = np.column_stack([Om, s8])
    r_b = partial_corr(beta1, w0, Z)
    z_b = perm_sig(beta1, w0, Z, r_b, n=2000, seed=1)
    print(f"  r(beta1_max, w0 | Om, s8) = {r_b:+.3f}  (perm z = {z_b:+.2f})")

    phantom = w0 < -1.10
    quint   = w0 > -0.90
    bp_m, bp_s = beta1[phantom].mean(), beta1[phantom].std(ddof=1)
    bq_m, bq_s = beta1[quint].mean(),   beta1[quint].std(ddof=1)
    print(f"  beta1_max phantom (w0<-1.10, N={phantom.sum()}): {bp_m:.0f} ± {bp_s:.0f}")
    print(f"  beta1_max quint   (w0>-0.90, N={quint.sum()}): {bq_m:.0f} ± {bq_s:.0f}")
    print(f"  DESI beta1_max = {desi_beta1:.0f}")
    # how far below the phantom subset minimum does DESI sit?
    phantom_min = beta1[phantom].min()
    z_desi_vs_phantom = (desi_beta1 - bp_m) / bp_s
    print(f"  phantom subset min = {phantom_min:.0f}; DESI is {z_desi_vs_phantom:+.1f}"
          f" sigma vs phantom mean; DESI below phantom min: {desi_beta1 < phantom_min}")

    # ---- Analysis B ----
    print("\n[B] Extrapolation: what w0 would bring a mock to DESI beta1_max?")
    X = np.column_stack([np.ones(len(w0)), Om, s8, w0])
    coef, *_ = np.linalg.lstsq(X, beta1, rcond=None)
    d, aOm, aS8, cW0 = coef
    Om_fid, s8_fid = 0.3175, 0.834
    base = d + aOm * Om_fid + aS8 * s8_fid   # beta1 at w0=0 fiducial
    if abs(cW0) < 1e-6:
        w0_needed = np.inf
    else:
        w0_needed = (desi_beta1 - base) / cW0
    print(f"  linear fit: beta1 = {d:.0f} + {aOm:.0f}*Om + {aS8:.0f}*s8 + {cW0:+.0f}*w0")
    print(f"  d(beta1)/d(w0) = {cW0:+.0f} per unit w0")
    print(f"  w0 needed to reach DESI (Om,s8 fiducial): {w0_needed:+.3f}")
    print(f"  (mock w0 range is [-1.30, -0.70]; suite covers only wa=0)")

    # ---- Verdict ----
    print("\n" + "=" * 70)
    excl_A = desi_beta1 < phantom_min
    excl_B = (w0_needed < -2.0) or (w0_needed > -0.5) or (cW0 >= 0 and desi_beta1 < base) \
             or not np.isfinite(w0_needed)
    exclude = excl_A and excl_B
    if exclude:
        print("  >>> EXCLUDE w0CDM (wa=0): no w0 in [-1.30,-0.70] reproduces the DESI")
        print("      beta1_max deficit. DESI lies below even the most phantom mocks, and")
        print(f"      the w0 required by extrapolation ({w0_needed:+.2f}) is outside the")
        print("      sampled range / wrong sign. The deficit is NOT a w0 effect.")
        print("      This is a clean, falsifiable result: the anomaly is not w0CDM(wa=0).")
    else:
        print("  >>> CANNOT exclude w0CDM(wa=0): phantom mocks approach DESI, or the")
        print("      extrapolated w0 is within/near range. w0 remains a candidate;")
        print("      investigate further before claiming exclusion.")
    print("\n  CAVEAT: this concerns w0CDM with wa=0 ONLY. CPL with wa!=0 (the DESI DR2")
    print("  best fit, w0=-0.667 wa=-1.079) is NOT testable here — no wa!=0 mocks exist")
    print("  in the suite. The exclusion does NOT extend to the full CPL space.")

    out = {
        "output_id": "phase8_w0_exclusion",
        "desi_beta1_max_masked": desi_beta1,
        "partial_corr_beta1_w0": r_b, "perm_z": z_b,
        "phantom_mean": float(bp_m), "phantom_min": float(phantom_min),
        "quint_mean": float(bq_m),
        "desi_below_phantom_min": bool(desi_beta1 < phantom_min),
        "dbeta1_dw0": float(cW0), "w0_needed_for_desi": float(w0_needed),
        "verdict": "EXCLUDE_w0CDM_wa0" if exclude else "CANNOT_EXCLUDE",
        "caveat": "Excludes w0CDM wa=0 only; CPL wa!=0 not testable (no mocks).",
    }
    json.dump(out, open(res / "phase8_w0_exclusion.json", "w"), indent=2)
    print(f"\n[SAVED] {res / 'phase8_w0_exclusion.json'}")


if __name__ == "__main__":
    main()
