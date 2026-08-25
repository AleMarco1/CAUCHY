#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_m2b_hodscatter.py

M2b - LA DISPERSIONE HOD: VERIFICA INDIPENDENTE, E SU PIU' DI UN PUNTO

PERCHE'
-------
La decomposizione della varianza (paper1_record_consolidato.md §2.4) e':

    cosmologia (7 parametri)   160   26.1%   misurato su nwLH, n = 2000
    realizzazione delle CI     246   61.6%   ottenuto per DIFFERENZA
    HOD / downsampling         110   12.3%   PRESO IN PRESTITO da M26

Il 110 e' l'unico termine che non abbiamo mai controllato, e il 246 discende da
esso per sottrazione: se il 110 e' sbagliato, lo sono entrambi.

M26 lo misura con 50 semi su UNA cosmologia e UNA realizzazione (indice nwLH
1805, vicino a Planck) e lo usa come se fosse universale. Non e' detto che lo
sia: la dispersione HOD potrebbe dipendere da quanti aloni ha il mock, quindi
dalla sua cosmologia.

COSA FA QUESTO SCRIPT
---------------------
Ripete il test a semi multipli su PIU' indici, scelti al 10, 50 e 90 percentile
della distribuzione di N_H1 dell'ensemble nwLH. Cosi' si misura:

  - sigma_HOD a ciascun indice, da confrontare con i 110 di M26
  - se sigma_HOD varia fra indici: in tal caso il 110 non e' rappresentativo e
    va quotato con una dispersione che oggi non ha
  - se sigma_HOD correla con N_H1 del mock: sarebbe un'eteroschedasticita' che
    la decomposizione ignora

NOTA SU M2a
-----------
La parte mancante - sigma(realizzazione) a cosmologia fissa nel cut-sky -
richiede i cataloghi FoF FIDUCIALI di Quijote, che NON sono su disco:
data/raw/quijote/3D_cubes/fiducial/ contiene solo df_m_128_PCS_z=0.npy, un
campo di densita' di materia. Solo latin_hypercube_nwLH_hod ha i FoF
(groups_003, groups_004). M2a resta aperta in attesa di quel download.

IL CANCELLO, ELEGANTE
---------------------
Il valore in per_mock_NGC_R5.jsonl per l'indice i e' stato prodotto con seme
42 + i. Quel seme viene usato come PRIMO della sequenza, quindi funge da
cancello E da punto dati: deve riprodurre il JSONL esattamente. Se non lo fa,
mi fermo su quell'indice.

USO
---
  python src\\paper1_rev_m2b_hodscatter.py --s 5      # cancello + tempi
  python src\\paper1_rev_m2b_hodscatter.py            # 3 indici x 40 semi
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

NH1 = "base.N_H1"
SD_HOD_M26 = 110.0
M26_INDEX = 1805
NWLH_SD = 312.9891651683112


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


def read_jsonl(path):
    recs = []
    if not Path(path).exists():
        return recs
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    recs.append(json.loads(line))
                except Exception:
                    pass
    return recs


def append_jsonl(path, obj):
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=True) + "\n")
        f.flush(); os.fsync(f.fileno())


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


def sd_err(sd, n):
    return sd / np.sqrt(2.0 * (n - 1)) if n > 1 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--s", type=int, default=40, help="semi per indice")
    ap.add_argument("--indices", default="",
                    help="indici espliciti, separati da virgola; se vuoto usa "
                         "1805 (M26) piu' i percentili 10/50/90")
    ap.add_argument("--min_idx", type=int, default=200)
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / "m2b_hodscatter_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    # ---------------------------------------------------------- indici
    print("=" * 78)
    print("M2b - DISPERSIONE HOD A COSMOLOGIA E REALIZZAZIONE FISSE")
    print("=" * 78)
    if args.indices:
        idxs = [int(t) for t in args.indices.split(",") if t.strip()]
    else:
        pool = sorted(i for i, v in nh1.items()
                      if i >= args.min_idx and np.isfinite(v))
        vals = np.array([nh1[i] for i in pool])
        order = np.argsort(vals)
        idxs = []
        for p in (10, 50, 90):
            idxs.append(pool[order[int(round((p / 100.0) * (len(pool) - 1)))]])
        if M26_INDEX in nh1 and M26_INDEX not in idxs:
            idxs = [M26_INDEX] + idxs
    print(f"\n  indici scelti: {idxs}")
    for i in idxs:
        v = nh1.get(i, np.nan)
        pct = 100.0 * np.mean([x < v for x in nh1.values() if np.isfinite(x)])
        tag = "  <- indice usato da M26" if i == M26_INDEX else ""
        print(f"    {i:>5d}: N_H1 = {v:.0f}  (percentile {pct:.0f}){tag}")
    print(f"\n  {args.s} semi per indice; il primo e' {args.seed}+indice, "
          f"cioe' quello del run congelato: funge da cancello.")

    # ---------------------------------------------------------- run
    done = {(r["idx"], r["seed"]) for r in read_jsonl(outj)}
    t0 = time.time(); c = 0
    for i in idxs:
        print(f"\n  --- indice {i}")
        for s in range(args.s):
            sd_ = (args.seed + i) if s == 0 else (args.seed + 500000 + 1000 * i + s)
            if (i, sd_) in done:
                continue
            rng = np.random.default_rng(sd_)
            ph, mh, vh = M.read_halo_catalog(i, args.snapnum)
            if ph is None or len(ph) < 50:
                print(f"    [!] catalogo {i} non utilizzabile")
                break
            pg, vg = T2.populate_with_virial(ph, mh, vh, hod, rng)
            if len(pg) < 100:
                continue
            ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
            if ps is None or len(ps) < 100:
                continue
            nu = M.voxelize_mock(ps, field_r, sum_wr, mask)
            if nu is None:
                continue
            v = float(M.compute_tda_features(nu, mask, M.N_THRESH,
                                             masked=True)[4])
            if s == 0:
                exp = nh1.get(i, np.nan)
                ok = np.isfinite(exp) and abs(v - exp) < 0.5
                print(f"    CANCELLO seme {sd_}: {v:.0f}  JSONL {exp:.0f}  "
                      f"{'OK' if ok else '*** DISCORDE: salto indice ***'}")
                if not ok:
                    break
            append_jsonl(outj, {"idx": i, "seed": sd_, "N_H1": v,
                                "ngal": int(len(ps)), "is_gate": s == 0})
            c += 1
            if c % 10 == 0:
                tot = len(idxs) * args.s
                print(f"    [{c}] N_H1={v:.0f}   "
                      f"ETA {(time.time()-t0)/c*(tot-c)/60:.0f} min")

    # ---------------------------------------------------------- analisi
    recs = read_jsonl(outj)
    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    print(f"\n  {'indice':>7s} {'n':>4s} {'N_H1 congelato':>15s} "
          f"{'media semi':>11s} {'sigma_HOD':>12s} {'vs M26':>9s}")
    per_idx = {}
    for i in idxs:
        v = np.array([r["N_H1"] for r in recs if r["idx"] == i], float)
        if v.size < 5:
            continue
        s_, e_ = float(v.std(ddof=1)), sd_err(float(v.std(ddof=1)), v.size)
        z = (s_ - SD_HOD_M26) / e_ if e_ else np.nan
        print(f"  {i:>7d} {v.size:>4d} {nh1.get(i, np.nan):>15.0f} "
              f"{v.mean():>11.1f} {s_:>7.1f}+/-{e_:<4.1f} {z:>+9.1f}")
        per_idx[str(i)] = {"n": int(v.size), "congelato": nh1.get(i),
                           "mean": float(v.mean()), "sd": s_,
                           "sd_err": float(e_), "z_vs_m26": float(z)}
    if len(per_idx) < 2:
        print("\n  troppi pochi indici completati.")
        atomic_write_json(res / "paper1" / "m2b_report_NGC.json",
                          {"per_indice": per_idx})
        return

    sds = np.array([v["sd"] for v in per_idx.values()])
    ers = np.array([v["sd_err"] for v in per_idx.values()])
    ns = np.array([v["congelato"] for v in per_idx.values()], float)

    print(f"\n  sigma_HOD attraverso gli indici: {sds.mean():.1f} +/- "
          f"{sds.std(ddof=1) if sds.size > 1 else 0:.1f}")
    print(f"  M26 riporta {SD_HOD_M26:.0f} (50 semi, indice {M26_INDEX})")
    chi2 = float(np.sum(((sds - sds.mean()) / ers) ** 2))
    dof = sds.size - 1
    print(f"\n  omogeneita' fra indici: chi2 = {chi2:.1f} su {dof} gradi")
    if chi2 < dof + 3 * np.sqrt(2 * dof):
        print(f"  -> sigma_HOD e' COMPATIBILE con un valore unico: il 110 di")
        print(f"     M26 puo' essere usato come universale, e ora con una")
        print(f"     verifica su piu' punti invece che su uno.")
    else:
        print(f"  -> sigma_HOD VARIA fra indici: il 110 non e' rappresentativo.")
        print(f"     La decomposizione va quotata con la dispersione fra")
        print(f"     indici, non con un numero singolo.")
        if sds.size >= 3 and np.isfinite(ns).all():
            r = float(np.corrcoef(ns, sds)[0, 1])
            print(f"     correlazione sigma_HOD x N_H1 del mock: r = {r:+.2f}")
            print(f"     (se forte, e' eteroschedasticita' che la")
            print(f"      decomposizione ignora)")

    sb = float(sds.mean())
    print("\n" + "=" * 78)
    print("EFFETTO SULLA DECOMPOSIZIONE")
    print("=" * 78)
    print(f"  sigma totale nwLH            {NWLH_SD:.1f}")
    print(f"  sigma_HOD  record / misurata {SD_HOD_M26:.1f} / {sb:.1f}")
    resid = 269.6
    for nome, sh in (("record", SD_HOD_M26), ("misurata", sb)):
        v2 = resid ** 2 - sh ** 2
        print(f"  sigma(realizzazione), {nome:>8s}: "
              f"{np.sqrt(v2) if v2 > 0 else float('nan'):.1f}")
    print(f"\n  L'effetto sul termine di realizzazione e' modesto perche' entra")
    print(f"  in quadratura: anche uno scarto del 30% su sigma_HOD sposta")
    print(f"  sigma(realizzazione) di pochi punti. La verifica serve a")
    print(f"  sostituire un numero preso in prestito con uno misurato, non a")
    print(f"  cambiare la conclusione.")

    print(f"\n  NOTA: la dispersione HOD e' rumore di NOSTRA costruzione, non")
    print(f"  varianza fisica. L'ensemble che entra al denominatore delle z la")
    print(f"  contiene: la dispersione intrinseca dei mock e'")
    print(f"  sqrt({NWLH_SD:.1f}^2 - {sb:.1f}^2) = "
          f"{np.sqrt(NWLH_SD**2 - sb**2):.1f}. Usarla al posto di "
          f"{NWLH_SD:.1f}")
    print(f"  alzerebbe la z. Non lo facciamo - la scelta conservativa e'")
    print(f"  tenere la dispersione piena - ma va dichiarato che e'")
    print(f"  conservativa, invece di lasciarlo intendere.")

    atomic_write_json(res / "paper1" / "m2b_report_NGC.json", {
        "script": "paper1_rev_m2b_hodscatter.py",
        "per_indice": per_idx, "sd_hod_media": sb,
        "sd_hod_dispersione": float(sds.std(ddof=1)) if sds.size > 1 else None,
        "m26": SD_HOD_M26, "chi2_omogeneita": chi2, "dof": int(dof),
        "sigma_intrinseca_nwlh": float(np.sqrt(NWLH_SD ** 2 - sb ** 2)),
        "m2a_bloccata": "cataloghi FoF fiduciali assenti su disco"})
    print(f"\n  report: {res/'paper1'/'m2b_report_NGC.json'}")


if __name__ == "__main__":
    main()
