#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_figures.py

Genera le figure del manoscritto rivisto dai report della revisione.

FIGURE PRODOTTE
---------------
  fig_phase.pdf        decomposizione fasi/spettro (N10). LA figura del paper:
                       il titolo nuovo si legge direttamente da qui.
  fig_persistence.pdf  sopravvivenza del deficit al taglio in persistenza (N2),
                       entrambe le normalizzazioni con la spiegazione della
                       divergenza
  fig_spectral.pdf     piano (f_half, N_H1) con DESI fuori dall'intervallo dei
                       mock (N1b) - mostra visivamente l'estrapolazione
  fig_wbar.pdf         trasferibilita' del criterio w_bar: bias assoluto e
                       differenziale per topologia (N8, N8b)
  fig_resolution.pdf   deficit e dispersione a 128^3 contro 256^3, con le
                       galassie per voxel (N9)

Le figure esistenti (fig_betti_matched.pdf, fig_retention_w.pdf) NON vengono
toccate.

STILE
-----
Larghezza colonna MNRAS 240 pt = 3.32 in; doppia colonna 504 pt = 7.0 in.
Font serif per coerenza con newtxtext. Nessun colore necessario alla lettura
(le figure restano leggibili in bianco e nero), coerentemente con la prassi
MNRAS.

USO
---
  python src\\paper1_rev_figures.py
  python src\\paper1_rev_figures.py --only phase,persistence
"""

import argparse
import json
import os
from pathlib import Path

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

COL = 3.32
DCOL = 7.0

plt.rcParams.update({
    "font.family": "serif",
    "font.size": 8,
    "axes.labelsize": 8,
    "axes.titlesize": 8,
    "legend.fontsize": 7,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.6,
    "ytick.major.width": 0.6,
    "lines.linewidth": 1.0,
    "figure.dpi": 200,
    "savefig.bbox": "tight",
    "savefig.pad_inches": 0.02,
})


def load_json(p):
    p = Path(p)
    if not p.exists():
        print(f"  [assente] {p}")
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def read_jsonl(p):
    p = Path(p)
    if not p.exists():
        return []
    out = []
    with open(p, encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except Exception:
                    pass
    return out


# ==================================================================== 1
def fig_phase(res, out):
    """N10: le quattro distribuzioni e le due frecce del deficit."""
    r = load_json(res / "paper1" / "n10_report_NGC.json")
    recs = read_jsonl(res / "paper1" / "n10_phases_NGC.jsonl")
    if r is None:
        return
    dpr = np.array([x["N_H1"] for x in recs if x["tipo"] == "desi_pr"])
    mor = np.array([x["N_H1_orig"] for x in recs if x["tipo"] == "mock_pr"])
    mpr = np.array([x["N_H1"] for x in recs if x["tipo"] == "mock_pr"])
    desi = r["desi_originale"]

    fig, ax = plt.subplots(figsize=(COL, 2.9))
    bins = np.linspace(min(desi, mor.min(), mpr.min(), dpr.min()) - 600,
                       max(mpr.max(), mor.max()) + 600, 45)
    ax.hist(mor, bins=bins, histtype="stepfilled", color="0.78",
            edgecolor="0.35", lw=0.7, label="mocks, original")
    ax.hist(mpr, bins=bins, histtype="step", color="k", lw=1.0, ls="--",
            label="mocks, phases randomised")
    if dpr.size:
        ax.hist(dpr, bins=bins, histtype="step", color="k", lw=1.0, ls=":",
                label="data, phases randomised")
    ax.axvline(desi, color="k", lw=1.4)

    # fascia riservata alle frecce: nessuna sovrapposizione con gli istogrammi
    ytop = ax.get_ylim()[1]
    ax.set_ylim(0, ytop * 1.42)
    y1, y2 = ytop * 1.28, ytop * 1.09
    ax.annotate("", xy=(desi, y1), xytext=(mor.mean(), y1),
                arrowprops=dict(arrowstyle="<->", lw=0.7, color="k"))
    ax.text(0.5 * (desi + mor.mean()), y1 + 0.03 * ytop,
            r"$D=%.0f$" % (mor.mean() - desi), ha="center", va="bottom",
            fontsize=7)
    if dpr.size:
        ax.annotate("", xy=(dpr.mean(), y2), xytext=(mpr.mean(), y2),
                    arrowprops=dict(arrowstyle="<->", lw=0.7, color="0.45"))
        ax.text(0.5 * (dpr.mean() + mpr.mean()), y2 + 0.03 * ytop,
                r"$D_\phi=%.0f$" % (mpr.mean() - dpr.mean()),
                ha="center", va="bottom", fontsize=7, color="0.3")
    ax.text(desi, ytop * 0.55, "data ", ha="right", va="center", fontsize=7,
            rotation=90)

    ax.set_xlabel(r"$N_{H_1}$")
    ax.set_ylabel("mocks per bin")
    ax.legend(frameon=False, loc="upper center",
              bbox_to_anchor=(0.5, -0.28), ncol=1, handlelength=1.6)
    frac = 100 * r["frazione_spettro"]
    ax.set_title(r"$D_\phi/D = %.1f$ per cent" % frac, loc="right",
                 fontsize=7)
    fig.savefig(out / "fig_phase.pdf")
    plt.close(fig)
    print(f"  fig_phase.pdf   (frazione spettrale {frac:.1f} per cent)")


# ==================================================================== 2
def fig_persistence(res, out):
    """N2: sopravvivenza del deficit, entrambe le normalizzazioni."""
    r = load_json(res / "paper1" / "n2_report_NGC.json")
    if r is None:
        return
    fig, axes = plt.subplots(1, 2, figsize=(DCOL, 2.3), sharey=True)
    for ax, tag, lab in ((axes[0], "ASSOLUTO",
                          r"$\varepsilon$ (units of $\nu$)"),
                         (axes[1], "AUTONORMALIZZATO",
                          r"$\varepsilon / (\nu_{99}-\nu_{1})$")):
        rows = r["tabelle"][tag]
        e = np.array([x["eps"] for x in rows])
        s = 100 * np.array([x["sopravvivenza"] for x in rows])
        n = np.array([x["mock_mean"] for x in rows])
        ok = n > 200
        ax.axhline(0, color="0.7", lw=0.6)
        ax.axhline(100, color="0.7", lw=0.6, ls=":")
        ax.plot(e[ok], s[ok], "-o", color="k", ms=2.5, mfc="w", mew=0.7)
        if (~ok).any():
            ax.plot(e[~ok], s[~ok], "o", color="0.6", ms=2.0)
        ax.set_xlabel(lab)
        ax.set_xscale("symlog", linthresh=e[e > 0].min())
        ax.set_ylim(-40, 135)
    axes[0].set_ylabel("surviving fraction of $D$ (per cent)")
    pm = r["desi"]["pers_median"]
    axes[0].axvline(pm, color="k", lw=0.6, ls="--")
    axes[0].text(pm, -34, " median\n persistence", fontsize=6, va="bottom")
    axes[0].set_title("absolute cut (adopted)", fontsize=7, loc="left")
    axes[1].set_title("self-normalised cut (control)", fontsize=7, loc="left")
    fig.savefig(out / "fig_persistence.pdf")
    plt.close(fig)
    print("  fig_persistence.pdf")


# ==================================================================== 3
def fig_spectral(res, out):
    """N1b: il piano (f_half, N_H1) con DESI fuori intervallo."""
    r = load_json(res / "paper1" / "n1b_report_NGC.json")
    spec = read_jsonl(res / "paper1" / "n1b_spectra_NGC.jsonl")
    pm = read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")
    if r is None or not spec:
        return
    nh = {}
    for j, rec in enumerate(pm):
        b = rec.get("base", {})
        try:
            k = int(str(rec.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            k = j
        nh[k] = float(b.get("N_H1", np.nan))
    x, y = [], []
    for s in spec:
        i = s.get("idx")
        if i in nh and np.isfinite(nh[i]):
            x.append(s["f_half"]); y.append(nh[i])
    x = np.array(x); y = np.array(y)
    p = r["piano"]["f_half"]

    fig, ax = plt.subplots(figsize=(COL, 2.5))
    ax.plot(x, y, ".", color="0.55", ms=1.8, rasterized=True,
            label="mocks (%d)" % x.size)
    xx = np.linspace(p["desi"] - 0.005, x.max() + 0.005, 100)
    ax.plot(xx, p["intercetta"] + p["pendenza"] * xx, "k-", lw=0.9)
    ax.axvspan(p["desi"] - 0.006, x.min(), color="0.92", zorder=0)
    ax.text(0.5 * (p["desi"] + x.min()), y.min(), "extrapolated ",
            ha="center", va="bottom", fontsize=6, color="0.35")
    ax.plot([p["desi"]], [p["nh1_predetto"]], "ks", ms=4, mfc="w", mew=0.9,
            label="predicted")
    ax.plot([p["desi"]], [p["nh1_osservato"]], "k*", ms=8, label="data")
    ax.annotate("", xy=(p["desi"], p["nh1_osservato"]),
                xytext=(p["desi"], p["nh1_predetto"]),
                arrowprops=dict(arrowstyle="->", lw=0.8))
    ax.text(p["desi"] + 0.004,
            0.5 * (p["nh1_osservato"] + p["nh1_predetto"]),
            r"$%.1f\,\sigma_{\rm rel}$" % abs(p["residuo_in_sigma"]),
            fontsize=7, va="center")
    ax.set_xlabel(r"$f_{1/2}$ (power fraction above $k_{\rm Nyq}/2$)")
    ax.set_ylabel(r"$N_{H_1}$")
    ax.legend(frameon=False, loc="lower right")
    fig.savefig(out / "fig_spectral.pdf")
    plt.close(fig)
    print("  fig_spectral.pdf")


# ==================================================================== 4
def fig_wbar(res, out):
    """N8/N8b: bias assoluto e differenziale per topologia."""
    a = load_json(res / "paper1" / "n8_report_128.json")
    b = load_json(res / "paper1" / "n8b_report_128.json")
    reca = read_jsonl(res / "paper1" / "n8_masks_128.jsonl")
    if a is None or not reca:
        return
    ref = {(x["sigma"], x["real"]): x["rho"] for x in reca
           if x["shape"] == "__full__"}
    shapes = ["slab", "shell", "tube", "wedge", "slab_holes"]
    names = {"slab": "slab", "shell": "shell", "tube": "tube",
             "wedge": "wedge", "slab_holes": "slab + holes"}
    mk = dict(zip(shapes, ["o", "s", "^", "D", "v"]))

    fig, axes = plt.subplots(1, 2, figsize=(DCOL, 2.3))
    ax = axes[0]
    for sh in shapes:
        d = [x for x in reca if x["shape"] == sh
             and (x["sigma"], x["real"]) in ref]
        if not d:
            continue
        w = np.array([x["w_bar"] for x in d])
        bi = 100 * np.array([x["rho"] / ref[(x["sigma"], x["real"])] - 1
                             for x in d])
        o = np.argsort(w)
        ax.plot(w[o], bi[o], mk[sh] + "-", ms=2.5, lw=0.7, color="k",
                mfc="w", mew=0.6, label=names[sh])
    ax.axvline(0.99, color="0.5", lw=0.7, ls="--")
    ax.text(0.99, ax.get_ylim()[0], r" $\bar w=0.99$", fontsize=6,
            va="bottom")
    ax.set_xlabel(r"$\bar w$")
    ax.set_ylabel("bias in loop density (per cent)")
    ax.set_title("absolute", fontsize=7, loc="left")
    ax.legend(frameon=False, loc="lower right", ncol=1)
    ax.set_xlim(0.93, 1.001)

    ax = axes[1]
    if b is not None and "per_forma" in b:
        lab = [names[s] for s in shapes if s in b["per_forma"]]
        va = [100 * b["per_forma"][s]["bias_abs"] for s in shapes
              if s in b["per_forma"]]
        vd = [100 * b["per_forma"][s]["bias_diff"] for s in shapes
              if s in b["per_forma"]]
        xp = np.arange(len(lab))
        ax.bar(xp - 0.2, va, 0.4, color="0.75", edgecolor="k", lw=0.6,
               label="absolute")
        ax.bar(xp + 0.2, vd, 0.4, color="k", label="differential")
        ax.set_xticks(xp)
        ax.set_xticklabels(lab, rotation=25, ha="right")
        ax.axhline(0, color="k", lw=0.6)
        ax.set_ylabel("bias (per cent)")
        ax.set_title(r"at $\bar w \geq 0.99$", fontsize=7, loc="left")
        ax.legend(frameon=False, loc="lower left")
    fig.savefig(out / "fig_wbar.pdf")
    plt.close(fig)
    print("  fig_wbar.pdf")


# ==================================================================== 5
def fig_resolution(res, out):
    """N9: deficit e dispersione alle due risoluzioni."""
    r = load_json(res / "paper1" / "n9_report_NGC.json")
    recs = read_jsonl(res / "paper1" / "n9_res256_NGC.jsonl")
    if r is None or "convergenza" not in r:
        return
    c = r["convergenza"]
    a = np.array([x["n128"] for x in recs if x.get("n128")], float)
    bb = np.array([x["n256"] for x in recs if x.get("n128")], float)

    fig, axes = plt.subplots(1, 2, figsize=(DCOL, 2.3))
    ax = axes[0]
    for arr, desi, lab, off in ((a, c["desi_128"], r"$128^3$", 0),
                                (bb, c["desi_256"], r"$256^3$", 1)):
        m, s = arr.mean(), arr.std(ddof=1)
        ax.errorbar([off], [0], yerr=[100 * s / m], fmt="o", color="k",
                    ms=3, capsize=2, lw=0.8)
        ax.plot([off], [-100 * (m - desi) / m], "k*", ms=9)
    ax.set_xticks([0, 1]); ax.set_xticklabels([r"$128^3$", r"$256^3$"])
    ax.set_xlim(-0.5, 1.5)
    ax.axhline(0, color="0.7", lw=0.6)
    ax.set_ylabel("per cent of mock mean")
    ax.set_title("deficit (stars) and mock dispersion (bars)",
                 fontsize=7, loc="left")
    ax.text(0, -100 * (a.mean() - c["desi_128"]) / a.mean() - 1.6,
            r"$%.1f$" % (100 * c["frazione_128"]), ha="center", fontsize=7)
    ax.text(1, -100 * (bb.mean() - c["desi_256"]) / bb.mean() - 1.6,
            r"$%.1f$" % (100 * c["frazione_256"]), ha="center", fontsize=7)

    ax = axes[1]
    ngal = 217614.0
    for off, ng in ((0, 128), (1, 256)):
        cell = 1997.3629 / ng
        vox = 307805 * (ng / 128) ** 3
        ax.bar([off], [ngal / vox], 0.5, color="0.75", edgecolor="k", lw=0.6)
        ax.text(off, ngal / vox + 0.02, r"$%.2f$" % (ngal / vox),
                ha="center", fontsize=7)
    ax.axhline(1.0, color="k", lw=0.7, ls="--")
    ax.text(1.45, 1.02, "one galaxy\nper voxel", fontsize=6, ha="right")
    ax.set_xticks([0, 1]); ax.set_xticklabels([r"$128^3$", r"$256^3$"])
    ax.set_xlim(-0.5, 1.5)
    ax.set_ylabel("galaxies per in-mask voxel")
    ax.set_title("sampling limit", fontsize=7, loc="left")
    fig.savefig(out / "fig_resolution.pdf")
    plt.close(fig)
    print("  fig_resolution.pdf")


# ==================================================================== main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--out", default="paper")
    ap.add_argument("--only", default="")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    out = root / args.out
    out.mkdir(parents=True, exist_ok=True)
    print(f"figure in {out}\n")

    todo = {"phase": fig_phase, "persistence": fig_persistence,
            "spectral": fig_spectral, "wbar": fig_wbar,
            "resolution": fig_resolution}
    sel = [t.strip() for t in args.only.split(",") if t.strip()] or list(todo)
    for k in sel:
        if k not in todo:
            print(f"  [ignoto] {k}")
            continue
        try:
            todo[k](res, out)
        except Exception as e:
            print(f"  [errore] {k}: {type(e).__name__}: {e}")

    print("\nInserire nel .tex con \\includegraphics[width=\\columnwidth]{...}")
    print("per fig_phase e fig_spectral (una colonna), e")
    print("\\includegraphics[width=\\textwidth]{...} dentro figure* per")
    print("fig_persistence, fig_wbar e fig_resolution (due colonne).")


if __name__ == "__main__":
    main()
