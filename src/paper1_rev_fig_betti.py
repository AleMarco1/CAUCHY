#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper1_rev_fig_betti.py — rigenerazione di fig_betti_matched.pdf per la
revisione di MN-26-2847-P.

PERCHE' VA RIGENERATA
---------------------
1. TECNICO. Il file standalone attualmente in uso e' esportato con un
   bounding box che taglia il bordo sinistro: l'etichetta dell'asse y del
   pannello superiore, beta_1(nu), e' persa e "(DESI - mock)/sigma" e'
   troncata. La versione incorporata nel PDF sottomesso ai referee le ha
   entrambe: cosi' com'e', la revisione peggiorerebbe la figura rispetto a
   quella gia' vista. (Verifica: inchiostro sul bordo sinistro del raster.)

2. R3.6(iii). Il referee chiede di non confondere il picco della CURVA con
   il picco del RESIDUO. Il testo ora lo distingue; la figura no. Qui si
   marcano esplicitamente i due picchi delle curve (nu ~ +1.34 DESI,
   ~ +1.0 mock rimappati) e il minimo del residuo (nu ~ 0).

3. R2.1 / E2. Sotto la disciplina dei rank, le z della decomposizione in
   soglia vanno etichettate per quello che sono. L'annotazione diventa
   "-22.1 sigma_mock" e l'asse "(DESI - mock)/sigma_mock", con la
   spiegazione in didascalia.

USO
---
Adattare la funzione load_curves() alla propria sorgente dati (il resto
dello script non va toccato). Servono quattro array sulla stessa griglia
di soglia:

    nu          soglie
    b1_desi     curva di Betti-1 del campo DESI NGC
    b1_mock_m   media dell'ensemble di mock RIMAPPATI alla PDF di DESI
    b1_mock_s   deviazione standard dello stesso ensemble, soglia per soglia

Poi:
    python paper1_rev_fig_betti.py --out fig_betti_matched.pdf

CONTROLLI AUTOMATICI (gate)
---------------------------
Lo script verifica che i valori ricostruiti coincidano con quelli congelati
e si ferma se non tornano: picco DESI 8457 a nu=+1.337, picco mock 13321,
valore a nu~0 mock 7162 +/- 183 contro DESI 3119, minimo del residuo -22.1.
E' lo stesso principio usato altrove nella revisione: mettere nell'output
una quantita' che DEVE avere un valore noto.
"""

import argparse
import sys

import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

# ------------------------------------------------------------------
# valori congelati usati come gate (record consolidato, sezione 5.2)
# ------------------------------------------------------------------
REF = dict(
    peak_desi=8457, peak_desi_nu=1.337,
    peak_mock=13321, peak_mock_nu=1.02,
    at_zero_mock=7162.0, at_zero_mock_sd=183.0, at_zero_desi=3119,
    z_min=-22.1, z_min_nu=0.03,
)
TOL = dict(counts=2.0, nu=0.05, z=0.15)   # tolleranze dei gate


def load_curves():
    """
    ADATTARE QUI. Deve restituire (nu, b1_desi, b1_mock_mean, b1_mock_sd).

    Esempio con un npz prodotto dallo step 6:

        d = np.load(r"D:\\projects\\cauchy\\results\\paper1\\betti_matched_NGC_R5.npz")
        return d["nu"], d["b1_desi"], d["b1_mock_mean"], d["b1_mock_sd"]

    Esempio se i mock rimappati sono salvati per realizzazione (shape
    (n_mock, n_nu)):

        d = np.load(r"...\\betti_remap_NGC_R5.npz")
        curves = d["b1_mock"]                      # (n_mock, n_nu)
        return d["nu"], d["b1_desi"], curves.mean(0), curves.std(0, ddof=1)
    """
    raise NotImplementedError(
        "load_curves() va adattata alla sorgente dati locale: vedere la "
        "docstring per i due casi tipici."
    )


def check_gates(nu, b1_desi, mock_m, mock_s, strict=True):
    """Verifica i valori congelati. Ritorna la lista dei fallimenti."""
    fails = []

    def cmp(name, got, want, tol):
        if not np.isfinite(got) or abs(got - want) > tol:
            fails.append(f"{name}: ottenuto {got:.4g}, atteso {want:.4g} "
                         f"(tolleranza {tol:g})")

    i_d = int(np.argmax(b1_desi))
    cmp("picco DESI", b1_desi[i_d], REF["peak_desi"], TOL["counts"])
    cmp("nu del picco DESI", nu[i_d], REF["peak_desi_nu"], TOL["nu"])

    i_m = int(np.argmax(mock_m))
    cmp("picco mock rimappati", mock_m[i_m], REF["peak_mock"], TOL["counts"])
    cmp("nu del picco mock", nu[i_m], REF["peak_mock_nu"], TOL["nu"])

    i_0 = int(np.argmin(np.abs(nu)))
    cmp("mock a nu~0", mock_m[i_0], REF["at_zero_mock"], 5.0)
    cmp("sd mock a nu~0", mock_s[i_0], REF["at_zero_mock_sd"], 5.0)
    cmp("DESI a nu~0", b1_desi[i_0], REF["at_zero_desi"], TOL["counts"])

    with np.errstate(divide="ignore", invalid="ignore"):
        z = (b1_desi - mock_m) / mock_s
    i_z = int(np.nanargmin(z))
    cmp("minimo del residuo", z[i_z], REF["z_min"], TOL["z"])
    cmp("nu del minimo", nu[i_z], REF["z_min_nu"], TOL["nu"])

    if fails and strict:
        print("GATE FALLITI — la figura non viene scritta:", file=sys.stderr)
        for f in fails:
            print("  -", f, file=sys.stderr)
        sys.exit(1)
    return fails


def make_figure(nu, b1_desi, mock_m, mock_s, out):
    with np.errstate(divide="ignore", invalid="ignore"):
        z = (b1_desi - mock_m) / mock_s

    i_d = int(np.argmax(b1_desi))
    i_m = int(np.argmax(mock_m))
    i_z = int(np.nanargmin(z))

    plt.rcParams.update({
        "font.size": 8, "axes.labelsize": 8,
        "xtick.labelsize": 7, "ytick.labelsize": 7,
        "legend.fontsize": 6.5, "legend.frameon": False,
        "axes.linewidth": 0.8, "lines.linewidth": 1.4,
    })

    # colonna MNRAS = 240 pt = 3.32 in. Si lascia respiro a sinistra per le
    # due etichette ruotate: e' il difetto del file precedente.
    fig, (ax, axr) = plt.subplots(
        2, 1, figsize=(3.32, 3.45), sharex=True,
        gridspec_kw=dict(height_ratios=[2.6, 1.0], hspace=0.08),
    )

    # ---------------- pannello superiore: curve ----------------
    ax.fill_between(nu, mock_m - mock_s, mock_m + mock_s,
                    color="#c6d9f0", zorder=1,
                    label=r"mocks, DESI PDF imposed ($\pm1\sigma$)")
    ax.plot(nu, mock_m, color="#1f5fa8", zorder=3)
    ax.plot(nu, b1_desi, color="#c1440e", zorder=4, label="DESI NGC")

    # R3.6(iii): i picchi delle CURVE, marcati e distinti dal residuo
    for i, col in ((i_m, "#1f5fa8"), (i_d, "#c1440e")):
        ax.plot(nu[i], (mock_m if col == "#1f5fa8" else b1_desi)[i],
                marker="v", ms=4.5, color=col, zorder=6, clip_on=False)
    ax.annotate("curve peaks", xy=(nu[i_m], mock_m[i_m]),
                xytext=(nu[i_m] + 0.55, mock_m[i_m] * 0.99),
                fontsize=6.2, color="0.25", va="top",
                arrowprops=dict(arrowstyle="-", lw=0.5, color="0.45"))

    ax.axvline(0.0, color="0.55", lw=0.7, ls=(0, (4, 3)), zorder=2)
    ax.set_ylabel(r"$\beta_1(\nu)$")
    ax.set_ylim(0, None)
    ax.legend(loc="upper left")

    # ---------------- pannello inferiore: residuo ----------------
    axr.axhline(0.0, color="0.6", lw=0.7)
    axr.axhline(-3.0, color="0.6", lw=0.7, ls=":")
    axr.plot(nu, z, color="0.15")
    axr.axvline(0.0, color="0.55", lw=0.7, ls=(0, (4, 3)))
    axr.plot(nu[i_z], z[i_z], marker="v", ms=5, color="#c1440e",
             zorder=5, clip_on=False)

    # R2.1: la z e' etichettata, non nuda
    axr.annotate(
        rf"residual peak: $-{abs(z[i_z]):.1f}\,\sigma_{{\rm mock}}$"
        rf" at $\nu={nu[i_z]:.2f}$",
        xy=(nu[i_z], z[i_z]), xytext=(nu[i_z] + 0.35, z[i_z] + 1.0),
        fontsize=6.2, color="0.15", va="bottom",
        arrowprops=dict(arrowstyle="-", lw=0.5, color="0.45"),
    )
    axr.set_xlabel(r"threshold $\nu$")
    axr.set_ylabel(r"$(\mathrm{DESI}-\mathrm{mock})/\sigma_{\rm mock}$")
    axr.set_xlim(nu.min(), nu.max())

    # margine sinistro esplicito: le etichette ruotate devono starci dentro
    fig.subplots_adjust(left=0.20, right=0.94, top=0.975, bottom=0.125)
    fig.savefig(out, format="pdf")   # NB: niente bbox_inches="tight"
    plt.close(fig)


def verify_output(path):
    """Controlla che il PDF non abbia inchiostro sui bordi (nessun taglio)."""
    try:
        import subprocess, tempfile, os
        from PIL import Image
        with tempfile.TemporaryDirectory() as td:
            stem = os.path.join(td, "p")
            subprocess.run(["pdftoppm", "-png", "-r", "200", path, stem],
                           check=True)
            png = [f for f in os.listdir(td) if f.endswith(".png")][0]
            a = np.array(Image.open(os.path.join(td, png)).convert("L"))
        ink = a < 250
        edges = dict(left=ink[:, 0].sum(), right=ink[:, -1].sum(),
                     top=ink[0, :].sum(), bottom=ink[-1, :].sum())
        bad = {k: int(v) for k, v in edges.items() if v > 0}
        if bad:
            print(f"ATTENZIONE: contenuto sul bordo {bad} — bounding box "
                  f"ancora stretto, aumentare 'left' in subplots_adjust.")
        else:
            print("bounding box: pulito su tutti e quattro i lati.")
    except Exception as exc:                                # pragma: no cover
        print(f"(verifica del bounding box saltata: {exc})")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="fig_betti_matched.pdf")
    ap.add_argument("--no-gates", action="store_true",
                    help="scrive la figura anche se i valori congelati non tornano")
    args = ap.parse_args()

    nu, b1_desi, mock_m, mock_s = (np.asarray(x, float) for x in load_curves())
    fails = check_gates(nu, b1_desi, mock_m, mock_s, strict=not args.no_gates)
    if fails:
        print(f"({len(fails)} gate falliti, scrittura forzata)")
    make_figure(nu, b1_desi, mock_m, mock_s, args.out)
    print(f"scritto {args.out}")
    verify_output(args.out)
