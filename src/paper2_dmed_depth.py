#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_dmed_depth.py — d_med e' la profondita' mediana del footprint

RETTIFICA dell'item 1.2b.  La definizione di d_med era stata identificata come
"mediana della distanza al primo vicino in unita' di griglia" (NGC 0.33126
contro il congelato 0.333, scarto 0.5%).  Era una COINCIDENZA NUMERICA.

`src/paper1_mask_erosion.py:19` dice invece, in chiaro:

    "Il footprint NGC ha profondita' mediana di soli 3 voxel"

e 3/9 = 0.3333 = `practical_limit_NGC`.  Il criterio sigma_px <~ d_med/9 e'
dunque una regola di GEOMETRIA DELLA MASCHERA: il kernel non deve arrivare a un
nono dello spessore della fetta.  Coerente col contesto di quel file, che parla
di contaminazione di bordo e di `gaussian_filter` applicato all'intero cubo.

Conferma indipendente nella stessa tabella:
    R=5, sigma_px=0.3204 -> 7.8% di voxel con w<0.99, w medio 0.998
contro il misurato in 1.2b: 0.0780 e 0.99799.  Il w-bar riproduce il valore
pubblicato: l'implementazione di 1.2b e' corretta, era sbagliata la lettura del
limite.

QUESTO SCRIPT misura la profondita' con piu' definizioni candidate e dichiara
quale riproduce 3.00 voxel su NGC.  Poi applica la stessa alla SGC, dove il
verdetto di 1.2c e' in bilico: riempimento 8.21% contro 14.68%.

Uso:
    python src\\paper2_dmed_depth.py --region NGC
    python src\\paper2_dmed_depth.py --region SGC --out results\\paper2\\dmed_NGC.jsonl
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

TARGET_NGC = 3.0            # dalla riga 19 di paper1_mask_erosion.py
FROZEN_LIMIT_NGC = 0.333
NGRID = 128


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


def runs_along_axis(mask, axis):
    """Lunghezze di tutti i tratti contigui in maschera lungo un asse."""
    m = np.moveaxis(mask, axis, -1)
    flat = m.reshape(-1, m.shape[-1])
    out = []
    pad = np.zeros((flat.shape[0], 1), bool)
    p = np.concatenate([pad, flat, pad], axis=1)
    d = np.diff(p.astype(np.int8), axis=1)
    for row in range(p.shape[0]):
        starts = np.flatnonzero(d[row] == 1)
        if starts.size == 0:
            continue
        ends = np.flatnonzero(d[row] == -1)
        out.append(ends - starts)
    return np.concatenate(out) if out else np.array([], int)


def depth_per_voxel(mask, axis):
    """Per ogni voxel in maschera, la lunghezza del tratto che lo contiene."""
    m = np.moveaxis(mask, axis, -1)
    flat = m.reshape(-1, m.shape[-1])
    depth = np.zeros_like(flat, dtype=np.int16)
    pad = np.zeros((flat.shape[0], 1), bool)
    p = np.concatenate([pad, flat, pad], axis=1)
    d = np.diff(p.astype(np.int8), axis=1)
    for row in range(p.shape[0]):
        st = np.flatnonzero(d[row] == 1)
        if st.size == 0:
            continue
        en = np.flatnonzero(d[row] == -1)
        for s, e in zip(st, en):
            depth[row, s:e] = e - s
    return np.moveaxis(depth.reshape(m.shape), -1, axis)


def edt_depth(mask):
    """
    Distanza EUCLIDEA dal complemento della maschera.

    E' la definizione VERA: `paper1_mask_erosion.py:78` importa
    `distance_transform_edt` da scipy.ndimage.  Non e' ne' city-block (6 vicini)
    ne' Chebyshev (26 vicini) ma sta fra le due, che quindi la incorniciano.
    """
    from scipy.ndimage import distance_transform_edt
    d = distance_transform_edt(mask)
    return d[mask]


def erosion_depth(mask, kind="6", kmax=25):
    """
    depth(v) = numero di erosioni che il voxel sopravvive + 1, cioe' la
    distanza dal complemento della maschera.  E' LA quantita' giusta: e' quella
    che misura "quanto lontano dal bordo sta un voxel tipico", ed e' cio' di cui
    parla paper1_mask_erosion.py quando dice che il kernel raccoglie segnale dal
    vuoto esterno.

    kind="6"  : vicini di faccia (city-block)
    kind="26" : tutti i vicini del cubo 3x3x3 (Chebyshev) -- erode piu' in fretta
    """
    m = mask.copy()
    depth = mask.astype(np.int16)          # chi e' in maschera ha almeno 1
    surv = [int(m.sum())]
    for _ in range(kmax):
        e = m.copy()
        if kind == "6":
            for ax in range(3):
                for sh in (1, -1):
                    e &= np.roll(m, sh, axis=ax)
        else:
            for sx in (-1, 0, 1):
                for sy in (-1, 0, 1):
                    for sz in (-1, 0, 1):
                        if sx == sy == sz == 0:
                            continue
                        e &= np.roll(np.roll(np.roll(m, sx, 0), sy, 1), sz, 2)
        for ax in range(3):
            for pos in (0, -1):
                idx = [slice(None)] * 3
                idx[ax] = pos
                e[tuple(idx)] = False
        m = e
        n = int(m.sum())
        surv.append(n)
        depth += m
        if n == 0:
            break
    return depth[mask], surv


def median_from_survival(surv):
    """Mediana della profondita' dalla curva di sopravvivenza, per interpolazione."""
    p = [x / surv[0] for x in surv]
    for i in range(len(p) - 1):
        if p[i] >= 0.5 > p[i + 1]:
            return i + 1 + (p[i] - 0.5) / (p[i] - p[i + 1])
    return float(len(p))


def radial_depth(mask, box_min, dx, n_rays=20000, seed=0):
    """
    Profondita' lungo la linea di vista: numero di voxel in maschera
    incontrati da un raggio uscente dall'origine (l'osservatore).
    """
    rng = np.random.default_rng(seed)
    # direzioni uniformi sulla sfera, tenute solo se il raggio interseca la maschera
    v = rng.normal(size=(n_rays, 3))
    v /= np.linalg.norm(v, axis=1)[:, None]
    # campiona lungo il raggio con passo mezzo voxel
    rmax = float(np.linalg.norm(np.abs(np.asarray(box_min)) + NGRID * dx))
    t = np.arange(0.0, rmax, dx * 0.5)
    counts = []
    step = 500
    for i0 in range(0, n_rays, step):
        vv = v[i0:i0 + step]
        pts = vv[:, None, :] * t[None, :, None]
        u = (pts - np.asarray(box_min)) / dx
        idx = np.floor(u).astype(int)
        ok = np.all((idx >= 0) & (idx < NGRID), axis=2)
        inm = np.zeros(ok.shape, bool)
        ii = idx[ok]
        inm[ok] = mask[ii[:, 0], ii[:, 1], ii[:, 2]]
        # un campione ogni mezzo voxel: dividi per 2 per avere voxel
        c = inm.sum(axis=1) * 0.5
        counts.append(c[c > 0])
    return np.concatenate(counts) if counts else np.array([])


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--rays", type=int, default=20000)
    p.add_argument("--out", default=None)
    a = p.parse_args()

    if a.src not in sys.path:
        sys.path.insert(0, a.src)
    G = __import__(a.geom_module)
    ds = G.data_side(a.region)
    mask = find_mask(ds)
    if mask is None:
        raise SystemExit("maschera non trovata in data_side")
    dx = float(ds["cell_size_mpc_h"])
    sig = float(ds["sigma_px"])
    bmin = np.asarray(ds["box_min"], float)

    print("=" * 72)
    print("d_med — profondita' mediana del footprint, regione %s" % a.region)
    print("=" * 72)
    print("  voxel in maschera: %d   riempimento %.2f%%   sigma_px %.5f"
          % (mask.sum(), 100 * mask.mean(), sig))
    print("\n  bersaglio: `paper1_mask_erosion.py:19` dichiara 3 voxel per NGC,")
    print("  e 3/9 = 0.3333 riproduce `practical_limit_NGC` = 0.333.\n")

    cands = {}
    print("  %-42s %9s %9s" % ("definizione", "mediana", "media"))
    print("  " + "-" * 62)

    # --- la definizione vera: EDT, come paper1_mask_erosion.py:78
    try:
        de = edt_depth(mask)
        cands["edt"] = float(np.median(de))
        print("  %-42s %9.3f %9.3f   <<< paper1_mask_erosion:78"
              % ("distanza EUCLIDEA dal bordo", np.median(de), de.mean()))
    except ImportError:
        print("  scipy assente: EDT non calcolabile")

    # --- le due che la incorniciano
    for kind, lab in (("6", "6 vicini di faccia (city-block, sopra)"),
                      ("26", "26 vicini (Chebyshev, sotto)")):
        d, surv = erosion_depth(mask, kind)
        med = median_from_survival(surv)
        cands["erosion_depth_%s" % kind] = med
        print("  %-42s %9.3f %9.3f"
              % ("distanza dal bordo, %s" % lab, med, float(d.mean())))
        pr = "    sopravvivenza: " + "  ".join(
            "k=%d %.4f" % (k, surv[k] / surv[0]) for k in range(min(5, len(surv))))
        print(pr)

    # --- diagnostiche secondarie, non candidate
    print("\n  (secondarie, per contesto: corde e linea di vista)")
    allr = np.concatenate([runs_along_axis(mask, ax) for ax in range(3)])
    cands["run_all"] = float(np.median(allr))
    print("  %-42s %9.3f %9.3f" % ("tratti contigui, tre assi insieme",
                                   np.median(allr), allr.mean()))
    rd = radial_depth(mask, bmin, dx, a.rays)
    if rd.size:
        cands["radial"] = float(np.median(rd))
        print("  %-42s %9.3f %9.3f" % ("lungo la linea di vista (%d raggi)" % a.rays,
                                       np.median(rd), rd.mean()))

    if "edt" in cands and "erosion_depth_26" in cands and "erosion_depth_6" in cands:
        lo, mid, hi = (cands["erosion_depth_26"], cands["edt"], cands["erosion_depth_6"])
        print("\n  incorniciamento: Chebyshev %.3f <= EDT %.3f <= city-block %.3f  -> %s"
              % (lo, mid, hi, "coerente" if lo <= mid <= hi else "INCOERENTE, da capire"))

    print("\n  quale riproduce il bersaglio?")
    prim = {k: v for k, v in cands.items()
            if k == "edt" or k.startswith("erosion_depth")}
    if a.region == "NGC":
        best = sorted(prim.items(), key=lambda kv: abs(kv[1] - TARGET_NGC))
        if "edt" in prim:
            best = [("edt", prim["edt"])] + [b for b in best if b[0] != "edt"]
        for k, v in best[:4]:
            flag = "   <<< COINCIDE" if abs(v - TARGET_NGC) < 0.06 else ""
            print("    %-24s %7.3f   (bersaglio 3.000, scarto %+.3f)%s"
                  % (k, v, v - TARGET_NGC, flag))
        top = best[0]
        print("\n    -> definizione adottata: %s = %.3f voxel" % top)
        print("       limite = d_med/9 = %.4f   (congelato: %.3f, scarto %+.4f)"
              % (top[1] / 9, FROZEN_LIMIT_NGC, top[1] / 9 - FROZEN_LIMIT_NGC))
        print("       margine del fiduciale: %+.1f%%" % (100 * (1 - sig / (top[1] / 9))))
        print("\n    NB: la profondita' dipende dall'ELEMENTO STRUTTURANTE, quindi")
        print("        1.2c dipende ora da 0.11.  Le due voci sono accoppiate.")
    else:
        print("    (il bersaglio 3.000 e' dichiarato per NGC; qui si applica la")
        print("     definizione scelta su NGC e si legge il limite che ne esce)")
        for k, v in sorted(prim.items()):
            print("    %-24s %7.3f  ->  limite %.4f  margine %+.1f%%"
                  % (k, v, v / 9, 100 * (1 - sig / (v / 9))))

    rec = {"schema": "paper2_dmed_depth_v1", "region": a.region,
           "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
           "sigma_px": sig, "cell_size_mpc_h": dx,
           "n_valid_voxels": int(mask.sum()), "fill": float(mask.mean()),
           "depth_candidates": cands,
           "limits": {k: v / 9 for k, v in cands.items()},
           "margins": {k: 1 - sig / (v / 9) for k, v in cands.items() if v > 0}}
    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            fh.write(json.dumps(rec, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("\n  scritto in %s" % a.out)


if __name__ == "__main__":
    main()
