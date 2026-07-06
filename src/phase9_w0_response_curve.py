#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 2
src/phase9_w0_response_curve.py

Isolated-referee Concern 3: the Phase 8 statement "reaching DESI requires
w0 ~ -294" is a linear extrapolation of a near-zero partial correlation ~200x
outside the sampled range. Not validated. This script replaces it with what the
data actually constrain WITHIN the sampled nwLH range.

It does three things on the labelled mocks (the ~200 with w0/Om/s8 in the npz):
  1. Partial correlation r(beta1_max, w0 | Om, s8) with a permutation p-value
     (residual-based; the honest measure of a w0 signal at fixed Om,s8).
  2. Binned response: mean beta1_max in w0 bins, to show (non)monotonicity.
  3. OLS slope d(beta1_max)/d(w0) at fixed Om,s8 with a bootstrap 95% CI, and the
     implied w0 to reach DESI IF the linear response held -- reported explicitly
     as an unvalidated extrapolation, with the extrapolation factor stated.

Key output: a reframed, defensible sentence for the paper, e.g.
  "Within the sampled range w0 in [wmin, wmax], beta1_max shows no significant
   dependence on w0 at fixed (Om, s8) (partial r = ..., p = ...). DESI's deficit
   is not reproduced by any sampled cosmology; attributing it to w0 alone would
   require w0 ~ X, an extrapolation ~Nx beyond the prior and therefore not a
   physical exclusion but a statement of the effect's magnitude."

Consumes results/phase9_likeforlike_arrays.npz (from phase9_extract_features.py).
Deterministic given --seed. No new field computation.

Run:
  python src\\phase9_w0_response_curve.py --project_root D:\\projects\\cauchy
"""

import argparse
import datetime
import json
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

N_BOOT = 5000
N_PERM = 20000
N_W0_BINS = 6


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def residualize(y, X):
    """Return residuals of y after OLS regression on [1, X]. X shape (n,k)."""
    A = np.column_stack([np.ones(len(y)), X])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ beta


def partial_corr(y, x, controls):
    """Partial correlation r(y, x | controls) via residualization."""
    ry = residualize(y, controls)
    rx = residualize(x, controls)
    denom = np.sqrt(np.sum(ry * ry) * np.sum(rx * rx))
    if denom == 0:
        return float("nan")
    return float(np.sum(ry * rx) / denom)


def perm_pvalue(y, x, controls, r_obs, n_perm, rng):
    """Two-sided permutation p-value for the partial correlation, permuting the
    residualized x against the residualized y."""
    ry = residualize(y, controls)
    rx = residualize(x, controls)
    denom = np.sqrt(np.sum(ry * ry) * np.sum(rx * rx))
    if denom == 0:
        return float("nan")
    count = 0
    n = len(ry)
    abs_obs = abs(r_obs)
    for _ in range(n_perm):
        perm = rng.permutation(n)
        r = np.sum(ry * rx[perm]) / denom
        if abs(r) >= abs_obs:
            count += 1
    return (count + 1) / (n_perm + 1)


def ols_slope_partial(y, w0, controls):
    """Slope of y on w0 controlling for controls: coefficient on w0 in the
    multiple regression y ~ 1 + w0 + controls."""
    A = np.column_stack([np.ones(len(y)), w0, controls])
    beta, *_ = np.linalg.lstsq(A, y, rcond=None)
    return float(beta[1])  # coefficient on w0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    rng = np.random.default_rng(args.seed)

    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    fig_dir = root / "figures"
    npz_path = res_dir / "phase9_likeforlike_arrays.npz"
    if not npz_path.exists():
        sys.exit(f"[FATAL] {npz_path} not found. Run phase9_extract_features.py first.")

    d = np.load(npz_path)
    beta1 = np.asarray(d["beta1_max"], float)
    w0 = np.asarray(d["w0"], float)
    Om = np.asarray(d["Om"], float)
    s8 = np.asarray(d["s8"], float)
    desi_b = float(d["desi_beta1max"])

    ok = np.isfinite(w0) & np.isfinite(Om) & np.isfinite(s8) & np.isfinite(beta1)
    beta1, w0, Om, s8 = beta1[ok], w0[ok], Om[ok], s8[ok]
    n = len(w0)
    print("=" * 70)
    print(f"CAUCHY Phase 9 - Script 2: beta1_max-w0 response (labelled N={n})")
    print("=" * 70)
    if n < 30:
        sys.exit(f"[FATAL] only {n} labelled mocks; need the pilot CSV merged into the npz.")

    w0min, w0max = float(w0.min()), float(w0.max())
    print(f"  w0 sampled range: [{w0min:.3f}, {w0max:.3f}]  (span {w0max-w0min:.3f})")
    print(f"  Om range: [{Om.min():.3f}, {Om.max():.3f}]  s8 range: [{s8.min():.3f}, {s8.max():.3f}]")

    controls = np.column_stack([Om, s8])

    # 1. partial correlation + permutation p
    r_part = partial_corr(beta1, w0, controls)
    p_perm = perm_pvalue(beta1, w0, controls, r_part, N_PERM, rng)
    print(f"\n  partial r(beta1_max, w0 | Om, s8) = {r_part:+.4f}  "
          f"(perm p = {p_perm:.4f}, N_perm={N_PERM})")

    # 2. binned response
    edges = np.quantile(w0, np.linspace(0, 1, N_W0_BINS + 1))
    edges[-1] += 1e-9
    which = np.clip(np.digitize(w0, edges) - 1, 0, N_W0_BINS - 1)
    bin_mid, bin_mean, bin_sem, bin_n = [], [], [], []
    for b in range(N_W0_BINS):
        sel = which == b
        if sel.sum() == 0:
            continue
        bin_mid.append(float(np.median(w0[sel])))
        bin_mean.append(float(beta1[sel].mean()))
        bin_sem.append(float(beta1[sel].std(ddof=1) / np.sqrt(sel.sum())) if sel.sum() > 1 else 0.0)
        bin_n.append(int(sel.sum()))
    print("\n  binned beta1_max vs w0 (at native Om,s8 mix):")
    for m, mu, se, nn in zip(bin_mid, bin_mean, bin_sem, bin_n):
        print(f"    w0~{m:+.3f}  beta1_max={mu:8.0f} +/- {se:5.0f}  (n={nn})")

    # 3. OLS slope at fixed Om,s8 + bootstrap CI
    slope = ols_slope_partial(beta1, w0, controls)
    boot = np.empty(N_BOOT)
    for k in range(N_BOOT):
        idx = rng.integers(0, n, n)
        boot[k] = ols_slope_partial(beta1[idx], w0[idx], controls[idx])
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"\n  OLS slope d(beta1_max)/d(w0) | Om,s8 = {slope:+.1f} "
          f"[95% CI {lo:+.1f}, {hi:+.1f}] loops per unit w0")

    # implied w0 to reach DESI IF linear response held (unvalidated extrapolation).
    # Only meaningful if the slope is DISTINGUISHABLE FROM ZERO (CI does not span 0).
    # When the CI crosses zero the inversion gap/slope is numerically meaningless
    # (a near-zero, sign-ambiguous denominator), so the extrapolation is UNDEFINED.
    gap = desi_b - float(beta1.mean())   # negative: DESI below
    slope_significant = (lo > 0) or (hi < 0)   # CI excludes zero
    if slope_significant and abs(slope) > 1e-6:
        w0_needed = float(np.mean(w0) + gap / slope)
        extrap_factor = abs(w0_needed - w0max) / (w0max - w0min)
        print(f"\n  IF-linear w0 to reach DESI = {w0_needed:.1f}  "
              f"(~{extrap_factor:.0f}x beyond the sampled range -> UNVALIDATED extrapolation)")
    else:
        w0_needed, extrap_factor = float("nan"), float("nan")
        print(f"\n  IF-linear w0 to reach DESI = UNDEFINED "
              f"(OLS slope CI [{lo:+.0f}, {hi:+.0f}] spans zero: no finite w0 follows "
              f"from a linear response indistinguishable from flat)")

    # significance verdict on the in-range w0 dependence
    w0_significant = np.isfinite(p_perm) and (p_perm < 0.05)
    if w0_significant:
        reframed = (f"Within the sampled range w0 in [{w0min:.2f}, {w0max:.2f}], "
                    f"beta1_max depends on w0 at fixed (Om,s8) (partial r={r_part:+.3f}, "
                    f"p={p_perm:.3f}); however DESI lies far below every sampled cosmology.")
    else:
        reframed = (f"Within the sampled range w0 in [{w0min:.2f}, {w0max:.2f}], beta1_max "
                    f"shows no significant dependence on w0 at fixed (Om,s8) "
                    f"(partial r={r_part:+.3f}, p={p_perm:.3f}); the response slope "
                    f"d(beta1_max)/d(w0) is indistinguishable from zero "
                    f"(OLS {slope:+.0f}, 95% CI [{lo:+.0f}, {hi:+.0f}]). DESI's deficit is "
                    f"not reproduced by any sampled cosmology, and the flat, sign-ambiguous "
                    f"w0 response admits no finite linear extrapolation to DESI. We therefore "
                    f"report the deficit as an anomaly relative to the w0CDM (wa=0) mock "
                    f"suite, not as a physical exclusion of a particular w0.")
    print("\n  [reframed sentence for the paper]")
    print("  " + reframed)

    # figure: binned response + DESI line
    fig, ax = plt.subplots(figsize=(6.2, 4.3))
    ax.scatter(w0, beta1, s=12, color="0.6", alpha=0.6, label="mocks (labelled)")
    ax.errorbar(bin_mid, bin_mean, yerr=bin_sem, fmt="o-", color="navy",
                capsize=3, label="binned mean")
    ax.axhline(desi_b, color="crimson", lw=2, label="DESI BGS")
    ax.set_xlabel("$w_0$"); ax.set_ylabel("$\\beta_1^{\\mathrm{max}}$")
    ax.set_title("$\\beta_1^{\\mathrm{max}}$ vs $w_0$ (sampled nwLH range)")
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"fig_phase9_w0_response.{ext}", dpi=200)
    plt.close(fig)

    out = {
        "schema_version": "2.0",
        "script": "phase9_w0_response_curve.py",
        "phase": "9",
        "concern_addressed": "isolated-referee Concern 3 (w0=-294 extrapolation)",
        "timestamp": _now_iso(),
        "n_labelled_mocks": n,
        "w0_range": [w0min, w0max],
        "partial_corr_beta1_w0_given_Om_s8": r_part,
        "perm_pvalue": p_perm,
        "n_perm": N_PERM,
        "binned_response": [
            {"w0_median": m, "beta1_max_mean": mu, "sem": se, "n": nn}
            for m, mu, se, nn in zip(bin_mid, bin_mean, bin_sem, bin_n)
        ],
        "ols_slope_per_unit_w0": slope,
        "ols_slope_bootstrap_ci95": [float(lo), float(hi)],
        "if_linear_w0_needed": w0_needed,
        "extrapolation_factor_beyond_range": extrap_factor,
        "in_range_w0_dependence_significant": bool(w0_significant),
        "reframed_paper_sentence": reframed,
        "figure": "fig_phase9_w0_response.pdf",
        "source_arrays": str(npz_path),
        "notes": ("w0 analysis uses the labelled subset (pilot CSV merged into the npz). "
                  "The if-linear w0_needed is reported ONLY to state the extrapolation "
                  "factor; it is not a physical exclusion."),
    }
    outp = res_dir / "phase9_w0_response.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}")
    print(f"          {fig_dir / 'fig_phase9_w0_response.pdf'}")
    print("\nReport the partial r line, the binned block, the OLS slope, and the "
          "reframed sentence.")


if __name__ == "__main__":
    main()
