#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2g_frozen.py

V2g - IL RECORD CONGELATO, E PERCHE' PROPRIO GLI INDICI 0-199

ACCERTATO LEGGENDO I SORGENTI
-----------------------------
phase9_extract_features.py e' il PRODUTTORE di phase9_likeforlike_arrays.npz.
Non e' l'ensemble congelato: e' una RICOMPUTAZIONE, scritta perche' la tabella
per-mock del run definitivo conteneva solo il pilota N=200 e l'istogramma
empirico serviva sui 2000 grezzi.

Il suo stesso docstring (riga 25) dichiara il riferimento congelato:
    phase8_test2_masked.json -> beta1_max 35436.7 +/- 313.0
cioe' il numero di Paper 1, che paper1_remap.py riproduce indipendentemente
(35436.686 +/- 312.99).

Il controllo di sanita' (righe 149-156) calcola
    drift = |media - media_congelata| / sigma_congelata
e lo confronta con 0.5. Sul valore reale: |35424.8 - 35436.7| / 313.0 = 0.038.
Passa. La DEVIAZIONE STANDARD viene stampata ma non confrontata mai: una sigma
passata da 313.0 a 444.8 (+42%) e' comparsa a schermo accanto al suo valore
congelato con l'esito "[ok] consistent with frozen run", ed e' finita nella
tabella battery di cauchy_mnras.tex (righe 459, 510, 636) e nella
decomposizione della varianza (riga 735).

IPOTESI ANCORA DA VERIFICARE
----------------------------
Perche' proprio 0-199. Sospetto: phase8_test2_fields/ contiene per quei 200
indici i cubi del PILOTA, mai sovrascritti dal run completo - coerente col
fatto che phase8_test2_permock.csv copra esattamente il pilota. E' un'ipotesi.

TEST DEFINITIVO (D)
-------------------
Caricare lo stesso indice dai DUE cache e confrontare i campi:
  - campi DIVERSI            -> differiscono i dati (cubi del pilota)
  - campi IDENTICI, TDA no   -> differisce il percorso di codice
Questo chiude la questione senza ulteriori inferenze.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2g_frozen.py
  python src\\paper1_rev_v2g_frozen.py --n_check 8
"""

import argparse
import csv
import datetime as dt
import json
import os
import tempfile
from pathlib import Path

import numpy as np

FROZEN_REF = {"mean": 35436.7, "std": 313.0}
NPZ_REF = {"mean": 35424.784, "std": 444.814}
# indici discrepanti noti (blocco) e controlli fuori blocco
DEFAULT_DISC = [0, 16, 27, 139, 105, 189]
DEFAULT_CTRL = [200, 500, 1000, 1805]


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


def walk_json(obj, prefix="", out=None, depth=0):
    """Appiattisce un JSON annidato per stamparlo per intero."""
    if out is None:
        out = []
    if depth > 6:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            walk_json(v, f"{prefix}{k}.", out, depth + 1)
    elif isinstance(obj, list):
        if len(obj) <= 8 and all(not isinstance(x, (dict, list)) for x in obj):
            out.append((prefix.rstrip("."), obj))
        else:
            out.append((prefix.rstrip("."), f"<lista di {len(obj)}>"))
    else:
        out.append((prefix.rstrip("."), obj))
    return out


def mtime(p):
    return dt.datetime.fromtimestamp(p.stat().st_mtime).strftime(
        "%Y-%m-%d %H:%M:%S")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--n_check", type=int, default=6,
                    help="quanti indici discrepanti confrontare campo-a-campo")
    ap.add_argument("--region", default="NGC")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    rep = {"script": "paper1_rev_v2g_frozen.py",
           "riferimenti": {"congelato": FROZEN_REF, "npz": NPZ_REF}}

    # ============================================================ A
    print("=" * 78)
    print("A - IL RECORD CONGELATO: phase8_test2_masked.json")
    print("=" * 78)
    fj = res / "phase8_test2_masked.json"
    if not fj.exists():
        print(f"  [!] {fj} non trovato")
    else:
        with open(fj, "r", encoding="utf-8") as f:
            J = json.load(f)
        print(f"  {fj}   ({fj.stat().st_size/1024:.1f} kB, mtime {mtime(fj)})\n")
        for k, v in walk_json(J):
            if isinstance(v, float):
                print(f"    {k:<44s} = {v:.6g}")
            else:
                print(f"    {k:<44s} = {v}")
        rep["phase8_test2_masked"] = J

        print(f"\n  CONFRONTO CON I DUE CANDIDATI:")
        print(f"    congelato dichiarato : {FROZEN_REF['mean']} +/- "
              f"{FROZEN_REF['std']}   (= Paper 1)")
        print(f"    npz ricomputato      : {NPZ_REF['mean']:.1f} +/- "
              f"{NPZ_REF['std']:.1f}   (= tabella battery M26)")
        print(f"    -> quale dei due compare in questo JSON e' IL numero")
        print(f"       congelato, e l'altro va corretto.")

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - IL CSV PER-MOCK: quali indici copre davvero?")
    print("=" * 78)
    fc = res / "phase8_test2_permock.csv"
    if not fc.exists():
        print(f"  [!] {fc} non trovato")
    else:
        rows = list(csv.DictReader(open(fc, newline="", encoding="utf-8")))
        print(f"  {fc}   ({len(rows)} righe, mtime {mtime(fc)})")
        print(f"  colonne: {list(rows[0].keys()) if rows else '-'}")
        idxs = []
        for r in rows:
            try:
                idxs.append(int(r.get("index", "")))
            except ValueError:
                pass
        if idxs:
            a = np.array(sorted(idxs))
            contiguo = bool(np.array_equal(a, np.arange(a[0], a[0] + a.size)))
            print(f"  indici: {a.min()}..{a.max()}   n={a.size}   "
                  f"contigui: {'SI' if contiguo else 'NO'}")
            print(f"  coincidono col blocco 0-199: "
                  f"{'SI' if (a.min() == 0 and a.max() == 199 and a.size == 200) else 'NO'}")
            rep["permock_csv"] = {"n": a.size, "min": int(a.min()),
                                  "max": int(a.max()), "contigui": contiguo,
                                  "colonne": list(rows[0].keys())}

    # ============================================================ C
    print("\n" + "=" * 78)
    print("C - I CUBI CONGELATI: phase8_test2_fields/")
    print("=" * 78)
    fd_ = res / "phase8_test2_fields"
    if not fd_.exists():
        print(f"  [!] {fd_} non trovato")
        files = []
    else:
        files = sorted(fd_.glob("test2_*.npz"))
        print(f"  {len(files)} file test2_*.npz")
        if files:
            print(f"  primi 3 nomi : {[p.name for p in files[:3]]}")
            print(f"  ultimi 3 nomi: {[p.name for p in files[-3:]]}")
            pad = all(len(p.stem.split('_')[1]) == len(files[0].stem.split('_')[1])
                      for p in files if len(p.stem.split('_')) > 1)
            print(f"  zero-padding uniforme: {'SI' if pad else 'NO (il sorted() lessicografico scramblerebbe l ordine)'}")

            szs = np.array([p.stat().st_size for p in files])
            mts = np.array([p.stat().st_mtime for p in files])
            fidx = []
            for p in files:
                try:
                    fidx.append(int(p.stem.split("_")[1]))
                except (IndexError, ValueError):
                    fidx.append(-1)
            fidx = np.array(fidx)
            inb = (fidx >= 0) & (fidx < 200)
            out = fidx >= 200
            print(f"\n  dimensioni: {len(np.unique(szs))} valori distinti")
            for u, c in zip(*np.unique(szs, return_counts=True)):
                print(f"    {u/1024/1024:>8.2f} MB -> {c} file")
            print(f"\n  blocco 0-199 ({int(inb.sum())} file) vs resto "
                  f"({int(out.sum())} file):")
            if inb.any() and out.any():
                print(f"    mtime mediano 0-199   : "
                      f"{dt.datetime.fromtimestamp(np.median(mts[inb])):%Y-%m-%d %H:%M}")
                print(f"    mtime mediano 200-fine: "
                      f"{dt.datetime.fromtimestamp(np.median(mts[out])):%Y-%m-%d %H:%M}")
                disgiunti = bool(mts[inb].max() < mts[out].min()
                                 or mts[inb].min() > mts[out].max())
                print(f"    intervalli di mtime disgiunti: "
                      f"{'SI *** scritti in due sessioni diverse ***' if disgiunti else 'NO'}")
                print(f"    dimensione unica nel blocco: "
                      f"{len(np.unique(szs[inb]))}, nel resto: "
                      f"{len(np.unique(szs[out]))}")
            else:
                disgiunti = None
                print(f"    [!] una delle due partizioni e' vuota - "
                      f"confronto mtime saltato")
            rep["campi_congelati"] = {
                "n_file": len(files), "padding_uniforme": bool(pad),
                "n_blocco": int(inb.sum()), "n_resto": int(out.sum()),
                "mtime_disgiunti": disgiunti,
                "dim_distinte_blocco": int(len(np.unique(szs[inb]))) if inb.any() else None,
                "dim_distinte_resto": int(len(np.unique(szs[out]))) if out.any() else None}

    # ============================================================ C2
    print("\n" + "=" * 78)
    print("C2 - npz['index']: l'array e' allineato agli indici dei mock?")
    print("=" * 78)
    npzp = res / "phase9_likeforlike_arrays.npz"
    m26 = idxarr = None
    if npzp.exists():
        z = np.load(npzp, allow_pickle=True)
        m26 = np.asarray(z["beta1_max"], float)
        if "index" in z.files:
            idxarr = np.asarray(z["index"]).ravel()
            mono = bool(np.array_equal(idxarr, np.arange(idxarr.size)))
            print(f"  index = 0..{idxarr.size-1} esattamente: "
                  f"{'SI' if mono else 'NO'}")
            if not mono:
                bad = np.where(idxarr != np.arange(idxarr.size))[0]
                print(f"    *** {bad.size} posizioni fuori posto; prime: "
                      f"{bad[:12].tolist()} ***")
                print(f"    valori attesi {np.arange(idxarr.size)[bad[:6]].tolist()}"
                      f" trovati {idxarr[bad[:6]].tolist()}")
                print(f"    -> il confronto posizionale fatto finora va RIFATTO")
            rep["npz_index_monotono"] = mono

    # ============================================================ D
    print("\n" + "=" * 78)
    print("D - TEST DEFINITIVO: gli stessi indici nei due cache")
    print("=" * 78)
    cache = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    print(f"  cache Paper 1 : {cache}")
    print(f"  cubi phase8   : {fd_}")
    if not cache.exists():
        print(f"  [!] cache Paper 1 non trovata")
    elif not files:
        print(f"  [!] cubi phase8 non trovati")
    else:
        check = DEFAULT_DISC[:args.n_check] + DEFAULT_CTRL
        print(f"\n  {'idx':>5s} {'zona':>10s} {'campi':>12s} "
              f"{'max|diff|':>12s} {'shape/dtype':>26s}")
        rep["confronto_campi"] = []
        for i in check:
            p1 = cache / f"delta_{i:04d}.npy"
            p8 = fd_ / f"test2_{i:04d}.npz"
            zona = "blocco" if i < 200 else "controllo"
            if not p1.exists() or not p8.exists():
                print(f"  {i:>5d} {zona:>10s} {'file assente':>12s}   "
                      f"{'p1=' + str(p1.exists()):>12s} p8={p8.exists()}")
                continue
            try:
                a = np.load(p1)
                b = np.load(p8)["delta"]
            except Exception as e:
                print(f"  {i:>5d} {zona:>10s} errore: {e}")
                continue
            if a.shape != b.shape:
                verdetto = "SHAPE DIVERSA"
                md = float("nan")
            else:
                d = np.abs(a.astype(np.float64) - b.astype(np.float64))
                md = float(d.max())
                verdetto = "IDENTICI" if md == 0.0 else "DIVERSI"
            print(f"  {i:>5d} {zona:>10s} {verdetto:>12s} {md:>12.6g} "
                  f"{str(a.shape) + ' ' + str(a.dtype):>26s}")
            rep["confronto_campi"].append(
                {"idx": i, "zona": zona, "verdetto": verdetto,
                 "max_diff": md, "shape": list(a.shape)})

        print("\n  LETTURA:")
        print("    campi DIVERSI nel blocco e IDENTICI nei controlli")
        print("      -> phase8_test2_fields/ contiene i cubi del PILOTA per")
        print("         0-199: differiscono i DATI. Ipotesi confermata.")
        print("    campi IDENTICI ovunque")
        print("      -> i dati coincidono e la differenza e' nel percorso di")
        print("         codice (compute_tda_features vs la nostra catena):")
        print("         ipotesi del pilota SMENTITA, si indaga il codice.")
        print("    campi DIVERSI anche nei controlli")
        print("      -> i due cache non sono confrontabili affatto e tutto il")
        print("         confronto 1800/2000 va reinterpretato.")

    outp = res / "paper1" / "rev_v2g_frozen_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()
