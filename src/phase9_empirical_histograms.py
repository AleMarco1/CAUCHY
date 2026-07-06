#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, Script 1 (final)
src/phase9_empirical_histograms.py

Isolated-referee Concern 1: replace the "Gaussian drawn from summary stats"
representation of the like-for-like (masked) mock distributions with the REAL
empirical distributions, and report EMPIRICAL rank / p-value.

Consumes results/phase9_likeforlike_arrays.npz produced by
phase9_extract_features.py (keys: beta1_max[N], pers1_mean[N], desi_beta1max,
desi_pers1, n_mocks, and w0/Om/s8/index for later scripts).

  - beta1_max : DESI is a DEFICIT (below mocks). One-sided P(mock <= DESI).
  - pers1     : DESI is an EXCESS  (above mocks). One-sided P(mock >= DESI).

Outputs:
  - results/phase9_empirical_histograms.json  (frozen numbers, schema 2.0)
  - figures/fig_phase9_beta1max_empirical.{pdf,png}
  - figures/fig_phase9_pers1_empirical.{pdf,png}

Gate9-S1 (pre-registered, reproduces the Phase 8 frozen headline):
  - beta1_max: DESI below ALL mocks (n_below == 0) AND empirical p <= 1/N.
  - pers1    : DESI NOT a >3 sigma excess by rank (rank_pct < 99.87)  ->
               consistent with the frozen BETA1_ONLY verdict (pers1 secondary).
A flag here means the empirical result departs from the frozen summary; it is a
signal to investigate before the figure enters the paper, not a publication gate.

Run:
  python src\\phase9_empirical_histograms.py --project_root D:\\projects\\cauchy
"""

import argparse
import datetime
import json
import os
import sys
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

GATE9_S1 = {
    "beta1max_desi_below_all_mocks": True,      # n_below == 0
    "beta1max_p_one_sided_le": 1.0 / 2000.0,
    "pers1_not_3sigma_excess_rank_pct_lt": 99.87,
}


def _now_iso():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()


def empirical_stats(mocks, desi, side):
    """side='deficit' -> P(mock <= desi); side='excess' -> P(mock >= desi)."""
    mocks = np.asarray(mocks, float)
    N = mocks.size
    mean = float(mocks.mean())
    std = float(mocks.std(ddof=1))
    z = (desi - mean) / std if std > 0 else float("nan")
    n_below = int(np.sum(mocks <= desi))
    n_above = int(np.sum(mocks >= desi))
    percentile = 100.0 * n_below / N
    n_extreme = n_below if side == "deficit" else n_above
    p_one_sided = (n_extreme + 1) / (N + 1)
    bound = f"p < 1/{N}" if n_extreme == 0 else None
    return {
        "n_mocks": N, "desi_value": float(desi),
        "mock_mean": mean, "mock_std": std, "z_score_gaussian_ref": z,
        "n_mocks_below": n_below, "n_mocks_above": n_above,
        "desi_percentile": percentile, "side": side,
        "n_more_extreme": n_extreme, "p_one_sided_empirical": p_one_sided,
        "p_empirical_bound_note": bound,
        "convention": "p = (n_more_extreme + 1)/(N + 1)",
    }


def make_fig(mocks, desi, st, title, xlabel, fig_dir, stub):
    mocks = np.asarray(mocks, float)
    fig, ax = plt.subplots(figsize=(6.0, 4.2))
    iqr = np.subtract(*np.percentile(mocks, [75, 25]))
    if iqr > 0:
        bw = 2 * iqr / (mocks.size ** (1.0 / 3.0))
        nbins = int(np.clip((mocks.max() - mocks.min()) / bw, 20, 60))
    else:
        nbins = 30
    ax.hist(mocks, bins=nbins, density=True, color="0.75",
            edgecolor="0.4", linewidth=0.5, label="mocks (empirical)")
    xs = np.linspace(mocks.min(), mocks.max(), 400)
    mu, sig = st["mock_mean"], st["mock_std"]
    if sig > 0:
        g = np.exp(-0.5 * ((xs - mu) / sig) ** 2) / (sig * np.sqrt(2 * np.pi))
        ax.plot(xs, g, "k--", linewidth=1.2, label="Gaussian (summary stats)")
    ax.axvline(desi, color="crimson", linewidth=2.0, label="DESI BGS")
    pstr = st["p_empirical_bound_note"] or f"p = {st['p_one_sided_empirical']:.3g}"
    ann = (f"DESI = {desi:.4g}\n"
           f"{st['n_mocks_below']}/{st['n_mocks']} mocks below\n"
           f"{pstr} (one-sided)\n"
           f"z (Gaussian) = {st['z_score_gaussian_ref']:.2f}")
    ax.text(0.03, 0.97, ann, transform=ax.transAxes, va="top", ha="left",
            fontsize=9, bbox=dict(boxstyle="round", fc="white", ec="0.6", alpha=0.9))
    ax.set_xlabel(xlabel); ax.set_ylabel("probability density"); ax.set_title(title)
    ax.legend(loc="upper right", fontsize=8, framealpha=0.9)
    fig.tight_layout()
    fig_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"{stub}.{ext}", dpi=200)
    plt.close(fig)
    return str(fig_dir / f"{stub}.pdf")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    args = ap.parse_args()
    root = Path(args.project_root).resolve()
    res_dir = root / "results"
    fig_dir = root / "figures"
    npz_path = res_dir / "phase9_likeforlike_arrays.npz"

    if not npz_path.exists():
        sys.exit(f"[FATAL] {npz_path} not found. Run phase9_extract_features.py first.")
    d = np.load(npz_path)
    beta1 = np.asarray(d["beta1_max"], float)
    pers1 = np.asarray(d["pers1_mean"], float)
    desi_b = float(d["desi_beta1max"])
    desi_p = float(d["desi_pers1"])
    N = beta1.size

    print("=" * 70)
    print(f"CAUCHY Phase 9 - Script 1: empirical histograms (N={N})")
    print("=" * 70)

    b1 = empirical_stats(beta1, desi_b, "deficit")
    p1 = empirical_stats(pers1, desi_p, "excess")
    print(f"[beta1_max] DESI={desi_b:.0f}  mean={b1['mock_mean']:.1f} std={b1['mock_std']:.1f}  "
          f"below={b1['n_mocks_below']}/{N}  p={b1['p_one_sided_empirical']:.3g}  "
          f"z={b1['z_score_gaussian_ref']:.2f}")
    print(f"[pers1]     DESI={desi_p:.5f}  mean={p1['mock_mean']:.5f} std={p1['mock_std']:.5f}  "
          f"pctile={p1['desi_percentile']:.2f}%  above={p1['n_mocks_above']}/{N}  "
          f"p={p1['p_one_sided_empirical']:.3g}  z={p1['z_score_gaussian_ref']:.2f}")

    fig_b = make_fig(beta1, desi_b, b1,
                     "Like-for-like mocks vs DESI: $\\beta_1^{\\mathrm{max}}$",
                     "$\\beta_1^{\\mathrm{max}}$ (loop count at peak)",
                     fig_dir, "fig_phase9_beta1max_empirical")
    fig_p = make_fig(pers1, desi_p, p1,
                     "Like-for-like mocks vs DESI: $\\langle \\mathrm{pers}_1 \\rangle$",
                     "$\\langle \\mathrm{pers}_1 \\rangle$ (mean $H_1$ persistence)",
                     fig_dir, "fig_phase9_pers1_empirical")

    flags = []
    if GATE9_S1["beta1max_desi_below_all_mocks"] and b1["n_mocks_below"] != 0:
        flags.append(f"beta1_max: expected 0 mocks below DESI, got {b1['n_mocks_below']}")
    if b1["p_one_sided_empirical"] > GATE9_S1["beta1max_p_one_sided_le"]:
        flags.append(f"beta1_max: p={b1['p_one_sided_empirical']:.3g} > {GATE9_S1['beta1max_p_one_sided_le']:.3g}")
    if p1["desi_percentile"] >= GATE9_S1["pers1_not_3sigma_excess_rank_pct_lt"]:
        flags.append(f"pers1: DESI percentile {p1['desi_percentile']:.2f}% >= "
                     f"{GATE9_S1['pers1_not_3sigma_excess_rank_pct_lt']}% (would be a >3sigma excess)")
    status = "CONFIRMED" if not flags else "FLAG"
    print(f"\n[GATE9-S1] {status}")
    for fl in flags:
        print("  - " + fl)

    out = {
        "schema_version": "2.0",
        "script": "phase9_empirical_histograms.py",
        "phase": "9",
        "concern_addressed": "isolated-referee Concern 1 (empirical histograms vs Gaussian)",
        "timestamp": _now_iso(),
        "comparison": "like-for-like cut-sky mocks, masked filtration, N={}".format(N),
        "source_arrays": str(npz_path),
        "beta1_max": b1,
        "pers1_mean": p1,
        "gate9_s1": {"criteria": GATE9_S1, "status": status, "flags": flags},
        "figures": {"beta1_max": os.path.basename(fig_b),
                    "pers1_mean": os.path.basename(fig_p)},
        "notes": ("Empirical rank/p-value are the quantities to quote; z_score is a "
                  "Gaussian-assumption reference only. Means reproduce the frozen "
                  "phase8_test2_masked.json; empirical spread is the true distribution."),
    }
    outp = res_dir / "phase9_empirical_histograms.json"
    with open(outp, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    print(f"\n[written] {outp}\n          {fig_b}\n          {fig_p}")


if __name__ == "__main__":
    main()
