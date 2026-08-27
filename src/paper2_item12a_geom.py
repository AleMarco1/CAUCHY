#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_item12a_geom.py — Paper 2, item 1.2a, meta' geometrica

Riscrittura di `paper2_item12a_apgrid.py` sull'architettura del modulo invece che
su un FITS letto per conto proprio.  Per ogni geometria:

    set_geometry(z_tab=, dc_tab=)      inietta la mappatura
    positions(region, "ran")           random riconvertiti con quella mappatura
    derive_box(pos_r, pad=5.0)         la REGOLA VERA (phase6_bgs_voxelize.py:166-168)

Tre scelte di progetto, ciascuna con un motivo:

1.  `kind="ran"` e' hard-coded.  Nel modulo qualunque altro token cade nel ramo
    `else` e restituisce le GALASSIE senza errore.  Lo script lo verifica contro
    N_rand congelato prima di produrre qualunque numero.

2.  Ogni geometria e' costruita come RAPPORTO sulla tabella D_C fiduciale del
    modulo, mai integrando da zero.  Motivo: la costante c/H0 del modulo
    (c = 299792.0 km/s) differisce dalla mia (299792.458) di un fattore costante
    1.0000015.  E' una dilatazione pura, dunque invisibile per la Proposizione 2,
    ma costruire per rapporti la cancella esattamente invece che quasi.

3.  Il punto fiduciale deve riprodurre i valori congelati a 1e-6 relativo, non a
    0.05 assoluto.  Con questa architettura il fiduciale e' un no-op bit-esatto.

Sola scrittura: JSONL append-only, atomico, ripartibile.  Ripristina la
geometria fiduciale in `finally`.

Uso:
    python src\\paper2_item12a_geom.py --region NGC --dry-run
    python src\\paper2_item12a_geom.py --region NGC --out results\\paper2\\item12a_geom_NGC.jsonl
    python src\\paper2_item12a_geom.py --region SGC --out results\\paper2\\item12a_geom_SGC.jsonl
"""

from __future__ import annotations

import argparse
import hashlib
import inspect
import json
import os
import sys
import time

import numpy as np

# --------------------------------------------------------------------------
# congelati — da data_side('NGC'), 25 agosto 2026
# --------------------------------------------------------------------------

FROZEN = {
    "NGC": {
        "box_size_mpc_h": 1997.3629167166155,
        "cell_size_mpc_h": 15.604397786848558,
        "sigma_px": 0.32042249039652254,
        "N_rand": 13248857,
        "N_data": 217614,
        "D_C_ZMIN": 292.535950750378,
        "D_C_ZMAX": 1080.7298534541035,
    },
    # SGC congelato il 27 ago 2026 dal cancello 2.1-M: box derivato dai random via
    # set_geometry (D3, rel 0.00e+00 sulle tre quantita'), maschera riprodotta per
    # identita' di array (307805/172225, np.array_equal True).
    "SGC": {
        "box_size_mpc_h": 1904.4501607158168,
        "cell_size_mpc_h": 14.878516880592318,
        "sigma_px": 0.33605500065144589,
        "N_rand": 5432939,
        "N_data": 82429,
        "D_C_ZMIN": 292.535950750378,
        "D_C_ZMAX": 1080.7298534541035,
    },
}
REL_TOL = 1e-6
SOFT_TOL = 5e-3

PAD = 5.0
NGRID = 128
R_SMOOTH = 5.0
ZMIN, ZMAX = 0.10, 0.40

OMM_FID, W0_FID = 0.3175, -1.0
C_OVER_H0 = 2997.92458          # solo per RAPPORTI: la costante si cancella

GRID_OMM_W0 = [(0.2500, -1.2), (0.2500, -1.0), (0.2500, -0.8),
               (0.2800, -1.2), (0.2800, -1.0), (0.2800, -0.8),
               (0.3175, -1.2), (0.3175, -1.0), (0.3175, -0.8),
               (0.3500, -1.2), (0.3500, -1.0), (0.3500, -0.8)]

# blocchi A e B dell'item 1.3, gauge minimax
LINE_A = [("A1", 0.9725), ("A2", 1.0000), ("A3", 1.0406)]
LINE_B = [("B1", 0.971070), ("B2", 0.985396), ("B3", 1.000000),
          ("B4", 1.014889), ("B5", 1.030071)]


# --------------------------------------------------------------------------
# aggancio al modulo
# --------------------------------------------------------------------------

def attach(srcdir, geom_mod, const_mod):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    G = __import__(geom_mod)
    M = getattr(G, "M", None)
    if M is None:
        M = __import__(const_mod)
    setg = getattr(M, "set_geometry", None) or getattr(G, "set_geometry", None)
    if setg is None:
        raise SystemExit("set_geometry() non trovata: inserire prima il blocco G2.")
    z_tab = dc_tab = None
    for zn, dn in (("_Z_TAB", "_DC_TAB"), ("Z_TAB", "DC_TAB")):
        if hasattr(M, zn) and hasattr(M, dn):
            z_tab = np.asarray(getattr(M, zn), float).copy()
            dc_tab = np.asarray(getattr(M, dn), float).copy()
            break
    if z_tab is None:
        raise SystemExit("tabella fiduciale (_Z_TAB/_DC_TAB) non trovata in %s" % M.__name__)
    print("[attach] %s + %s ; tabella fiduciale: %d nodi, z in [%.4f, %.4f]"
          % (G.__name__, M.__name__, z_tab.size, z_tab.min(), z_tab.max()))
    print("[attach] set_geometry%s" % inspect.signature(setg))
    return G, M, setg, z_tab, dc_tab


def call_set_geometry(setg, **kw):
    """Passa solo i parametri che la firma accetta."""
    ok = set(inspect.signature(setg).parameters)
    return setg(**{k: v for k, v in kw.items() if k in ok})


# --------------------------------------------------------------------------
# deformazioni, tutte come rapporto sulla tabella del modulo
# --------------------------------------------------------------------------

def e_of_z(z, omm, w0):
    return np.sqrt(omm * (1 + z) ** 3 + (1 - omm) * (1 + z) ** (3 * (1 + w0)))


def dc_from_scratch(z, omm, w0):
    i = 1.0 / e_of_z(z, omm, w0)
    return C_OVER_H0 * np.concatenate(
        [[0.0], np.cumsum(0.5 * (i[1:] + i[:-1]) * np.diff(z))])


def deform_cosmology(z_tab, dc_fid, omm, w0):
    """dc_new = dc_fid * g(z), con g rapporto di due integrazioni: c/H0 si cancella."""
    if (omm, w0) == (OMM_FID, W0_FID):
        return dc_fid.copy(), 1.0
    zf = np.linspace(0.0, max(z_tab.max(), ZMAX + 0.05), 90001)
    g_fine = np.ones_like(zf)
    a = dc_from_scratch(zf, OMM_FID, W0_FID)
    b = dc_from_scratch(zf, omm, w0)
    nz = a > 0
    g_fine[nz] = b[nz] / a[nz]
    g_fine[~nz] = g_fine[nz][0] if nz.any() else 1.0
    g = np.interp(z_tab, zf, g_fine)
    return dc_fid * g, float(np.nanmedian(g))


def minimax_alpha(r_fid, r_new):
    g = r_new / r_fid
    lo, hi = float(g.min()), float(g.max())
    if hi - lo < 1e-15:
        return 0.5 * (lo + hi), 0.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        d = r_fid * (mid - g)
        if float(d.max()) - float((-d).max()) > 0.0:
            hi = mid
        else:
            lo = mid
    a = 0.5 * (lo + hi)
    return a, float(np.max(np.abs(r_new - a * r_fid)))


def deform_ap(z_tab, dc_fid, alpha_iso, F_ap):
    """
    Lemma 3: F_AP costante  <=>  f(r) = A r^(1/F).
    A e' fissato imponendo che l'alpha_iso MINIMAX valga il bersaglio.
    """
    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    r = dc_fid[m]
    if abs(F_ap - 1.0) < 1e-12:
        return dc_fid * alpha_iso
    x = dc_fid ** (1.0 / F_ap)
    a1, _ = minimax_alpha(r, x[m])          # alpha_iso di A=1
    A = alpha_iso / a1
    return A * x


# --------------------------------------------------------------------------
# geometria di un punto
# --------------------------------------------------------------------------

def unpack_box(box):
    if isinstance(box, dict):
        bmin = np.asarray(box.get("box_min"), float).ravel()
        L = float(np.asarray(
            box.get("box_size", box.get("L", box.get("side")))).ravel()[0])
        return bmin, L
    if isinstance(box, tuple):
        bmin = np.asarray(box[0], float).ravel()
        L = float(np.asarray(box[1], float).ravel()[0])
        return bmin, L
    a = np.asarray(box, float).ravel()
    return a[:3], float(a[-1])


class RadialCache:
    """
    La deformazione e' PURAMENTE RADIALE: r -> f(r) lungo n_hat invariato.
    Quindi basta una sola lettura del catalogo, al fiduciale, e poi si
    riscalano i raggi.  Diciotto letture di un FITS da 1.5 GB diventano una.

    Matematicamente identico al ricaricare; `--verify-fast` lo dimostra su un
    punto confrontando col percorso completo set_geometry -> positions.
    """

    def __init__(self, G, setg, region, z_tab, dc_fid):
        call_set_geometry(setg, z_tab=z_tab, dc_tab=dc_fid)
        pos, _ = _as_pos(G.positions(region, "ran"))
        pos = np.asarray(pos, float)
        r0 = np.linalg.norm(pos, axis=1)
        good = r0 > 0
        if not good.all():
            pos, r0 = pos[good], r0[good]
        self.nhat = pos / r0[:, None]
        # inversione r -> z sulla tabella fiduciale (D_C strettamente crescente)
        order = np.argsort(dc_fid)
        self.z_of = np.interp(r0, dc_fid[order], z_tab[order])
        self.n = len(r0)
        del pos, r0
        print("[cache] %d random letti una volta sola; z ricavati in [%.4f, %.4f]"
              % (self.n, self.z_of.min(), self.z_of.max()))

    def positions_for(self, z_tab, dc_new):
        return self.nhat * np.interp(self.z_of, z_tab, dc_new)[:, None]


def box_of(G, pos, pad):
    ext = pos.max(axis=0) - pos.min(axis=0)
    k = int(np.argmax(ext))
    second = float(np.partition(ext, -2)[-2])
    try:
        box = G.derive_box(pos, pad=pad)
    except TypeError:
        box = G.derive_box(pos)
    bmin, L = unpack_box(box)
    return ext, k, second, bmin, L


def geometry_fast(G, cache, z_tab, dc_new, pad):
    pos = cache.positions_for(z_tab, dc_new)
    ext, k, second, bmin, L = box_of(G, pos, pad)
    del pos
    return {
        "N_rand": int(cache.n),
        "extent_x": float(ext[0]), "extent_y": float(ext[1]), "extent_z": float(ext[2]),
        "axis_dom": "xyz"[k], "axis_dom_margin": float(ext[k] / second - 1.0),
        "box_min": [float(v) for v in bmin],
        "box_size_mpc_h": L, "cell_size_mpc_h": L / NGRID,
        "sigma_px": R_SMOOTH / (L / NGRID),
        "D_C_ZMIN": float(np.interp(ZMIN, z_tab, dc_new)),
        "D_C_ZMAX": float(np.interp(ZMAX, z_tab, dc_new)),
    }


def geometry_at(G, setg, region, z_tab, dc_new, pad):
    call_set_geometry(setg, z_tab=z_tab, dc_tab=dc_new)
    pos, _w = _as_pos(G.positions(region, "ran"))
    ext = pos.max(axis=0) - pos.min(axis=0)
    k = int(np.argmax(ext))
    second = float(np.partition(ext, -2)[-2])
    try:
        box = G.derive_box(pos, pad=pad)
    except TypeError:
        box = G.derive_box(pos)
    bmin, L = unpack_box(box)
    n = len(pos)
    del pos
    return {
        "N_rand": int(n),
        "extent_x": float(ext[0]), "extent_y": float(ext[1]), "extent_z": float(ext[2]),
        "axis_dom": "xyz"[k],
        "axis_dom_margin": float(ext[k] / second - 1.0),
        "box_min": [float(v) for v in bmin],
        "box_size_mpc_h": L,
        "cell_size_mpc_h": L / NGRID,
        "sigma_px": R_SMOOTH / (L / NGRID),
        "D_C_ZMIN": float(np.interp(ZMIN, z_tab, dc_new)),
        "D_C_ZMAX": float(np.interp(ZMAX, z_tab, dc_new)),
    }


def _as_pos(out):
    if isinstance(out, tuple):
        return np.asarray(out[0]), (np.asarray(out[1]) if len(out) > 1 else None)
    return np.asarray(out), None


# --------------------------------------------------------------------------
# cancello
# --------------------------------------------------------------------------

def gate_fiducial(region, geom):
    ref = FROZEN.get(region, {})
    soft = ref.get("_soft", False)
    tol = SOFT_TOL if soft else REL_TOL
    print("\n[gate] punto fiduciale, regione %s (%s)"
          % (region, "soft, non ancora congelato" if soft else "stretto"))
    bad = []
    for k, v in ref.items():
        if k.startswith("_") or k not in geom:
            continue
        got = geom[k]
        rel = abs(got - v) / abs(v) if v else abs(got - v)
        flag = "ok" if rel <= tol else "SCARTO"
        print("    %-16s %20.10f  atteso %20.10f  rel %8.1e  %s" % (k, got, v, rel, flag))
        if rel > tol:
            bad.append(k)
    if bad and not soft:
        print("\n    CANCELLO FALLITO su: %s" % ", ".join(bad))
        print("    Non produrre numeri.  Cause tipiche: `kind` sbagliato in positions(),")
        print("    tabella fiduciale non ripristinata, pad diverso da %.1f." % PAD)
        sys.exit(3)
    if soft:
        print("\n    Valori da incollare in FROZEN['%s'] per congelare la regione:" % region)
        for k in ("box_size_mpc_h", "cell_size_mpc_h", "sigma_px",
                  "N_rand", "D_C_ZMIN", "D_C_ZMAX"):
            if k in geom:
                print("        %r: %r," % (k, geom[k]))
    print("    [gate] superato.")


# --------------------------------------------------------------------------
# I/O
# --------------------------------------------------------------------------

def cfg_hash(d):
    return hashlib.sha256(json.dumps(d, sort_keys=True).encode()).hexdigest()[:16]


def done_keys(path, cfg):
    out = set()
    if not path or not os.path.exists(path):
        return out
    with open(path, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
            except json.JSONDecodeError:
                continue
            if r.get("config_hash") == cfg:
                out.add((r.get("region"), r.get("point")))
    return out


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# --------------------------------------------------------------------------

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--const-module", default="phase8_cutsky_mocks")
    p.add_argument("--pad", type=float, default=PAD)
    p.add_argument("--out", default=None)
    p.add_argument("--blocks", nargs="*", default=["fid", "cosmo", "A", "B"],
                   help="quali blocchi eseguire")
    p.add_argument("--dry-run", action="store_true",
                   help="solo fiduciale e cancello, nessun altro punto")
    p.add_argument("--exact", action="store_true",
                   help="ricarica il catalogo a ogni punto invece di riscalare i raggi")
    p.add_argument("--verify-fast", action="store_true",
                   help="confronta il percorso veloce col completo su un punto")
    a = p.parse_args()

    G, M, setg, z_tab, dc_fid = attach(a.src, a.geom_module, a.const_module)
    cfg = cfg_hash({"pad": a.pad, "ngrid": NGRID, "R": R_SMOOTH,
                    "zmin": ZMIN, "zmax": ZMAX, "kind": "ran", "v": 1})
    done = done_keys(a.out, cfg) if a.out else set()

    points = [("FID", dict(kind="fid"))]
    if not a.dry_run:
        if "cosmo" in a.blocks:
            points += [("C_%.4f_%+.1f" % (o, w), dict(kind="cosmo", omm=o, w0=w))
                       for o, w in GRID_OMM_W0 if (o, w) != (OMM_FID, W0_FID)]
        if "A" in a.blocks:
            points += [(n, dict(kind="ap", alpha_iso=al, F_ap=1.0))
                       for n, al in LINE_A if n != "A2"]
        if "B" in a.blocks:
            points += [(n, dict(kind="ap", alpha_iso=1.0, F_ap=F))
                       for n, F in LINE_B if n != "B3"]

    cache = None if a.exact else RadialCache(G, setg, a.region, z_tab, dc_fid)

    rows = []
    try:
        for name, spec in points:
            if (a.region, name) in done:
                print("[skip] %s" % name)
                continue
            if spec["kind"] == "fid":
                dc_new, tag = dc_fid.copy(), {}
            elif spec["kind"] == "cosmo":
                dc_new, _ = deform_cosmology(z_tab, dc_fid, spec["omm"], spec["w0"])
                tag = {"omm": spec["omm"], "w0": spec["w0"]}
            else:
                dc_new = deform_ap(z_tab, dc_fid, spec["alpha_iso"], spec["F_ap"])
                tag = {"alpha_iso_target": spec["alpha_iso"], "F_ap_target": spec["F_ap"]}

            m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
            a_mmx, res_mmx = minimax_alpha(dc_fid[m], dc_new[m])

            if cache is None:
                geom = geometry_at(G, setg, a.region, z_tab, dc_new, a.pad)
            else:
                geom = geometry_fast(G, cache, z_tab, dc_new, a.pad)
                if a.verify_fast and name != "FID":
                    ex = geometry_at(G, setg, a.region, z_tab, dc_new, a.pad)
                    d = abs(ex["box_size_mpc_h"] - geom["box_size_mpc_h"])
                    print("  [verify-fast] %s: |L_veloce - L_completo| = %.3e "
                          "(rel %.1e)  %s" % (name, d, d / ex["box_size_mpc_h"],
                                              "OK" if d < 1e-6 else "SCARTO"))
                    a.verify_fast = False
            rec = {"schema": "paper2_item12a_geom_v1", "config_hash": cfg,
                   "region": a.region, "point": name, "block": spec["kind"],
                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                   "alpha_iso_minimax": a_mmx,
                   "anis_residual_minimax_hMpc": res_mmx}
            rec.update(tag)
            rec.update(geom)
            rec["anis_residual_minimax_vox"] = res_mmx / geom["cell_size_mpc_h"]
            rec["alpha_box"] = geom["box_size_mpc_h"] / FROZEN["NGC"]["box_size_mpc_h"] \
                if a.region == "NGC" else None

            if name == "FID":
                gate_fiducial(a.region, geom)
                fid_geom = geom
            else:
                rec["alpha_box"] = geom["box_size_mpc_h"] / fid_geom["box_size_mpc_h"]
                rec["axis_dom_switch"] = geom["axis_dom"] != fid_geom["axis_dom"]
                rec["alpha_box_minus_alpha_iso"] = rec["alpha_box"] - a_mmx
                print("  %-14s L=%10.4f dx=%9.6f sig=%.6f asse=%s(%.1f%%) "
                      "a_iso=%.6f a_box=%.6f res=%.4f vox%s"
                      % (name, geom["box_size_mpc_h"], geom["cell_size_mpc_h"],
                         geom["sigma_px"], geom["axis_dom"],
                         100 * geom["axis_dom_margin"], a_mmx, rec["alpha_box"],
                         rec["anis_residual_minimax_vox"],
                         "  <<< CAMBIO-ASSE" if rec["axis_dom_switch"] else ""))
            rows.append(rec)
            if a.out:
                append_atomic(a.out, rec)
    finally:
        call_set_geometry(setg, z_tab=z_tab, dc_tab=dc_fid)
        print("\n[restore] geometria fiduciale ripristinata.")

    print("\n%d punti scritti%s." % (len(rows), (" in " + a.out) if a.out else ""))


if __name__ == "__main__":
    main()
