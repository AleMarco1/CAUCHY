#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_item12a_apgrid.py — Paper 2, item 1.2a

Ricalcola la tabella di triage AP usando il bounding box EFFETTIVO ricomputato dal
catalogo random per ogni punto di griglia, invece di assumere che il lato del cubo
scali come alpha_iso.

Colonne nuove rispetto alla tabella congelata:
  * axis_dom      : quale asse cartesiano fissa il lato del cubo (rottura (v) di 1.1b)
  * alpha_box     : L(punto)/L(fiduciale) -- NON coincide con alpha_iso
  * dx_eff        : passo di griglia effettivo
  * sigma_px_eff  : R / dx_eff, non 0.3204/alpha_iso
  * F_AP          : in ENTRAMBE le convenzioni, esplicitamente etichettate

Modalita':
  --cosmo-only : solo colonne cosmologiche, non richiede dati.  Secondi.
  --selftest   : validazione della meccanica su footprint sintetico.  Secondi.
  (default)    : richiede il catalogo random della regione.        Minuti.

Esempi (PowerShell):
  python src\\paper2_item12a_apgrid.py --cosmo-only --out results\\paper2\\item12a_cosmo.jsonl
  python src\\paper2_item12a_apgrid.py --selftest
  python src\\paper2_item12a_apgrid.py --region NGC --randoms <path> ^
      --out results\\paper2\\item12a_NGC.jsonl

Output append-only JSONL, scrittura atomica, ripartibile: rilanciare salta i punti
gia' presenti con la stessa firma di configurazione.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import numpy as np

# --------------------------------------------------------------------------
# Costanti congelate.  Ogni valore qui e' un cancello: se il run non lo
# riproduce, il run si ferma.
# --------------------------------------------------------------------------

C_OVER_H0 = 2997.92458          # h^-1 Mpc
OMM_FID, W0_FID = 0.3175, -1.0  # fiduciale Quijote
ZMIN, ZMAX = 0.10, 0.40         # taglio vero del carving (carve_cutsky:453)
NGRID = 128
PAD_DEFAULT = 5.0               # h^-1 Mpc, additivo nell'implementazione
R_SMOOTH = 5.0                  # h^-1 Mpc, nominale
SIGMA_PX_FID = 0.3204
# Il limite pratico NON e' una costante globale: dipende dalla regione, perche'
# d_med e' la mediana della distanza euclidea dal bordo della MASCHERA di quella
# regione. Trattarlo come globale e' l'errore che ha prodotto un falso allarme
# sul fiduciale SGC. Definizione e valori vivono in paper2_data_geometry.
try:
    from paper2_data_geometry import PRACTICAL_LIMIT, D_MED_VOXEL
except ImportError:                       # eseguito fuori da src/
    D_MED_VOXEL = {"NGC": 3.0000000, "SGC": 2.8284271}
    PRACTICAL_LIMIT = {r: d / 9.0 for r, d in D_MED_VOXEL.items()}

FROZEN = {
    "NGC": {"L": 1997.36, "dx": 1997.36 / NGRID},
    "SGC": {"L": 14.88 * NGRID, "dx": 14.88},
}
L_TOL = 0.05                    # h^-1 Mpc; il cancello di §2 del record

GRID_OMM_W0 = [
    (0.2500, -1.2), (0.2500, -1.0), (0.2500, -0.8),
    (0.2800, -1.2), (0.2800, -1.0), (0.2800, -0.8),
    (0.3175, -1.2), (0.3175, -1.0), (0.3175, -0.8),
    (0.3500, -1.2), (0.3500, -1.0), (0.3500, -0.8),
]

# valori congelati della tabella del 25 agosto, per il cancello cosmologico
FROZEN_ALPHA_ISO = {
    (0.2500, -1.2): 1.0406, (0.2500, -1.0): 1.0150, (0.2500, -0.8): 0.9892,
    (0.2800, -1.2): 1.0320, (0.2800, -1.0): 1.0082, (0.2800, -0.8): 0.9840,
    (0.3175, -1.2): 1.0218, (0.3175, -1.0): 1.0000, (0.3175, -0.8): 0.9778,
    (0.3500, -1.2): 1.0132, (0.3500, -1.0): 0.9931, (0.3500, -0.8): 0.9725,
}
ALPHA_TOL = 2e-4


# --------------------------------------------------------------------------
# Cosmologia
# --------------------------------------------------------------------------

def e_of_z(z, omm, w0):
    """H(z)/H0 per w0CDM piatto.  OML = 1 - OMM, come nel codice."""
    return np.sqrt(omm * (1.0 + z) ** 3
                   + (1.0 - omm) * (1.0 + z) ** (3.0 * (1.0 + w0)))


def dc_table(z_tab, omm, w0):
    """D_C(z) in h^-1 Mpc su z_tab, che deve partire da 0 ed essere crescente."""
    integrand = 1.0 / e_of_z(z_tab, omm, w0)
    cum = np.concatenate([[0.0],
                          np.cumsum(0.5 * (integrand[1:] + integrand[:-1])
                                    * np.diff(z_tab))])
    return C_OVER_H0 * cum


def minimax_alpha(r_fid, r_new):
    """
    Chebyshev: alpha che minimizza max|f - alpha r|, senza pesi e senza scipy.

    h(a) = max_i r_i(a - g_i) - max_i r_i(g_i - a)  e' strettamente crescente in a;
    l'ottimo e' il suo zero.  Bisezione, 200 passi = precisione macchina.
    Motivazione: per la Proposizione 2 la parte isotropa e' assorbibile nella
    convenzione di griglia, quindi il residuo FISICO e' il minimo su alpha,
    non quello del fit ai minimi quadrati.
    """
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


def fit_alpha_iso(r_fid, r_new, weights=None):
    """Minimi quadrati per l'origine: alpha = argmin sum w (f - a r)^2."""
    w = np.ones_like(r_fid) if weights is None else weights
    return float((w * r_fid * r_new).sum() / (w * r_fid * r_fid).sum())


def cosmo_row(omm, w0, nz_weights=None, nz_grid=None):
    """Colonne che non richiedono il catalogo: alpha_iso, residuo, F_AP."""
    z_full = np.linspace(0.0, ZMAX + 0.05, 90001)
    sel = (z_full >= ZMIN) & (z_full <= ZMAX)
    zz = z_full[sel]
    r_fid = dc_table(z_full, OMM_FID, W0_FID)[sel]
    r_new = dc_table(z_full, omm, w0)[sel]

    w_uni = None
    a_uni = fit_alpha_iso(r_fid, r_new, w_uni)

    if nz_weights is not None and nz_grid is not None:
        w_nz = np.interp(zz, nz_grid, nz_weights, left=0.0, right=0.0)
        a_nz = fit_alpha_iso(r_fid, r_new, w_nz)
    else:
        w_nz, a_nz = None, None

    a_ref = a_nz if a_nz is not None else a_uni
    resid = float(np.max(np.abs(r_new - a_ref * r_fid)))
    a_mmx, resid_mmx = minimax_alpha(r_fid, r_new)

    # dilatazione locale e distorsione AP, in entrambe le convenzioni
    g = r_new / r_fid                                   # alpha_perp locale
    alpha_par = e_of_z(zz, OMM_FID, W0_FID) / e_of_z(zz, omm, w0)
    F_perp_over_par = g / alpha_par                     # = D_M H / (D_M H)^fid
    F_par_over_perp = 1.0 / F_perp_over_par             # convenzione della tabella 25 ago

    return {
        "alpha_iso_uniform_z": a_uni,
        "alpha_iso_nz_weighted": a_nz,
        "alpha_iso_used": a_ref,
        "alpha_iso_weighting": "nz" if a_nz is not None else "uniform_z",
        "anis_residual_hMpc": resid,
        "alpha_iso_minimax": a_mmx,
        "anis_residual_minimax_hMpc": resid_mmx,
        "gauge_gain_pct": (100.0 * (1.0 - resid_mmx / resid)) if resid > 0 else 0.0,
        "g_local_min": float(g.min()), "g_local_max": float(g.max()),
        "F_AP_perp_over_par_min": float(F_perp_over_par.min()),
        "F_AP_perp_over_par_max": float(F_perp_over_par.max()),
        "F_AP_par_over_perp_min": float(F_par_over_perp.min()),
        "F_AP_par_over_perp_max": float(F_par_over_perp.max()),
        "monotone_ok": bool(np.all(np.diff(r_new) > 0)),   # cancello 2.4, gratis
    }


# --------------------------------------------------------------------------
# Geometria dal catalogo random
# --------------------------------------------------------------------------

def sky_to_unit(ra_deg, dec_deg):
    ra = np.radians(ra_deg)
    dec = np.radians(dec_deg)
    cd = np.cos(dec)
    return np.stack([cd * np.cos(ra), cd * np.sin(ra), np.sin(dec)], axis=1)


def derive_box_local(xyz, pad=PAD_DEFAULT, ngrid=NGRID):
    """
    Regola documentata: lato del cubo = max_k(estensione_k) + 2*pad,
    origine per asse = min_k - pad.  Restituisce anche l'asse dominante.
    """
    lo = xyz.min(axis=0)
    hi = xyz.max(axis=0)
    ext = hi - lo
    axis_dom = int(np.argmax(ext))
    L = float(ext[axis_dom] + 2.0 * pad)
    return {
        "extent_x": float(ext[0]), "extent_y": float(ext[1]), "extent_z": float(ext[2]),
        "axis_dom": "xyz"[axis_dom],
        "axis_dom_margin": float(ext[axis_dom] / np.partition(ext, -2)[-2] - 1.0),
        "box_min": [float(v) for v in (lo - pad)],
        "L": L,
        "dx": L / ngrid,
    }


def load_randoms(path, ra_col, dec_col, z_col):
    """FITS, .npy strutturato, o CSV.  Restituisce (ra, dec, z) in gradi/adim."""
    ext = os.path.splitext(path)[1].lower()
    if ext in (".fits", ".fit", ".fits.gz"):
        try:
            import fitsio
            d = fitsio.read(path, columns=[ra_col, dec_col, z_col])
        except ImportError:
            from astropy.io import fits
            with fits.open(path, memmap=True) as h:
                d = h[1].data
            return (np.asarray(d[ra_col], float), np.asarray(d[dec_col], float),
                    np.asarray(d[z_col], float))
    elif ext == ".npy":
        d = np.load(path, allow_pickle=False)
    else:
        d = np.genfromtxt(path, delimiter=",", names=True)
    return (np.asarray(d[ra_col], float), np.asarray(d[dec_col], float),
            np.asarray(d[z_col], float))


# --------------------------------------------------------------------------
# I/O append-only
# --------------------------------------------------------------------------

def config_hash(payload):
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()[:16]


def already_done(out_path, cfg):
    done = set()
    if not os.path.exists(out_path):
        return done
    with open(out_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                rec = json.loads(line)
            except json.JSONDecodeError:
                continue
            if rec.get("config_hash") == cfg:
                done.add((rec.get("region"), rec.get("omm"), rec.get("w0")))
    return done


def append_atomic(out_path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(out_path)) or ".", exist_ok=True)
    with open(out_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# --------------------------------------------------------------------------
# Cancelli
# --------------------------------------------------------------------------

def gate_cosmology():
    """Riproduce i 12 alpha_iso congelati.  Nessun numero nuovo senza questo."""
    bad = []
    for (omm, w0), a_ref in FROZEN_ALPHA_ISO.items():
        row = cosmo_row(omm, w0)
        if abs(row["alpha_iso_uniform_z"] - a_ref) > ALPHA_TOL:
            bad.append((omm, w0, row["alpha_iso_uniform_z"], a_ref))
    if bad:
        print("CANCELLO COSMOLOGICO FALLITO:", file=sys.stderr)
        for b in bad:
            print("   Om=%.4f w0=%.1f  ottenuto %.6f  atteso %.4f" % b, file=sys.stderr)
        sys.exit(2)
    print("[gate] 12/12 alpha_iso riprodotti entro %.0e" % ALPHA_TOL)


def gate_fiducial_box(region, geom):
    ref = FROZEN[region]["L"]
    if abs(geom["L"] - ref) > L_TOL:
        print("CANCELLO GEOMETRICO FALLITO: %s L=%.4f atteso %.4f (tol %.2f)"
              % (region, geom["L"], ref, L_TOL), file=sys.stderr)
        print("  -> il box non e' derivato dai random con questa regola, "
              "oppure pad/ngrid differiscono.  Fermarsi qui.", file=sys.stderr)
        sys.exit(3)
    print("[gate] %s: L fiduciale %.4f riprodotto (atteso %.4f)" % (region, geom["L"], ref))


# --------------------------------------------------------------------------
# Esecuzione
# --------------------------------------------------------------------------

def run(args):
    gate_cosmology()

    # cosmo_only nella firma: altrimenti i record cosmologici bloccherebbero
    # per (region, omm, w0) i record geometrici scritti nello stesso file.
    cfg = config_hash({"pad": args.pad, "ngrid": args.ngrid, "R": args.R,
                       "zmin": ZMIN, "zmax": ZMAX, "v": 2,
                       "cosmo_only": bool(args.cosmo_only)})
    done = already_done(args.out, cfg) if args.out else set()

    ra = dec = z = None
    nz_grid = nz_w = None
    if not args.cosmo_only:
        ra, dec, z = load_randoms(args.randoms, args.ra_col, args.dec_col, args.z_col)
        keep = (z >= ZMIN) & (z <= ZMAX)
        ra, dec, z = ra[keep], dec[keep], z[keep]
        print("[dati] %s: %d random nel taglio z" % (args.region, z.size))
        nz_w, edges = np.histogram(z, bins=120, range=(ZMIN, ZMAX))
        nz_grid = 0.5 * (edges[1:] + edges[:-1])
        nz_w = nz_w.astype(float)
        nhat = sky_to_unit(ra, dec)

    z_full = np.linspace(0.0, ZMAX + 0.05, 90001)
    rows = []
    geom_fid = None

    for omm, w0 in GRID_OMM_W0:
        key = (args.region, omm, w0)
        if key in done:
            print("[skip] gia' presente: Om=%.4f w0=%.1f" % (omm, w0))
            continue

        rec = {"schema": "paper2_item12a_v1", "config_hash": cfg,
               "region": args.region, "omm": omm, "w0": w0,
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
        rec.update(cosmo_row(omm, w0, nz_w, nz_grid))

        if not args.cosmo_only:
            dc = dc_table(z_full, omm, w0)
            r_j = np.interp(z, z_full, dc)
            xyz = nhat * r_j[:, None]
            geom = derive_box_local(xyz, pad=args.pad, ngrid=args.ngrid)
            if (omm, w0) == (OMM_FID, W0_FID):
                gate_fiducial_box(args.region, geom)
                geom_fid = geom
            rec.update(geom)
            rec["sigma_px_eff"] = args.R / geom["dx"]
            rec["sigma_px_approx_old"] = SIGMA_PX_FID / rec["alpha_iso_used"]
            lim = PRACTICAL_LIMIT[args.region]
            rec["d_med_voxel"] = D_MED_VOXEL[args.region]
            rec["practical_limit"] = lim
            rec["margin_vs_dmed9"] = 1.0 - rec["sigma_px_eff"] / lim
            rec["anis_residual_vox"] = rec["anis_residual_hMpc"] / geom["dx"]
            rec["anis_residual_minimax_vox"] = rec["anis_residual_minimax_hMpc"] / geom["dx"]
            # In SGC il limite e' superato in TUTTI i punti, fiduciale compreso:
            # li' non e' un criterio di esclusione ma un caveat (item 1.2c), e il
            # rimedio e' l'erosione. Il flag resta, ma va letto per regione.
            rec["over_practical_limit"] = bool(rec["sigma_px_eff"] > lim)
            rec["excluded_1_2c_sigma_px"] = bool(
                args.region == "NGC" and rec["sigma_px_eff"] > lim)
            if geom_fid is not None:
                rec["alpha_box"] = geom["L"] / geom_fid["L"]
                rec["alpha_box_minus_alpha_iso"] = rec["alpha_box"] - rec["alpha_iso_used"]
                rec["axis_dom_switch"] = bool(geom["axis_dom"] != geom_fid["axis_dom"])

        rows.append(rec)
        if args.out:
            append_atomic(args.out, rec)

    print_table(rows, args.cosmo_only)
    return rows


def print_table(rows, cosmo_only):
    if not rows:
        print("nessuna riga nuova.")
        return
    print()
    if cosmo_only:
        hdr = ("%7s %5s | %9s %9s | %8s | %9s %8s %7s | %13s" %
               ("Om", "w0", "a_iso(z)", "a_iso(nz)", "res LSQ",
                "a_minimax", "res mmx", "guad.", "F perp/par"))
        print(hdr); print("-" * len(hdr))
        for r in rows:
            print("%7.4f %5.1f | %9.5f %9s | %8.2f | %9.5f %8.2f %6.1f%% | %6.4f-%6.4f" % (
                r["omm"], r["w0"], r["alpha_iso_uniform_z"],
                ("%.5f" % r["alpha_iso_nz_weighted"]) if r["alpha_iso_nz_weighted"] else "--",
                r["anis_residual_hMpc"], r["alpha_iso_minimax"],
                r["anis_residual_minimax_hMpc"], r["gauge_gain_pct"],
                r["F_AP_perp_over_par_min"], r["F_AP_perp_over_par_max"]))
    else:
        hdr = ("%7s %5s | %5s %6s | %9s %9s %9s | %8s %8s %7s | %s" %
               ("Om", "w0", "asse", "marg", "L", "dx", "a_box",
                "a_iso", "sig_px", "res vox", "flag"))
        print(hdr); print("-" * len(hdr))
        for r in rows:
            flags = []
            if r.get("axis_dom_switch"):
                flags.append("CAMBIO-ASSE")
            if r.get("over_practical_limit") and not r.get("excluded_1_2c_sigma_px"):
                flags.append("oltre-limite(caveat)")
            if r.get("excluded_1_2c_sigma_px"):
                flags.append("ESCLUSO-sigma_px")
            if abs(r.get("alpha_box_minus_alpha_iso", 0.0)) > 5e-4:
                flags.append("a_box!=a_iso")
            print("%7.4f %5.1f | %5s %5.1f%% | %9.3f %9.5f %9.5f | %8.5f %8.4f %7.3f | %s" % (
                r["omm"], r["w0"], r["axis_dom"], 100 * r["axis_dom_margin"],
                r["L"], r["dx"], r.get("alpha_box", float("nan")),
                r["alpha_iso_used"], r["sigma_px_eff"], r["anis_residual_vox"],
                ",".join(flags) if flags else "-"))
    print()


# --------------------------------------------------------------------------
# Selftest: meccanica, non dati
# --------------------------------------------------------------------------

def selftest():
    print("=== selftest ===")
    gate_cosmology()

    rng = np.random.default_rng(20260825)
    n = 200_000
    ra = rng.uniform(120.0, 240.0, n)
    dec = np.degrees(np.arcsin(rng.uniform(np.sin(np.radians(-5.0)),
                                           np.sin(np.radians(60.0)), n)))
    u = rng.uniform(0, 1, n)
    z = ZMIN + (ZMAX - ZMIN) * u ** (1.0 / 3.0)
    nhat = sky_to_unit(ra, dec)

    z_full = np.linspace(0.0, ZMAX + 0.05, 90001)
    dc = dc_table(z_full, OMM_FID, W0_FID)
    r0 = np.interp(z, z_full, dc)
    g0 = derive_box_local(nhat * r0[:, None])
    print("  footprint sintetico: L=%.3f dx=%.5f asse=%s margine=%.2f%%"
          % (g0["L"], g0["dx"], g0["axis_dom"], 100 * g0["axis_dom_margin"]))

    # T1: dilatazione esatta -> L = alpha*E + 2p, asse invariato, alpha_box != alpha
    ok = True
    for alpha in (0.9725, 1.0406):
        g = derive_box_local(nhat * (alpha * r0)[:, None])
        E0 = g0["L"] - 2 * PAD_DEFAULT
        L_pred = alpha * E0 + 2 * PAD_DEFAULT
        d = abs(g["L"] - L_pred)
        same_axis = (g["axis_dom"] == g0["axis_dom"])
        a_box = g["L"] / g0["L"]
        print("  T1 alpha=%.4f: |L-L_pred|=%.2e  asse invariato=%s  "
              "alpha_box=%.6f (alpha=%.4f, scarto %.2e)"
              % (alpha, d, same_axis, a_box, alpha, a_box - alpha))
        ok &= (d < 1e-8) and same_axis

    # T2: a F_AP=1 il residuo anisotropo deve annullarsi
    zz = z_full[(z_full >= ZMIN) & (z_full <= ZMAX)]
    r_fid = dc_table(z_full, OMM_FID, W0_FID)[(z_full >= ZMIN) & (z_full <= ZMAX)]
    a = 1.0317
    res = float(np.max(np.abs(a * r_fid - fit_alpha_iso(r_fid, a * r_fid) * r_fid)))
    print("  T2 mappa puramente lineare: residuo anisotropo = %.3e h^-1 Mpc" % res)
    ok &= res < 1e-9

    # T3: identita' F_AP = 1  <=>  residuo = 0
    row = cosmo_row(OMM_FID, W0_FID)
    print("  T3 fiduciale: residuo=%.3e  F_AP in [%.6f, %.6f]  monotona=%s"
          % (row["anis_residual_hMpc"], row["F_AP_perp_over_par_min"],
             row["F_AP_perp_over_par_max"], row["monotone_ok"]))
    ok &= row["anis_residual_hMpc"] < 1e-9 and row["monotone_ok"]

    # T4: monotonia di f(r) su tutti i punti -- cancello 2.4 anticipato
    nonmono = [(o, w) for (o, w) in GRID_OMM_W0 if not cosmo_row(o, w)["monotone_ok"]]
    print("  T4 cancello 2.4 (monotonia): %d punti non monotoni su %d"
          % (len(nonmono), len(GRID_OMM_W0)))
    ok &= not nonmono

    # T5: append-only + ripartenza
    tmp = "._selftest_item12a.jsonl"
    if os.path.exists(tmp):
        os.remove(tmp)
    cfg = config_hash({"x": 1})
    append_atomic(tmp, {"config_hash": cfg, "region": "T", "omm": 0.3175, "w0": -1.0})
    d1 = already_done(tmp, cfg)
    append_atomic(tmp, {"config_hash": "altro", "region": "T", "omm": 0.25, "w0": -1.2})
    d2 = already_done(tmp, cfg)
    print("  T5 ripartenza: %d record con la firma corrente, %d dopo un record estraneo"
          % (len(d1), len(d2)))
    ok &= (len(d1) == 1 and len(d2) == 1)
    os.remove(tmp)

    print("=== selftest %s ===" % ("PASSATO" if ok else "FALLITO"))
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(description="Paper 2 item 1.2a — griglia AP col box effettivo")
    p.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
    p.add_argument("--randoms", help="catalogo random (fits/npy/csv)")
    p.add_argument("--ra-col", default="RA")
    p.add_argument("--dec-col", default="DEC")
    p.add_argument("--z-col", default="Z")
    p.add_argument("--pad", type=float, default=PAD_DEFAULT)
    p.add_argument("--ngrid", type=int, default=NGRID)
    p.add_argument("--R", type=float, default=R_SMOOTH)
    p.add_argument("--out", default=None, help="JSONL append-only")
    p.add_argument("--cosmo-only", action="store_true")
    p.add_argument("--selftest", action="store_true")
    a = p.parse_args()

    if a.selftest:
        sys.exit(selftest())
    if not a.cosmo_only and not a.randoms:
        p.error("serve --randoms, oppure usare --cosmo-only")
    run(a)


if __name__ == "__main__":
    main()
