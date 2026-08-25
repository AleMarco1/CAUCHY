#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2h_monotone.py

V2h - I DUE CACHE SONO LA STESSA INFORMAZIONE?

ACCERTATO (v2g, sezione A) - QUESTIONE CHIUSA
---------------------------------------------
phase8_test2_masked.json, generato 2026-07-03, n_mock_valid=2000,
masked_filtration=true:
    mock_beta1_max: mean 35436.686  std 312.9891651683112  z_desi -22.94228
Le stesse cifre decimali che paper1_remap.py produce indipendentemente.
Il record congelato dice 313.0. 445 e' l'artefatto della ricomputazione di
phase9_extract_features.py, passato attraverso un controllo di sanita' che
confronta la media e mai la deviazione standard.
Il record contiene anche: "N=2000; empirical p-floor ~1/2001. Ranks primary."
-> la disciplina basata sui ranghi era gia' dichiarata nel run originale.

PROBLEMA APERTO (v2g, sezione D)
--------------------------------
Il confronto max|a-b| sul cubo intero da' DIVERSI anche sui controlli
(idx 200/500/1000/1805: max|diff| 3138..10281). Ma quel test era sbagliato,
ed e' cieco a due spiegazioni benigne che spiegherebbero insieme le
differenze ovunque E l'accordo esatto su 1800 valori di N_H1:

  1. INVARIANZA MONOTONA. N_H1 dai sottolivelli del complesso cubico non
     cambia sotto rimappatura strettamente monotona. Se i due cache tengono
     la stessa informazione in scale diverse (conteggi vs delta = N/Nbar - 1,
     affine e monotona) i valori differiscono di migliaia e la TDA e'
     identica. L'accordo esatto su 1800 mock DIMOSTRA l'equivalenza
     monotona, non la contraddice.
  2. MASCHERA. Se i cubi di phase8 sono gia' mascherati e i nostri no, fuori
     maschera i valori sono arbitrari - e la filtrazione mascherata li
     ignora comunque.

TEST CORRETTO
-------------
Confrontare i campi con un criterio INVARIANTE PER TRASFORMAZIONI MONOTONE e
ristretto ALLA MASCHERA:
  - concordanza degli ordinamenti dei voxel (Spearman su un campione)
  - verifica che b sia funzione monotona di a (isotonia sui ranghi)
  - fit affine b = alpha*a + beta con residuo: se il residuo e' nullo, la
    relazione e' affine, il caso piu' semplice di monotona
Dove l'ordinamento coincide -> stessa informazione, TDA necessariamente
uguale. Dove diverge -> dati genuinamente diversi.

ESITO ATTESO SE L'IPOTESI DEL PILOTA E' VERA
--------------------------------------------
controlli (idx>=200) monotonamente equivalenti, blocco (idx<200) no.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2h_monotone.py
  python src\\paper1_rev_v2h_monotone.py --n_sample 400000
"""

import argparse
import json
import os
import tempfile
from pathlib import Path

import numpy as np

BLOCK_IDX = [0, 16, 27, 105, 139, 189]
CTRL_IDX = [200, 500, 1000, 1805]


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


def find_mask(root, region):
    name = f"bgs_{region.lower()}_mask_128.npy"
    for c in (root / "data" / "processed" / "phase6_fields" / name,
              root / "data" / "processed" / "paper1_fields" / name):
        if c.exists():
            return c
    hits = list(root.rglob(name))
    return hits[0] if hits else None


def spearman_sample(x, y):
    rx = np.argsort(np.argsort(x, kind="stable"))
    ry = np.argsort(np.argsort(y, kind="stable"))
    return float(np.corrcoef(rx, ry)[0, 1])


def monotone_report(a, b, n_sample, rng):
    """a, b: vettori 1D gia' ristretti alla maschera."""
    n = a.size
    if n > n_sample:
        sel = rng.choice(n, n_sample, replace=False)
        xs, ys = a[sel], b[sel]
    else:
        xs, ys = a, b

    rho = spearman_sample(xs, ys)
    r = float(np.corrcoef(xs, ys)[0, 1])

    # fit affine e residuo relativo
    A = np.column_stack([xs, np.ones(xs.size)])
    coef, *_ = np.linalg.lstsq(A, ys, rcond=None)
    resid = ys - A @ coef
    scale = float(np.std(ys)) or 1.0
    rel = float(np.max(np.abs(resid)) / scale)

    # violazioni di monotonia: ordinando per x, y deve essere non decrescente
    o = np.argsort(xs, kind="stable")
    yo = ys[o]
    dec = int(np.sum(np.diff(yo) < 0))
    frac_dec = dec / max(yo.size - 1, 1)

    return {"n_confrontati": int(xs.size),
            "spearman": rho, "pearson": r,
            "alpha": float(coef[0]), "beta": float(coef[1]),
            "residuo_affine_relativo": rel,
            "violazioni_monotonia_frac": float(frac_dec)}


def verdict(m):
    if m["spearman"] > 0.999999 and m["violazioni_monotonia_frac"] < 1e-6:
        return "MONOTONAMENTE EQUIVALENTI"
    if m["spearman"] > 0.999:
        return "quasi monotoni (verificare)"
    return "DATI DIVERSI"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--region", default="NGC")
    ap.add_argument("--n_sample", type=int, default=300000,
                    help="voxel campionati dentro maschera per indice")
    ap.add_argument("--seed", type=int, default=12345)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    cache = root / "data" / "processed" / "paper1_mock_deltas" / args.region
    fields = res / "phase8_test2_fields"
    rng = np.random.default_rng(args.seed)
    rep = {"script": "paper1_rev_v2h_monotone.py", "regione": args.region}

    mp = find_mask(root, args.region)
    if mp is None:
        print(f"[!] maschera bgs_{args.region.lower()}_mask_128.npy non trovata")
        return
    mask = np.load(mp).astype(bool).ravel()
    print("=" * 78)
    print("MASCHERA")
    print("=" * 78)
    print(f"  {mp}")
    print(f"  voxel dentro maschera: {int(mask.sum())} / {mask.size} "
          f"({100*mask.mean():.1f}%)")
    rep["maschera"] = {"file": str(mp), "n_dentro": int(mask.sum()),
                       "frazione": float(mask.mean())}

    print("\n" + "=" * 78)
    print("STATISTICHE DEI DUE CACHE (dentro maschera)")
    print("=" * 78)
    print(f"  {'idx':>5s} {'cache':>8s} {'media':>12s} {'sd':>12s} "
          f"{'min':>12s} {'max':>12s}")

    rows = []
    for i in BLOCK_IDX + CTRL_IDX:
        p1 = cache / f"delta_{i:04d}.npy"
        p8 = fields / f"test2_{i:04d}.npz"
        if not (p1.exists() and p8.exists()):
            print(f"  {i:>5d}  file assente (p1={p1.exists()} p8={p8.exists()})")
            continue
        a = np.load(p1).ravel().astype(np.float64)
        b = np.load(p8)["delta"].ravel().astype(np.float64)
        if a.size != mask.size or b.size != mask.size:
            print(f"  {i:>5d}  shape incompatibile con la maschera")
            continue
        am, bm = a[mask], b[mask]
        print(f"  {i:>5d} {'paper1':>8s} {am.mean():>12.4g} "
              f"{am.std():>12.4g} {am.min():>12.4g} {am.max():>12.4g}")
        print(f"  {i:>5d} {'phase8':>8s} {bm.mean():>12.4g} "
              f"{bm.std():>12.4g} {bm.min():>12.4g} {bm.max():>12.4g}")
        rows.append((i, am, bm, a, b))

    print("\n" + "=" * 78)
    print("TEST DI EQUIVALENZA MONOTONA, DENTRO MASCHERA")
    print("=" * 78)
    print(f"  {'idx':>5s} {'zona':>10s} {'Spearman':>12s} {'viol.mono':>11s} "
          f"{'resid.affine':>13s} {'verdetto':>28s}")
    rep["confronto"] = []
    for i, am, bm, a, b in rows:
        m = monotone_report(am, bm, args.n_sample, rng)
        v = verdict(m)
        zona = "blocco" if i < 200 else "controllo"
        print(f"  {i:>5d} {zona:>10s} {m['spearman']:>12.8f} "
              f"{m['violazioni_monotonia_frac']:>11.2e} "
              f"{m['residuo_affine_relativo']:>13.3e} {v:>28s}")
        m.update({"idx": i, "zona": zona, "verdetto": v})
        rep["confronto"].append(m)

        # quanto conta la maschera: stesso test FUORI maschera
        out = ~mask
        if out.sum() > 1000:
            mo = monotone_report(a[out], b[out], min(args.n_sample,
                                                     int(out.sum())), rng)
            rep["confronto"][-1]["fuori_maschera_spearman"] = mo["spearman"]

    print("\n" + "=" * 78)
    print("LETTURA")
    print("=" * 78)
    blk = [c for c in rep["confronto"] if c["zona"] == "blocco"]
    ctl = [c for c in rep["confronto"] if c["zona"] == "controllo"]
    ok_ctl = all(c["verdetto"] == "MONOTONAMENTE EQUIVALENTI" for c in ctl) and ctl
    ok_blk = all(c["verdetto"] == "MONOTONAMENTE EQUIVALENTI" for c in blk) and blk

    if ok_ctl and not ok_blk:
        print("  controlli equivalenti, blocco no")
        print("  -> IPOTESI DEL PILOTA CONFERMATA: phase8_test2_fields/")
        print("     conserva per 0-199 cubi diversi (il pilota), mai")
        print("     sovrascritti dal run completo. La ricomputazione di")
        print("     phase9 li ha letti come se fossero l'ensemble definitivo.")
        print("     Indagine chiusa: 313.0 e' il numero, 445 l'artefatto.")
    elif ok_ctl and ok_blk:
        print("  tutti equivalenti, blocco compreso")
        print("  -> i dati coincidono ovunque: la differenza sui 200 sta nel")
        print("     PERCORSO DI CODICE. Da confrontare compute_tda_features")
        print("     di phase8 con la catena di paper1_remap.py.")
    elif not ok_ctl:
        print("  nemmeno i controlli sono monotonamente equivalenti")
        print("  -> i due cache NON contengono la stessa informazione, eppure")
        print("     1800 valori di N_H1 coincidono esattamente. Questo e'")
        print("     contraddittorio e va risolto prima di ogni altra cosa:")
        print("     verificare che la maschera usata qui sia quella della")
        print("     filtrazione, e che delta_XXXX.npy sia il campo in")
        print("     ingresso alla TDA e non un prodotto intermedio.")
    print("\n  NB: la colonna alpha/beta del report dice quale trasformazione")
    print("  lega i due cache. alpha=1, beta=0 -> identici. Un residuo affine")
    print("  nullo con alpha diverso da 1 -> semplice cambio di scala.")

    outp = res / "paper1" / "rev_v2h_monotone_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()
