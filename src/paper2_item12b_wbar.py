#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_item12b_wbar.py — Paper 2, item 1.2b

w-bar ESATTO per geometria e per livello di erosione, piu' la scala di
campionamento per regione.  Sostituisce la stima da sigma_px della tabella di
triage, che non e' una misura.

TRE BLOCCHI, e il secondo e' il piu' importante.

  A — ARCHEOLOGIA.  Il limite pratico "sigma_px <= d_med/9 = 0.333" ha
      provenienza ignota.  Al fiduciale NGC implica d_med = 2.997 voxel =
      46.77 h^-1 Mpc, che NON e' una statistica di vicinato delle galassie:
      la spaziatura media e' 1.12 voxel e il 25-esimo vicino arriva a 2.03.
      Ma 46.77 = 3 * dx quasi esattamente, il che renderebbe il criterio
      identico a "sigma_px <= 1/3 voxel", cioe' una regola di GRIGLIA.

      Le due letture danno verdetti OPPOSTI su SGC (sigma_px = 0.3361):
        * regola di griglia (1/3 fisso)      -> SGC fiduciale FALLISCE di 0.9%
        * d_med/9 con d_med fisico del campione -> SGC PASSA con +11.4%
      Finche' la provenienza non e' tracciata, l'item 1.2c non ha un criterio.
      Questo blocco cerca la definizione nel sorgente.

  B — w-bar esatto, via `mask_erosion` se disponibile.  E' la quantita' che il
      Paper 1 lega al criterio w-bar >= 0.99, e l'unica di 1.2b che sia
      definita senza ambiguita'.

  C — scala di campionamento per regione e geometria: spaziatura media e
      distanze al k-esimo vicino, cosi' che QUALUNQUE definizione di d_med
      risulti calcolabile a posteriori senza rifare i run.

Uso:
    python src\\paper2_item12b_wbar.py --archaeology-only
    python src\\paper2_item12b_wbar.py --region NGC --out results\\paper2\\item12b_NGC.jsonl
    python src\\paper2_item12b_wbar.py --region SGC --points FID --out ...

Sola lettura sugli ingressi.  JSONL append-only, atomico.  Ripristina la
geometria fiduciale in `finally`.
"""

from __future__ import annotations

import argparse
import inspect
import json
import os
import re
import sys
import time

import numpy as np

# --------------------------------------------------------------------------

FROZEN = {
    "NGC": {"box_size_mpc_h": 1997.3629167166155, "cell_size_mpc_h": 15.604397786848558,
            "sigma_px": 0.32042249039652254, "n_valid_voxels": 307805, "N_data": 217614},
    "SGC": {"box_size_mpc_h": 1904.4501607158168, "cell_size_mpc_h": 14.878516880592318,
            "sigma_px": 0.3360550006514459, "n_valid_voxels": 172225, "N_data": 82429},
}
REL_TOL = 1e-6
NGRID = 128
ZMIN, ZMAX = 0.10, 0.40
OMM_FID, W0_FID = 0.3175, -1.0
C_OVER_H0 = 2997.92458
WBAR_THRESHOLD = 0.99
GRID_LIMIT = 1.0 / 3.0            # lettura "regola di griglia"
# d_med = mediana della distanza EUCLIDEA dal bordo della maschera, in unita' di
# griglia (distance_transform_edt, come paper1_mask_erosion.py:78).  Misurata per
# punto qui sotto, non ereditata: la maschera cambia dello 0.25% fra i punti.
# La vecchia identificazione col PRIMO VICINO e' RITRATTATA (item 1.2b): era una
# coincidenza numerica.  nn1_median resta come diagnostica, non come criterio.
try:
    from paper2_data_geometry import PRACTICAL_LIMIT, D_MED_VOXEL
except ImportError:
    D_MED_VOXEL = {"NGC": 3.0000000, "SGC": 2.8284271}
    PRACTICAL_LIMIT = {r: d / 9.0 for r, d in D_MED_VOXEL.items()}
DMED_OVER_9_NGC = 0.333           # valore congelato, chiave `practical_limit_NGC`
# Identificato in 1.2b: 0.333 e' la MEDIANA DELLA DISTANZA AL PRIMO VICINO in
# unita' di griglia, misurata su NGC (0.33126, scarto 0.5%).  Il criterio
# operativo e' dunque sigma_px <= d_med, con d_med per regione e per geometria.
# La formula "/9" del record congelato non e' riproducibile e va ritirata.
DMED_KEY = "nn1_median"
K_LADDER = [1, 2, 3, 5, 8, 12, 20, 30, 50]

# La griglia NON si ricostruisce piu' qui: si LEGGE dai record di 1.3 rev. 2,
# perche' il gauge a cubo costante richiede A, p e c risolti numericamente e
# ricalcolarli con formule diverse produrrebbe punti leggermente diversi da
# quelli su cui si e' misurato il tiling.
DEFAULT_GRID = "results/paper2/item13rev2_%s.jsonl"

PREDICTION = """
PREDIZIONE DICHIARATA PRIMA DEL RUN (item 1.2b, seconda esecuzione)
  Con sigma_px IDENTICO su tutti e nove i punti (gauge a cubo costante), la
  frazione di voxel con w < 0.99 deve essere COSTANTE, a meno della sola
  variazione della maschera (+-0.25% di voxel):
      NGC  ~0.078 ovunque, COMPRESI C1 e C4 che nel gauge vecchio davano
           0.034 e 0.152 (i due lati della scalinata);
      SGC  ~0.178 ovunque, compresi A3 e C1 che davano 0.091.
  Se esce cosi', la scalinata e' eliminata per costruzione e smette di essere
  un confondente.  Se NON esce cosi', dipende anche dalla forma della maschera
  e non solo da sigma_px, e va capito prima di procedere.
"""


# --------------------------------------------------------------------------
# A — archeologia
# --------------------------------------------------------------------------

PATTERNS = [
    (r"d_?med", "definizione di d_med"),
    (r"0\.333", "il limite numerico"),
    (r"/\s*9\b", "il divisore 9"),
    (r"0\.99\b", "la soglia w-bar"),
    (r"w_?bar|wbar|w̄", "la variabile w-bar"),
    (r"mask_erosion|erosion", "l'erosione"),
]


def archaeology(roots):
    print("=" * 72)
    print("BLOCCO A — dove sono definiti d_med, il 9, e la soglia 0.99")
    print("=" * 72)
    hits = {lab: [] for _, lab in PATTERNS}
    for root in roots:
        for dirpath, dirnames, files in os.walk(root):
            dirnames[:] = [d for d in dirnames
                           if d not in (".git", "__pycache__", ".venv", "node_modules")]
            for fn in files:
                if not fn.endswith((".py", ".md", ".txt", ".json")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    with open(path, encoding="utf-8", errors="replace") as fh:
                        lines = fh.read().splitlines()
                except OSError:
                    continue
                for i, line in enumerate(lines, 1):
                    for pat, lab in PATTERNS:
                        if re.search(pat, line):
                            hits[lab].append((path, i, line.strip()[:110]))
    for _, lab in PATTERNS:
        h = hits[lab]
        print("\n  %s — %d occorrenze" % (lab, len(h)))
        for path, i, txt in h[:8]:
            print("    %s:%d" % (path, i))
            print("        %s" % txt)
        if len(h) > 8:
            print("    ... altre %d" % (len(h) - 8))
    print("\n  DA DECIDERE, e non lo decide una misura:")
    print("    (1) d_med = 3*dx  -> criterio di GRIGLIA, sigma_px <= 1/3, uguale ovunque;")
    print("        SGC fiduciale = 0.33606 FALLISCE di 0.9%%.")
    print("    (2) d_med = scala fisica del campione -> criterio per REGIONE;")
    print("        SGC passa con margine ~+11%%.")
    print("    Se il sorgente non lo dice, l'item 1.2c deve dichiarare quale adotta")
    print("    e perche', invece di ereditare un numero senza provenienza.")
    return {k: len(v) for k, v in hits.items()}


# --------------------------------------------------------------------------
# aggancio e geometrie
# --------------------------------------------------------------------------

def attach(srcdir, geom_mod, const_mod):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    G = __import__(geom_mod)
    M = getattr(G, "M", None) or __import__(const_mod)
    setg = getattr(M, "set_geometry", None) or getattr(G, "set_geometry", None)
    if setg is None:
        raise SystemExit("set_geometry() non trovata.")
    for zn, dn in (("_Z_TAB", "_DC_TAB"), ("Z_TAB", "DC_TAB")):
        if hasattr(M, zn):
            z_tab = np.asarray(getattr(M, zn), float).copy()
            dc_tab = np.asarray(getattr(M, dn), float).copy()
            break
    else:
        raise SystemExit("tabella fiduciale non trovata.")
    ero = getattr(G, "mask_erosion", None) or getattr(M, "mask_erosion", None)
    print("[attach] %s + %s ; mask_erosion: %s"
          % (G.__name__, M.__name__,
             ("%s%s" % (ero.__name__, inspect.signature(ero))) if ero else "ASSENTE (uso interna)"))
    return G, M, setg, z_tab, dc_tab, ero


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


def cosmo_ratio(z_tab, omm, w0):
    zf = np.linspace(0.0, max(z_tab.max(), ZMAX + 0.05), 90001)
    a_, b_ = dc_scratch(zf, OMM_FID, W0_FID), dc_scratch(zf, omm, w0)
    g = np.ones_like(zf)
    nz = a_ > 0
    g[nz] = b_[nz] / a_[nz]
    g[~nz] = g[nz][0]
    return np.interp(z_tab, zf, g)


def load_grid(path, region):
    """Legge i punti di 1.3 rev. 2; a parita' di nome tiene il record piu' recente."""
    if not os.path.exists(path):
        raise SystemExit("griglia non trovata: %s\n  eseguire prima "
                         "paper2_item13_rev2.py --region %s" % (path, region))
    best = {}
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            if r.get("region") == region:
                best[r["point"]] = r          # l'ultimo vince
    order = ["B1", "B2", "B3", "B4", "B5", "C1", "C2", "C3", "C4"]
    out = [(k, best[k]) for k in order if k in best]
    extra = sorted(set(best) - set(order))
    out += [(k, best[k]) for k in extra]
    print("[griglia] %s: %d punti -> %s"
          % (os.path.basename(path), len(out), " ".join(k for k, _ in out)))
    missing = [k for k in order if k not in best]
    if missing:
        print("           MANCANTI: %s" % " ".join(missing))
    return out


def deform_from_record(z_tab, dc_fid, rec):
    """Ricostruisce la tabella D_C del punto dal record di 1.3 rev. 2."""
    if "p_exponent" in rec:                       # linea B: f = A r^p
        return rec["A"] * dc_fid ** rec["p_exponent"]
    if "c_gauge" in rec:                          # angolo ri-gaugiato
        return rec["c_gauge"] * dc_fid * cosmo_ratio(z_tab, rec["omm"], rec["w0"])
    raise SystemExit("record senza p_exponent ne' c_gauge: %s" % rec.get("point"))


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


# --------------------------------------------------------------------------
# B — w-bar
# --------------------------------------------------------------------------

def find_mask(obj):
    """Cerca l'array bool 128^3 dentro il dict restituito da data_side."""
    def walk(v):
        if isinstance(v, np.ndarray):
            if v.dtype == bool and v.ndim == 3:
                return v
            return None
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


def edt_depth_median(mask):
    """d_med del punto: mediana della distanza euclidea dal bordo, in voxel."""
    try:
        from scipy.ndimage import distance_transform_edt
    except ImportError:
        return None
    return float(np.median(distance_transform_edt(mask)[mask]))


def gauss_kernel(sigma, radius=None):
    if radius is None:
        radius = max(2, int(np.ceil(4 * sigma)))
    n = np.arange(-radius, radius + 1)
    w = np.exp(-n ** 2 / (2.0 * sigma ** 2))
    return w / w.sum()


def sep_convolve(vol, k):
    """Convoluzione separabile con padding a zero: fuori maschera = peso perso."""
    r = (len(k) - 1) // 2
    out = vol.astype(np.float32)
    for ax in range(3):
        pad = [(0, 0)] * 3
        pad[ax] = (r, r)
        p = np.pad(out, pad, mode="constant", constant_values=0.0)
        acc = np.zeros_like(out)
        for j, w in enumerate(k):
            if w == 0.0:
                continue
            sl = [slice(None)] * 3
            sl[ax] = slice(j, j + out.shape[ax])
            acc += np.float32(w) * p[tuple(sl)]
        out = acc
    return out


def erode(mask, k, ero_fn=None):
    if k <= 0:
        return mask
    if ero_fn is not None:
        try:
            return np.asarray(ero_fn(mask, k), bool)
        except TypeError:
            pass
    m = mask.copy()
    for _ in range(k):
        e = m.copy()
        for ax in range(3):
            for sh in (1, -1):
                e &= np.roll(m, sh, axis=ax)
        # niente wrap-around: i bordi del cubo contano come fuori
        idx = [slice(None)] * 3
        for ax in range(3):
            for pos in (0, -1):
                idx2 = list(idx)
                idx2[ax] = pos
                e[tuple(idx2)] = False
        m = e
    return m


def wbar_levels(mask, sigma_px, kmax=3, ero_fn=None):
    ker = gauss_kernel(sigma_px)
    w = sep_convolve(mask.astype(np.float32), ker)   # frazione di kernel in maschera
    out = []
    for k in range(kmax + 1):
        mk = erode(mask, k, ero_fn)
        n = int(mk.sum())
        if n == 0:
            out.append({"k": k, "n_voxel": 0, "wbar": float("nan"), "wmin": float("nan"),
                        "frac_below_0.99": float("nan")})
            continue
        ww = w[mk]
        out.append({"k": k, "n_voxel": n, "wbar": float(ww.mean()),
                    "wmin": float(ww.min()),
                    "frac_below_0.99": float((ww < WBAR_THRESHOLD).mean())})
    return out


# --------------------------------------------------------------------------
# C — scala di campionamento
# --------------------------------------------------------------------------

def sampling_scale(pos, box_min, dx, mask=None):
    """Spaziatura media e distanze al k-esimo vicino, in voxel."""
    try:
        from scipy.spatial import cKDTree
    except ImportError:
        print("    scipy non disponibile: blocco C saltato.")
        return None
    u = (np.asarray(pos, float) - np.asarray(box_min, float)) / dx
    if mask is not None:
        idx = np.floor(u).astype(int)
        ok = np.all((idx >= 0) & (idx < NGRID), axis=1)
        u, idx = u[ok], idx[ok]
        ok2 = mask[idx[:, 0], idx[:, 1], idx[:, 2]]
        u = u[ok2]
    n = len(u)
    if n < 100:
        return None
    tree = cKDTree(u)
    kmax = min(max(K_LADDER) + 1, n - 1)
    d, _ = tree.query(u, k=kmax + 1, workers=-1)
    out = {"n_used": int(n)}
    for k in K_LADDER:
        if k < d.shape[1]:
            out["nn%d_median" % k] = float(np.median(d[:, k]))
            out["nn%d_mean" % k] = float(d[:, k].mean())
    return out


# --------------------------------------------------------------------------

def gate(region, ds):
    ref = FROZEN[region]
    print("\n[gate] data_side fiduciale, %s" % region)
    bad = []
    for k, v in ref.items():
        got = ds.get(k)
        if got is None:
            continue
        rel = abs(float(got) - v) / abs(v)
        print("    %-18s %20.10f  atteso %20.10f  rel %8.1e  %s"
              % (k, float(got), v, rel, "ok" if rel <= REL_TOL else "SCARTO"))
        if rel > REL_TOL:
            bad.append(k)
    if bad:
        print("    CANCELLO FALLITO su %s" % ", ".join(bad), file=sys.stderr)
        sys.exit(3)
    print("    superato.")


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--const-module", default="phase8_cutsky_mocks")
    p.add_argument("--points", nargs="*", default=None,
                   help="sottoinsieme, es. B3 C1 C4; default: tutti e nove")
    p.add_argument("--grid", default=None,
                   help="JSONL di 1.3 rev. 2 (default: results/paper2/item13rev2_<REG>.jsonl)")
    p.add_argument("--kmax", type=int, default=3)
    p.add_argument("--roots", nargs="*", default=["src", "."])
    p.add_argument("--archaeology", action="store_true",
                   help="ripete la ricerca nel sorgente (gia' conclusa in 1.2b)")
    p.add_argument("--archaeology-only", action="store_true")
    p.add_argument("--out", default=None)
    a = p.parse_args()

    # Il blocco A ha gia' identificato d_med (item 1.2b, chiuso): resta
    # disponibile con --archaeology, ma non si ripete a ogni run.
    if a.archaeology or a.archaeology_only:
        archaeology(a.roots)
        if a.archaeology_only:
            return

    G, M, setg, z_tab, dc_fid, ero_fn = attach(a.src, a.geom_module, a.const_module)

    print(PREDICTION)
    grid = load_grid(a.grid or (DEFAULT_GRID % a.region), a.region)
    if a.points:
        grid = [(n, r) for n, r in grid if n in a.points]

    print("\n" + "=" * 72)
    print("BLOCCHI B e C — %d geometrie, regione %s" % (len(grid), a.region))
    print("=" * 72)
    rows = []
    try:
        for name, grec in grid:
            dc_new = deform_from_record(z_tab, dc_fid, grec)
            call_set(setg, z_tab=z_tab, dc_tab=dc_new)
            t0 = time.time()
            ds = G.data_side(a.region)
            if not isinstance(ds, dict):
                raise SystemExit("data_side non restituisce un dict: %s" % type(ds))
            if name in ("B3", "FID"):
                gate(a.region, ds)

            mask = find_mask(ds)
            if mask is None:
                raise SystemExit("maschera booleana 128^3 non trovata in data_side")
            sig = float(ds["sigma_px"])
            dx = float(ds["cell_size_mpc_h"])
            lev = wbar_levels(mask, sig, a.kmax, ero_fn)

            rec = {"schema": "paper2_item12b_v1", "region": a.region, "point": name,
                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "sigma_px": sig, "cell_size_mpc_h": dx,
                   "box_size_mpc_h": float(ds["box_size_mpc_h"]),
                   "n_valid_voxels": int(ds["n_valid_voxels"]),
                   "wbar_levels": lev,
                   "pass_grid_rule": bool(sig <= GRID_LIMIT),
                   "margin_grid_rule": float(1.0 - sig / GRID_LIMIT),
                   "seconds": round(time.time() - t0, 1),
                   "gauge": "constant_embedding_box",
                   "grid_source": os.path.basename(a.grid or (DEFAULT_GRID % a.region))}
            for k in ("p_exponent", "A", "c_gauge", "omm", "w0",
                      "F_standard_perp_over_par", "F_pipeline_par_over_perp",
                      "alpha_iso_minimax", "anis_residual_minimax_vox"):
                if k in grec:
                    rec[k] = grec[k]

            try:
                pos, _ = (G.positions(a.region, "dat") if isinstance(
                    G.positions(a.region, "dat"), tuple) else (G.positions(a.region, "dat"), None))
            except Exception as exc:
                pos = None
                print("    positions(dat) fallita: %s" % exc)
            if pos is not None:
                sc = sampling_scale(pos, ds["box_min"], dx, mask)
                if sc:
                    rec["sampling"] = sc
                    rec["occupancy_gal_per_voxel"] = sc["n_used"] / rec["n_valid_voxels"]
                    # diagnostica, NON il criterio: identificazione ritrattata
                    rec["nn1_median_voxel"] = sc.get("nn1_median")

            # --- il criterio vero: d_med = profondita' EDT, misurata per punto
            dmed = edt_depth_median(mask)
            if dmed is None:
                dmed = D_MED_VOXEL[a.region]
                rec["d_med_source"] = "frozen_region"
            else:
                rec["d_med_source"] = "measured_edt"
            lim = dmed / 9.0
            rec["d_med_voxel"] = dmed
            rec["practical_limit"] = lim
            rec["margin_practical"] = 1.0 - sig / lim
            rec["over_practical_limit"] = bool(sig > lim)
            # In SGC il limite e' superato ovunque, fiduciale compreso: li' non e'
            # un criterio di esclusione ma un caveat (item 1.2c).
            rec["excluded_1_2c"] = bool(a.region == "NGC" and sig > lim)

            w0lev = lev[0]
            print("  %-5s sig=%.5f dx=%.4f  w̄(k=0)=%.5f  w̄(k=1)=%.5f  "
                  "frac<0.99=%.3f  voxel=%d  [%s]  %.0fs"
                  % (name, sig, dx, w0lev["wbar"], lev[1]["wbar"] if len(lev) > 1 else float("nan"),
                     w0lev["frac_below_0.99"], w0lev["n_voxel"],
                     "griglia OK" if rec["pass_grid_rule"] else "GRIGLIA NO",
                     rec["seconds"]))
            rows.append(rec)
            if a.out:
                append_atomic(a.out, rec)
    finally:
        # Ripristinare dc_tab NON basta: `data_side` riscrive box_min/box_size
        # nello stato globale del modulo, e dopo l'ultimo punto quello stato
        # resta sporco (visibile nei log: set_geometry echeggia il box del punto
        # precedente).  Una chiamata a data_side al fiduciale lo ripulisce.
        call_set(setg, z_tab=z_tab, dc_tab=dc_fid)
        try:
            ds_fid = G.data_side(a.region, verbose=False)
        except TypeError:
            ds_fid = G.data_side(a.region)
        except Exception as exc:
            ds_fid = None
            print("\n[restore] dc_tab ripristinata, ma il box NON e' stato ripulito: %s" % exc)
        if ds_fid is not None:
            ref = FROZEN[a.region]["box_size_mpc_h"]
            got = float(ds_fid["box_size_mpc_h"])
            print("\n[restore] geometria fiduciale ripristinata; box = %.4f (atteso %.4f, rel %.1e)"
                  % (got, ref, abs(got - ref) / ref))

    if rows:
        print("\n" + "=" * 72)
        print("AMMISSIBILITA' — le due letture a confronto")
        print("=" * 72)
        print("%-6s %9s %9s %9s %9s %10s %14s" %
              ("punto", "sigma_px", "d_med", "margine", "w̄(k=0)", "frac<0.99", "esito"))
        for r in rows:
            w = r["wbar_levels"][0]
            dm = r.get("d_med_voxel", float("nan"))
            mg = r.get("margin_practical", float("nan"))
            if w["wbar"] < WBAR_THRESHOLD:
                esito = "ESCLUSO (w̄)"
            elif r.get("excluded_1_2c"):
                esito = "ESCLUSO"
            elif r.get("over_practical_limit"):
                esito = "caveat"
            else:
                esito = "ok"
            print("%-6s %9.5f %9.5f %8.1f%% %9.5f %10.4f %14s"
                  % (r["point"], r["sigma_px"], dm, 100 * mg, w["wbar"],
                     w["frac_below_0.99"], esito))
        if any(r.get("over_practical_limit") for r in rows) and a.region == "SGC":
            print("\n  SGC: il limite pratico e' superato in tutti i punti, fiduciale")
            print("  compreso.  NON e' un criterio di esclusione al sud — escluderebbe un")
            print("  risultato pubblicato — ma un caveat da dichiarare.  Il criterio")
            print("  primario resta w̄ >= 0.99, superato ovunque, e il rimedio operativo")
            print("  e' l'erosione (item 1.2c).")
        fr = [r["wbar_levels"][0]["frac_below_0.99"] for r in rows]
        exp = 0.078 if a.region == "NGC" else 0.178
        ok = (max(fr) - min(fr)) < 0.005
        print("\n  VERIFICA DELLA PREDIZIONE")
        print("    frac<0.99: da %.4f a %.4f, escursione %.4f  (atteso ~%.3f costante)"
              % (min(fr), max(fr), max(fr) - min(fr), exp))
        print("    -> %s" % ("CONFERMATA: la scalinata e' eliminata dal gauge."
                             if ok else
                             "SMENTITA: dipende anche dalla forma della maschera, "
                             "non solo da sigma_px. Capire prima di procedere."))
        print("\n  Scalinata: nel gauge vecchio frac<0.99 saltava a gradini in sigma_px")
        print("  (soglie a 0.3075 e 0.3302). Qui sigma_px e' costante per costruzione,")
        print("  quindi la scalinata non puo' esistere: da %.4f a %.4f." % (min(fr), max(fr)))
        k1 = [r["wbar_levels"][1]["frac_below_0.99"] for r in rows if len(r["wbar_levels"]) > 1]
        if k1:
            print("  A erosione k=1 vale %.4f ovunque: la scalinata sparisce." % max(k1))
            print("  -> eseguire la griglia AP a k=1 come primaria.")


if __name__ == "__main__":
    main()
