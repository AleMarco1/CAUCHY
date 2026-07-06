#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Phase 9, re-plot helper
src/phase9_replot_beta1max.py

Regenerates ONLY figures/fig_phase9_beta1max_empirical.{pdf,png} from the frozen
results/phase9_likeforlike_arrays.npz, with formatting fixes:
  - x-limits set from the data with symmetric padding (centered, zoomed);
  - legend moved to the empty upper-left region (off the mock bulk);
  - stats annotation placed in the empty central band (no overlap with bars,
    legend, or the DESI line).
No numbers change; this only re-renders the same empirical distribution.

Run:
  python src\\phase9_replot_beta1max.py --project_root D:\\projects\\cauchy
"""

import argparse
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", type=str, default="D:\\projects\\cauchy")
    ap.add_argument("--pad_frac", type=float, default=0.05,
                    help="x-axis padding as a fraction of the data span")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    npz = root / "results" / "phase9_likeforlike_arrays.npz"
    fig_dir = root / "figures"
    d = np.load(npz)
    b = np.asarray(d["beta1_max"], float)
    desi = float(d["desi_beta1max"])
    N = b.size

    mean, std = float(b.mean()), float(b.std(ddof=1))
    n_below = int(np.sum(b <= desi))
    p = (n_below + 1) / (N + 1)
    z = (desi - mean) / std

    fig, ax = plt.subplots(figsize=(6.6, 4.3))

    # Freedman-Diaconis bins over the data
    iqr = np.subtract(*np.percentile(b, [75, 25]))
    bw = 2 * iqr / (b.size ** (1.0 / 3.0)) if iqr > 0 else (b.max() - b.min()) / 30
    nbins = int(np.clip((b.max() - b.min()) / bw, 25, 70))
    ax.hist(b, bins=nbins, density=True, color="0.75",
            edgecolor="0.4", linewidth=0.5, label="mocks (empirical)")

    xs = np.linspace(b.min(), b.max(), 400)
    if std > 0:
        g = np.exp(-0.5 * ((xs - mean) / std) ** 2) / (std * np.sqrt(2 * np.pi))
        ax.plot(xs, g, "k--", linewidth=1.2, label="Gaussian (summary stats)")

    ax.axvline(desi, color="crimson", linewidth=2.0, label="DESI BGS")

    # --- x-limits: symmetric padding => centered + zoomed --------------------
    lo = min(desi, float(b.min()))
    hi = float(b.max())
    span = hi - lo
    pad = args.pad_frac * span
    ax.set_xlim(lo - pad, hi + pad)

    # --- legend off the bars (bulk is on the right) --------------------------
    ax.legend(loc="upper left", fontsize=8, framealpha=0.95)

    # --- stats annotation in the empty central band --------------------------
    pstr = f"p < 1/{N}" if n_below == 0 else f"p = {p:.3g}"
    ann = (f"DESI = {desi:.0f}\n"
           f"{n_below}/{N} mocks below\n"
           f"rank {n_below if n_below else 1}/{N},  {pstr}\n"
           f"z (Gaussian) = {z:.2f}")
    ax.text(0.40, 0.62, ann, transform=ax.transAxes, va="top", ha="left",
            fontsize=9, bbox=dict(boxstyle="round", fc="white", ec="0.6", alpha=0.95))

    ax.set_xlabel(r"$\beta_1^{\mathrm{max}}$ (loop count at peak)")
    ax.set_ylabel("probability density")
    ax.set_title(r"Like-for-like mocks vs DESI: $\beta_1^{\mathrm{max}}$")
    fig.tight_layout()

    fig_dir.mkdir(parents=True, exist_ok=True)
    for ext in ("pdf", "png"):
        fig.savefig(fig_dir / f"fig_phase9_beta1max_empirical.{ext}", dpi=200)
    plt.close(fig)
    print(f"[written] {fig_dir / 'fig_phase9_beta1max_empirical.pdf'}  (+ .png)")
    print(f"  xlim = [{lo-pad:.0f}, {hi+pad:.0f}]  N={N}  below={n_below}  {pstr}")


if __name__ == "__main__":
    main()
