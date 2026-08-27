#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_probe_randoms2.py — perche' il box non torna

La sonda 1 ha stabilito che positions() funziona ma restituisce comoventi, e che
il lato del cubo ricostruito (1975.36) non riproduce il valore congelato (1997.36).
Questa sonda separa le ipotesi.

Domande, in ordine:
  Q1  quali token di `kind` accetta positions(), e quante righe restituisce ciascuno?
      (217 614 sono poche per un catalogo random: sospetto di aver ricevuto i dati)
  Q2  positions() applica un taglio in z di default?  Confronto con zmin/zmax espliciti.
  Q3  derive_box() del modulo che lato produce, sulle stesse posizioni?
      Questo usa la REGOLA VERA (phase6_bgs_voxelize.py:166-168), non la mia.
  Q4  da quali file legge?  Anatomia del sorgente attorno a .ran.fits / .dat.fits.
  Q5  quali file DESI esistono davvero sul disco?  (filtri corretti: .ran.fits, .dat.fits)

**Sola lettura.**  Non scrive nulla.  Carica cataloghi, quindi non e' istantanea.
Non tocca results/paper1/: sono ingressi di v1.

Uso (da D:\\projects\\cauchy):
    python src\\paper2_probe_randoms2.py --region NGC
    python src\\paper2_probe_randoms2.py --region NGC --data-side   # piu' lento
"""

from __future__ import annotations

import argparse
import importlib
import inspect
import os
import re
import sys

import numpy as np

FROZEN_L = {"NGC": 1997.36, "SGC": 14.88 * 128}
PAD = 5.0
NGRID = 128
KIND_TOKENS = ["ran", "dat", "randoms", "random", "rand", "R", "data", "galaxies", "D"]

DESI_HINTS = (".ran.fits", ".dat.fits", "clustering", "random", "rand", "_ran")
SKIP_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".idea"}


def human(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024 or u == "TB":
            return "%.1f %s" % (n, u)
        n /= 1024.0


def as_positions(out):
    """positions() restituisce (pos, w) oppure pos.  Normalizza."""
    if isinstance(out, tuple):
        pos = np.asarray(out[0])
        w = np.asarray(out[1]) if len(out) > 1 else None
    else:
        pos, w = np.asarray(out), None
    return pos, w


def describe(pos, w, label=""):
    ext = pos.max(axis=0) - pos.min(axis=0)
    k = int(np.argmax(ext))
    second = float(np.partition(ext, -2)[-2])
    print("      %sN=%d  estensioni=[%.2f, %.2f, %.2f]  dominante=%s (%.2f)  margine=%.1f%%"
          % (label, len(pos), ext[0], ext[1], ext[2], "xyz"[k], ext[k],
             100 * (ext[k] / second - 1)))
    print("      %sL(max+2*%.1f) = %.2f" % (label, PAD, ext[k] + 2 * PAD))
    if w is not None:
        print("      %spesi: min=%.4f max=%.4f media=%.4f somma=%.4g"
              % (label, w.min(), w.max(), w.mean(), w.sum()))
    return float(ext[k])


# ------------------------------------------------------------------ Q1

def q1_kinds(mod, region, tokens=None):
    print("\n[Q1] token di `kind` accettati, e quante righe danno")
    results = {}
    for tok in (tokens or KIND_TOKENS):
        try:
            out = mod.positions(region, tok)
        except Exception as exc:
            print("    kind=%-10s -> %s: %s" % (tok, type(exc).__name__, str(exc)[:80]))
            continue
        pos, w = as_positions(out)
        print("    kind=%-10s OK" % tok)
        ext = describe(pos, w, "  ")
        results[tok] = (len(pos), ext)
        del pos, w, out
    print()
    if results:
        n_by = sorted(results.items(), key=lambda kv: -kv[1][0])
        print("    riepilogo, dal piu' numeroso:")
        for tok, (n, ext) in n_by:
            print("      %-10s N=%9d  ext_max=%.2f" % (tok, n, ext))
        big = [t for t, (n, _) in results.items() if n == n_by[0][1][0]]
        if len(set(n for n, _ in results.values())) == 1:
            print("    !! tutti i token danno lo STESSO N: `kind` probabilmente ignorato,")
            print("       oppure normalizzato internamente.  Guardare il sorgente (Q4).")
        elif len(big) == 1:
            print("    -> solo %r restituisce i random; tutti gli altri cadono nel ramo"
                  % big[0])
            print("       else e restituiscono i DATI, senza errore.  Usare sempre %r."
                  % big[0])
    return results


# ------------------------------------------------------------------ Q2

def q2_zcut(mod, region, kind):
    print("\n[Q2] taglio in z: default contro esplicito")
    try:
        p0, w0 = as_positions(mod.positions(region, kind))
    except Exception as exc:
        print("    chiamata base fallita: %s" % exc)
        return
    e0 = describe(p0, w0, "default          ")
    for zmin, zmax in ((0.1, 0.4), (0.0, 10.0)):
        try:
            p1, w1 = as_positions(mod.positions(region, kind, zmin=zmin, zmax=zmax))
        except Exception as exc:
            print("    zmin=%.2f zmax=%.2f -> %s: %s" % (zmin, zmax, type(exc).__name__, exc))
            continue
        print("    zmin=%.2f zmax=%.2f:" % (zmin, zmax))
        e1 = describe(p1, w1, "  ")
        if len(p1) == len(p0):
            print("      -> stesso N del default")
        else:
            print("      -> N cambia di %+d rispetto al default (%.2f%%)"
                  % (len(p1) - len(p0), 100.0 * (len(p1) - len(p0)) / len(p0)))
        print("      -> lato: %.2f contro %.2f del default (scarto %.2f)"
              % (e1 + 2 * PAD, e0 + 2 * PAD, (e1 - e0)))
        del p1, w1


# ------------------------------------------------------------------ Q3

def q3_derive_box(mod, region, kind):
    print("\n[Q3] derive_box() del modulo — la regola vera")
    try:
        pos, _ = as_positions(mod.positions(region, kind))
    except Exception as exc:
        print("    positions() fallita: %s" % exc)
        return
    try:
        box = mod.derive_box(pos, pad=PAD)
    except TypeError:
        box = mod.derive_box(pos)
    print("    tipo restituito: %s" % type(box).__name__)
    if isinstance(box, dict):
        for k, v in box.items():
            print("      %-14s %s" % (k, v))
    elif isinstance(box, tuple):
        for i, v in enumerate(box):
            print("      [%d] %s" % (i, np.asarray(v).ravel()[:6]))
    else:
        print("      %s" % (np.asarray(box).ravel()[:8],))

    # confronto esplicito col congelato
    L = extract_L(box)
    ref = FROZEN_L.get(region)
    print()
    if L is None:
        print("    non sono riuscito a estrarre un lato scalare dal risultato.")
        print("    -> riportare l'output qui sopra cosi' com'e'.")
    else:
        print("    lato dal modulo : %.4f" % L)
        print("    lato congelato  : %.4f" % ref)
        print("    scarto          : %+.4f   (dx: %.5f contro %.5f)"
              % (L - ref, L / NGRID, ref / NGRID))
        if abs(L - ref) < 0.05:
            print("    -> COERENTE.  L'item 1.2a puo' partire con questo kind.")
        else:
            print("    -> INCOERENTE.  Non produrre numeri finche' non e' spiegato.")
            pad_eq = (ref - (L - 2 * PAD)) / 2
            if 0.0 < pad_eq < 60.0:
                print("       pad che riprodurrebbe il congelato: %.4f" % pad_eq)
            else:
                print("       lo scarto e' troppo grande per essere padding "
                      "(richiederebbe pad=%.1f): e' il campione, non il bordo." % pad_eq)
    for p in (5.0, 10.0, 15.6044, 16.0):
        try:
            b = mod.derive_box(pos, pad=p)
            LL = extract_L(b)
            if LL is not None:
                print("      pad=%-8.4f -> L=%.4f  (scarto dal congelato %+.4f)"
                      % (p, LL, LL - ref))
        except Exception:
            pass


def extract_L(box):
    if isinstance(box, dict):
        for k in ("L", "box_size", "side", "L_box", "size"):
            if k in box:
                v = np.asarray(box[k]).ravel()
                return float(v[0])
    elif isinstance(box, tuple):
        for v in box:
            a = np.asarray(v).ravel()
            if a.size == 1:
                return float(a[0])
            if a.size == 3 and np.allclose(a, a[0]):
                return float(a[0])
    else:
        a = np.asarray(box).ravel()
        if a.size == 1:
            return float(a[0])
    return None


# ------------------------------------------------------------------ Q4

def q4_source(src_file):
    print("\n[Q4] anatomia del sorgente: da dove legge")
    if not src_file or not os.path.exists(src_file):
        print("    sorgente non disponibile")
        return
    with open(src_file, "r", encoding="utf-8", errors="replace") as fh:
        lines = fh.read().splitlines()
    keys = ("ran.fits", "dat.fits", "clustering", "base", "glob", "Table.read",
            "fitsio", "fits.open", "os.path.join", "DATA_DIR", "def positions")
    shown = set()
    for i, line in enumerate(lines):
        if any(k in line for k in keys):
            lo, hi = max(0, i - 2), min(len(lines), i + 3)
            for j in range(lo, hi):
                if j not in shown:
                    print("    %4d: %s" % (j + 1, lines[j][:110]))
                    shown.add(j)
            print("    " + "-" * 60)
            if len(shown) > 90:
                print("    ... (troncato)")
                return


# ------------------------------------------------------------------ Q5

def q5_disk(roots):
    print("\n[Q5] file DESI sul disco (filtri corretti)")
    hits, seen = [], set()
    for root in roots:
        if not os.path.isdir(root):
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            if os.path.abspath(dirpath).replace("\\", "/").endswith("results/paper1"):
                continue
            for fn in filenames:
                low = fn.lower()
                if not any(h in low for h in DESI_HINTS):
                    continue
                p = os.path.join(dirpath, fn)
                ap = os.path.abspath(p)
                if ap in seen:
                    continue
                seen.add(ap)
                try:
                    hits.append((os.path.getsize(p), p))
                except OSError:
                    pass
    hits.sort(reverse=True)
    if not hits:
        print("    nessuno")
    for sz, p in hits[:40]:
        tag = "  <-- BOSS DR12, e' del Paper 3" if "dr12" in p.lower() else ""
        print("    %10s  %s%s" % (human(sz), p, tag))
    if len(hits) > 40:
        print("    ... altri %d" % (len(hits) - 40))


# ------------------------------------------------------------------ main

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--module", default="paper2_data_geometry")
    ap.add_argument("--src", default="src")
    ap.add_argument("--region", default="NGC")
    ap.add_argument("--kind", default="ran",
                    help="token per Q2/Q3.  DEVE essere 'ran' per i random: nel modulo "
                         "qualunque altro valore cade nel ramo else e restituisce i DATI")
    ap.add_argument("--roots", nargs="*", default=["."])
    ap.add_argument("--kinds", nargs="*", default=None,
                    help="limita i token provati in Q1 (ognuno ricarica il catalogo)")
    ap.add_argument("--data-side", action="store_true",
                    help="chiama anche data_side(region): piu' lento, ma decisivo")
    a = ap.parse_args()

    if a.src not in sys.path:
        sys.path.insert(0, a.src)
    mod = importlib.import_module(a.module)
    print("=" * 70)
    print("paper2_probe_randoms2 — regione %s — sola lettura" % a.region)
    print("modulo: %s" % getattr(mod, "__file__", "?"))
    print("congelato: L=%.2f  dx=%.5f" % (FROZEN_L[a.region], FROZEN_L[a.region] / NGRID))
    print("=" * 70)
    print("\n[0] firma di positions(): %s" % inspect.signature(mod.positions))

    q1_kinds(mod, a.region, a.kinds)
    q2_zcut(mod, a.region, a.kind)
    q3_derive_box(mod, a.region, a.kind)
    q4_source(getattr(mod, "__file__", None))
    q5_disk(a.roots)

    if a.data_side:
        print("\n[Q6] data_side(%r)" % a.region)
        try:
            d = mod.data_side(a.region)
        except Exception as exc:
            print("    fallita: %s: %s" % (type(exc).__name__, exc))
        else:
            for k, v in (d.items() if isinstance(d, dict) else []):
                try:
                    arr = np.asarray(v)
                except Exception:
                    # valore ragged: tipicamente la tupla dei campi voxelizzati
                    try:
                        parts = ["%s%s" % (np.shape(e), getattr(e, "dtype", ""))
                                 for e in v]
                        print("    %-22s <sequenza di %d: %s>"
                              % (k, len(v), "; ".join(parts)))
                    except Exception:
                        print("    %-22s <%s, non ispezionabile>" % (k, type(v).__name__))
                    continue
                if arr.dtype == object:
                    print("    %-22s <object array %s>" % (k, arr.shape))
                elif arr.ndim == 0 or arr.size <= 6:
                    print("    %-22s %s" % (k, v))
                else:
                    print("    %-22s <%s %s>" % (k, arr.shape, arr.dtype))

    print("\n" + "=" * 70)
    print("COSA RIPORTARE: i blocchi Q1, Q2, Q3 per intero.")
    print("Q1 dice se `randoms` e' il token giusto; Q2 se c'e' un taglio in z")
    print("nascosto; Q3 se derive_box() riproduce il lato congelato.")
    print("=" * 70)


if __name__ == "__main__":
    main()
