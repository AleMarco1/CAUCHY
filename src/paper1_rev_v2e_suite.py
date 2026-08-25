#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2e_suite.py

V2e - CHE COSA SONO I PRIMI 200 MOCK?

FATTO NUOVO
-----------
w0, Om, s8 in phase9_likeforlike_arrays.npz sono definiti ESATTAMENTE per gli
indici 0-199 e NaN per i restanti 1800. Il blocco che differisce fra le due
catene e' precisamente il blocco che porta i metadati cosmologici. E i valori
non sono fiduciali: il mock 139 ha Om=0.1033, s8=0.675, w0=-1.260, mentre la
cosmologia fiduciale di Quijote e' Om=0.3175, s8=0.834, w0=-1.

DUE LETTURE
-----------
(a) METADATI INCOMPLETI: tutti 2000 dal Latin hypercube, lookup dei parametri
    popolato solo per i primi 200 e mai completato. Lascia il blocco 0-199
    senza spiegazione.
(b) ENSEMBLE MISTO: i primi 200 dal Latin hypercube (cosmologia variabile),
    i restanti 1800 dal set fiduciale (cosmologia fissa, quindi nessun
    parametro per mock). Spiegherebbe tutto in una volta: la divergenza fra
    catene confinata al blocco, i 13 collassi di M26 confinati al blocco
    (cosmologie estreme del LH producono genuinamente pochi loop), e
    sigma=445 piu' larga della nostra 313.

Distinguere (a) da (b) NON si fa inferendo dai numeri: si fa leggendo il
codice che ha scritto l'npz e i percorsi dei file mock effettivamente caricati.

CORREZIONI RISPETTO A v2d
-------------------------
  - v2d metteva la finitezza della cosmologia dentro la maschera 'ok' e poi
    usava 'ok' anche per i confronti su N_H1: campione azzerato e crash.
    Qui le maschere sono separate.
  - il criterio "escludere i mock a cosmologia indefinita" era costruito su
    un artefatto (1800 mock su 2000 sono NaN) ed e' RITIRATO.
  - le correlazioni N_H1 x cosmologia sono su n=200, non 2000: qui vengono
    riportate con il loro errore standard.

Solo lettura. Scrive un report JSON con scrittura atomica.

USO
---
  python src\\paper1_rev_v2e_suite.py
"""

import argparse
import json
import os
import re
import tempfile
from pathlib import Path

import numpy as np

DESI = {"NGC": 28256.0, "SGC": 15122.0}
NH1 = "base.N_H1"
BLOCK = 200
ROBUST_Z = 5.0
COSMO_KEYS = ("w0", "Om", "s8")

# Quijote, cosmologia fiduciale
QUIJOTE_FID = {"Om": 0.3175, "s8": 0.834, "w0": -1.0, "Ob": 0.049,
               "h": 0.6711, "ns": 0.9624}

# termini da cercare nei sorgenti
GREP = ["likeforlike", "phase9_likeforlike_arrays", "beta1_max",
        "latin", "Latin", "nwLH", "LH", "fiducial", "fiduciale",
        "quijote", "Quijote", "w0", "s8", "hypercube", "n_mocks",
        "delta_", "paper1_mock_deltas"]


# ---------------------------------------------------------------- io
def read_jsonl(path):
    recs, bad = [], 0
    with open(path, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                recs.append(json.loads(line))
            except Exception:
                bad += 1
    return recs, bad


def flatten(d, prefix=""):
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        else:
            out[key] = v
    return out


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


def robust(v):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    med = float(np.median(v))
    mad = float(1.4826 * np.median(np.abs(v - med)))
    return med, (mad if mad > 0 else float(v.std(ddof=1)))


def _ndtr(x):
    import math
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


def mannwhitney(a, b):
    a = np.asarray(a, float); b = np.asarray(b, float)
    n1, n2 = a.size, b.size
    allv = np.concatenate([a, b])
    order = np.argsort(allv, kind="stable")
    ranks = np.empty(allv.size, float)
    sv = allv[order]
    i = 0
    while i < sv.size:
        j = i
        while j + 1 < sv.size and sv[j + 1] == sv[i]:
            j += 1
        ranks[order[i:j + 1]] = 0.5 * (i + j) + 1.0
        i = j + 1
    U1 = ranks[:n1].sum() - n1 * (n1 + 1) / 2.0
    mu = n1 * n2 / 2.0
    _, cnt = np.unique(allv, return_counts=True)
    N = allv.size
    tie = float(((cnt ** 3 - cnt).sum()) / (N * (N - 1)))
    sd = np.sqrt(n1 * n2 / 12.0 * ((N + 1) - tie))
    z = (U1 - mu) / sd if sd > 0 else 0.0
    return float(z), float(2.0 * (1.0 - _ndtr(abs(z))))


def ks_two(a, b):
    a = np.sort(np.asarray(a, float)); b = np.sort(np.asarray(b, float))
    allv = np.concatenate([a, b])
    ca = np.searchsorted(a, allv, side="right") / a.size
    cb = np.searchsorted(b, allv, side="right") / b.size
    d = float(np.max(np.abs(ca - cb)))
    ne = a.size * b.size / (a.size + b.size)
    lam = (np.sqrt(ne) + 0.12 + 0.11 / np.sqrt(ne)) * d
    p = 2.0 * sum((-1) ** (k - 1) * np.exp(-2.0 * k * k * lam * lam)
                  for k in range(1, 101))
    return d, float(min(max(p, 0.0), 1.0))


def compare_block(name, v):
    """Confronto blocco 0-199 vs resto su valori finiti. Nessuna maschera
    esterna: e' l'errore che aveva azzerato il campione in v2d."""
    v = np.asarray(v, float)
    idx = np.arange(v.size)
    g = np.isfinite(v)
    a, b = v[g & (idx < BLOCK)], v[g & (idx >= BLOCK)]
    if a.size < 5 or b.size < 5:
        print(f"\n    {name}: n={a.size}/{b.size} - saltato")
        return {"saltato": True, "n_blocco": int(a.size), "n_resto": int(b.size)}
    ma, sa = robust(a); mb, sb = robust(b)
    z, p = mannwhitney(a, b)
    d, pk = ks_two(a, b)
    print(f"\n    {name}")
    print(f"      0-199    n={a.size:<5d} mediana={ma:>10.1f} "
          f"sigma_MAD={sa:>7.1f} sigma={a.std(ddof=1):>7.1f}")
    print(f"      200-fine n={b.size:<5d} mediana={mb:>10.1f} "
          f"sigma_MAD={sb:>7.1f} sigma={b.std(ddof=1):>7.1f}")
    print(f"      diff mediana {ma - mb:+.1f}   rapporto sigma_MAD "
          f"{sa / sb:.3f}")
    print(f"      Mann-Whitney z={z:+.2f} p={p:.3g}   KS D={d:.4f} p={pk:.3g}")
    verd = "BLOCCO ANOMALO" if (p < 0.01 or pk < 0.01) else "compatibile"
    print(f"      -> {verd}")
    return {"n_blocco": int(a.size), "n_resto": int(b.size),
            "mediana_blocco": ma, "mediana_resto": mb,
            "sigma_mad_blocco": sa, "sigma_mad_resto": sb,
            "mw_z": z, "mw_p": p, "ks_d": d, "ks_p": pk, "verdetto": verd}


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--m26_npz", default="results\\phase9_likeforlike_arrays.npz")
    ap.add_argument("--ctx", type=int, default=2,
                    help="righe di contesto attorno a ogni match nei sorgenti")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    our_dir = root / "results" / "paper1"
    rep = {"script": "paper1_rev_v2e_suite.py"}

    parts = [q for q in args.m26_npz.replace("\\", "/").split("/") if q]
    npz_path = (Path(args.m26_npz) if Path(args.m26_npz).is_absolute()
                else root.joinpath(*parts))
    z = np.load(npz_path, allow_pickle=True)
    m26 = np.asarray(z["beta1_max"], float)
    pers = np.asarray(z["pers1_mean"], float) if "pers1_mean" in z.files else None
    cos = {k: np.asarray(z[k], float).ravel() for k in COSMO_KEYS
           if k in z.files}

    ours = {}
    for reg in ("NGC", "SGC"):
        p = our_dir / f"per_mock_{reg}_R5.jsonl"
        if p.exists():
            recs, _ = read_jsonl(p)
            ours[reg] = np.array([float(flatten(r).get(NH1, np.nan))
                                  for r in recs])

    # ============================================================ A
    print("=" * 78)
    print("A - ANATOMIA DEGLI ARRAY COSMOLOGICI")
    print("=" * 78)
    rep["cosmologia"] = {}
    for k, a in cos.items():
        fin = np.isfinite(a)
        i_fin = np.where(fin)[0]
        contiguo = bool(i_fin.size and
                        np.array_equal(i_fin, np.arange(i_fin[0], i_fin[-1] + 1)))
        v = a[fin]
        nuniq = int(np.unique(np.round(v, 10)).size)
        print(f"\n  {k}: {fin.sum()} finiti su {a.size}")
        print(f"    indici finiti: {i_fin[0]}..{i_fin[-1]}  "
              f"contigui: {'SI' if contiguo else 'NO'}")
        print(f"    valori distinti: {nuniq}")
        print(f"    range [{v.min():.5f}, {v.max():.5f}]   "
              f"mediana {np.median(v):.5f}   sd {v.std(ddof=1):.5f}")
        if k in QUIJOTE_FID:
            fid = QUIJOTE_FID[k]
            costante = bool(np.allclose(v, v[0], atol=1e-6))
            print(f"    fiduciale Quijote {k} = {fid}")
            print(f"    tutti uguali fra loro: {'SI' if costante else 'NO'}")
            print(f"    compatibili col fiduciale: "
                  f"{'SI' if costante and abs(v[0]-fid) < 1e-3 else 'NO'}")
            print(f"    -> {'FIDUCIALE' if costante else 'COSMOLOGIA VARIABILE (Latin hypercube)'}")
        rep["cosmologia"][k] = {
            "n_finiti": int(fin.sum()), "contigui": contiguo,
            "primo": int(i_fin[0]) if i_fin.size else None,
            "ultimo": int(i_fin[-1]) if i_fin.size else None,
            "n_distinti": nuniq, "min": float(v.min()), "max": float(v.max()),
            "mediana": float(np.median(v)), "sd": float(v.std(ddof=1))}

    print("\n  LETTURA:")
    print("    valori variabili sui primi 200 e assenti dopo -> compatibile con")
    print("      (b) ENSEMBLE MISTO: 200 dal Latin hypercube + 1800 fiduciali.")
    print("    per confermare serve il codice, non i numeri: vedi sezione B.")

    # ============================================================ B
    print("\n" + "=" * 78)
    print("B - CHI HA SCRITTO L'NPZ, E QUALI MOCK HA CARICATO")
    print("=" * 78)
    srcs = []
    for d in (root / "src", root):
        if d.exists():
            srcs += [p for p in d.rglob("*.py")
                     if ".venv" not in str(p) and "site-packages" not in str(p)]
    srcs = sorted(set(srcs))
    print(f"  {len(srcs)} file .py analizzati sotto {root}\n")

    pat = re.compile("|".join(re.escape(g) for g in GREP))
    hits = {}
    for p in srcs:
        try:
            lines = p.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:
            continue
        loc = [i for i, L in enumerate(lines) if pat.search(L)]
        if loc:
            hits[str(p)] = (lines, loc)

    # priorita': i file che scrivono l'npz o che nominano il Latin hypercube
    def prio(item):
        path, (lines, loc) = item
        txt = "\n".join(lines)
        s = 0
        if "phase9_likeforlike_arrays" in txt: s -= 100
        if "likeforlike" in txt: s -= 40
        if re.search(r"latin|hypercube|nwLH", txt, re.I): s -= 30
        if re.search(r"fiducial|fiduciale", txt, re.I): s -= 20
        return (s, -len(loc), path)

    rep["sorgenti"] = {}
    for path, (lines, loc) in sorted(hits.items(), key=prio)[:6]:
        print("-" * 78)
        print(f"  {path}   ({len(loc)} righe rilevanti)")
        print("-" * 78)
        shown = set()
        for i in loc[:60]:
            lo, hi = max(0, i - args.ctx), min(len(lines), i + args.ctx + 1)
            if any(j in shown for j in range(lo, hi)):
                continue
            for j in range(lo, hi):
                mark = ">>" if j == i else "  "
                print(f"  {mark} {j+1:>5d}| {lines[j][:150]}")
                shown.add(j)
            print()
        rep["sorgenti"][path] = len(loc)

    print("\n  DA CERCARE IN QUESTO OUTPUT:")
    print("    - il percorso da cui vengono caricati i mock 0-199 e quello dei")
    print("      restanti 1800: se sono directory DIVERSE, la lettura (b) e'")
    print("      confermata e l'ensemble di M26 e' misto.")
    print("    - se w0/Om/s8 vengono letti da un file di parametri del Latin")
    print("      hypercube troncato a 200 righe, siamo nella lettura (a).")
    print("    - come viene costruito l'array beta1_max: una concatenazione di")
    print("      due liste e' la firma della (b).")

    # ============================================================ C
    print("\n" + "=" * 78)
    print("C - SCAMBIABILITA' DEL BLOCCO (versione corretta, senza maschera)")
    print("=" * 78)
    rep["scambiabilita"] = {}
    for name, arr in ([(f"nostra catena {r}", ours[r]) for r in ours]
                      + [("catena M26 (NGC)", m26)]
                      + ([("M26 mean_pers1", pers)] if pers is not None else [])):
        key = name.replace(" ", "_").replace("(", "").replace(")", "")
        rep["scambiabilita"][key] = compare_block(name, arr)

    print("\n  VERDETTO:")
    vn = rep["scambiabilita"].get("nostra_catena_NGC", {}).get("verdetto")
    vm = rep["scambiabilita"].get("catena_M26_NGC", {}).get("verdetto")
    pn = rep["scambiabilita"].get("nostra_catena_NGC", {}).get("ks_p")
    pm = rep["scambiabilita"].get("catena_M26_NGC", {}).get("ks_p")
    print(f"    nostra NGC: {vn}   (KS p = {pn})")
    print(f"    M26       : {vm}   (KS p = {pm})")
    print("    ATTENZIONE: 200 contro 1800 e' un confronto a potenza asimmetrica.")
    print("    Se i due p-value differiscono di poco, la differenza e' di grado")
    print("    e non autorizza ad attribuire il difetto a una delle due catene.")

    # ============================================================ D
    print("\n" + "=" * 78)
    print("D - CORRELAZIONE N_H1 x COSMOLOGIA, CON IL SUO ERRORE (n=200)")
    print("=" * 78)
    print("  RITIRATO da v2c/v2d: quelle correlazioni erano su n=200 ma")
    print("  presentate come se fossero sull'intero ensemble.")
    rep["corr_cosmologia"] = {}
    if "NGC" in ours:
        v = ours["NGC"]
        for k, a in cos.items():
            m = np.isfinite(a) & np.isfinite(v)
            n = int(m.sum())
            if n < 10:
                continue
            r = float(np.corrcoef(a[m], v[m])[0, 1])
            se = 1.0 / np.sqrt(n - 3)
            zf = 0.5 * np.log((1 + r) / (1 - r))
            lo, hi = np.tanh(zf - 1.96 * se), np.tanh(zf + 1.96 * se)
            print(f"    {k:>4s}: r = {r:+.3f}   IC95% [{lo:+.3f}, {hi:+.3f}]"
                  f"   n = {n}   -> {abs(zf)/se:.1f} sigma")
            rep["corr_cosmologia"][k] = {"r": r, "ic95": [float(lo), float(hi)],
                                         "n": n, "sigma": float(abs(zf) / se)}
        print("\n  Con n=200 l'errore su r e' ~0.071: valori attorno a 0.15 sono")
        print("  a due sigma scarsi. Non sono misure stabilite e non reggono")
        print("  l'argomento 'la cosmologia non puo' produrre il deficit'.")
        print("  Quell'argomento va rifatto sull'intero ensemble, e per farlo")
        print("  servono i parametri dei 1800 mock mancanti.")

    outp = our_dir / "rev_v2e_suite_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 78)
    print(f"report scritto in: {outp}")
    print("=" * 78)


if __name__ == "__main__":
    main()
