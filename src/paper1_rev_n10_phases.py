#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_n10_phases.py

N10 - RANDOMIZZAZIONE DELLE FASI A SPETTRO FISSATO

Referee 3 §1(a). E' il test che chiude E3 senza extrapolare nulla.

PERCHE' E' SALITO IN CIMA
-------------------------
N1c ha misurato che P(k)+PDF spiegano il 26.5% del deficit e che DESI cade a 30
dispersioni dalla relazione dei mock. Ma la distanza di Mahalanobis di DESI
nello spazio a 16 bande e' 34.3 contro ~4 di un mock tipico: la relazione va
EXTRAPOLATA, e ogni frazione di deficit spiegata dipende da un'assunzione di
linearita' che nessun mock verifica in quella regione.

N10 non extrapola: usa gli spettri OSSERVATI.

IL DISEGNO, PIU' FORTE DI QUELLO DEL PIANO
------------------------------------------
Non si confronta DESI-con-fasi-randomizzate contro i mock ORIGINALI: sarebbe
sbilanciato, perche' la randomizzazione cambia N_H1 anche per ragioni che non
c'entrano con DESI. Si applica la STESSA procedura a entrambi e si misura come
cambia il DEFICIT:

    frazione attribuibile allo spettro = deficit_PR / deficit_originale

  ~ 1  -> il deficit sopravvive alla randomizzazione: e' spettrale, e la tesi
          "oltre il due-punti" cade
  ~ 0  -> il deficit svanisce randomizzando: era informazione di fase, e la
          tesi e' dimostrata
  intermedio -> si quota la frazione, che e' il risultato

UNA CONSEGUENZA GRADITA DEL LEMMA
---------------------------------
La randomizzazione delle fasi rende il campo gaussiano in spazio reale,
cambiandone la PDF a un punto. Ma N_H1 e' invariante per rimappature monotone,
quindi il cambio di PDF NON contamina la misura: il confronto e' puramente
fasi contro spettro. Non serve ripristinare la PDF.

METODO
------
Per un campo reale la randomizzazione deve preservare la simmetria hermitiana.
Si prendono le ampiezze del campo e le fasi di un rumore bianco gaussiano:

    A   = |rfftn(nu)|
    W   = rfftn(randn(shape))
    nu' = irfftn(A * W / |W|)

che restituisce per costruzione un campo reale con |F| identico.

Il campo risultante NON e' nullo fuori maschera, ma la filtrazione mascherata
sostituisce comunque l'esterno con la sentinella, quindi non incide. Stesso
trattamento per DESI e per i mock.

AUTOCONTROLLI
-------------
  1. N_H1 del campo DESI originale deve dare 28256
  2. lo spettro del campo randomizzato deve coincidere con l'originale a
     precisione di macchina (max|dA|/A < 1e-10)
  3. N_H1 originale di ogni mock deve coincidere col JSONL
Se uno fallisce, lo script si ferma.

PARALLELISMO
------------
Usa gudhi: compete per CPU con paper1_rev_n2_persistence.py. Su macchina
multicore i due processi occupano core diversi. Parti da --n_desi 10
--n_mock 10 e verifica che l'ETA di N2 non peggiori.

Append-only JSONL, resumable.

USO
---
  python src\\paper1_rev_n10_phases.py --n_desi 10 --n_mock 10    # pilota
  python src\\paper1_rev_n10_phases.py --n_desi 50 --n_mock 100
"""

import argparse
import json
import os
import sys
import tempfile
import time
from pathlib import Path

import numpy as np

DESI_NH1 = 28256.0
NH1 = "base.N_H1"
MIN_IDX = 200


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


def phase_randomize(nu, rng, check=False):
    """Campo reale con lo stesso |F(k)| e fasi casuali."""
    F = np.fft.rfftn(nu.astype(np.float64))
    A = np.abs(F)
    W = np.fft.rfftn(rng.standard_normal(nu.shape))
    aW = np.abs(W)
    aW[aW == 0] = 1.0
    out = np.fft.irfftn(A * (W / aW), s=nu.shape)
    err = None
    if check:
        A2 = np.abs(np.fft.rfftn(out))
        d = np.abs(A2 - A)
        scale = A.max() if A.max() > 0 else 1.0
        err = float(d.max() / scale)
    return out.astype(np.float32), err


def stats(v):
    v = np.asarray(v, float)
    return {"n": int(v.size), "mean": float(v.mean()),
            "std": float(v.std(ddof=1)) if v.size > 1 else 0.0,
            "sem": float(v.std(ddof=1) / np.sqrt(v.size)) if v.size > 1 else 0.0,
            "min": float(v.min()), "max": float(v.max())}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--n_desi", type=int, default=50)
    ap.add_argument("--n_mock", type=int, default=100)
    ap.add_argument("--min_idx", type=int, default=MIN_IDX)
    ap.add_argument("--seed", type=int, default=20260725)
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    res = root / "results"
    fdir = res / "phase8_test2_fields"
    outj = res / "paper1" / "n10_phases_NGC.jsonl"
    desi_cache = res / "paper1" / "n1_desi_nu_NGC.npy"

    sys.path.insert(0, str(root / "src"))
    import phase8_cutsky_mocks as M
    mask = np.load(root / "data" / "processed" / "phase6_fields" /
                   "bgs_ngc_mask_128.npy").astype(bool)
    rng = np.random.default_rng(args.seed)

    print("=" * 78)
    print("N10 - RANDOMIZZAZIONE DELLE FASI A SPETTRO FISSATO")
    print("=" * 78)

    nh1 = {}
    for j, r in enumerate(read_jsonl(res / "paper1" / "per_mock_NGC_R5.jsonl")):
        fl = flatten(r)
        try:
            kk = int(str(fl.get("key", j)).split("_")[-1])
        except (TypeError, ValueError):
            kk = j
        nh1[kk] = float(fl.get(NH1, np.nan))

    # ---------------------------------------------------- autocontrolli
    print("\n[A] AUTOCONTROLLI")
    if not desi_cache.exists():
        print("  [FATAL] campo nu di DESI non in cache: esegui prima N1b")
        return
    nu_d = np.load(desi_cache)
    v = float(M.compute_tda_features(nu_d, mask, M.N_THRESH, masked=True)[4])
    print(f"  1. N_H1(DESI originale) = {v:.0f}  atteso {DESI_NH1:.0f}  "
          f"{'OK' if abs(v-DESI_NH1) < 0.5 else 'FALLITO'}")
    if abs(v - DESI_NH1) > 0.5:
        return
    _, err = phase_randomize(nu_d, np.random.default_rng(0), check=True)
    print(f"  2. errore relativo sullo spettro dopo randomizzazione: "
          f"{err:.3e}  {'OK' if err < 1e-10 else 'FALLITO'}")
    if err >= 1e-10:
        print("     Lo spettro non e' preservato: il metodo e' sbagliato.")
        return

    done = {(r["tipo"], r["idx"]) for r in read_jsonl(outj)}

    # ---------------------------------------------------- DESI randomizzato
    print(f"\n[B] DESI: {args.n_desi} realizzazioni a fasi randomizzate")
    t0 = time.time()
    for k in range(args.n_desi):
        if ("desi_pr", k) in done:
            continue
        pr, _ = phase_randomize(nu_d, np.random.default_rng(args.seed + k))
        f = M.compute_tda_features(pr, mask, M.N_THRESH, masked=True)
        append_jsonl(outj, {"tipo": "desi_pr", "idx": k, "N_H1": float(f[4]),
                            "mean_pers1": float(f[5]), "b1_peak": float(f[1])})
        if k == 0 or (k + 1) % 10 == 0:
            el = time.time() - t0
            print(f"    [{k+1}/{args.n_desi}] N_H1={f[4]:.0f}  "
                  f"{el/(k+1):.1f} s/realizzazione")

    # ---------------------------------------------------- mock randomizzati
    files = [(int(p.stem.split("_")[1]), p)
             for p in sorted(fdir.glob("test2_*.npz"))]
    files = [(i, p) for i, p in files if i >= args.min_idx][:args.n_mock]
    print(f"\n[C] MOCK: {len(files)} campi, una randomizzazione ciascuno")
    t0 = time.time()
    for n, (i, p) in enumerate(files, 1):
        if ("mock_pr", i) in done:
            continue
        nu = np.load(p)["delta"]
        orig = float(M.compute_tda_features(nu, mask, M.N_THRESH, masked=True)[4])
        exp = nh1.get(i, np.nan)
        if np.isfinite(exp) and abs(orig - exp) > 0.5:
            print(f"  *** idx {i}: originale {orig:.0f} ma JSONL {exp:.0f}. "
                  f"Mi fermo. ***")
            return
        pr, _ = phase_randomize(nu, np.random.default_rng(args.seed + 10000 + i))
        f = M.compute_tda_features(pr, mask, M.N_THRESH, masked=True)
        append_jsonl(outj, {"tipo": "mock_pr", "idx": i,
                            "N_H1_orig": orig, "N_H1": float(f[4]),
                            "mean_pers1": float(f[5]), "b1_peak": float(f[1])})
        if n == 1 or n % 10 == 0:
            el = time.time() - t0
            print(f"    [{n}/{len(files)}] idx={i} orig={orig:.0f} "
                  f"PR={f[4]:.0f}  ETA {el/n*(len(files)-n)/60:.1f} min")

    # ---------------------------------------------------- analisi
    print("\n" + "=" * 78)
    print("RISULTATO")
    print("=" * 78)
    recs = read_jsonl(outj)
    dpr = np.array([r["N_H1"] for r in recs if r["tipo"] == "desi_pr"])
    mpr = np.array([r["N_H1"] for r in recs if r["tipo"] == "mock_pr"])
    mor = np.array([r["N_H1_orig"] for r in recs if r["tipo"] == "mock_pr"])
    if dpr.size < 3 or mpr.size < 3:
        print("  campioni troppo piccoli per l'analisi.")
        return

    sd, sm, so = stats(dpr), stats(mpr), stats(mor)
    print(f"\n  {'':>22s} {'n':>5s} {'media':>11s} {'sd':>9s} {'SEM':>8s}")
    print(f"  {'DESI originale':>22s} {1:>5d} {DESI_NH1:>11.0f} "
          f"{'-':>9s} {'-':>8s}")
    print(f"  {'DESI randomizzato':>22s} {sd['n']:>5d} {sd['mean']:>11.1f} "
          f"{sd['std']:>9.1f} {sd['sem']:>8.1f}")
    print(f"  {'mock originali':>22s} {so['n']:>5d} {so['mean']:>11.1f} "
          f"{so['std']:>9.1f} {so['sem']:>8.1f}")
    print(f"  {'mock randomizzati':>22s} {sm['n']:>5d} {sm['mean']:>11.1f} "
          f"{sm['std']:>9.1f} {sm['sem']:>8.1f}")

    d_or = so["mean"] - DESI_NH1
    d_pr = sm["mean"] - sd["mean"]
    se_pr = np.sqrt(sm["sem"] ** 2 + sd["sem"] ** 2)
    frac = d_pr / d_or if d_or else np.nan
    below = int((mpr < sd["mean"]).sum())

    print(f"\n  deficit originale      : {d_or:>9.0f}")
    print(f"  deficit dopo randomizz.: {d_pr:>9.0f} +/- {se_pr:.0f}")
    print(f"  FRAZIONE ATTRIBUIBILE ALLO SPETTRO: {100*frac:.1f}%  "
          f"(+/- {100*se_pr/abs(d_or):.1f}%)")
    print(f"  residuo di fase        : {100*(1-frac):.1f}%")
    print(f"\n  la media di DESI randomizzato cade sotto {below}/{mpr.size} "
          f"mock randomizzati")
    print(f"  effetto della randomizzazione:")
    print(f"    su DESI : {DESI_NH1:.0f} -> {sd['mean']:.0f}  "
          f"({100*(sd['mean']-DESI_NH1)/DESI_NH1:+.1f}%)")
    print(f"    su mock : {so['mean']:.0f} -> {sm['mean']:.0f}  "
          f"({100*(sm['mean']-so['mean'])/so['mean']:+.1f}%)")

    print("\n  LETTURA:")
    if frac > 0.85:
        print("    Il deficit SOPRAVVIVE alla randomizzazione: e' spettrale.")
        print("    La tesi 'oltre il due-punti' cade e il titolo va rivisto")
        print("    sull'origine spettrale.")
    elif frac < 0.35:
        print("    Il deficit SVANISCE randomizzando: era informazione di")
        print("    fase. E' la dimostrazione che Referee 3 chiede, senza")
        print("    extrapolazioni.")
    else:
        print("    ESITO INTERMEDIO: lo spettro spiega una frazione")
        print("    sostanziale ma non tutto. Va quotata la frazione, con la")
        print("    sua barra d'errore, come risultato principale.")
    print(f"\n    Confronto con N1c, che stimava il 26.5% per estrapolazione")
    print(f"    lineare a Mahalanobis 34: qui {100*frac:.1f}% senza")
    print(f"    extrapolare. Se i due numeri concordano, l'assunzione di")
    print(f"    linearita' di N1c era giustificata; se no, N10 e' quello da")
    print(f"    citare e la discrepanza va discussa.")

    atomic_write_json(res / "paper1" / "n10_report_NGC.json", {
        "script": "paper1_rev_n10_phases.py",
        "desi_originale": DESI_NH1, "desi_pr": sd,
        "mock_originali": so, "mock_pr": sm,
        "deficit_originale": float(d_or), "deficit_pr": float(d_pr),
        "sem_deficit_pr": float(se_pr),
        "frazione_spettro": float(frac),
        "residuo_fase": float(1 - frac),
        "n1c_frazione_per_confronto": 0.265})
    print(f"\n  report: {res/'paper1'/'n10_report_NGC.json'}")


if __name__ == "__main__":
    main()
