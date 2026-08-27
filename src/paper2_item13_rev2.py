#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_item13_rev2.py — linea B a CUBO COSTANTE

Perche' la revisione.  La rev. 1 definiva il blocco B come "alpha_iso = 1",
sostenendo che il tiling dipende da alpha_iso e non da F_AP e che la linea del
segnale fosse quindi immune.  L'item 1.5a l'ha smentito: il lato del cubo e'
fissato da alpha_BOX, non da alpha_iso, e alpha_box varia dello 0.8% lungo B.
In NGC le repliche intere passano da 16 (B1, B2) a 15 (FID, B4) a 14 (B5), con
la frazione indipendente che scivola del 2.5% lungo la linea che dovrebbe
portare il segnale puro.

Perche' la soluzione e' legittima.  Per la Proposizione 2 le due scelte
differiscono per una dilatazione isotropa pura, che con box ri-derivato lascia
le coordinate di griglia invariate a 1.3e-2 voxel: sono lo stesso oggetto
fisico, e il residuo IN VOXEL e' invariante di gauge.

Perche' e' la scelta giusta.  Il tiling introduce una scala fisica ESTERNA — il
lato 1000 h^-1 Mpc della scatola Quijote — che non scala con la deformazione.
Quella scala CONSUMA la liberta' di gauge che la Prop. 2 garantisce.  Fra tutti
i gauge equivalenti, quello a L costante e' l'unico che neutralizza il
confondente, e in piu' rende costanti dx e sigma_px: sparisce anche l'1.64%
picco-picco che era il problema dell'item 1.4a.

Costruzione.  La famiglia e' f(r) = A r^p (Lemma 3; p = 1/F nella convenzione
standard alpha_perp/alpha_par, p = F_ap nella convenzione della pipeline, come
stabilito da 1.3a).  Per ogni bersaglio di residuo si risolve

    esterno:  p   tale che  residuo_minimax(A(p), p) = bersaglio [h^-1 Mpc]
    interno:  A   tale che  L(A, p) = L_fiduciale

Il bersaglio e' dichiarato in unita' FISICHE, non in voxel, cosi' i due emisferi
sondano la stessa deformazione: 8.875 h^-1 Mpc e' il residuo minimax massimo
sull'intera griglia (Om=0.25, w0=-1.2), e la linea e' simmetrica.

Uso:
    python src\\paper2_item13_rev2.py --region NGC --out results\\paper2\\item13rev2_NGC.jsonl
    python src\\paper2_item13_rev2.py --region SGC --out results\\paper2\\item13rev2_SGC.jsonl
    python src\\paper2_item13_rev2.py --region NGC --verify-tiling
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
NGRID = 128
PAD = 5.0
R_SMOOTH = 5.0
L_BOX = 1000.0

FROZEN_L = {"NGC": 1997.3629167166155, "SGC": 1904.4501607158168}
# residuo minimax massimo sulla griglia (Om, w0), gauge di Chebyshev
RESID_MAX_HMPC = 8.875
TARGETS = [("B1", -1.0), ("B2", -0.5), ("B3", 0.0), ("B4", +0.5), ("B5", +1.0)]

# Angoli: cosmologie reali, da RI-GAUGIARE anch'esse a cubo costante.  Anche il
# loro alpha_iso e' gauge, e lasciarle nel gauge originale reintroduce sia il
# gradino di tiling (C1 aveva 17 repliche, C4 14, contro 15 del fiduciale) sia la
# scalinata di w_bar (C1 frac<0.99 = 0.034, C4 = 0.152, contro 0.078).
CORNERS = [("C1", 0.2500, -1.2), ("C2", 0.2500, -0.8),
           ("C3", 0.3500, -1.2), ("C4", 0.3500, -0.8)]
OMM_FID, W0_FID = 0.3175, -1.0
C_OVER_H0 = 2997.92458


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


def minimax(r_fid, r_new):
    """alpha di Chebyshev e residuo: min_alpha max |f - alpha r|."""
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


def brent(f, lo, hi, tol=1e-13, nmax=200):
    """Bisezione robusta: le funzioni qui sono monotone e ben condizionate."""
    flo, fhi = f(lo), f(hi)
    if flo * fhi > 0:
        raise ValueError("radice non racchiusa: f(%g)=%g f(%g)=%g" % (lo, flo, hi, fhi))
    for _ in range(nmax):
        mid = 0.5 * (lo + hi)
        fm = f(mid)
        if abs(hi - lo) < tol:
            return mid
        if flo * fm <= 0:
            hi, fhi = mid, fm
        else:
            lo, flo = mid, fm
    return 0.5 * (lo + hi)


class Cache:
    """
    Una sola lettura del catalogo random.  La deformazione e' puramente radiale,
    quindi basta riscalare i raggi: identico al ricaricare, e non serve rifare
    l'inversione r -> z a ogni tentativo del solutore.
    """

    def __init__(self, G, setg, region, z_tab, dc_fid):
        call_set(setg, z_tab=z_tab, dc_tab=dc_fid)
        out = G.positions(region, "ran")
        pos = np.asarray(out[0] if isinstance(out, tuple) else out, float)
        r0 = np.linalg.norm(pos, axis=1)
        good = r0 > 0
        pos, r0 = pos[good], r0[good]
        self.nhat = pos / r0[:, None]
        order = np.argsort(dc_fid)
        self.z_of = np.interp(r0, dc_fid[order], z_tab[order])
        self.r0 = r0
        self.n = len(r0)
        del pos
        print("[cache] %d random letti una volta sola" % self.n)

    def box_side(self, A, p):
        r = A * self.r0 ** p
        x = self.nhat * r[:, None]
        ext = x.max(axis=0) - x.min(axis=0)
        return float(ext.max() + 2 * PAD)


# --------------------------------------------------------------------------

def solve_line(cache, z_tab, dc_fid, L_target, targets, verbose=True):
    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    r = dc_fid[m]

    def A_for_L(p):
        """A tale che il cubo derivato abbia lato L_target."""
        return brent(lambda A: cache.box_side(A, p) - L_target,
                     1e-6, 1e6 if p < 1 else 1e3)

    def resid_for(p):
        A = A_for_L(p)
        f = A * r ** p
        a, res = minimax(r, f)
        return A, a, res

    rows = []
    for name, frac in targets:
        tgt = frac * RESID_MAX_HMPC
        if abs(frac) < 1e-12:
            p = 1.0
        else:
            # p > 1 e p < 1 danno residui di segno opposto nella parametrizzazione;
            # il segno di frac sceglie il ramo.
            g = lambda pp: resid_for(pp)[2] - abs(tgt)          # noqa: E731
            p = brent(g, 1.0 + 1e-9, 1.12) if frac > 0 else brent(g, 0.90, 1.0 - 1e-9)
        A, a_iso, res = resid_for(p)
        L = cache.box_side(A, p)
        dx = L / NGRID
        rows.append({
            "point": name, "target_frac": frac, "target_resid_hMpc": tgt,
            "p_exponent": p,
            "F_standard_perp_over_par": 1.0 / p,
            "F_pipeline_par_over_perp": p,
            "A": A, "box_size_mpc_h": L, "cell_size_mpc_h": dx,
            "sigma_px": R_SMOOTH / dx,
            "alpha_iso_minimax": a_iso,
            "anis_residual_minimax_hMpc": res,
            "anis_residual_minimax_vox": res / dx,
        })
        if verbose:
            print("  %-3s p=%.8f  F_std=%.6f  F_pipe=%.6f  A=%.6g" %
                  (name, p, 1.0 / p, p, A))
            print("      L=%.6f  dx=%.7f  sigma_px=%.7f  a_iso=%.6f  res=%.4f = %.4f vox"
                  % (L, dx, R_SMOOTH / dx, a_iso, res, res / dx))
    return rows


def e_of_z(z, omm, w0):
    return np.sqrt(omm * (1 + z) ** 3 + (1 - omm) * (1 + z) ** (3 * (1 + w0)))


def dc_scratch(z, omm, w0):
    i = 1.0 / e_of_z(z, omm, w0)
    return C_OVER_H0 * np.concatenate([[0.0], np.cumsum(0.5 * (i[1:] + i[:-1]) * np.diff(z))])


def cosmo_ratio(z_tab, omm, w0):
    """g(z) = D_C^new / D_C^fid, come rapporto: la costante c/H0 si cancella."""
    zf = np.linspace(0.0, max(z_tab.max(), ZMAX + 0.05), 90001)
    a_, b_ = dc_scratch(zf, OMM_FID, W0_FID), dc_scratch(zf, omm, w0)
    g = np.ones_like(zf)
    nz = a_ > 0
    g[nz] = b_[nz] / a_[nz]
    g[~nz] = g[nz][0]
    return np.interp(z_tab, zf, g)


def solve_corners(cache, z_tab, dc_fid, L_target, verbose=True):
    """
    Ogni angolo e' ri-gauge a cubo costante: dc = c * dc_fid * g(z), con c
    scelto perche' il cubo derivato abbia lato L_target.  La deformazione
    ANISOTROPA e' intatta; cambia solo la parte isotropa, che e' gauge.
    """
    m = (z_tab >= ZMIN) & (z_tab <= ZMAX)
    r = dc_fid[m]
    order = np.argsort(dc_fid)
    rows = []
    for name, omm, w0 in CORNERS:
        g = cosmo_ratio(z_tab, omm, w0)
        g_of_r = np.interp(cache.r0, dc_fid[order], g[order])

        def side(c):
            rr = c * cache.r0 * g_of_r
            x = cache.nhat * rr[:, None]
            ext = x.max(axis=0) - x.min(axis=0)
            return float(ext.max() + 2 * PAD)

        c = brent(lambda cc: side(cc) - L_target, 0.5, 2.0)
        f = c * dc_fid * g
        a_iso, res = minimax(r, f[m])
        L = side(c)
        dx = L / NGRID
        rows.append({
            "point": name, "omm": omm, "w0": w0, "c_gauge": c,
            "box_size_mpc_h": L, "cell_size_mpc_h": dx,
            "sigma_px": R_SMOOTH / dx, "alpha_iso_minimax": a_iso,
            "anis_residual_minimax_hMpc": res,
            "anis_residual_minimax_vox": res / dx,
        })
        if verbose:
            print("  %-3s Om=%.4f w0=%+.1f  c=%.8f  L=%.6f  dx=%.7f  sigma_px=%.7f"
                  % (name, omm, w0, c, L, dx, R_SMOOTH / dx))
            print("      a_iso=%.6f  res=%.4f h^-1 Mpc = %.4f vox"
                  % (a_iso, res, res / dx))
    return rows


def cmd(a):
    G, M, setg, z_tab, dc_fid = attach(a.src, a.geom_module, a.const_module)
    L_target = FROZEN_L[a.region]
    print("=" * 72)
    print("1.3 rev. 2 — linea B a cubo costante, regione %s" % a.region)
    print("=" * 72)
    print("  L bersaglio = %.10f  (congelato)" % L_target)
    print("  residuo di riferimento = %.3f h^-1 Mpc (massimo sulla griglia)\n"
          % RESID_MAX_HMPC)

    cache = Cache(G, setg, a.region, z_tab, dc_fid)
    print()
    rows = solve_line(cache, z_tab, dc_fid, L_target, TARGETS)
    if not a.no_corners:
        print("\n  angoli, ri-gauge a cubo costante:")
        rows += solve_corners(cache, z_tab, dc_fid, L_target)
    print("\n  NB: la linea A collassa sul fiduciale.  Per una dilatazione pura")
    print("      f = A r, imporre L = L_fid da' A*E + 2p = E + 2p, cioe' A = 1")
    print("      ESATTO: A1 e A3 diventano il punto fiduciale.  Non e' una perdita,")
    print("      e' la Proposizione 2 resa manifesta dal gauge.  Il test di chiusura")
    print("      migra nel cancello 2.2, che lo fa ad alpha = 1.05.")

    Ls = np.array([r["box_size_mpc_h"] for r in rows])
    sg = np.array([r["sigma_px"] for r in rows])
    print("\n" + "=" * 72)
    print("VERIFICHE")
    print("=" * 72)
    print("  L costante?      escursione %.3e h^-1 Mpc  (rel %.1e)"
          % (Ls.max() - Ls.min(), (Ls.max() - Ls.min()) / Ls.mean()))
    print("  sigma_px costante? escursione %.3e  (rel %.1e)  <- era 1.64%% picco-picco"
          % (sg.max() - sg.min(), (sg.max() - sg.min()) / sg.mean()))
    aa = np.array([r["alpha_iso_minimax"] for r in rows])
    print("  alpha_iso deriva da %.6f a %.6f (%.2f%%): e' GAUGE, non un difetto"
          % (aa.min(), aa.max(), 100 * (aa.max() / aa.min() - 1)))
    rv = np.array([r["anis_residual_minimax_vox"] for r in rows])
    print("  residuo in voxel: %s" % "  ".join("%.4f" % v for v in rv))

    if a.verify_tiling:
        print("\n" + "=" * 72)
        print("TILING sui punti nuovi")
        print("=" * 72)
        reps = []
        try:
            for rrow in rows:
                if "p_exponent" in rrow:
                    dc_new = rrow["A"] * dc_fid ** rrow["p_exponent"]
                else:
                    dc_new = rrow["c_gauge"] * dc_fid * cosmo_ratio(
                        z_tab, rrow["omm"], rrow["w0"])
                call_set(setg, z_tab=z_tab, dc_tab=dc_new)
                ds = G.data_side(a.region)
                mask = None
                for v in ds.values():
                    if isinstance(v, np.ndarray) and v.dtype == bool and v.ndim == 3:
                        mask = v
                    elif isinstance(v, (list, tuple)):
                        for x in v:
                            if isinstance(x, np.ndarray) and x.dtype == bool and x.ndim == 3:
                                mask = x
                idx = np.argwhere(mask)
                x = np.asarray(ds["box_min"], float) + (idx + 0.5) * float(ds["cell_size_mpc_h"])
                rep = np.floor(x / L_BOX).astype(np.int32)
                nrep = int(np.unique(rep, axis=0).shape[0])
                dxx = float(ds["cell_size_mpc_h"])
                ncell = int(np.ceil(L_BOX / dxx))
                cell = np.clip(np.floor((x - rep * L_BOX) / dxx).astype(np.int64),
                               0, ncell - 1)
                flat = (cell[:, 0] * ncell + cell[:, 1]) * ncell + cell[:, 2]
                u = np.unique(flat).size
                reps.append(nrep)
                rrow["n_replicas_total"] = nrep
                rrow["independent_fraction"] = u / len(flat)
                print("  %-3s L=%.4f  repliche=%d  indip=%.4f"
                      % (rrow["point"], float(ds["box_size_mpc_h"]), nrep, u / len(flat)))
        finally:
            call_set(setg, z_tab=z_tab, dc_tab=dc_fid)
            try:
                G.data_side(a.region, verbose=False)
            except Exception:
                pass
            print("\n[restore] geometria fiduciale ripristinata.")
        if len(set(reps)) == 1:
            print("\n  GRADINO ELIMINATO: %d repliche su tutti e %d i punti della griglia."
                  % (reps[0], len(reps)))
        else:
            print("\n  !! il gradino sopravvive: %s. Il gauge a L costante non basta,"
                  % sorted(set(reps)))
            print("     e va capito perche' prima di pre-registrare.")

    if a.out:
        os.makedirs(os.path.dirname(os.path.abspath(a.out)) or ".", exist_ok=True)
        with open(a.out, "a", encoding="utf-8") as fh:
            for r in rows:
                r.update({"schema": "paper2_item13rev2_v1", "region": a.region,
                          "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                          "gauge": "constant_embedding_box",
                          "L_target": L_target})
                fh.write(json.dumps(r, sort_keys=True) + "\n")
            fh.flush()
            os.fsync(fh.fileno())
        print("\nscritto in %s" % a.out)

    print("\n  Da passare a make_dc_tab_ap (convenzione alpha_par/alpha_perp, item 1.3a):")
    for r in rows:
        if "p_exponent" in r:
            print("    %-3s  F_ap=%.8f   A=%.8g" % (r["point"], r["p_exponent"], r["A"]))
        else:
            print("    %-3s  (cosmologia Om=%.4f w0=%+.1f, dc = %.8f * dc_fid * g(z))"
                  % (r["point"], r["omm"], r["w0"], r["c_gauge"]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--src", default="src")
    p.add_argument("--geom-module", default="paper2_data_geometry")
    p.add_argument("--const-module", default="phase8_cutsky_mocks")
    p.add_argument("--verify-tiling", action="store_true")
    p.add_argument("--no-corners", action="store_true",
                   help="solo linea B (comportamento della prima versione)")
    p.add_argument("--out", default=None)
    cmd(p.parse_args())


if __name__ == "__main__":
    main()
