#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_fig_F1.py -- Figura F1 del Paper 2: residuo anisotropo delle deformazioni della griglia.

Disegna, per ogni geometria della linea B (B1, B2, B4, B5, B6) e per i quattro angoli (C1..C4), il
residuo u(r) = (f(r) - alpha_mm * r) / cella, in voxel, contro la distanza comovente sull'intervallo
di redshift della survey; alpha_mm e' l'alpha minimax della stessa `deform` che ha costruito la
griglia. Due pannelli, NGC e SGC, ciascuno nelle proprie unita' di voxel, con la linea del padding
(5.0 h^-1 Mpc) e, come riferimento inferiore, la banda del residuo di implementazione misurato sul
blocco A (Prop. 2').

Scrive, e non tocca altro:
  papers/paper2/MNRAS/figures/F1_anisotropic_residual.pdf     (metadati senza data: deterministico)
  results/paper2/fig_F1.jsonl                                 (append-only, un record per run)
Il registro porta, per punto: residuo minimax CALCOLATO (voxel NGC e SGC) e spostamento di griglia
MISURATO (grid_shift_vs_fid.max di results/paper2/fase3.jsonl, gauge 'regauged'), col loro rapporto.

Cancelli prima di disegnare (la macchina deve riprodurre il depositato e il registrato):
  residuo di B4 = 0.2844 voxel NGC (protocollo §4; stessa tolleranza 0.002 di paper2_append_amend15.py);
  B6 = 0.8531 voxel NGC (record 15);
  B1, B2, B4, B5 e C1..C4 in h^-1 Mpc contro anis_residual_minimax_hMpc di item12a_geom_NGC.jsonl
  (tolleranza 0.03 h^-1 Mpc, cioe' 0.002 voxel). In h^-1 Mpc e non in voxel: quel registro divide
  per la cella del gauge a cubo VARIABILE (alpha_box * cella), e cosi' la colonna in voxel degli
  angoli nel protocollo §4 (0.5409, 0.1067, 0.1325, 0.3729). Nel gauge a cubo costante gli stessi
  residui valgono 0.569, 0.105, 0.135, 0.360 voxel.

Sottocomandi: selftest | run | verify. Dalla radice del repository.
"""
import argparse
import hashlib
import json
import os
import sys
from datetime import datetime, timezone

import numpy as np

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:  # pragma: no cover
    pass

J = os.path.join
FASE3 = J("results", "paper2", "fase3.jsonl")
ITEM12A = J("results", "paper2", "item12a_geom_NGC.jsonl")
REG = J("results", "paper2", "fig_F1.jsonl")
PDF = J("papers", "paper2", "MNRAS", "figures", "F1_anisotropic_residual.pdf")
MOD_TABLE = "phase8_cutsky_mocks"      # _Z_TAB, _DC_TAB: la tabella fiduciale di produzione
MOD_GRID = "paper2_item13a_15a"        # deform, minimax_alpha, ZMIN, ZMAX, LINE_B, CORNERS
PAD = 5.0                              # h^-1 Mpc, padding fiduciale
TOL = 0.002                            # le cifre depositate sono quattro

DEPOSITED_NGC = {"B4": 0.2844, "B6": 0.8531}           # voxel, cella fiduciale (costante)
TOL_MPC = 0.03                                          # h^-1 Mpc, pari a 0.002 voxel
CORNER_KEY = {"C1": (0.25, -1.2), "C2": (0.25, -0.8), "C3": (0.35, -1.2), "C4": (0.35, -0.8)}
LINE = ("B1", "B2", "B4", "B5", "B6")
CORNER = ("C1", "C2", "C3", "C4")
BLOCK_A = ("A0", "A0m", "A1", "A1m", "A3", "A3m")


class F1Error(Exception):
    pass


# ----------------------------------------------------------------------------- calcolo

def minimax_alpha(r, f):
    """Stessa bisezione di paper2_item13a_15a.minimax_alpha (usata nel selftest)."""
    g = f / r
    lo, hi = float(g.min()), float(g.max())
    if hi - lo < 1e-15:
        return 0.5 * (lo + hi)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        d = r * (mid - g)
        if float(d.max()) - float((-d).max()) > 0.0:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def residual_curve(I13, z, dc, spec, cell):
    """(r, u) sull'intervallo della survey: u = (f - alpha_mm r)/cell, e il suo massimo modulo."""
    f = np.asarray(I13.deform(z, dc, spec), float)
    m = (z >= I13.ZMIN) & (z <= I13.ZMAX)
    r, fm = dc[m], f[m]
    al = I13.minimax_alpha(r, fm)
    u = (fm - al * r) / cell
    return r, u, float(np.max(np.abs(u))), float(al)


def gate(name, got, want, tol=TOL):
    if abs(got - want) > tol:
        raise F1Error("cancello %s: la macchina da' %.4f voxel contro %.4f depositati (tolleranza %.3f); "
                      "non disegno con un codice che non riproduce il depositato" % (name, got, want, tol))


def read_fase3(text):
    """Per punto e regione, dal gauge 'regauged': F_ap, sigma_px, spostamento misurato. Unione, non 'ultimo'."""
    out = {}
    for i, riga in enumerate(text.splitlines(), 1):
        if not riga.strip():
            continue
        r = json.loads(riga)
        if r.get("gauge") not in ("regauged", "fid"):
            continue
        key = (r["region"], r["point"])
        val = {"F_ap": r.get("F_ap"), "sigma_px": r.get("sigma_px"),
               "grid_shift": (r.get("grid_shift_vs_fid") or {}).get("max")}
        if key in out and out[key] != val:
            raise F1Error("fase3.jsonl riga %d: %s compare con valori diversi (%r contro %r)" % (i, key, out[key], val))
        out[key] = val
    return out


def read_item12a(text):
    """Residuo minimax in h^-1 Mpc per punto: le chiavi sono il nome (B) o (omm, w0) (angoli)."""
    out = {}
    for riga in text.splitlines():
        if not riga.strip():
            continue
        r = json.loads(riga)
        if r.get("block") == "ap":
            key = r["point"]
        elif r.get("block") == "cosmo":
            key = (round(float(r["omm"]), 4), round(float(r["w0"]), 4))
        else:
            continue
        v = float(r["anis_residual_minimax_hMpc"])
        if key in out and abs(out[key] - v) > 1e-9:
            raise F1Error("item12a_geom: %r con due valori (%r, %r)" % (key, out[key], v))
        out[key] = v
    return out


def cells_from(f3):
    cells = {}
    for reg in ("NGC", "SGC"):
        sp = {v["sigma_px"] for (rg, _), v in f3.items() if rg == reg and v["sigma_px"] is not None}
        if len(sp) != 1:
            raise F1Error("sigma_px non unico in %s: %r (il gauge a cubo costante lo vuole identico)" % (reg, sp))
        cells[reg] = 5.0 / sp.pop()       # sigma_px = R / cella, R = 5 h^-1 Mpc
    return cells


def compute(I13, z, dc, f3, i12):
    cells = cells_from(f3)
    specs = {}
    for name, F in I13.LINE_B:
        specs[name] = dict(kind="ap", alpha_iso=1.0, F_ap=float(F))
    b6 = {v["F_ap"] for (rg, p), v in f3.items() if p == "B6"}
    if len(b6) != 1:
        raise F1Error("F_ap di B6 non univoco in fase3.jsonl: %r" % b6)
    specs["B6"] = dict(kind="ap", alpha_iso=1.0, F_ap=float(b6.pop()))
    for name, omm, w0 in I13.CORNERS:
        specs[name] = dict(kind="cosmo", omm=float(omm), w0=float(w0))
    curves, points = {}, {}
    for name in LINE + CORNER:
        if name not in specs:
            raise F1Error("punto %s assente dalla griglia di %s" % (name, MOD_GRID))
        rec = {"spec": specs[name]}
        for reg in ("NGC", "SGC"):
            r, u, umax, al = residual_curve(I13, z, dc, specs[name], cells[reg])
            rec["residual_minimax_hMpc"] = umax * cells[reg]
            curves[(reg, name)] = (r, u)
            rec["alpha_minimax"] = al
            rec["residual_minimax_voxel_" + reg] = umax
            gs = f3.get((reg, name), {}).get("grid_shift")
            rec["grid_shift_measured_voxel_" + reg] = gs
            rec["measured_over_minimax_" + reg] = (gs / umax) if (gs is not None and umax > 0) else None
        points[name] = rec
    for name, want in DEPOSITED_NGC.items():
        gate(name, points[name]["residual_minimax_voxel_NGC"], want)
    for name in ("B1", "B2", "B4", "B5") + CORNER:
        key = CORNER_KEY.get(name, name)
        if key not in i12:
            raise F1Error("item12a_geom_NGC.jsonl: manca %r" % (key,))
        gate(name + " [h^-1 Mpc]", points[name]["residual_minimax_hMpc"], i12[key], tol=TOL_MPC)
    block_a = {}
    for reg in ("NGC", "SGC"):
        vals = [f3[(reg, p)]["grid_shift"] for p in BLOCK_A if (reg, p) in f3 and f3[(reg, p)]["grid_shift"] is not None]
        if len(vals) != len(BLOCK_A):
            raise F1Error("blocco A incompleto in %s: %d punti su %d" % (reg, len(vals), len(BLOCK_A)))
        block_a[reg] = max(vals)
    return cells, curves, points, block_a


# ----------------------------------------------------------------------------- figura

def draw(cells, curves, block_a, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    stili = {"B1": ("-", 1.2), "B2": ("-", 0.8), "B4": ("--", 0.8), "B5": ("--", 1.2), "B6": ("-.", 1.2),
             "C1": (":", 1.2), "C2": (":", 0.8), "C3": (":", 0.8), "C4": (":", 1.2)}
    fig, axes = plt.subplots(2, 1, figsize=(3.4, 4.6), sharex=True)
    for ax, reg in zip(axes, ("NGC", "SGC")):
        pad = PAD / cells[reg]
        ax.axhspan(-block_a[reg], block_a[reg], color="0.85", lw=0)
        for s in (+1, -1):
            ax.axhline(s * pad, color="0.3", lw=0.7, ls=(0, (6, 3)))
        for name in LINE + CORNER:
            r, u = curves[(reg, name)]
            ls, lw = stili[name]
            ax.plot(r, u, ls=ls, lw=lw, color="k")
            ax.annotate(name, (r[-1], u[-1]), xytext=(2, 0), textcoords="offset points",
                        fontsize=6, va="center")
        ax.set_ylabel(r"$u$ [voxel, %s]" % reg, fontsize=8)
        ax.tick_params(labelsize=7)
        ax.text(0.02, 0.92, reg, transform=ax.transAxes, fontsize=8, va="top")
    axes[-1].set_xlabel(r"comoving distance [$h^{-1}\,$Mpc]", fontsize=8)
    fig.tight_layout(h_pad=0.4)
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    fig.savefig(path, metadata={"CreationDate": None, "ModDate": None, "Creator": "paper2_fig_F1.py",
                                "Producer": None})
    plt.close(fig)


# ----------------------------------------------------------------------------- disco

def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest()


def attach(srcdir="src"):
    if srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    try:
        M = __import__(MOD_TABLE)
        I13 = __import__(MOD_GRID)
    except Exception as e:
        raise F1Error("impossibile importare %s / %s da %s: %s" % (MOD_TABLE, MOD_GRID, srcdir, e))
    z = np.asarray(M._Z_TAB, float).copy()
    dc = np.asarray(M._DC_TAB, float).copy()
    return I13, z, dc


def cmd_run():
    if not (os.path.isdir("src") and os.path.isdir("results") and os.path.isdir("papers")):
        raise F1Error("lanciare dalla radice del repository")
    I13, z, dc = attach()
    f3 = read_fase3(open(FASE3, encoding="utf-8").read())
    i12 = read_item12a(open(ITEM12A, encoding="utf-8").read())
    cells, curves, points, block_a = compute(I13, z, dc, f3, i12)
    draw(cells, curves, block_a, PDF)
    rec = {"schema": "paper2_fig_F1_v1", "utc": datetime.now(timezone.utc).isoformat(),
           "inputs": {FASE3: sha_file(FASE3), ITEM12A: sha_file(ITEM12A),
                      J("src", MOD_TABLE + ".py"): sha_file(J("src", MOD_TABLE + ".py")),
                      J("src", MOD_GRID + ".py"): sha_file(J("src", MOD_GRID + ".py")),
                      J("src", "paper2_fig_F1.py"): sha_file(J("src", "paper2_fig_F1.py"))},
           "cells": cells, "pad_voxel": {k: PAD / v for k, v in cells.items()},
           "block_A_max_grid_shift_voxel": block_a, "points": points,
           "gates": {k: {"deposited": v, "computed": points[k]["residual_minimax_voxel_NGC"]}
                     for k, v in DEPOSITED_NGC.items()},
           "pdf": {PDF: sha_file(PDF)}}
    with open(REG, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(rec, ensure_ascii=False, sort_keys=True) + "\n")
    print("cancelli: %d/%d PASS" % (len(DEPOSITED_NGC) + 8, len(DEPOSITED_NGC) + 8))
    for p in LINE + CORNER:
        q = points[p]
        print("%-3s minimax %.3f h-1Mpc = %.4f / %.4f voxel  misurato %s / %s  rapporto %s / %s" % (
            p, q["residual_minimax_hMpc"], q["residual_minimax_voxel_NGC"], q["residual_minimax_voxel_SGC"],
            _f(q["grid_shift_measured_voxel_NGC"]), _f(q["grid_shift_measured_voxel_SGC"]),
            _f(q["measured_over_minimax_NGC"], 3), _f(q["measured_over_minimax_SGC"], 3)))
    print("blocco A (massimo dello spostamento misurato): NGC %.4f, SGC %.4f" % (block_a["NGC"], block_a["SGC"]))
    print("figura: %s  sha %s" % (PDF, rec["pdf"][PDF][:12]))
    print("ESITO: SCRITTA")


def _f(x, n=4):
    return "-" if x is None else ("%." + str(n) + "f") % x


def cmd_verify():
    if not os.path.exists(REG) or not os.path.exists(PDF):
        raise F1Error("registro o figura assenti: lanciare 'run'")
    h = sha_file(PDF)
    recs = [json.loads(l) for l in open(REG, encoding="utf-8") if l.strip()]
    match = [r for r in recs if r.get("pdf", {}).get(PDF) == h]
    if not match:
        raise F1Error("la figura su disco (%s) non corrisponde a nessun record del registro" % h[:12])
    f3h = sha_file(FASE3)
    stale = [r for r in match if r["inputs"].get(FASE3) != f3h]
    print("record che descrivono la figura: %d; ingresso fase3.jsonl invariato: %s" % (len(match), "si'" if not stale else "NO"))
    print("ESITO: %s" % ("PASS" if not stale else "FAIL"))
    return 0 if not stale else 1


# ----------------------------------------------------------------------------- selftest

def _t_minimax():
    r = np.linspace(300.0, 1080.0, 2001)
    f = r ** (1 / 1.03) * 1.2
    al = minimax_alpha(r, f)
    d = f - al * r
    return abs(d.max() + d.min()) < 1e-9 * abs(d).max()


class _FakeI13:
    ZMIN, ZMAX = 0.10, 0.40
    LINE_B = [("B1", 0.97107), ("B2", 0.985396), ("B4", 1.014889), ("B5", 1.030071)]
    CORNERS = [("C1", 0.25, -1.2), ("C2", 0.25, -0.8), ("C3", 0.35, -1.2), ("C4", 0.35, -0.8)]
    minimax_alpha = staticmethod(minimax_alpha)

    @staticmethod
    def deform(z, dc, spec):
        if spec["kind"] == "ap":
            if abs(spec["F_ap"] - 1) < 1e-12:
                return dc.copy()
            return dc ** (1 / spec["F_ap"])
        return dc * (1 + 0.1 * (spec["omm"] - 0.3) * z)


def _t_identita():
    z = np.linspace(0, 0.5, 501)
    dc = 3000 * z
    _, _, umax, _ = residual_curve(_FakeI13, z, dc, dict(kind="ap", alpha_iso=1.0, F_ap=1.0), 15.6)
    return umax < 1e-12


def _t_padding():
    return abs(PAD / (5.0 / 0.32042249039652254) - 0.32042249039652254) < 1e-15


def _t_cancello():
    try:
        gate("B4", 0.2900, 0.2844)
    except F1Error:
        pass
    else:
        return False
    gate("B4", 0.2850, 0.2844)
    return True


def _righe(extra=()):
    rs = [{"region": reg, "point": "FID", "gauge": "fid", "sigma_px": s} for reg, s in (("NGC", 0.32), ("SGC", 0.336))]
    for reg, s in (("NGC", 0.32), ("SGC", 0.336)):
        for p in LINE + CORNER + BLOCK_A:
            F = 1.0455 if p == "B6" else None
            rs.append({"region": reg, "point": p, "gauge": "regauged", "sigma_px": s, "F_ap": F,
                       "grid_shift_vs_fid": {"max": 0.01 if p in BLOCK_A else 0.5}})
    rs += list(extra)
    return "\n".join(json.dumps(r) for r in rs) + "\n"


def _t_unione():
    f3 = read_fase3(_righe())
    ok = len(f3) == 2 * (1 + len(LINE + CORNER + BLOCK_A)) and cells_from(f3)["NGC"] == 5.0 / 0.32
    dup = {"region": "NGC", "point": "B1", "gauge": "regauged", "sigma_px": 0.32, "F_ap": None,
           "grid_shift_vs_fid": {"max": 0.7}}
    try:
        read_fase3(_righe([dup]))
    except F1Error:
        return ok
    return False


def _t_sigma_non_unico():
    bad = {"region": "NGC", "point": "B2", "gauge": "regauged", "sigma_px": 0.33, "F_ap": None,
           "grid_shift_vs_fid": {"max": 0.5}}
    t = _righe().replace('"point": "B2", "gauge": "regauged", "sigma_px": 0.32', '"point": "B2", "gauge": "regauged", "sigma_px": 0.33', 1)
    try:
        cells_from(read_fase3(t))
    except F1Error:
        return True
    return False


def _t_pdf_deterministico():
    try:
        import matplotlib  # noqa: F401
    except Exception:
        return True   # senza matplotlib il run fallirebbe comunque in modo esplicito
    import tempfile
    d = tempfile.mkdtemp(prefix="st_f1_")
    r = np.linspace(300, 1080, 50)
    cells = {"NGC": 15.6, "SGC": 14.9}
    curves = {(reg, p): (r, np.sin(r / 100) * 0.1) for reg in cells for p in LINE + CORNER}
    a, b = J(d, "a.pdf"), J(d, "b.pdf")
    draw(cells, curves, {"NGC": 0.014, "SGC": 0.014}, a)
    draw(cells, curves, {"NGC": 0.014, "SGC": 0.014}, b)
    return open(a, "rb").read() == open(b, "rb").read()


def _t_item12a():
    t = "\n".join(json.dumps(r) for r in [
        {"block": "ap", "point": "B1", "anis_residual_minimax_hMpc": 8.87},
        {"block": "cosmo", "omm": 0.25, "w0": -1.2, "anis_residual_minimax_hMpc": 8.87},
        {"block": "fid", "point": "FID", "anis_residual_minimax_hMpc": 0.0}]) + "\n"
    d = read_item12a(t)
    ok = d == {"B1": 8.87, (0.25, -1.2): 8.87}
    try:
        read_item12a(t + json.dumps({"block": "ap", "point": "B1", "anis_residual_minimax_hMpc": 8.9}) + "\n")
    except F1Error:
        return ok
    return False


TESTS = [
    ("minimax: estremi positivo e negativo uguali", _t_minimax),
    ("deformazione identica -> residuo nullo", _t_identita),
    ("padding in voxel = sigma_px (R = padding = 5)", _t_padding),
    ("cancello: scarto oltre tolleranza -> errore, entro -> passa", _t_cancello),
    ("fase3: lettura per unione; stesso punto con valori diversi -> errore", _t_unione),
    ("sigma_px non unico in una regione -> errore", _t_sigma_non_unico),
    ("PDF deterministico: due salvataggi, byte identici", _t_pdf_deterministico),
    ("item12a: residui in h^-1 Mpc per nome e per (omm, w0); doppione diverso -> errore", _t_item12a),
]


def selftest():
    ok = 0
    for nome, fn in TESTS:
        try:
            esito = bool(fn())
        except Exception as e:
            esito = False
            nome += " [%s: %s]" % (type(e).__name__, e)
        ok += esito
        if not esito:
            print("  FAIL  " + nome)
    print("selftest: %d/%d %s" % (ok, len(TESTS), "PASS" if ok == len(TESTS) else "FAIL"))
    return ok == len(TESTS)


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("comando", choices=["selftest", "run", "verify"])
    a = ap.parse_args()
    try:
        if a.comando == "selftest":
            return 0 if selftest() else 1
        if a.comando == "run":
            if not selftest():
                raise F1Error("selftest non superato")
            cmd_run()
            return 0
        return cmd_verify()
    except F1Error as e:
        print("ERRORE: %s" % e)
        print("ESITO: FALLITO")
        return 2


if __name__ == "__main__":
    sys.exit(main())
