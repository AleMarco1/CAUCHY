#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_item13a_15a.py — item 1.3a (convenzione di F_AP) e 1.5a (tiling per punto)

  conv     1.3a — quale convenzione implementa `make_dc_tab_ap`?
           Per il Lemma 3, F_AP e' costante SE E SOLO SE f(r) = A r^(1/F).
           Basta quindi una regressione di ln f su ln r:
              pendenza 1/1.03 = 0.9709  ->  F = alpha_perp/alpha_par (standard, D_M H/c)
              pendenza 1.03            ->  F = alpha_par/alpha_perp (il reciproco)
              nessuna delle due        ->  la funzione non produce F costante
           Blocca l'etichettatura di tutto il blocco B: campionare nella
           convenzione sbagliata mette i punti dalla parte opposta del fiduciale.

  tiling   1.5a — molteplicita' di tiling per geometria, via `x mod L_box`.

           CORREZIONE DEL 29 AGO 2026, e chiude un filo aperto.  La frazione
           indipendente usciva 0.7111-0.7125 contro lo 0.696 del reference, e il
           2% non era attribuito.  Non era fisica: `ceil(l_box/dx)` dava 65 bin
           larghi dx, che coprono 1014.3 h^-1 Mpc invece di 1000.  I bin devono
           tassellare il periodo, altrimenti si contano celle che non esistono.
           Ora `round(l_box/dx)` bin larghi l_box/nb, come rev1_r11_tiling.py, e
           il fiduciale NGC deve riprodurre 214 215 celle distinte all'unita'.

           ATTESA DA VERIFICARE, e contraddice il canovaccio.  Il canovaccio dice
           che il tiling dipende da alpha_iso e non da F_AP, quindi che il blocco
           B (alpha_iso = 1) e' immune.  Ma il lato del cubo e' fissato da
           alpha_box, NON da alpha_iso, e alpha_box varia dello 0.8% lungo B.
           I lati misurati in 1.2a per NGC:

               B1 2013.58   B2 2005.47   FID 1997.36   B4 1989.25   B5 1981.13

           e la soglia dove il numero di repliche intere puo' cambiare sta
           attorno a 2000 h^-1 Mpc.  In NGC la linea B ATTRAVERSA la soglia; in
           SGC (1888-1920) no.  Se confermato, l'immunita' del blocco B vale solo
           al sud, e il disegno dell'item 1.3 va corretto.

           La soglia vera non e' pero' esattamente 2000: dipende da box_min mod
           L_box asse per asse.  Va misurata, non dedotta.

Uso:
    python src\\paper2_item13a_15a.py conv
    python src\\paper2_item13a_15a.py tiling --region NGC --out results\\paper2\\item15a_NGC.jsonl
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import sys
import time

import numpy as np

ZMIN, ZMAX = 0.10, 0.40
OMM_FID, W0_FID = 0.3175, -1.0
C_OVER_H0 = 2997.92458
NGRID = 128
L_BOX_DEFAULT = 1000.0          # scatola periodica Quijote, h^-1 Mpc

# M26 R1 §5.6 / reference `tiling`, fiduciale NGC — cancello DURO del blocco tiling.
# Valori pieni, non arrotondati: col binning corretto (vedi tiling_stats) il
# fiduciale deve riprodurre 214 215 celle distinte ESATTAMENTE, all'unita'. Lo
# 0.70 e l'1.44 che stavano qui erano gli arrotondamenti del manoscritto e non
# potevano decidere nulla: il 2% di scarto che hanno lasciato passare era la
# binnatura sbagliata.
FROZEN_TILING_NGC = {
    "distinct_box_cells": 214215,
    "in_survey_voxels": 307805,
    "independent_fraction": 214215 / 307805,      # 0.69594384...
    "mult_mean": 307805 / 214215,                 # 1.43685...
    "mult_max": 5,
}

# A1m e A3m: emendamenti 27 e 28. Specchi ESATTI di A1 e A3 attorno a 1, cioe'
# 1 + 0.0275 e 1 - 0.0406. Servono perche' A1 e A3 stanno a distanze DIVERSE da
# 1 (0.0275 contro 0.0406, rapporto 1.4764) e con due punti asimmetrici pari e
# dispari NON si separano: una risposta puramente pari e quadratica darebbe
# A3/A1 = 1.4764^2 = 2.18, che si legge come un 37% di dispari inesistente.
# Con due coppie simmetriche la decomposizione e' pulita, e le due ampiezze
# distinguono un dispari LINEARE (rapporto atteso 1.476) da un GRADINO (1.000).
# A3m = 0.9594 e' sotto il range fisico isotropo [0.9725, 1.0406]: sul blocco A
# il segnale e' zero PER TEOREMA a qualunque alpha, quindi il test nullo resta
# valido. Dichiarato, non nascosto.
# I nomi non sono A2 e A4: sulla linea B il 3 e' saltato perche' B3 e' il
# fiduciale, quindi A2 e' riservato per la stessa convenzione.
# Qui c'e' SOLO alpha_iso: c, L e il box li deriva deform(), e il record 28
# vieta di scriverli in un secondo posto.
# A0 e A0m: emendamento 30. TERZA ampiezza, |alpha - 1| = 0.018627, che e' la
# continuazione GEOMETRICA verso il basso: 0.0275^2/0.0406, cosi' le tre
# ampiezze sono equispaziate in log a rapporto 1.476364.
# Serve perche' il residuo ad alpha = 1 e' ZERO ESATTO (alpha = 1 E' il
# fiduciale) e il record 29 lo misura in DISCESA fra 0.0275 e 0.0406: c'e'
# quindi un MASSIMO in (0, 0.0406), e due ampiezze non dicono dove. La terza
# si'. La potenza stimata sulle due note predice |pari| = 32.4/75.4/15.1 a
# questa ampiezza contro 18.0/32.5/5.5 a 0.0275; ma non puo' divergere per
# a -> 0, quindi quella predizione deve fallire e la domanda e' se lo fa gia' qui.
# Verso il basso NON per la leva (0.7792 contro 0.7802: non discrimina) ma
# perche' 0.0600 metterebbe entrambi gli alpha fuori range, e perche' il
# vincolo residuo(0)=0 morde a piccola ampiezza.
# Entrambi DENTRO [0.9725, 1.0406]: nessuna dichiarazione di fuori-range.
LINE_A = [("A0", 0.981373), ("A1", 0.9725), ("A1m", 1.0275),
          ("A3", 1.0406), ("A3m", 0.9594), ("A0m", 1.018627)]
# B6: emendamento 15, record 15. Terza unita' del campionamento equispaziato in
# residuo minimax (B2/B4 = 1, B1/B5 = 2). Valore DERIVATO da
# paper2_append_amend15.py, non digitato: 0.853136 voxel NGC, e supera di
# 0.005028 il F_max di C1 (1.040504), che la linea B non bracketava.
LINE_B = [("B1", 0.971070), ("B2", 0.985396), ("B4", 1.014889), ("B5", 1.030071),
          ("B6", 1.045531810025433)]
CORNERS = [("C1", 0.2500, -1.2), ("C2", 0.2500, -0.8),
           ("C3", 0.3500, -1.2), ("C4", 0.3500, -0.8)]


# --------------------------------------------------------------------------

def attach(srcdir, geom_mod, const_mod):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    G = __import__(geom_mod)
    M = getattr(G, "M", None) or __import__(const_mod)
    setg = getattr(M, "set_geometry", None) or getattr(G, "set_geometry", None)
    for zn, dn in (("_Z_TAB", "_DC_TAB"), ("Z_TAB", "DC_TAB")):
        if hasattr(M, zn):
            return (G, M, setg, np.asarray(getattr(M, zn), float).copy(),
                    np.asarray(getattr(M, dn), float).copy())
    raise SystemExit("tabella fiduciale non trovata")


def call_set(setg, **kw):
    ok = set(inspect.signature(setg).parameters)
    return setg(**{k: v for k, v in kw.items() if k in ok})


def e_of_z(z, omm, w0):
    return np.sqrt(omm * (1 + z) ** 3 + (1 - omm) * (1 + z) ** (3 * (1 + w0)))


def dc_scratch(z, omm, w0):
    i = 1.0 / e_of_z(z, omm, w0)
    return C_OVER_H0 * np.concatenate([[0.0], np.cumsum(0.5 * (i[1:] + i[:-1]) * np.diff(z))])


def minimax_alpha(r_fid, r_new):
    g = r_new / r_fid
    lo, hi = float(g.min()), float(g.max())
    if hi - lo < 1e-15:
        return 0.5 * (lo + hi)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        d = r_fid * (mid - g)
        if float(d.max()) - float((-d).max()) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def deform(z_tab, dc_fid, spec):
    if spec["kind"] == "fid":
        return dc_fid.copy()
    if spec["kind"] == "cosmo":
        zf = np.linspace(0.0, max(z_tab.max(), ZMAX + 0.05), 90001)
        a, b = dc_scratch(zf, OMM_FID, W0_FID), dc_scratch(zf, spec["omm"], spec["w0"])
        g = np.ones_like(zf)
        nz = a > 0
        g[nz] = b[nz] / a[nz]
        g[~nz] = g[nz][0]
        return dc_fid * np.interp(z_tab, zf, g)
    F, al = spec["F_ap"], spec["alpha_iso"]
    if abs(F - 1.0) < 1e-12:
        return dc_fid * al
    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    x = dc_fid ** (1.0 / F)
    return (al / minimax_alpha(dc_fid[m], x[m])) * x


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# --------------------------------------------------------------------------
# 1.3a
# --------------------------------------------------------------------------

def cmd_conv(a):
    G, M, setg, z_tab, dc_fid = attach(a.src, a.geom_module, a.const_module)
    fn = getattr(M, "make_dc_tab_ap", None) or getattr(G, "make_dc_tab_ap", None)
    print("=" * 72)
    print("1.3a — convenzione di F_AP in make_dc_tab_ap")
    print("=" * 72)
    if fn is None:
        print("  make_dc_tab_ap NON trovata: il blocco B va costruito con la forma")
        print("  chiusa del Lemma 3, f(r) = A r^(1/F), che e' quello che gia' fa")
        print("  paper2_item12a_geom.deform().  In tal caso la convenzione la")
        print("  scegliamo noi e va solo DICHIARATA: qui usiamo alpha_perp/alpha_par.")
        return
    print("  firma: make_dc_tab_ap%s" % inspect.signature(fn))

    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    r = dc_fid[m]
    rows = []
    for F in (a.f_test, 1.0 / a.f_test):
        try:
            out = fn(alpha_iso=1.0, F_ap=F, z_pivot=a.z_pivot)
        except TypeError:
            out = fn(1.0, F, a.z_pivot)
        dc_new = np.asarray(out[1] if isinstance(out, tuple) else out, float)
        if dc_new.shape != dc_fid.shape:
            dc_new = np.interp(z_tab, np.linspace(z_tab.min(), z_tab.max(), dc_new.size), dc_new)
        f = dc_new[m]
        p = np.polyfit(np.log(r), np.log(f), 1)
        resid = float(np.max(np.abs(f - np.exp(p[1]) * r ** p[0])))
        a_mmx = minimax_alpha(r, f)
        rows.append({"F_ap_passed": F, "loglog_slope": float(p[0]),
                     "F_implied_perp_over_par": float(1.0 / p[0]),
                     "powerlaw_residual_hMpc": resid, "alpha_iso_minimax": a_mmx})
        print("\n  F_ap=%.4f  ->  pendenza ln f / ln r = %.6f" % (F, p[0]))
        print("      1/pendenza = %.6f" % (1.0 / p[0]))
        print("      residuo dalla legge di potenza = %.4e h^-1 Mpc" % resid)
        print("      alpha_iso minimax risultante   = %.6f" % a_mmx)

    print("\n  verdetto")
    s0 = rows[0]["loglog_slope"]
    if abs(s0 - 1.0 / a.f_test) < 1e-3:
        conv = "alpha_perp/alpha_par (standard, D_M H/c)"
    elif abs(s0 - a.f_test) < 1e-3:
        conv = "alpha_par/alpha_perp (reciproco)"
    else:
        conv = "NESSUNA: la funzione non produce F costante"
    print("    convenzione implementata: %s" % conv)
    if rows[0]["powerlaw_residual_hMpc"] > 1e-6:
        print("    ATTENZIONE: residuo dalla legge di potenza non nullo -> F NON e'")
        print("    costante in z, e il Lemma 3 non si applica alla funzione com'e'.")
    print("\n    Da dichiarare nel manoscritto con la FORMULA, non col nome.")
    if a.out:
        append_atomic(a.out, {"schema": "paper2_item13a_v1", "utc": _now(),
                              "convention": conv, "tests": rows})


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


# --------------------------------------------------------------------------
# 1.5a
# --------------------------------------------------------------------------

def find_mask(obj):
    def walk(v):
        if isinstance(v, np.ndarray):
            return v if (v.dtype == bool and v.ndim == 3) else None
        if isinstance(v, dict):
            for x in v.values():
                r = walk(x)
                if r is not None:
                    return r
        elif isinstance(v, (list, tuple)):
            for x in v:
                r = walk(x)
                if r is not None:
                    return r
        return None
    return walk(obj)


def tiling_stats(mask, box_min, dx, l_box):
    """
    Mappa i centri dei voxel in maschera dentro la scatola periodica e misura:
      - quante repliche intere servono, per asse e in totale;
      - la frazione INDIPENDENTE (celle di scatola distinte / voxel in maschera);
      - la distribuzione di molteplicita'.
    """
    idx = np.argwhere(mask)
    x = np.asarray(box_min, float) + (idx + 0.5) * dx

    rep = np.floor(x / l_box).astype(np.int32)
    per_axis = [int(np.unique(rep[:, k]).size) for k in range(3)]
    n_rep = int(np.unique(rep, axis=0).shape[0])

    # I bin devono TASSELLARE la scatola periodica. Con `ceil(l_box/dx)` uscivano
    # 65 bin larghi dx = 15.6044, cioe' 1014.3 h^-1 Mpc: 14.3 in piu' del periodo,
    # ultimo bin parziale, griglia disallineata. Piu' celle disponibili significa
    # meno collisioni, quindi frazione indipendente gonfiata: e' l'intero scarto
    # fra lo 0.7111-0.7125 misurato qui e lo 0.696 di M26 §5.6, che usa
    # nb = round(L/dx) bin larghi L/nb (rev1_r11_tiling.py:87-89). Non era una
    # discrepanza fisica: erano due binnature, e questa era quella sbagliata.
    n_cell = int(round(l_box / dx))               # 64, non 65
    bw = l_box / n_cell                           # 15.6250, non 15.6044
    cell = np.floor((x - rep * l_box) / bw).astype(np.int64)
    np.clip(cell, 0, n_cell - 1, out=cell)
    flat = (cell[:, 0] * n_cell + cell[:, 1]) * n_cell + cell[:, 2]
    _, counts = np.unique(flat, return_counts=True)

    n = len(flat)
    return {
        "n_voxel": int(n),
        "replicas_per_axis": per_axis,
        "n_replicas_total": n_rep,
        "box_cells_per_axis": n_cell,
        "box_cell_width_hMpc": float(bw),         # dichiarata, non dedotta da dx
        "distinct_box_cells": int(counts.size),
        "independent_fraction": float(counts.size) / n,
        "mult_mean": float(n) / counts.size,
        "mult_max": int(counts.max()),
        "mult_hist": {str(k): int(v) for k, v in
                      zip(*np.unique(counts, return_counts=True))},
    }


def load_boxes(path, region, gauge="regauged"):
    """Box per punto dal registro del 3.1, gauge dell'emendamento 13.

    Non si riderivano qui: il gauge e' implementato in paper2_runner_fase3.py e
    una seconda implementazione sarebbe la classe di difetto del 445/313. Il
    fiduciale sta nel record del cancello D3, che ha gauge "fid".
    """
    out = {}
    with open(path, encoding="utf-8") as fh:
        for l in fh:
            if not l.strip():
                continue
            r = json.loads(l)
            if r.get("region") != region:
                continue
            if r.get("gate") == "d3" or r.get("gauge") == "fid":
                nm = "FID"
            elif r.get("gauge") == gauge:
                nm = r.get("point")
            else:
                continue
            if nm and "box_min" in r:
                out[nm] = {"box_min": np.asarray(r["box_min"], float),
                           "box_size": float(r["box_size"]),
                           "cell": float(r["cell"]),
                           "sigma_px": float(r["sigma_px"]),
                           "R_SMOOTH": float(r["R_SMOOTH"]),
                           "dc_c": float(r.get("c", 1.0))}
    return out


def cmd_tiling(a):
    G, M, setg, z_tab, dc_fid = attach(a.src, a.geom_module, a.const_module)
    boxes = load_boxes(a.boxes, a.region) if a.boxes else None
    if boxes is not None:
        costante = len({round(v["box_size"], 6) for v in boxes.values()}) == 1
        print("  [gauge] box letti da %s: %d punti, lato %s"
              % (a.boxes, len(boxes), "COSTANTE" if costante else "variabile"))
    plan = [("FID", dict(kind="fid"))]
    plan += [(n, dict(kind="ap", alpha_iso=al, F_ap=1.0)) for n, al in LINE_A]
    plan += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=F)) for n, F in LINE_B]
    plan += [(n, dict(kind="cosmo", omm=o, w0=w)) for n, o, w in CORNERS]
    if a.points:
        plan = [(n, s) for n, s in plan if n in a.points]

    print("=" * 72)
    print("1.5a — tiling per geometria, regione %s (L_box = %.1f)" % (a.region, a.l_box))
    print("=" * 72)
    rows = []
    try:
        for name, spec in plan:
            dc_pt = deform(z_tab, dc_fid, spec)
            if boxes is None:
                # Percorso storico: il cubo si deriva qui, con padding additivo.
                # E' il gauge a cubo VARIABILE, superato dall'emendamento 13.
                call_set(setg, z_tab=z_tab, dc_tab=dc_pt)
                ds = G.data_side(a.region)
                mask = find_mask(ds)
                if mask is None:
                    raise SystemExit("maschera non trovata")
                bmin = ds["box_min"]
                cell = float(ds["cell_size_mpc_h"])
                bsize = float(ds["box_size_mpc_h"])
            else:
                if name not in boxes:
                    print("  %-5s box assente nel registro, salto" % name)
                    continue
                b = boxes[name]
                # La tabella va riscalata di c, come al passo 3 del gauge: senza,
                # le posizioni non stanno nel cubo che si sta imponendo.
                call_set(setg, z_tab=z_tab, dc_tab=dc_pt * b["dc_c"])
                M.R_SMOOTH = b["R_SMOOTH"]
                call_set(setg, box_min=b["box_min"], box_size=b["box_size"])
                e = abs(float(M.SIGMA_PX) - b["sigma_px"]) / b["sigma_px"]
                if e > 1e-9:
                    raise SystemExit(
                        "[FATAL] %s: sigma_px %r contro %r nel registro (rel %.2e). "
                        "Il box letto non e' quello che il 3.1 ha usato."
                        % (name, float(M.SIGMA_PX), b["sigma_px"], e))
                pos_r, w_r = G.positions(a.region, "ran")
                field_r = M.cic_3d(pos_r, w_r, M.NGRID, M.BOX_MIN, M.BOX_SIZE)
                out_m = G.build_mask(field_r, "v1_fullcube")
                mask = out_m[0] if isinstance(out_m, tuple) else out_m
                del pos_r, w_r, field_r
                bmin, cell, bsize = b["box_min"], b["cell"], b["box_size"]
            st = tiling_stats(mask, bmin, cell, a.l_box)
            st.update({"schema": "paper2_item15a_v1", "region": a.region,
                       "point": name, "utc": _now(),
                       "gauge": "amend13" if boxes is not None else "cubo_variabile",
                       "box_size_mpc_h": float(bsize),
                       "cell_size_mpc_h": float(cell)})
            st.update(spec)
            rows.append(st)
            if a.out:
                append_atomic(a.out, st)
            print("  %-5s L=%9.3f  repliche %s tot=%2d  indip=%.4f  mult media=%.4f max=%d"
                  % (name, st["box_size_mpc_h"], st["replicas_per_axis"],
                     st["n_replicas_total"], st["independent_fraction"],
                     st["mult_mean"], st["mult_max"]))
            if name == "FID" and a.region == "NGC":
                f = FROZEN_TILING_NGC
                got_c, got_v = st["distinct_box_cells"], st["n_voxel"]
                exact = (got_c == f["distinct_box_cells"]
                         and got_v == f["in_survey_voxels"]
                         and st["mult_max"] == f["mult_max"])
                print("        cancello M26 §5.6: celle distinte %d atteso %d | "
                      "voxel %d atteso %d | mult max %d atteso %d"
                      % (got_c, f["distinct_box_cells"], got_v,
                         f["in_survey_voxels"], st["mult_max"], f["mult_max"]))
                print("        indip %.8f atteso %.8f   mult media %.6f atteso %.6f"
                      % (st["independent_fraction"], f["independent_fraction"],
                         st["mult_mean"], f["mult_mean"]))
                if not exact:
                    # All'unita', non entro una tolleranza: e' un conteggio di
                    # celle, non una misura, e uno scarto qui significa che il
                    # binning o la maschera non sono quelli che hanno prodotto
                    # i numeri pubblicati.
                    raise SystemExit(
                        "[FATAL] il fiduciale NGC non riproduce M26 §5.6 "
                        "all'unita' (celle %d/%d, voxel %d/%d). Non uso questi "
                        "numeri per la griglia." % (got_c, f["distinct_box_cells"],
                                                    got_v, f["in_survey_voxels"]))
                print("        -> riprodotto all'unita'.")
    finally:
        call_set(setg, z_tab=z_tab, dc_tab=dc_fid)
        try:
            G.data_side(a.region, verbose=False)
        except Exception:
            pass
        print("\n[restore] geometria fiduciale ripristinata.")

    if rows:
        print("\n" + "=" * 72)
        print("IL GRADINO — cambia il numero di repliche attraverso la griglia?")
        print("=" * 72)
        tot = sorted({r["n_replicas_total"] for r in rows})
        print("  valori distinti di repliche totali: %s" % tot)
        if len(tot) > 1:
            for t in tot:
                who = [r["point"] for r in rows if r["n_replicas_total"] == t]
                print("    %2d repliche: %s" % (t, " ".join(who)))
            bl = [r for r in rows if str(r.get("point", "")).startswith("B")]
            if bl and len({r["n_replicas_total"] for r in bl}) > 1:
                print("\n  !! IL GRADINO ATTRAVERSA LA LINEA B.")
                print("     L'immunita' del blocco B al tiling, affermata nel canovaccio,")
                print("     NON vale in questa regione: il lato del cubo e' fissato da")
                print("     alpha_box, non da alpha_iso, e alpha_box varia lungo B.")
                print("     Il disegno dell'item 1.3 va corretto per %s." % a.region)
        else:
            print("  nessun gradino: il numero di repliche e' costante sulla griglia.")
        sp = [(r["point"], r["independent_fraction"]) for r in rows]
        sp.sort(key=lambda kv: kv[1])
        print("\n  frazione indipendente: da %.4f (%s) a %.4f (%s), escursione %.1f%%"
              % (sp[0][1], sp[0][0], sp[-1][1], sp[-1][0],
                 100 * (sp[-1][1] / sp[0][1] - 1)))


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--const-module", default="phase8_cutsky_mocks")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("conv")
    c.add_argument("--f-test", type=float, default=1.03)
    c.add_argument("--z-pivot", type=float, default=0.25)
    c.add_argument("--out", default=None)
    t = sub.add_parser("tiling")
    t.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    t.add_argument("--l-box", type=float, default=L_BOX_DEFAULT)
    t.add_argument("--points", nargs="*", default=None)
    t.add_argument("--out", default=None)
    t.add_argument("--boxes", default=None,
                   help="registro del 3.1 da cui leggere i box del gauge "
                        "dell'emendamento 13, invece di derivarli qui")
    a = p.parse_args()
    {"conv": cmd_conv, "tiling": cmd_tiling}[a.cmd](a)


if __name__ == "__main__":
    main()
