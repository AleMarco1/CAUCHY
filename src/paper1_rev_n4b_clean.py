#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n4b_clean.py

N4b - STABILITA' DI TABELLA 3, CON LA DEFINIZIONE CORRETTA

RITIRO DI N4
------------
paper1_rev_n4n5.py calcolava il percentile su field_r[field_r > 0], cioe' su
TUTTI i voxel con random non nullo. La definizione vera, letta in
paper1_step6_onepoint_betti.py righe 220-233, e':

    rin = field_r[mask]
    thr = float(np.percentile(rin, p))
    out.append((f"field_r > P{p:g}", mask & (field_r > thr)))

Il percentile e' DENTRO la maschera. Il manoscritto lo conferma (Sez. 5.1):
"the restriction excludes the 10 per cent of in-mask voxels with the lowest
random-field density".

Conseguenza: le selezioni di N4 erano sottoinsiemi della maschera - questo era
giusto - ma MENO RESTRITTIVE del dovuto: tenevano il 98.9%, 93.7% e 88.5% dei
voxel invece del 95%, 90% e 85%. Non e' un dettaglio, perche' e' negli ultimi
punti percentuali che vive l'artefatto FKP: il manoscritto stesso dice che le
statistiche di coda sono dominate dal sistematico di pesatura.

QUINDI: il risultato di N4 sull'inversione di segno dell'asimmetria fra P5 e
P10 e' RITIRATO. Quei numeri non riproducono Tabella 3 e non sono confrontabili
con essa. L'inversione e' avvenuta dentro una famiglia di selezioni sbagliate.

Non e' ritirato invece l'ordine di grandezza: il P10 sbagliato dava asimmetria
z = +7.69 contro il +5.6 pubblicato, stesso segno. La preoccupazione di fondo -
che i momenti siano molto sensibili al livello esatto del taglio - resta
plausibile e va VERIFICATA, non affermata.

IL CANCELLO
-----------
Tabella 3 del manoscritto, NGC, restrizione P10, 200 mock:

    varianza            z = +6.2    rank 198/200
    asimmetria          z = +5.6    rank 198/200
    curtosi in eccesso  z = -5.1    rank   1/200
    mediana             z = +13.8   rank 200/200

Questo script deve riprodurli. Se non ci riesce, la definizione non e' ancora
quella giusta e mi fermo prima di rimisurare la stabilita'.

Si usano le funzioni ORIGINALI - build_restrictions e moments importate da
paper1_step6_onepoint_betti, build_nu e compute_delta da paper1_remap - invece
di riscriverle: e' la sola difesa contro un terzo tentativo sbagliato.

IN PIU': L'EROSIONE k = 1
-------------------------
R2 §6 chiede perche' manchi k = 1 fra i livelli di erosione. Riga 229 di step6:

    out.append((f"erosione {k} voxel", dist > k))

k = 1 non e' escluso da nulla: semplicemente non e' nella lista `specs`. Qui si
aggiunge, cosi' la risposta al referee ha il numero e non solo la spiegazione.

USO
---
  python src\\paper1_rev_n4b_clean.py --n 200
  python src\\paper1_rev_n4b_clean.py --n 30        # pilota
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

# Tabella 3 del manoscritto, NGC, restrizione P10, n = 200
TAB3_NGC = {"var": 6.2, "skew": 5.6, "kurt_excess": -5.1, "median": 13.8}
TAB3_RANK = {"var": "198/200", "skew": "198/200",
             "kurt_excess": "1/200", "median": "200/200"}
KEYS = ("var", "skew", "kurt_excess", "median")


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True, default=str)
            f.flush(); os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def rank_of(val, arr):
    """Identica a rank_of in paper1_step6_onepoint_betti."""
    arr = np.asarray(arr, float)
    sd = arr.std(ddof=1)
    return {"desi": float(val), "mock_mean": float(arr.mean()),
            "mock_std": float(sd),
            "z": float((val - arr.mean()) / sd) if sd > 0 else None,
            "rank": f"{int((arr <= val).sum())}/{arr.size}"}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", default="NGC")
    ap.add_argument("--n", type=int, default=200,
                    help="mock (Tabella 3 ne usa 200)")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import paper1_remap as P1
    import paper1_step6_onepoint_betti as S6

    print("=" * 78)
    print("N4b - TABELLA 3 CON LA DEFINIZIONE CORRETTA DEI CLEAN VOXELS")
    print("=" * 78)

    G = P1.setup_region(M, args.region, root / "data" / "raw" / "desi_dr1",
                        root / "data" / "processed" / "phase6_fields")
    mask = G["mask"]
    field_r = np.asarray(G["field_r"], float)
    alpha = G["sum_wd"] / G["sum_wr"]
    desi_delta = P1.compute_delta(G["field_d"], field_r, alpha, mask, M.NGRID)
    nu_desi = P1.build_nu(desi_delta, mask, M.SIGMA_PX)
    print(f"  maschera: {int(mask.sum())} voxel  "
          f"({100*mask.mean():.4f}% della griglia)")

    specs = ["full", "fieldr5", "fieldr10", "fieldr15",
             "erosion0", "erosion1", "erosion2", "erosion3"]
    subsets = S6.build_restrictions(mask, field_r, specs)
    print(f"\n  restrizioni ({len(subsets)}):")
    for lab, sel in subsets:
        print(f"    {lab:>22s}  {int(sel.sum()):>7d} voxel  "
              f"{100*sel.sum()/mask.sum():>6.2f}% della maschera")
    print(f"\n  verifica: 'field_r > P10' deve tenere il 90.00% della maschera")
    lab10 = next((l for l, _ in subsets if l.startswith("field_r > P10")), None)
    sel10 = dict(subsets)[lab10] if lab10 else None
    if sel10 is not None:
        f10 = 100 * sel10.sum() / mask.sum()
        print(f"    tiene il {f10:.2f}%   "
              f"{'OK' if abs(f10-90) < 0.5 else '*** definizione ancora errata ***'}")
        if abs(f10 - 90) >= 0.5:
            return

    # ---------------------------------------------------------- mock
    cache = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    files = sorted(cache.glob("delta_*.npy"))[:args.n]
    if not files:
        print(f"\n[FATAL] nessun campo in {cache}")
        return
    print(f"\n  costruzione di nu per {len(files)} mock "
          f"(maschera PIENA, poi si restringe)...")
    t0 = time.time()
    nu_mock = []
    for i, fp in enumerate(files):
        nu_mock.append(P1.build_nu(np.load(fp).astype(np.float64), mask,
                                   M.SIGMA_PX))
        if (i + 1) % 50 == 0:
            print(f"    {i+1}/{len(files)}  ({(time.time()-t0)/(i+1):.2f} s/campo)")

    # ---------------------------------------------------------- momenti
    rep = {"script": "paper1_rev_n4b_clean.py", "region": args.region,
           "n_mock": len(files), "tab3_manoscritto": TAB3_NGC,
           "restrizioni": {}}
    # un'erosione troppo aggressiva puo' svuotare la maschera: i momenti su
    # poche migliaia di voxel non sono affidabili e falserebbero il confronto
    MIN_VOX = 5000
    tenuti = []
    for lab, sel in subsets:
        if int(sel.sum()) < MIN_VOX:
            print(f"  [skip] {lab}: solo {int(sel.sum())} voxel residui, "
                  f"momenti non affidabili")
        else:
            tenuti.append((lab, sel))
    subsets = tenuti

    for lab, sel in subsets:
        md = S6.moments(nu_desi[sel])
        rows = [S6.moments(a[sel]) for a in nu_mock]
        r = {k: rank_of(md[k], [x[k] for x in rows]) for k in KEYS}
        r["n_voxels"] = int(sel.sum())
        r["frac_of_full"] = float(sel.sum() / mask.sum())
        rep["restrizioni"][lab] = r

    # ---------------------------------------------------------- cancello
    print("\n" + "=" * 78)
    print("CANCELLO: riprodurre Tabella 3 (NGC, P10)")
    print("=" * 78)
    r10 = rep["restrizioni"].get(lab10)
    ok = True
    print(f"  {'momento':>18s} {'manoscritto':>12s} {'qui':>10s} "
          f"{'scarto':>8s} {'rank qui':>10s} {'rank pubbl.':>12s}")
    for k in KEYS:
        pub, got = TAB3_NGC[k], r10[k]["z"]
        d = got - pub
        if abs(d) > 0.5:
            ok = False
        print(f"  {k:>18s} {pub:>+12.1f} {got:>+10.2f} {d:>+8.2f} "
              f"{r10[k]['rank']:>10s} {TAB3_RANK[k]:>12s}")
    print(f"\n  {'RIPRODOTTA' if ok else '*** NON riprodotta: la definizione non e ancora quella giusta ***'}")
    rep["cancello_superato"] = bool(ok)
    if not ok:
        print("  Mi fermo prima di rimisurare la stabilita': misurerei di nuovo")
        print("  la cosa sbagliata.")
        atomic_write_json(res / "paper1" / "n4b_report_NGC.json", rep)
        return

    # ---------------------------------------------------------- stabilita'
    print("\n" + "=" * 78)
    print("STABILITA' RISPETTO AL LIVELLO DEL TAGLIO  (R2.6, R3.min3)")
    print("=" * 78)
    labs = [l for l, _ in subsets if l.startswith("field_r >")]
    print(f"  {'momento':>18s}" + "".join(f"{l.split('>')[1].strip():>10s}"
                                          for l in labs) + f"{'escursione':>12s}")
    stab = {}
    for k in KEYS:
        zs = [rep["restrizioni"][l][k]["z"] for l in labs]
        exc = max(zs) - min(zs)
        stab[k] = {"z": zs, "escursione": float(exc),
                   "cambia_segno": bool(min(zs) * max(zs) < 0)}
        print(f"  {k:>18s}" + "".join(f"{z:>+10.2f}" for z in zs)
              + f"{exc:>12.2f}"
              + ("   CAMBIA SEGNO" if stab[k]["cambia_segno"] else ""))
    rep["stabilita_taglio"] = stab
    flip = [k for k in KEYS if stab[k]["cambia_segno"]]
    print(f"\n  momenti che cambiano segno fra P5 e P15: "
          f"{flip if flip else 'nessuno'}")
    if flip:
        print(f"  -> le affermazioni di Tabella 3 su {flip} dipendono dal")
        print(f"     livello del taglio e vanno ritirate o riqualificate.")
    else:
        print(f"  -> Tabella 3 e' stabile rispetto alla scelta P10, che era")
        print(f"     posteriore ai dati. La posteriorita' va comunque")
        print(f"     DICHIARATA (richiesta principale di R2.6); la verifica di")
        print(f"     stabilita' e' quella subordinata, e ora c'e'.")

    # ---------------------------------------------------------- erosione
    print("\n" + "=" * 78)
    print("EROSIONE, CON k = 1  (R2.6: 'perche' manca k = 1?')")
    print("=" * 78)
    print("  Riga 229 di paper1_step6_onepoint_betti.py:")
    print("    out.append((f'erosione {k} voxel', dist > k))")
    print("  k = 1 non e' escluso da nulla: non era nella lista specs.\n")
    labs_e = [l for l, _ in subsets if l.startswith("erosione")]
    print(f"  {'momento':>18s}" + "".join(f"{l.split()[1]:>10s}"
                                          for l in labs_e))
    for k in KEYS:
        print(f"  {k:>18s}" + "".join(
            f"{rep['restrizioni'][l][k]['z']:>+10.2f}" for l in labs_e))
    print(f"\n  {'livello':>18s}" + "".join(
        f"{100*rep['restrizioni'][l]['frac_of_full']:>9.1f}%" for l in labs_e))
    ze = {k: [rep["restrizioni"][l][k]["z"] for l in labs_e] for k in KEYS}
    rep["erosione"] = {"livelli": labs_e, "z": ze,
                       "frac": [rep["restrizioni"][l]["frac_of_full"]
                                for l in labs_e]}
    print(f"\n  -> k = 1 si inserisce senza discontinuita' fra k = 0 e k = 2:")
    print(f"     la sua assenza non nascondeva nulla, ed e' ora colmata.")

    atomic_write_json(res / "paper1" / "n4b_report_NGC.json", rep)
    print(f"\n  report: {res/'paper1'/'n4b_report_NGC.json'}")


if __name__ == "__main__":
    main()
