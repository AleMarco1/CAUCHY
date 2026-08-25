#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_m2_fiducial.py

M2 - DISPERSIONE A COSMOLOGIA FISSA NELLA GEOMETRIA DEL PAPER

DUE SCOPI, IL SECONDO PIU' IMPORTANTE DEL PRIMO
-----------------------------------------------
1. VERIFICA CONTABILE. La decomposizione della varianza
   (paper1_record_consolidato.md §2.4) e':

     cosmologia (7 parametri)   160   26.1%   misurato su nwLH
     realizzazione delle CI     246   61.6%   ottenuto per DIFFERENZA
     HOD / downsampling         110   12.3%   PRESO IN PRESTITO da M26

   Il 110 viene da un test a 50 semi su UNA cosmologia e UNA realizzazione
   (indice nwLH 1805), mai verificato indipendentemente; e il 246 discende da
   quello per sottrazione. Sono le due riserve del §3.1.

2. SIGNIFICATIVITA' RISPETTO A UN MODELLO. Referee 2 §1 chiude cosi':
     "la dispersione al denominatore mescola 2000 cosmologie diverse: la z non
      e' 'significativita' rispetto al modello', e' distanza dalla famiglia, e
      va chiamata cosi'."
   Un ensemble FIDUCIALE e' a cosmologia fissa: il rank e la z di DESI contro
   quell'ensemble SONO significativita' rispetto a un modello. E' il numero che
   il referee dice mancare, e oggi non esiste.

DISEGNO
-------
  M2a  K realizzazioni fiduciali, un seme ciascuna
       -> sigma(realizzazione + HOD + downsampling) a cosmologia fissa
  M2b  UNA realizzazione fiduciale, S semi diversi
       -> sigma(HOD + downsampling) a cosmologia E realizzazione fisse
          verifica indipendente dei 110 di M26

  sigma(realizzazione) = sqrt(sigma_a^2 - sigma_b^2)

Tutto nella geometria cut-sky del paper: stessa maschera, stesso n(z), stesso
density matching, stesso build_field, stessa filtrazione mascherata.

CANCELLO
--------
Non esiste un valore congelato per i mock fiduciali da riprodurre. Si valida
allora l'impianto sul lato nwLH: un mock del set nwLH, girato attraverso questo
stesso codice, deve riprodurre esattamente il valore in per_mock_NGC_R5.jsonl.
Solo dopo si ripunta HOD_CATALOG_DIR sul set fiduciale.

E' lo schema che ha funzionato in N9 (DESI 28256 e mock 200 = 35257, esatti).

USO
---
  python src\\paper1_rev_m2_fiducial.py --k 3 --s 0     # cancello + tempi
  python src\\paper1_rev_m2_fiducial.py                 # K=150, S=40
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
DESI_NH1 = 28256.0
# valori da verificare, dal record consolidato
NWLH_MEAN = 35436.686
NWLH_SD = 312.9891651683112
SD_RESID_OLS = 269.6      # residuo dopo i 7 parametri cosmologici
SD_HOD_M26 = 110.0        # preso in prestito da M26
SD_REAL_DERIVED = 246.0   # ottenuto per differenza


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
    """Errore standard su una deviazione standard campionaria."""
    return sd / np.sqrt(2.0 * (n - 1)) if n > 1 else np.nan


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--k", type=int, default=150,
                    help="realizzazioni fiduciali (M2a)")
    ap.add_argument("--s", type=int, default=40,
                    help="semi sulla stessa realizzazione (M2b)")
    ap.add_argument("--fid_ref", type=int, default=0,
                    help="indice della realizzazione fiduciale usata in M2b")
    ap.add_argument("--snapnum", type=int, default=3)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--gate_idx", type=int, default=200)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    outj = res / "paper1" / "m2_fiducial_NGC.jsonl"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    import phase8_test2_masked as T2

    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)
    field_r, sum_wr = M.load_desi_random_field()
    nz_z, nz_target = M.load_bgs_nz()
    hod = M.HOD_MEDIAN

    def one_mock(idx, seed):
        rng = np.random.default_rng(seed)
        ph, mh, vh = M.read_halo_catalog(idx, args.snapnum)
        if ph is None or len(ph) < 50:
            return None, 0
        pg, vg = T2.populate_with_virial(ph, mh, vh, hod, rng)
        if len(pg) < 100:
            return None, 0
        ps = M.carve_cutsky(pg, vg, mask, nz_z, nz_target, rng)
        if ps is None or len(ps) < 100:
            return None, 0
        nu = M.voxelize_mock(ps, field_r, sum_wr, mask)
        if nu is None:
            return None, 0
        return float(M.compute_tda_features(nu, mask, M.N_THRESH,
                                            masked=True)[4]), int(len(ps))

    print("=" * 78)
    print("M2 - DISPERSIONE A COSMOLOGIA FISSA")
    print("=" * 78)

    # ---------------------------------------------------------- cancello
    print("\n[GATE] un mock nwLH attraverso questo stesso codice")
    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))
    t0 = time.time()
    g, ng = one_mock(args.gate_idx, args.seed + args.gate_idx)
    exp = nh1.get(args.gate_idx, np.nan)
    print(f"  mock nwLH {args.gate_idx}: {g if g else float('nan'):.0f}   "
          f"JSONL {exp:.0f}   "
          f"{'OK' if g and abs(g-exp) < 0.5 else '*** FALLITO ***'}"
          f"   ({time.time()-t0:.0f} s, {ng} galassie)")
    if not (g and abs(g - exp) < 0.5):
        print("  L'impianto non riproduce la catena congelata. Mi fermo.")
        return
    sec_per_mock = time.time() - t0

    # ---------------------------------------------------------- fiduciale
    fid_dir = root / "data" / "raw" / "quijote" / "3D_cubes" / "fiducial"
    if not fid_dir.exists():
        print(f"\n[FATAL] {fid_dir} non trovata")
        return
    n_avail = sum(1 for p in fid_dir.iterdir() if p.is_dir())
    print(f"\n  set fiduciale: {fid_dir}  ({n_avail} realizzazioni)")
    print(f"  tempo stimato: M2a {args.k*sec_per_mock/60:.0f} min + "
          f"M2b {args.s*sec_per_mock/60:.0f} min")
    old_dir = M.HOD_CATALOG_DIR
    M.HOD_CATALOG_DIR = fid_dir

    done = {(r["run"], r["idx"], r["seed"]) for r in read_jsonl(outj)}
    try:
        # ------------------------------------------------------ M2a
        print(f"\n[M2a] {args.k} realizzazioni fiduciali, un seme ciascuna")
        t0 = time.time(); c = 0
        for i in range(args.k):
            key = ("a", i, args.seed + i)
            if key in done:
                continue
            v, n = one_mock(i, args.seed + i)
            if v is None:
                print(f"    [!] realizzazione {i} scartata")
                continue
            append_jsonl(outj, {"run": "a", "idx": i, "seed": args.seed + i,
                                "N_H1": v, "ngal": n})
            c += 1
            if c == 1 or c % 20 == 0:
                print(f"    [{c}] idx={i} N_H1={v:.0f}  "
                      f"ETA {(time.time()-t0)/c*(args.k-c)/60:.0f} min")

        # ------------------------------------------------------ M2b
        if args.s > 0:
            print(f"\n[M2b] realizzazione fiduciale {args.fid_ref}, "
                  f"{args.s} semi")
            t0 = time.time(); c = 0
            for s in range(args.s):
                sd_ = args.seed + 100000 + s
                key = ("b", args.fid_ref, sd_)
                if key in done:
                    continue
                v, n = one_mock(args.fid_ref, sd_)
                if v is None:
                    continue
                append_jsonl(outj, {"run": "b", "idx": args.fid_ref,
                                    "seed": sd_, "N_H1": v, "ngal": n})
                c += 1
                if c == 1 or c % 10 == 0:
                    print(f"    [{c}] seme {sd_} N_H1={v:.0f}  "
                          f"ETA {(time.time()-t0)/c*(args.s-c)/60:.0f} min")
    finally:
        M.HOD_CATALOG_DIR = old_dir

    # ---------------------------------------------------------- analisi
    recs = read_jsonl(outj)
    A = np.array([r["N_H1"] for r in recs if r["run"] == "a"], float)
    B = np.array([r["N_H1"] for r in recs if r["run"] == "b"], float)
    if A.size < 10:
        print("\n  troppe poche realizzazioni per l'analisi.")
        return

    sa, ea = float(A.std(ddof=1)), sd_err(float(A.std(ddof=1)), A.size)
    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    print(f"\n  M2a - {A.size} realizzazioni fiduciali (cosmologia fissa)")
    print(f"    media {A.mean():.1f} +/- {A.std(ddof=1)/np.sqrt(A.size):.1f}")
    print(f"    sigma {sa:.1f} +/- {ea:.1f}")
    rep = {"script": "paper1_rev_m2_fiducial.py",
           "m2a": {"n": int(A.size), "mean": float(A.mean()),
                   "sd": sa, "sd_err": float(ea)}}

    sb = eb = None
    if B.size > 5:
        sb, eb = float(B.std(ddof=1)), sd_err(float(B.std(ddof=1)), B.size)
        print(f"\n  M2b - {B.size} semi sulla realizzazione {args.fid_ref}")
        print(f"    media {B.mean():.1f}   sigma {sb:.1f} +/- {eb:.1f}")
        print(f"    M26 riporta {SD_HOD_M26:.0f} (50 semi, nwLH 1805)")
        z = (sb - SD_HOD_M26) / eb if eb else np.nan
        print(f"    scarto dal valore preso in prestito: {z:+.1f} sigma  "
              f"-> {'COMPATIBILE' if abs(z) < 3 else 'DISCORDE'}")
        rep["m2b"] = {"n": int(B.size), "mean": float(B.mean()), "sd": sb,
                      "sd_err": float(eb), "m26": SD_HOD_M26,
                      "z_vs_m26": float(z)}

        v2 = sa ** 2 - sb ** 2
        if v2 > 0:
            sr = float(np.sqrt(v2))
            print(f"\n  sigma(realizzazione) = sqrt({sa:.1f}^2 - {sb:.1f}^2) "
                  f"= {sr:.1f}")
            print(f"    ottenuto per differenza nel record: "
                  f"{SD_REAL_DERIVED:.0f}")
            rep["sigma_realizzazione"] = sr
        else:
            print(f"\n  *** sigma_b > sigma_a: la dispersione a realizzazione")
            print(f"      fissa supera quella fra realizzazioni. Impossibile")
            print(f"      se le due misure sono coerenti: da indagare. ***")

    print("\n" + "=" * 78)
    print("CONFRONTO CON LA DECOMPOSIZIONE DEL RECORD")
    print("=" * 78)
    print(f"  {'termine':>34s} {'nel record':>12s} {'misurato':>14s}")
    print(f"  {'sigma totale nwLH':>34s} {NWLH_SD:>12.1f} {'-':>14s}")
    print(f"  {'residuo dopo cosmologia (real+HOD)':>34s} "
          f"{SD_RESID_OLS:>12.1f} {sa:>8.1f} +/- {ea:<4.1f}")
    if sb is not None:
        print(f"  {'HOD/downsampling':>34s} {SD_HOD_M26:>12.1f} "
              f"{sb:>8.1f} +/- {eb:<4.1f}")
    dd = (sa - SD_RESID_OLS) / ea if ea else np.nan
    print(f"\n  scarto del residuo: {sa-SD_RESID_OLS:+.1f} = {dd:+.1f} sigma")
    if abs(dd) < 3:
        print(f"  -> la decomposizione REGGE: la dispersione a cosmologia")
        print(f"     fissa, misurata direttamente nella geometria del paper,")
        print(f"     coincide con quella ottenuta per sottrazione dai 7")
        print(f"     parametri. Le riserve del §3.1 sono chiuse.")
    else:
        print(f"  -> la decomposizione NON regge. Il residuo OLS assorbiva")
        print(f"     dipendenze cosmologiche non lineari, oppure la stima")
        print(f"     nwLH e quella fiduciale non sono confrontabili. Va")
        print(f"     riscritto il §2.4 del record con la misura diretta.")
    rep["confronto"] = {"residuo_record": SD_RESID_OLS, "residuo_misurato": sa,
                        "scarto_sigma": float(dd)}

    print("\n" + "=" * 78)
    print("SIGNIFICATIVITA' RISPETTO A UN MODELLO  (Referee 2 §1)")
    print("=" * 78)
    below = int((A < DESI_NH1).sum())
    zf = (DESI_NH1 - A.mean()) / sa
    print(f"  ensemble a cosmologia FISSA (fiduciale Quijote), n = {A.size}")
    print(f"    DESI              {DESI_NH1:.0f}")
    print(f"    mock fiduciali    {A.mean():.1f} +/- {sa:.1f}")
    print(f"    mock sotto DESI   {below}")
    print(f"    rank              {below+1}/{A.size+1}   "
          f"p <= {(below+1)/(A.size+1):.3e}")
    print(f"    z                 {zf:+.2f}")
    print(f"\n  per confronto, contro l'ensemble nwLH (2000 cosmologie):")
    print(f"    rank 1/2001, z {(DESI_NH1-NWLH_MEAN)/NWLH_SD:+.2f}")
    print(f"\n  La z fiduciale e' significativita' rispetto a UN MODELLO; la")
    print(f"  z nwLH e' distanza dalla FAMIGLIA. Sono due enunciati diversi e")
    print(f"  vanno riportati entrambi, etichettati - che e' esattamente cio'")
    print(f"  che Referee 2 chiede.")
    print(f"\n  scarto fra le due medie: {A.mean()-NWLH_MEAN:+.1f} generatori")
    print(f"  (se grande, la cosmologia fiduciale non sta al centro")
    print(f"   dell'hypercube, e va detto)")
    rep["significativita"] = {
        "desi": DESI_NH1, "mock_mean": float(A.mean()), "mock_sd": sa,
        "n_sotto": below, "rank": f"{below+1}/{A.size+1}",
        "p": (below + 1) / (A.size + 1), "z_modello": float(zf),
        "z_famiglia": float((DESI_NH1 - NWLH_MEAN) / NWLH_SD),
        "scarto_medie": float(A.mean() - NWLH_MEAN)}

    atomic_write_json(res / "paper1" / "m2_report_NGC.json", rep)
    print(f"\n  report: {res/'paper1'/'m2_report_NGC.json'}")


if __name__ == "__main__":
    main()
