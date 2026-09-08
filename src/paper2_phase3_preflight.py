#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_phase3_preflight.py — item 3.0a: pre-flight geometrico della Fase 3.

NESSUN CAMPO, NESSUNA TDA (salvo --tiling, esplicito). Solo posizioni e cubi.
Risponde a una domanda sola: nel gauge dell'emendamento 13, la nuvola deformata
sta dentro il cubo di embedding, su tutte e sei le facce, per random e galassie?

IL GAUGE (emendamento 13, item 0.14b)
  Per ogni punto di misura il cubo e' DERIVATO, con padding MOLTIPLICATIVO:
      1. inietta la deformazione naturale, derive_box(pos_r, pad=5.0) -> L_punto
      2. c = L_fid / L_punto
      3. reinietta dc_tab * c, derive_box(pos_r, pad=5.0*c) -> L = L_fid esatto
  Allora dx e sigma_px sono identici al fiduciale per COSTRUZIONE e non per
  forzatura, box_min segue la nuvola, e il clipping e' zero per costruzione
  invece che limitato da una tolleranza.

  Il blocco A (dilatazione isotropa pura) gira in ENTRAMBI i gauge:
    - derivato, pad = 5*alpha: e' il cancello 2.2b ai valori della griglia.
      L = alpha * L_fid, e la Prop. 2 vale in forma esatta.
    - ri-gaugiato, pad = 5c: L = L_fid, ma la dilatazione totale e' D = c*alpha
      != 1, quindi resta il residuo della Prop. 2'. Su A il segnale fisico e'
      NULLO per teorema, quindi max|du| misurato E' il costo del ri-gauge, in
      voxel, sui dati veri. E' l'unico punto della griglia dove quel costo si
      puo' isolare: su B e C si sommerebbe al segnale.

PERCHE' LA CACHE, E PERCHE' HA UN CANCELLO
  G.positions() rilegge il FITS a ogni chiamata: 187 s (NGC, 13.2 M random) e
  76 s (SGC, 5.4 M). Il pre-flight ne farebbe ~52, cioe' due ore, per aritmetica
  su array gia' in memoria. Qui il FITS si legge UNA volta per emisfero e si
  tengono RA/DEC/z/w; a ogni geometria si ricalcola solo D_C(z).

  La cache tiene seno e coseno, NON le posizioni. Le posizioni dipendono dalla
  mappatura e rimetterle in cache sarebbe la stessa classe di difetto della
  maschera caricata da disco (item 2.1-M).

  E l'ordine dei prodotti e' quello di paper2_data_geometry.py:146-148,
      pos = (dC * cos(dec)) * cos(ra),  (dC * cos(dec)) * sin(ra),  dC * sin(dec)
  valutato da sinistra. Precalcolare il versore cos(dec)*cos(ra) e moltiplicarlo
  per dC darebbe scarti a 1e-16: in virgola mobile (a*b)*c != a*(b*c).
  Il cancello verifica l'identita' BIT A BIT contro G.positions().

PREDIZIONI, dichiarate qui prima di girare (item 1.4, cancello prima)
  P1  Dopo il ri-gauge, L = L_fid con scarto relativo <= 1e-12, su ogni punto
      dei blocchi B e C.
  P2  Clippati contro il cubo DERIVATO: zero ovunque, su tutte e sei le facce,
      random e galassie. E' per costruzione, quindi un valore non nullo qui
      significa che derive_box e cic_3d non concordano, non che il punto e'
      difficile.
  P3  Clippati contro il cubo FIDUCIALE forzato (il gauge SUPERATO, calcolato
      solo per confronto): non nulli esattamente sui punti con dL > 0, nulli
      dove dL < 0. E' la RETRODIZIONE della predizione smentita: il clipping
      segue il SEGNO di dL, cioe' la parte isotropa residua, non il residuo
      anisotropo. Registrata nell'emendamento 13.
  P4  Blocco A, gauge derivato: L = 1942.710437 (A1) e 2078.049851 (A3) in NGC,
      come predetto dalla Prop. 2' in item 1.1a.
  P5  Blocco A, gauge ri-gaugiato: L = L_fid a 1e-12, e spostamento di griglia
      max|du| = (N/2)*|c*alpha - 1|, cioe' ~1.2e-2 voxel. NON e' zero, e non e'
      trascurabile: il 2.2a ha misurato 0.031 voxel -> 216 voxel di maschera ->
      34 generatori. Se P5 e' confermata, il ri-gauge ha un costo dichiarabile.
  P6  Asse dominante del lato del cubo invariato su tutti i punti (item 1.1b v).

Uso:
    python src\\paper2_phase3_preflight.py selftest
    python src\\paper2_phase3_preflight.py gate --region NGC
    python src\\paper2_phase3_preflight.py run --region NGC --out results\\paper2\\preflight_NGC.jsonl
    python src\\paper2_phase3_preflight.py run --region SGC --points B1 B5 C1 --no-cache-gate
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np

# --------------------------------------------------------------------------
# Ancore operative: i due record `d2` di results/paper2/fase2.jsonl.
# Emendamento 13, item 0.14a. NON sono i congelati di phase6/phase9: quelli
# differiscono di 2.86e-9 relativo (residuo della tabella a 4001 nodi) e, in
# NGC, portano un sigma_px scritto da un run a R = 14.8.
# --------------------------------------------------------------------------
ANCHOR = {
    "NGC": {"box_size": 1997.3629110094512, "cell": 15.604397742261337,
            "sigma_px": 0.32042249039652254, "R_SMOOTH": 4.999999985713251,
            "n_valid_voxels": 307805, "N_H1": 28256,
            "N_rand": 13248857, "N_data": 217614},
    "SGC": {"box_size": 1904.450156441475, "cell": 14.878516847199023,
            "sigma_px": 0.33605500065144590, "R_SMOOTH": 4.999999988778017,
            "n_valid_voxels": 172225, "N_H1": 15122,
            "N_rand": 5432939, "N_data": 82429},
}

# Prop. 2' (item 1.1a): lato del cubo atteso sul blocco A, gauge derivato.
PROP2_A_NGC = {"A1": 1942.710437, "A3": 2078.049851}

PAD_FID = 5.0
NGRID = 128
TOL_L_REL = 1e-12          # ri-gauge: L deve tornare L_fid
TOL_ANCHOR_REL = 1e-12     # cancello sul fiduciale


# --------------------------------------------------------------------------
# Aritmetica pura, testabile senza i moduli del progetto
# --------------------------------------------------------------------------

def positions_from_trig(dC, cos_dec, sin_dec, cos_ra, sin_ra):
    """Replica ESATTA di paper2_data_geometry.positions():146-148.

    L'ordine dei prodotti e' significativo: (dC * cos_dec) * cos_ra, valutato
    da sinistra come nel sorgente. Non fattorizzare.
    """
    return np.column_stack([dC * cos_dec * cos_ra,
                            dC * cos_dec * sin_ra,
                            dC * sin_dec])


def derive_box_pure(pos, pad):
    """Regola di phase6_bgs_voxelize.py:166-168, ripetuta qui solo per il
    selftest. In produzione si chiama G.derive_box, non questa."""
    lo = pos.min(axis=0) - pad
    hi = pos.max(axis=0) + pad
    return lo, float((hi - lo).max())


def clipped_per_face(pos, box_min, box_size):
    """Posizioni fuori dal cubo, PER FACCIA. cic_3d (phase8:495-508) non le
    scarta: le impila sulle facce.

    Il margine non e' lo stesso sulle sei facce. Il cubo ha lato fissato
    dall'estensione dell'asse DOMINANTE, e l'origine e' min-pad asse per asse:
    quindi il margine e' pad su tutte e tre le facce basse e sulla faccia alta
    del solo asse dominante, mentre sulle altre due facce alte e' grande.
    Un totale aggregato nasconderebbe quale faccia perde.
    """
    box_min = np.asarray(box_min, float)
    hi = box_min + box_size
    out = {}
    tot = np.zeros(len(pos), dtype=bool)
    for k, ax in enumerate("xyz"):
        lo_m = pos[:, k] < box_min[k]
        hi_m = pos[:, k] >= hi[k]
        out[f"lo_{ax}"] = int(lo_m.sum())
        out[f"hi_{ax}"] = int(hi_m.sum())
        out[f"excess_lo_{ax}"] = float(box_min[k] - pos[:, k].min())
        out[f"excess_hi_{ax}"] = float(pos[:, k].max() - hi[k])
        tot |= lo_m | hi_m
    out["n_clipped"] = int(tot.sum())
    return out


def grid_shift(pos_a, box_min_a, cell_a, pos_b, box_min_b, cell_b):
    """max|du| fra due geometrie, in unita' di griglia, oggetto per oggetto.

    Su una deformazione isotropa pura (blocco A) il segnale fisico e' nullo per
    la Prop. 2, quindi questo numero E' l'artefatto e nient'altro.
    """
    ua = (pos_a - np.asarray(box_min_a, float)) / cell_a
    ub = (pos_b - np.asarray(box_min_b, float)) / cell_b
    d = np.abs(ua - ub)
    return {"max": float(d.max()),
            "per_axis": [float(d[:, k].max()) for k in range(3)],
            "median": float(np.median(d.max(axis=1)))}


def dominant_axis(pos):
    e = pos.max(axis=0) - pos.min(axis=0)
    k = int(np.argmax(e))
    o = sorted(e)[-2]
    return {"axis": "xyz"[k], "extent": [float(v) for v in e],
            "margin_frac": float(e[k] / o - 1.0)}


# --------------------------------------------------------------------------
# Aggancio ai moduli del progetto
# --------------------------------------------------------------------------

def attach(srcdir="src"):
    if srcdir and srcdir not in sys.path:
        sys.path.insert(0, srcdir)
    import paper2_data_geometry as G
    import phase8_cutsky_mocks as M
    import paper2_item13a_15a as I13     # deform(), tiling_stats(): si IMPORTANO
    z = np.asarray(M._Z_TAB, float).copy()
    dc = np.asarray(M._DC_TAB, float).copy()
    return G, M, I13, z, dc


class Cache:
    """RA/DEC/z/w letti una volta, piu' seno e coseno. Le POSIZIONI no."""

    def __init__(self, G, M, region, kind, verbose=True):
        from astropy.io import fits
        from pathlib import Path
        base = M.DESI_DIR / f"BGS_BRIGHT-21.5_{region}"
        path = Path(f"{base}_0_clustering.ran.fits") if kind == "ran" \
            else Path(f"{base}_clustering.dat.fits")
        if not path.exists():
            raise FileNotFoundError(path)
        t0 = time.perf_counter()
        with fits.open(path) as h:
            t = h["LSS"].data
            mz = (t["Z"] >= M.ZMIN) & (t["Z"] <= M.ZMAX)
            ra = t["RA"][mz].astype(np.float64)
            dec = t["DEC"][mz].astype(np.float64)
            self.z = t["Z"][mz].astype(np.float64)
            w = t["WEIGHT_FKP"][mz].astype(np.float64)
            if kind == "dat":
                w = w * t["WEIGHT"][mz].astype(np.float64)
        self.w = w
        rar, decr = np.radians(ra), np.radians(dec)
        self.cos_dec, self.sin_dec = np.cos(decr), np.sin(decr)
        self.cos_ra, self.sin_ra = np.cos(rar), np.sin(rar)
        del ra, dec, rar, decr
        self.region, self.kind, self.M = region, kind, M
        self.n = int(len(self.z))
        if verbose:
            print(f"  [cache] {region}/{kind}: {self.n:,} oggetti in "
                  f"{time.perf_counter()-t0:.1f} s")

    def positions(self):
        """Posizioni nella mappatura CORRENTE. D_C si ricalcola sempre."""
        dC = np.atleast_1d(self.M.comoving_distance(self.z)).astype(np.float64)
        return positions_from_trig(dC, self.cos_dec, self.sin_dec,
                                   self.cos_ra, self.sin_ra), self.w


def cache_gate(G, cache, verbose=True):
    """Identita' BIT A BIT fra la cache e G.positions(), nella mappatura
    corrente. Costa una rilettura del FITS, una volta per emisfero."""
    fast, _ = cache.positions()
    slow, _ = G.positions(cache.region, cache.kind)
    if fast.shape != slow.shape:
        return {"ok": False, "reason": f"forme diverse {fast.shape} {slow.shape}"}
    d = float(np.abs(fast - slow).max())
    ident = bool(np.array_equal(fast, slow))
    if verbose:
        print(f"  [cancello cache] {cache.region}/{cache.kind}: "
              f"max|diff| = {d:.3e}  array_equal = {ident}")
    return {"ok": ident, "max_abs_diff": d, "array_equal": ident, "n": cache.n}


# --------------------------------------------------------------------------
# Il gauge
# --------------------------------------------------------------------------

def point_plan(I13, points=None):
    plan = [("FID", dict(kind="fid"), "fid")]
    for n, al in I13.LINE_A:
        plan.append((n, dict(kind="ap", alpha_iso=al, F_ap=1.0), "A"))
    for n, F in I13.LINE_B:
        plan.append((n, dict(kind="ap", alpha_iso=1.0, F_ap=F), "B"))
    for n, o, w in I13.CORNERS:
        plan.append((n, dict(kind="cosmo", omm=o, w0=w), "C"))
    if points:
        plan = [p for p in plan if p[0] in points]
    return plan


def measure(G, M, I13, cache_r, cache_d, z_tab, dc_fid, name, spec, block,
            L_fid, box_min_fid, pos_fid, want_tiling=False):
    """Un punto, nei gauge che gli competono. Nessun campo, salvo --tiling."""
    rec = {"schema": "paper2_preflight_v1", "point": name, "block": block,
           "region": cache_r.region, "utc": _now()}
    rec.update({k: v for k, v in spec.items() if k != "kind"})
    rec["deform_kind"] = spec["kind"]

    dc_pt = I13.deform(z_tab, dc_fid, spec)

    # --- passo 1: deformazione naturale, pad additivo -----------------------
    M.set_geometry(z_tab=z_tab, dc_tab=dc_pt, verbose=False)
    pos_r, _ = cache_r.positions()
    bmin_nat, L_nat = _derive(G, pos_r, PAD_FID)
    rec["derived"] = _leg(pos_r, bmin_nat, L_nat, box_min_fid, L_fid, pos_fid)
    rec["derived"]["pad"] = PAD_FID
    rec["dL_vs_fid"] = L_nat - L_fid

    # Clippati contro il cubo FIDUCIALE forzato: il gauge SUPERATO, calcolato
    # solo per confronto e per la retrodizione P3.
    rec["forced_fiducial_box"] = clipped_per_face(pos_r, box_min_fid, L_fid)

    # --- passo 2: ri-gauge a cubo costante ----------------------------------
    if block in ("A", "B", "C"):
        c = L_fid / L_nat
        M.set_geometry(z_tab=z_tab, dc_tab=dc_pt * c, verbose=False)
        pos_rg, _ = cache_r.positions()
        bmin_rg, L_rg = _derive(G, pos_rg, PAD_FID * c)
        leg = _leg(pos_rg, bmin_rg, L_rg, box_min_fid, L_fid, pos_fid)
        leg.update({"c": c, "pad": PAD_FID * c,
                    "L_rel_err_vs_fid": abs(L_rg - L_fid) / L_fid,
                    "P1_ok": abs(L_rg - L_fid) / L_fid <= TOL_L_REL})
        if block == "A":
            # Segnale fisico nullo per la Prop. 2: max|du| E' l'artefatto.
            # Prop. 2': dilatazione residua attorno al CENTRO del cubo. Il
            # punto estremo non e' lo spigolo ma la galassia piu' esterna, che
            # sta a N/2 - p/dx: il termine di padding vale lo 0.5% ed e' la
            # ragione per cui la forma senza correzione predice a 0.995.
            a1 = c * spec["alpha_iso"] - 1.0
            leg["prop2_residual_dilation"] = a1
            leg["prop2_predicted_shift_voxel"] = abs(
                (0.5 * NGRID - PAD_FID / (L_fid / NGRID)) * a1)
            leg["prop2_predicted_shift_voxel_corner"] = abs(0.5 * NGRID * a1)
        rec["regauged"] = leg

        if cache_d is not None:
            pos_dg, _ = cache_d.positions()
            rec["regauged"]["galaxies"] = clipped_per_face(pos_dg, bmin_rg, L_rg)
            rec["regauged"]["n_galaxies"] = int(len(pos_dg))
            del pos_dg

        if want_tiling:
            rec["regauged"]["tiling_note"] = (
                "richiede la maschera: usare --tiling, che costruisce il campo")
        del pos_rg
    del pos_r
    return rec


def _derive(G, pos, pad):
    out = G.derive_box(pos, pad=pad)
    bmin, L = (out[0], float(out[1])) if isinstance(out, tuple) else (out, None)
    return np.asarray(bmin, float), L


def _leg(pos, bmin, L, box_min_fid, L_fid, pos_fid):
    cell = L / NGRID
    d = {"box_min": [float(v) for v in bmin], "box_size": L, "cell": cell,
         "sigma_px_if_R5": 5.0 / cell,
         "clipped": clipped_per_face(pos, bmin, L),
         "dominant": dominant_axis(pos)}
    if pos_fid is not None:
        d["grid_shift_vs_fid"] = grid_shift(pos, bmin, cell,
                                            pos_fid, box_min_fid, L_fid / NGRID)
    return d


def _now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def append_atomic(path, rec):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or ".", exist_ok=True)
    with open(path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(rec, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


# --------------------------------------------------------------------------
# Comandi
# --------------------------------------------------------------------------

def cmd_gate(a):
    """Riproduce un valore congelato PRIMA di riportarne di nuovi."""
    G, M, I13, z_tab, dc_fid = attach(a.src)
    reg = a.region
    anc = ANCHOR[reg]
    print("=" * 72)
    print(f"3.0a — cancello del pre-flight, {reg}")
    print("=" * 72)
    fails = 0

    # 1. deformazione nulla -> tabella fiduciale, bit a bit
    dc0 = I13.deform(z_tab, dc_fid, dict(kind="fid"))
    ok = bool(np.array_equal(dc0, dc_fid))
    print(f"  [{'ok ' if ok else 'FAIL'}] deform(fid) e' la tabella fiduciale "
          f"(array_equal={ok})")
    fails += (not ok)

    fn = getattr(M, "make_dc_tab_ap", None)
    if fn is not None:
        try:
            out = fn(alpha_iso=1.0, F_ap=1.0)
            dc1 = np.asarray(out[1] if isinstance(out, tuple) else out, float)
            if dc1.shape == dc_fid.shape:
                # D_C(0) = 0: il rapporto e' 0/0 al primo nodo. Il confronto va
                # fatto dove la tabella e' usata, cioe' sull'intervallo del
                # campione. Dividere sull'intera tabella dava nan.
                m = (z_tab >= M.ZMIN) & (z_tab <= M.ZMAX)
                r = float(np.abs(dc1[m] / dc_fid[m] - 1.0).max())
                bit = bool(np.array_equal(dc1, dc_fid))
                print(f"  [{'ok ' if r <= 1e-12 else 'FAIL'}] "
                      f"make_dc_tab_ap(1,1) vs fiduciale su [{M.ZMIN}, {M.ZMAX}]: "
                      f"rel max {r:.3e} (array_equal sull'intera tabella={bit})")
                fails += (r > 1e-12)
        except Exception as exc:
            print(f"  [ -- ] make_dc_tab_ap(1,1): {type(exc).__name__} {exc}")

    # 2. cubo fiduciale contro l'ancora operativa
    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    cache_r = Cache(G, M, reg, "ran")
    if cache_r.n != anc["N_rand"]:
        print(f"  [FAIL] N_rand = {cache_r.n}, atteso {anc['N_rand']}")
        fails += 1
    pos_r, _ = cache_r.positions()
    bmin, L = _derive(G, pos_r, PAD_FID)
    for k, got, exp in (("box_size", L, anc["box_size"]),
                        ("cell", L / NGRID, anc["cell"]),
                        ("sigma_px", anc["R_SMOOTH"] / (L / NGRID), anc["sigma_px"])):
        r = abs(got - exp) / abs(exp)
        ok = r <= TOL_ANCHOR_REL
        fails += (not ok)
        print(f"  [{'ok ' if ok else 'FAIL'}] {k:<10} {got!r} atteso {exp!r} "
              f"(rel {r:.2e})")

    # 3. cancello della cache: identita' bit a bit con G.positions()
    if not a.no_cache_gate:
        g = cache_gate(G, cache_r)
        fails += (not g["ok"])

    # 4. zero clippati al fiduciale
    cl = clipped_per_face(pos_r, bmin, L)
    ok = cl["n_clipped"] == 0
    fails += (not ok)
    print(f"  [{'ok ' if ok else 'FAIL'}] clippati al fiduciale = "
          f"{cl['n_clipped']} (atteso 0)")
    print(f"         margini alti per asse: "
          f"{[round(-cl[f'excess_hi_{x}'], 3) for x in 'xyz']}")
    print(f"         asse dominante: {dominant_axis(pos_r)}")

    print(f"\n  {'CANCELLO SUPERATO' if not fails else f'{fails} FALLIMENTI'}")
    return 1 if fails else 0


def cmd_run(a):
    G, M, I13, z_tab, dc_fid = attach(a.src)
    reg = a.region
    print("=" * 72)
    print(f"3.0a — pre-flight geometrico, {reg}")
    print("=" * 72)

    M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
    cache_r = Cache(G, M, reg, "ran")
    cache_d = None if a.no_galaxies else Cache(G, M, reg, "dat")
    if not a.no_cache_gate:
        g = cache_gate(G, cache_r)
        if not g["ok"]:
            sys.exit("[FATAL] la cache non e' bit-identica a G.positions(). "
                     "Il percorso veloce non e' legittimo.")

    pos_fid, _ = cache_r.positions()
    box_min_fid, L_fid = _derive(G, pos_fid, PAD_FID)
    anc = ANCHOR[reg]
    if abs(L_fid - anc["box_size"]) / anc["box_size"] > TOL_ANCHOR_REL:
        sys.exit(f"[FATAL] L fiduciale {L_fid!r} != ancora {anc['box_size']!r}. "
                 "Lanciare prima `gate`.")
    print(f"  fiduciale: L = {L_fid!r}  cella = {L_fid/NGRID!r}")

    rows = []
    try:
        for name, spec, block in point_plan(I13, a.points):
            if name == "FID":
                continue
            t0 = time.perf_counter()
            rec = measure(G, M, I13, cache_r, cache_d, z_tab, dc_fid,
                          name, spec, block, L_fid, box_min_fid, pos_fid)
            rec["seconds"] = time.perf_counter() - t0
            rows.append(rec)
            if a.out:
                append_atomic(a.out, rec)
            d, rg = rec["derived"], rec.get("regauged", {})
            print(f"\n  {name:<4} [{block}]  dL = {rec['dL_vs_fid']:+9.3f}")
            print(f"       derivato   L={d['box_size']:12.6f}  "
                  f"clippati={d['clipped']['n_clipped']}")
            if rg:
                print(f"       ri-gauge   L={rg['box_size']:12.6f}  "
                      f"rel={rg['L_rel_err_vs_fid']:.2e}  "
                      f"clippati={rg['clipped']['n_clipped']}"
                      + (f"  galassie={rg['galaxies']['n_clipped']}"
                         if "galaxies" in rg else ""))
                if "grid_shift_vs_fid" in rg:
                    print(f"       spostamento di griglia vs fid: "
                          f"max {rg['grid_shift_vs_fid']['max']:.4f} voxel")
                if block == "A":
                    print(f"       P5: predetto {rg['prop2_predicted_shift_voxel']:.4f} "
                          f"voxel, misurato {rg['grid_shift_vs_fid']['max']:.4f}")
            fb = rec["forced_fiducial_box"]
            print(f"       [cubo fiduciale forzato, gauge superato] "
                  f"clippati={fb['n_clipped']}")
    finally:
        M.set_geometry(z_tab=z_tab, dc_tab=dc_fid, verbose=False)
        print("\n[restore] geometria fiduciale ripristinata.")

    _verdict(rows)
    return 0


def _verdict(rows):
    if not rows:
        return
    print("\n" + "=" * 72)
    print("VERDETTO contro le predizioni dichiarate")
    print("=" * 72)
    p1 = [r["point"] for r in rows if "regauged" in r and not r["regauged"]["P1_ok"]]
    print(f"  P1  L = L_fid dopo il ri-gauge: "
          f"{'CONFERMATA' if not p1 else 'SMENTITA su ' + ' '.join(p1)}")
    p2 = [r["point"] for r in rows
          if r.get("regauged", {}).get("clipped", {}).get("n_clipped", 0)
          or r.get("regauged", {}).get("galaxies", {}).get("n_clipped", 0)]
    print(f"  P2  zero clippati nel gauge nuovo: "
          f"{'CONFERMATA' if not p2 else 'SMENTITA su ' + ' '.join(p2)}")
    pos_dl = {r["point"] for r in rows if r["dL_vs_fid"] > 0}
    clip_forced = {r["point"] for r in rows
                   if r["forced_fiducial_box"]["n_clipped"] > 0}
    print(f"  P3  clipping a cubo forzato segue il segno di dL: "
          f"{'CONFERMATA' if pos_dl == clip_forced else 'SMENTITA'}")
    print(f"      dL > 0: {sorted(pos_dl)}")
    print(f"      clippa: {sorted(clip_forced)}")
    for r in rows:
        if r["block"] == "A" and "regauged" in r:
            rg = r["regauged"]
            pr, ms = rg["prop2_predicted_shift_voxel"], rg["grid_shift_vs_fid"]["max"]
            print(f"  P5  {r['point']}: predetto {pr:.5f}, misurato {ms:.5f}, "
                  f"rapporto {ms/pr if pr else float('nan'):.4f}")
    ax = {r["point"]: r["derived"]["dominant"]["axis"] for r in rows}
    same = len(set(ax.values())) == 1
    print(f"  P6  asse dominante invariato: "
          f"{'CONFERMATA' if same else 'SMENTITA — ' + str(ax)}")


def cmd_selftest(a):
    ok = True

    def expect(name, cond, extra=""):
        nonlocal ok
        ok = ok and bool(cond)
        print(f"  [{'ok' if cond else 'FAIL'}] {name} {extra}")

    rng = np.random.default_rng(20260829)
    n = 20000
    ra = rng.uniform(120.0, 240.0, n)
    dec = rng.uniform(-5.0, 60.0, n)
    z = rng.uniform(0.1, 0.4, n)
    dC = 2997.92458 * z / (1.0 + 0.5 * z)
    rar, decr = np.radians(ra), np.radians(dec)
    cd, sd, cr, sr = np.cos(decr), np.sin(decr), np.cos(rar), np.sin(rar)

    ref = np.column_stack([dC * np.cos(decr) * np.cos(rar),
                           dC * np.cos(decr) * np.sin(rar),
                           dC * np.sin(decr)])
    got = positions_from_trig(dC, cd, sd, cr, sr)
    expect("1. cache bit-identica alla formula del sorgente",
           np.array_equal(ref, got))

    bad = np.column_stack([dC * (cd * cr), dC * (cd * sr), dC * sd])
    expect("2. e la fattorizzazione NON lo e' (percio' il cancello serve)",
           not np.array_equal(ref, bad),
           f"(max|diff| = {np.abs(ref-bad).max():.3e})")

    bmin, L = derive_box_pure(ref, 5.0)
    cl = clipped_per_face(ref, bmin, L)
    expect("3. cubo derivato dai propri punti: zero clippati",
           cl["n_clipped"] == 0)

    shrunk = L * 0.99
    cl2 = clipped_per_face(ref, bmin, shrunk)
    expect("4. cubo accorciato: clippa, e solo sulle facce alte",
           cl2["n_clipped"] > 0
           and all(cl2[f"lo_{x}"] == 0 for x in "xyz")
           and any(cl2[f"hi_{x}"] > 0 for x in "xyz"),
           f"(n={cl2['n_clipped']})")

    # La traslazione va fatta sull'asse DOMINANTE: e' l'unico dove il margine
    # alto vale pad. Sugli altri due il cubo avanza, e una traslazione piccola
    # non sfonda niente — che e' il punto dell'asimmetria delle facce.
    k = int(np.argmax(ref.max(axis=0) - ref.min(axis=0)))
    step = np.zeros(3); step[k] = 5.0 + 1.0
    cl3 = clipped_per_face(ref + step, bmin, L)
    ax = "xyz"[k]
    expect("5. traslazione sull'asse dominante: sfonda in alto, non in basso",
           cl3[f"lo_{ax}"] == 0 and cl3[f"hi_{ax}"] > 0,
           f"(asse {ax}, lo={cl3[f'lo_{ax}']} hi={cl3[f'hi_{ax}']})")
    j = (k + 1) % 3
    step2 = np.zeros(3); step2[j] = 5.0 + 1.0
    cl4 = clipped_per_face(ref + step2, bmin, L)
    expect("5b. stessa traslazione su un asse non dominante: non sfonda",
           cl4["n_clipped"] == 0,
           f"(asse {'xyz'[j]}, margine alto "
           f"{-cl4[f'excess_hi_' + 'xyz'[j]]:.1f} h^-1Mpc)")

    # ri-gauge su dilatazione isotropa pura: L torna L_fid, e resta il residuo
    alpha = 1.0406
    pos_a = ref * alpha
    _, L_nat = derive_box_pure(pos_a, 5.0)
    c = L / L_nat
    pos_rg = ref * (alpha * c)
    bmin_rg, L_rg = derive_box_pure(pos_rg, 5.0 * c)
    expect("6. ri-gauge: L torna L_fid a 1e-12",
           abs(L_rg - L) / L <= 1e-12, f"(rel {abs(L_rg-L)/L:.2e})")

    gs = grid_shift(pos_rg, bmin_rg, L_rg / NGRID, ref, bmin, L / NGRID)
    corner = abs(0.5 * NGRID * (c * alpha - 1.0))
    pred = abs((0.5 * NGRID - 5.0 / (L / NGRID)) * (c * alpha - 1.0))
    expect("7. e il residuo della Prop. 2' e' quello predetto in forma chiusa",
           abs(gs["max"] - pred) / pred < 1e-3,
           f"(predetto {pred:.6f}, misurato {gs['max']:.6f})")
    expect("7b. la forma SENZA il termine di padding sbaglia dello 0.5%",
           0.002 < abs(gs["max"] - corner) / corner < 0.02,
           f"(spigolo {corner:.6f}, rapporto {gs['max']/corner:.5f})")

    expect("8. il residuo NON e' zero: il ri-gauge ha un costo",
           gs["max"] > 1e-3, f"({gs['max']:.5f} voxel)")

    _, L_prop = derive_box_pure(ref * alpha, 5.0 * alpha)
    expect("9. gauge derivato con pad moltiplicativo: L = alpha * L_fid esatto",
           abs(L_prop - alpha * L) / (alpha * L) <= 1e-12)

    bmin_p, L_p = derive_box_pure(ref * alpha, 5.0 * alpha)
    gs0 = grid_shift(ref * alpha, bmin_p, L_p / NGRID, ref, bmin, L / NGRID)
    expect("10. e li' la Prop. 2 e' esatta: spostamento nullo",
           gs0["max"] < 1e-9, f"({gs0['max']:.3e} voxel)")

    dom = dominant_axis(ref)
    expect("11. asse dominante identificato con margine",
           dom["axis"] in "xyz" and dom["margin_frac"] >= 0.0)

    print(f"\nselftest: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--src", default="src")
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest")
    for nm in ("gate", "run"):
        q = sub.add_parser(nm)
        q.add_argument("--region", choices=["NGC", "SGC"], default="NGC")
        q.add_argument("--no-cache-gate", action="store_true",
                       help="salta il confronto bit a bit con G.positions()")
        if nm == "run":
            q.add_argument("--points", nargs="*", default=None)
            q.add_argument("--out", default=None)
            q.add_argument("--no-galaxies", action="store_true")
    a = p.parse_args()
    return {"selftest": cmd_selftest, "gate": cmd_gate, "run": cmd_run}[a.cmd](a)


if __name__ == "__main__":
    sys.exit(main())
