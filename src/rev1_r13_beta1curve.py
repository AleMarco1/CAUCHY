"""
CAUCHY — MN-26-2100-P revision, referee point R1.3
src/rev1_r13_beta1curve.py

"Does the beta_1 curve exhibit local or global features from the 20% deficit
that would hint at its origin, such as from complexes of particular scales?"

The deficit is a difference of COUNTS, so it admits two exact decompositions:
every finite H1 generator has a birth threshold b and a persistence p = b - d,
and binning the generators by either variable partitions beta1_max. Summed over
bins, each decomposition reproduces the deficit to the generator.

  (A) Birth-threshold decomposition. Where along the filtration are the missing
      generators born? Concentrated near the beta_1 peak, in the tails, or
      spread out?
  (B) Persistence decomposition. Are the missing generators near-diagonal
      (short-lived, i.e. sampling-scale) or persistent (prominent loops)?

Both are reported twice: on the raw nu axis, and on the axis normalised by each
field's own in-mask standard deviation. The raw version is the honest one but is
confounded — data and mocks have different one-point distributions, so a
bin-by-bin residual mixes "different amplitude distribution" with "different
topology". The normalised version removes the single overall scale but not the
shape. Neither is a clean topological decomposition at matched one-point
distribution; that comparison is deliberately left out of scope here.

Design rules, as in rev1_r14_monotone.py:
  * No reimplementation of the pipeline. The DESI field is built with
    P8.build_field and the mock fields with the same code path; the masked H1
    diagram is extracted with a routine that is checked, field by field, against
    P8.compute_tda_features (count and mean persistence must agree exactly).
  * Reproduction gate on the DESI side (beta1_max == 28256) and provenance gate
    on the mock deltas (recomputed values must equal the frozen ensemble).

Run from the project root with the `cauchy` env active:

  python src\\rev1_r13_beta1curve.py --n_mocks 200 ^
      --mock_dir data\\processed\\paper1_mock_deltas\\NGC ^
      --frozen results\\phase9_ngc_clean_beta1.npz

Output: results/revision/rev1_r13_beta1curve.json  (summary, all quoted numbers)
        results/revision/rev1_r13_beta1curve.npz   (per-field histograms/curves)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

BETA1MAX_REF = 28256
PERS1_REF = 0.7246

ROOT = Path.cwd()
SRC = ROOT / "src"
OUT_DIR = ROOT / "results" / "revision"

parser = argparse.ArgumentParser()
parser.add_argument("--n_mocks", type=int, default=200)
parser.add_argument("--mock_dir", type=str,
                    default="data/processed/paper1_mock_deltas/NGC")
parser.add_argument("--frozen", type=str,
                    default="results/phase9_ngc_clean_beta1.npz")
parser.add_argument("--frozen_key", type=str, default="beta1_max")
parser.add_argument("--n_check", type=int, default=5)
parser.add_argument("--n_bins", type=int, default=120)
parser.add_argument("--occ_frac", type=float, default=0.005,
                    help="A bin counts as occupied if the mock mean exceeds this "
                         "fraction of the peak bin.")
parser.add_argument("--no_cache", action="store_true")
parser.add_argument("--skip_gates", action="store_true",
                    help="Diagnostic only. Never for a number that enters the paper.")
ARGS = parser.parse_args()

OUT_DIR.mkdir(parents=True, exist_ok=True)
sys.path.insert(0, str(SRC))


def load_pipeline():
    import phase8_cutsky_mocks as P8
    for a in ("build_field", "compute_tda_features", "load_desi_random_field",
              "load_desi_data_field", "NGRID", "SIGMA_PX", "N_THRESH",
              "DESI_MASK_FILE"):
        if not hasattr(P8, a):
            sys.exit(f"[ERRORE] phase8_cutsky_mocks non espone '{a}'.")
    return P8


def load_desi_cached(P8):
    cache = OUT_DIR / "desi_inputs_cache.npz"
    if cache.exists() and not ARGS.no_cache:
        z = np.load(cache)
        print(f"      (cache: {cache.name})")
        return z["field_d"], z["field_r"], float(z["alpha"])
    field_r, sum_wr = P8.load_desi_random_field()
    field_d, sum_wd = P8.load_desi_data_field()
    alpha = sum_wd / sum_wr
    np.savez(cache, field_d=field_d, field_r=field_r, alpha=np.float64(alpha))
    return field_d, field_r, alpha


def field_from_delta(delta_raw, mask, P8):
    """The log branch of the pipeline, starting from a stored raw contrast."""
    from scipy.ndimage import gaussian_filter
    delta = np.asarray(delta_raw, dtype=np.float64).copy()
    delta[~mask] = 0.0
    nu = np.zeros_like(delta)
    nu[mask] = np.log(1.0 + np.clip(delta[mask], -1.0 + 1e-3, None))
    nu = gaussian_filter(nu, sigma=P8.SIGMA_PX)
    nu[~mask] = 0.0
    nu[mask] -= nu[mask].mean()
    return nu.astype(np.float32)


# --------------------------------------------------------------------------
# Masked H1 diagram. This mirrors the masked branch of P8.compute_tda_features
# line for line; the caller checks it against that function on every field.
# --------------------------------------------------------------------------
def masked_h1_diagram(field, mask):
    import gudhi
    f = np.asarray(field, dtype=np.float64)
    SENT = 1.0e6
    fw = f.copy()
    fw[~mask] = -SENT
    fneg = -fw
    cutoff = SENT / 2.0
    cc = gudhi.CubicalComplex(dimensions=list(fneg.shape),
                              top_dimensional_cells=fneg.flatten())
    cc.compute_persistence()
    diag = np.array(cc.persistence_intervals_in_dimension(1))
    if diag.size == 0:
        return np.array([]), np.array([])
    keep = np.isfinite(diag[:, 1]) & (diag[:, 0] < cutoff) & (diag[:, 1] < cutoff)
    df = diag[keep]
    b, d = -df[:, 0], -df[:, 1]
    return b, d


def diagram_checked(field, mask, P8, tag):
    b, d = masked_h1_diagram(field, mask)
    feats = P8.compute_tda_features(field, mask, P8.N_THRESH, masked=True)
    n_ref, p_ref = int(feats[4]), float(feats[5])
    p = b - d
    if len(p) != n_ref or not np.isclose(p.mean(), p_ref, rtol=0, atol=1e-9):
        sys.exit(f"[STOP] {tag}: il diagramma estratto non concorda con "
                 f"compute_tda_features ({len(p)} vs {n_ref}; "
                 f"{p.mean():.10f} vs {p_ref:.10f}). Fermati.")
    return b, d, p, n_ref


def betti_curve(b, d, grid):
    """beta_1(nu) with the pipeline's own convention: alive iff b >= nu > d."""
    return np.array([np.sum((b >= nu) & (d < nu)) for nu in grid], dtype=float)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def cumulative_span(delta_per_bin, frac):
    """Smallest number of bins (taken in order of decreasing contribution)
    holding `frac` of the total positive deficit, as a fraction of all bins."""
    tot = delta_per_bin[delta_per_bin > 0].sum()
    if tot <= 0:
        return None
    order = np.sort(delta_per_bin[delta_per_bin > 0])[::-1]
    c = np.cumsum(order) / tot
    k = int(np.searchsorted(c, frac) + 1)
    return k / float(delta_per_bin.size)


def main():
    print("=" * 72)
    print("R1.3 — DECOMPOSIZIONE DEL DEFICIT IN SOGLIA E IN PERSISTENZA")
    print("=" * 72)
    P8 = load_pipeline()
    mask = np.load(P8.DESI_MASK_FILE)

    # ---------------- DESI ----------------
    print("\n[1/4] Lato DESI...")
    field_d, field_r, alpha = load_desi_cached(P8)
    nu_desi = P8.build_field(field_d, field_r, alpha, mask)
    b_D, d_D, p_D, n_D = diagram_checked(nu_desi, mask, P8, "DESI")
    sig_D = float(nu_desi[mask].std())
    print(f"      beta1_max = {n_D} (atteso {BETA1MAX_REF})  "
          f"<pers1> = {p_D.mean():.4f}  sigma_nu = {sig_D:.4f}")
    if n_D != BETA1MAX_REF and not ARGS.skip_gates:
        sys.exit("[STOP] baseline non riprodotta.")

    # ---------------- provenance + range pre-pass ----------------
    # The grids must cover the mock generators too, otherwise the histograms
    # would silently drop them and the decomposition would not close. The same
    # pass doubles as the provenance gate.
    print("\n[2/4] Provenance gate e calibrazione delle griglie...")
    mock_dir = Path(ARGS.mock_dir)
    files = sorted(mock_dir.glob("*.npy"))
    if not files:
        sys.exit(f"[ERRORE] nessun .npy in {mock_dir}")
    fz = np.load(ARGS.frozen)
    arr_fz = np.asarray(fz[ARGS.frozen_key])
    ok = True
    lo_m, hi_m, p_m, sg_m = [], [], [], []
    for i in range(min(ARGS.n_check, len(files))):
        nu_m = field_from_delta(np.load(files[i]), mask, P8)
        bm, dm, pm, nm = diagram_checked(nu_m, mask, P8, files[i].name)
        ref = int(round(float(arr_fz[i])))
        ok = ok and (nm == ref)
        sg = float(nu_m[mask].std())
        lo_m.append(min(bm.min(), dm.min())); hi_m.append(bm.max())
        p_m.append(pm.max()); sg_m.append(sg)
        print(f"      {files[i].name}: {nm} vs {ref}  "
              f"{'OK' if nm == ref else 'DIVERSO'}")
    if not ok and not ARGS.skip_gates:
        sys.exit("[STOP] provenance gate fallito.")

    # Common grids, fixed once from data and mocks together, with a 20% margin,
    # then applied identically to every field.
    lo = float(np.floor(min(b_D.min(), d_D.min(), min(lo_m)) * 1.2))
    hi = float(np.ceil(max(b_D.max(), max(hi_m)) * 1.2))
    edges_b = np.linspace(lo, hi, ARGS.n_bins + 1)
    centres_b = 0.5 * (edges_b[1:] + edges_b[:-1])
    p_hi = float(np.ceil(max(p_D.max(), max(p_m)) * 1.2))
    edges_p = np.linspace(0.0, p_hi, ARGS.n_bins + 1)
    centres_p = 0.5 * (edges_p[1:] + edges_p[:-1])
    # Normalised axes: each field divided by its own in-mask sigma. The grid
    # must span the union of the normalised ranges -- the mock sigma is smaller
    # than the DESI one, so a grid built from sigma_DESI alone truncates the
    # mocks and the decomposition stops closing.
    bn_lo = min([lo / sig_D] + [l / g for l, g in zip(lo_m, sg_m)]) * 1.2
    bn_hi = max([hi / sig_D] + [h / g for h, g in zip(hi_m, sg_m)]) * 1.2
    pn_hi = max([p_D.max() / sig_D] + [q / g for q, g in zip(p_m, sg_m)]) * 1.2
    edges_bn = np.linspace(bn_lo, bn_hi, ARGS.n_bins + 1)
    edges_pn = np.linspace(0.0, pn_hi, ARGS.n_bins + 1)
    print(f"      sigma_nu: DESI {sig_D:.4f}, mock {np.mean(sg_m):.4f} "
          f"(rapporto {sig_D/np.mean(sg_m):.3f})")
    print(f"      griglie normalizzate: nascita [{bn_lo:.2f}, {bn_hi:.2f}], "
          f"persistenza [0, {pn_hi:.2f}]")
    grid_nu = np.linspace(lo, hi, 201)
    print(f"      griglia nascita [{lo:.2f}, {hi:.2f}] in {ARGS.n_bins} bin; "
          f"persistenza [0, {p_hi:.2f}]")

    H = {}
    H["desi_birth"] = np.histogram(b_D, bins=edges_b)[0].astype(float)
    H["desi_pers"] = np.histogram(p_D, bins=edges_p)[0].astype(float)
    H["desi_birth_n"] = np.histogram(b_D / sig_D, bins=edges_bn)[0].astype(float)
    H["desi_pers_n"] = np.histogram(p_D / sig_D, bins=edges_pn)[0].astype(float)
    curve_D = betti_curve(b_D, d_D, grid_nu)
    print(f"      picco beta1 a nu = {grid_nu[np.argmax(curve_D)]:.3f}, "
          f"altezza {curve_D.max():.0f}")

    # ---------------- mocks ----------------
    files = files[:ARGS.n_mocks]
    print(f"\n[3/4] {len(files)} mock...")
    Mb, Mp, Mbn, Mpn, Mc, Mn, Ms = [], [], [], [], [], [], []
    t0 = time.time()
    for i, f in enumerate(files):
        nu = field_from_delta(np.load(f), mask, P8)
        b, d, p, n = diagram_checked(nu, mask, P8, f.name)
        sg = float(nu[mask].std())
        Mb.append(np.histogram(b, bins=edges_b)[0])
        Mp.append(np.histogram(p, bins=edges_p)[0])
        Mbn.append(np.histogram(b / sg, bins=edges_bn)[0])
        Mpn.append(np.histogram(p / sg, bins=edges_pn)[0])
        Mc.append(betti_curve(b, d, grid_nu))
        Mn.append(n); Ms.append(sg)
        el = time.time() - t0
        print(f"      [{i+1}/{len(files)}] {f.name}  beta1_max={n}  "
              f"({el/(i+1):.1f}s/mock)")
    Mb = np.array(Mb, float); Mp = np.array(Mp, float)
    Mbn = np.array(Mbn, float); Mpn = np.array(Mpn, float)
    Mc = np.array(Mc, float); Mn = np.array(Mn, float); Ms = np.array(Ms, float)

    # ---------------- analysis ----------------
    print("\n[4/4] Decomposizioni...")
    out = {"n_mocks": len(files), "mock_dir": str(mock_dir),
           "desi": {"beta1_max": n_D, "pers1_mean": float(p_D.mean()),
                    "sigma_nu": sig_D,
                    "beta1_peak_nu": float(grid_nu[np.argmax(curve_D)]),
                    "beta1_peak_height": float(curve_D.max())},
           "mock": {"beta1_max_mean": float(Mn.mean()),
                    "beta1_max_std": float(Mn.std(ddof=1)),
                    "sigma_nu_mean": float(Ms.mean())},
           "grids": {"birth_edges": edges_b.tolist(),
                     "pers_edges": edges_p.tolist(),
                     "nu_grid": grid_nu.tolist()},
           "decompositions": {}}
    total_deficit = float(Mn.mean() - n_D)
    out["total_deficit"] = total_deficit
    print(f"      deficit totale: {total_deficit:.1f} "
          f"({100*total_deficit/Mn.mean():.1f}%)")

    for name, (hD, hM, edges) in {
            "birth_raw": (H["desi_birth"], Mb, edges_b),
            "pers_raw": (H["desi_pers"], Mp, edges_p),
            "birth_sigma_normalised": (H["desi_birth_n"], Mbn, edges_bn),
            "pers_sigma_normalised": (H["desi_pers_n"], Mpn, edges_pn)}.items():
        mM, sM = hM.mean(axis=0), hM.std(axis=0, ddof=1)
        dlt = mM - hD
        closes = bool(abs(dlt.sum() - total_deficit) < 1.0)
        with np.errstate(divide="ignore", invalid="ignore"):
            z = np.where(sM > 0, dlt / sM, 0.0)
        occupied = mM > ARGS.occ_frac * mM.max()
        n_below3 = int(np.sum((z > 3) & occupied))
        n_above3 = int(np.sum((z < -3) & occupied))
        n_occ = int(occupied.sum())
        centres = 0.5 * (edges[1:] + edges[:-1])
        pos = dlt > 0
        wmean = float((centres[pos] * dlt[pos]).sum() / dlt[pos].sum()) if pos.any() else None
        # local vs global: is the deficit a uniform (1-f) rescaling of the mock
        # histogram, or does its fractional depth vary from bin to bin?
        with np.errstate(divide="ignore", invalid="ignore"):
            fbin = np.where(mM > 0, 1.0 - hD / np.maximum(mM, 1e-9), np.nan)
        fo = fbin[occupied]
        rec = {"sums_to_total_deficit": closes,
               "n_bins_excess_above_3sigma": n_above3,
               "frac_occupied_bins_excess_above_3sigma": n_above3 / n_occ if n_occ else None,
               "fractional_deficit_global": float(total_deficit / float(np.sum(mM))),
               "fractional_deficit_per_bin_median": float(np.nanmedian(fo)),
               "fractional_deficit_per_bin_p10": float(np.nanpercentile(fo, 10)),
               "fractional_deficit_per_bin_p90": float(np.nanpercentile(fo, 90)),
               "mock_generator_weighted_mean_position": float((centres * mM).sum() / mM.sum()),
               "occupied_range": [float(centres[occupied].min()),
                                  float(centres[occupied].max())],
               "deficit_sum_over_bins": float(dlt.sum()),
               "n_occupied_bins": n_occ,
               "n_bins_deficit_above_3sigma": n_below3,
               "frac_occupied_bins_above_3sigma": n_below3 / n_occ if n_occ else None,
               "bins_holding_50pct_of_deficit": cumulative_span(dlt, 0.50),
               "bins_holding_80pct_of_deficit": cumulative_span(dlt, 0.80),
               "deficit_weighted_mean_position": wmean,
               "delta_per_bin": dlt.tolist(),
               "z_per_bin": z.tolist(),
               "bin_centres": centres.tolist()}
        out["decompositions"][name] = rec
        f50 = rec["bins_holding_50pct_of_deficit"]
        f50s = f"{100*f50:.0f}%" if f50 is not None else "n/d"
        print(f"      {name:24s} chiude={closes}  "
              f"bin occupati={n_occ}  con deficit >3sigma={n_below3}  "
              f"50% del deficit in {f50s} dei bin")
        if not closes:
            print("        [ATTENZIONE] la decomposizione non somma al deficit "
                  "totale: griglia troppo stretta, riportamelo.")

    # ---- beta_1 curve on the common nu axis: displacement, not just depth
    mC, sC = Mc.mean(axis=0), Mc.std(axis=0, ddof=1)
    occ_c = mC > ARGS.occ_frac * mC.max()
    below = int(np.sum((curve_D < mC - 3 * sC) & occ_c))
    above = int(np.sum((curve_D > mC + 3 * sC) & occ_c))
    out["beta1_curve"] = {
        "desi_peak_nu": float(grid_nu[np.argmax(curve_D)]),
        "desi_peak_height": float(curve_D.max()),
        "mock_peak_nu": float(grid_nu[np.argmax(mC)]),
        "mock_peak_height": float(mC.max()),
        "n_occupied_thresholds": int(occ_c.sum()),
        "n_below_3sigma_band": below,
        "n_above_3sigma_band": above,
        "frac_below_3sigma_band": below / int(occ_c.sum()),
        "frac_above_3sigma_band": above / int(occ_c.sum())}
    print(f"      curva beta1: picco DESI nu={out['beta1_curve']['desi_peak_nu']:.2f} "
          f"h={curve_D.max():.0f} | mock nu={out['beta1_curve']['mock_peak_nu']:.2f} "
          f"h={mC.max():.0f}")
    print(f"      DESI sotto la banda 3sigma nel {100*below/int(occ_c.sum()):.0f}% "
          f"delle soglie occupate, SOPRA nel {100*above/int(occ_c.sum()):.0f}%")

    # persistence split: near-diagonal vs persistent, at the DESI median
    med = float(np.median(p_D))
    lowD = int((p_D <= med).sum()); highD = int((p_D > med).sum())
    cp = np.cumsum(Mp, axis=1)
    k = int(np.searchsorted(edges_p, med)) - 1
    k = max(0, min(k, Mp.shape[1] - 1))
    lowM = float(cp[:, k].mean()); highM = float((Mn - cp[:, k]).mean())
    out["persistence_split_at_desi_median"] = {
        "median_persistence_desi": med,
        "desi_below": lowD, "desi_above": highD,
        "mock_below_mean": lowM, "mock_above_mean": highM,
        "deficit_below": lowM - lowD, "deficit_above": highM - highD,
        "frac_of_deficit_below_median": (lowM - lowD) / total_deficit}
    print(f"      split a p = {med:.4f}: deficit sotto = {lowM-lowD:.0f}, "
          f"sopra = {highM-highD:.0f} "
          f"({100*(lowM-lowD)/total_deficit:.0f}% sotto)")

    out["timestamp"] = stamp()
    out["script"] = "src/rev1_r13_beta1curve.py"
    (OUT_DIR / "rev1_r13_beta1curve.json").write_text(
        json.dumps(out, indent=2), encoding="utf-8")
    np.savez_compressed(
        OUT_DIR / "rev1_r13_beta1curve.npz",
        edges_b=edges_b, edges_p=edges_p, edges_bn=edges_bn, edges_pn=edges_pn,
        nu_grid=grid_nu, desi_birth=H["desi_birth"], desi_pers=H["desi_pers"],
        desi_birth_n=H["desi_birth_n"], desi_pers_n=H["desi_pers_n"],
        desi_curve=curve_D, mock_birth=Mb, mock_pers=Mp, mock_birth_n=Mbn,
        mock_pers_n=Mpn, mock_curve=Mc, mock_beta1max=Mn, mock_sigma=Ms,
        desi_beta1max=n_D, desi_sigma=sig_D)
    print(f"\n[OUT] {OUT_DIR / 'rev1_r13_beta1curve.json'}")
    print(f"[OUT] {OUT_DIR / 'rev1_r13_beta1curve.npz'}")


if __name__ == "__main__":
    if not SRC.exists():
        sys.exit(f"[ERRORE] Lancia dalla root del progetto. Cwd: {ROOT}")
    main()
