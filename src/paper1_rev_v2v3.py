#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CAUCHY - Paper 1, revisione MNRAS
src/paper1_rev_v2v3.py

V2 - DISCREPANZA DI DISPERSIONE CON M26   (punto bloccante E2 dell'editore)
V3 - RANK EMPIRICI                        (statistica primaria della revisione)

Solo lettura: non tocca nessun file esistente, scrive un unico report JSON
in results\\paper1\\ con scrittura atomica.

IL PROBLEMA (V2)
----------------
M26, tabella battery, baseline B3, N=2000:   35425 +/- 445   ->  z = -16.1
Questo lavoro, stesso ensemble dichiarato:   35436.7 +/- 313 ->  z = -22.9

Le MEDIE concordano allo 0.03%, le DEVIAZIONI STANDARD differiscono di un
fattore 1.42. Una sigma piu' piccola gonfia meccanicamente la significativita'.
Finche' non e' spiegata, nessun numero con sigma al denominatore e' difendibile.

IPOTESI DA DISCRIMINARE
-----------------------
H1  seeding diverso: stessa procedura, realizzazioni HOD/subsampling diverse.
    -> i valori per-mock NON correlano indice per indice, ma le due
       distribuzioni hanno la STESSA larghezza. Se le larghezze differiscono,
       H1 da sola non basta.
H2  density matching: una delle due catene sottocampiona a densita' fissa e
    l'altra no. Le 2000 cosmologie hanno n(z) diverse; senza matching la
    varianza di n_gal entra in N_H1 e allarga la distribuzione.
    -> la nostra sigma sarebbe la piu' STRETTA (coerente con l'osservato)
       e N_H1 correlerebbe col numero di galassie del mock.
H3  sottoinsieme/statistica diversa: valori identici mock per mock ma stima
    della varianza diversa (ddof, clipping, sottoinsieme dei 2000).
    -> correlazione ~1 con valori uguali: si vede subito.

USO
---
  python src\\paper1_rev_v2v3.py
  python src\\paper1_rev_v2v3.py --m26_file results\\phase8\\qualcosa.json
"""

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path

import numpy as np

# ---------------------------------------------------------------- costanti
DESI = {"NGC": 28256.0, "SGC": 15122.0}
M26_NGC = {"mean": 35425.0, "std": 445.0, "n": 2000}

# chiavi candidate per N_H1 di baseline (mock non rimappato)
N_H1_HINTS = ("n_h1", "nh1", "beta1_max", "b1max", "loops", "n_loops")
BASELINE_HINTS = ("orig", "base", "pre", "raw", "in", "mock")
REMAP_HINTS = ("remap", "post", "out", "prime")
NGAL_HINTS = ("ngal", "n_gal", "n_obj", "ngalaxies", "n_galaxies", "count",
              "n_points", "npart", "n_tracers")


# ---------------------------------------------------------------- io utils
def read_jsonl(path):
    """Legge un JSONL append-only tollerando righe troncate in coda."""
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
    """Appiattisce un dict annidato in {chiave_puntata: valore scalare}."""
    out = {}
    for k, v in d.items():
        key = f"{prefix}{k}"
        if isinstance(v, dict):
            out.update(flatten(v, key + "."))
        elif isinstance(v, (int, float)) and not isinstance(v, bool):
            out[key] = float(v)
        elif isinstance(v, str):
            out[key] = v
    return out


def atomic_write_json(path, obj):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump(obj, f, indent=2, ensure_ascii=True)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    except Exception:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


# ---------------------------------------------------------------- statistica
def describe(v):
    v = np.asarray(v, float)
    n = v.size
    q = np.percentile(v, [1, 25, 50, 75, 99])
    sd = float(v.std(ddof=1))
    return {
        "n": int(n),
        "mean": float(v.mean()),
        "std": sd,
        "std_err": sd / np.sqrt(2.0 * (n - 1)),          # errore su sigma
        "sem": sd / np.sqrt(n),                           # errore sulla media
        "min": float(v.min()), "max": float(v.max()),
        "p01": float(q[0]), "p25": float(q[1]), "median": float(q[2]),
        "p75": float(q[3]), "p99": float(q[4]),
        "sigma_from_iqr": float((q[3] - q[1]) / 1.349),
        "sigma_from_mad": float(1.4826 * np.median(np.abs(v - np.median(v)))),
        "skew": float(((v - v.mean()) ** 3).mean() / sd ** 3),
        "kurt_excess": float(((v - v.mean()) ** 4).mean() / sd ** 4 - 3.0),
    }


def spearman(a, b):
    ra = np.argsort(np.argsort(a, kind="stable"))
    rb = np.argsort(np.argsort(b, kind="stable"))
    return float(np.corrcoef(ra, rb)[0, 1])


# ---------------------------------------------------------------- selezione chiavi
def pick_key(cols, hints_primary, hints_secondary=(), vmin=1e3, vmax=1e6):
    """Sceglie la colonna il cui nome contiene gli hint e i cui valori sono
    nel range plausibile. Ritorna (chiave, motivo) oppure (None, None)."""
    cands = []
    for k, v in cols.items():
        if v.dtype.kind not in "fi" or v.size < 10:
            continue
        med = float(np.median(v))
        if not (vmin < med < vmax):
            continue
        kl = k.lower()
        score = 0
        if any(h in kl for h in hints_primary):
            score += 10
        if hints_secondary and any(h in kl for h in hints_secondary):
            score += 5
        if any(h in kl for h in REMAP_HINTS):
            score -= 8
        if score > 0:
            cands.append((score, k))
    if not cands:
        return None, None
    cands.sort(key=lambda t: (-t[0], t[1]))
    return cands[0][1], f"score={cands[0][0]}"


# ---------------------------------------------------------------- caccia a M26
def numeric_arrays_from_json(obj, prefix="", out=None, depth=0):
    """Estrae ricorsivamente liste di numeri lunghe >= 100 da un JSON."""
    if out is None:
        out = {}
    if depth > 8:
        return out
    if isinstance(obj, dict):
        for k, v in obj.items():
            numeric_arrays_from_json(v, f"{prefix}{k}.", out, depth + 1)
    elif isinstance(obj, list) and len(obj) >= 100:
        try:
            a = np.asarray(obj, dtype=float)
        except Exception:
            return out
        if a.ndim == 1 and np.isfinite(a).all():
            out[prefix.rstrip(".")] = a
    return out


def hunt_m26(root, forced, our_dir):
    """Cerca in results\\ file che contengano un ensemble di ~2000 valori
    di N_H1 nel range dei mock (30k-45k)."""
    cands = []
    if forced:
        files = [Path(forced)]
    else:
        rdir = root / "results"
        if not rdir.exists():
            return cands
        files = [p for p in rdir.rglob("*")
                 if p.suffix.lower() in (".json", ".npz", ".npy")
                 and our_dir not in p.parents]
    for p in files:
        try:
            if p.suffix.lower() == ".json":
                if p.stat().st_size > 200e6:
                    continue
                with open(p, "r", encoding="utf-8", errors="replace") as f:
                    obj = json.load(f)
                arrs = numeric_arrays_from_json(obj)
            elif p.suffix.lower() == ".npz":
                z = np.load(p, allow_pickle=True)
                arrs = {}
                for k in z.files:
                    a = np.asarray(z[k])
                    if a.ndim == 1 and a.size >= 100 and a.dtype.kind in "fi":
                        arrs[k] = a.astype(float)
            else:
                a = np.load(p, allow_pickle=False, mmap_mode="r")
                arrs = ({"": np.asarray(a, float)}
                        if a.ndim == 1 and a.size >= 100 else {})
        except Exception:
            continue
        for k, a in arrs.items():
            med = float(np.median(a))
            if 2.5e4 < med < 5.0e4 and a.size >= 100:
                cands.append({"file": str(p), "key": k, "n": int(a.size),
                              "mean": float(a.mean()),
                              "std": float(a.std(ddof=1)),
                              "median": med, "_arr": a})
    cands.sort(key=lambda c: (abs(c["n"] - 2000), abs(c["mean"] - 35425.0)))
    return cands


# ---------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--project_root", default="D:\\projects\\cauchy")
    ap.add_argument("--m26_file", default=None,
                    help="forza un file specifico per il confronto M26")
    ap.add_argument("--nh1_key", default=None,
                    help="forza il nome della colonna N_H1 di baseline")
    args = ap.parse_args()

    root = Path(args.project_root).resolve()
    our_dir = root / "results" / "paper1"
    rep = {"script": "paper1_rev_v2v3.py",
           "scopo": "V2 dispersione vs M26; V3 rank empirici",
           "desi": DESI, "m26_ngc": M26_NGC, "regioni": {}}

    # ---------------------------------------------------- carica i JSONL
    cols_by_reg, meta_by_reg = {}, {}
    for reg in ("NGC", "SGC"):
        p = our_dir / f"per_mock_{reg}_R5.jsonl"
        if not p.exists():
            print(f"[!] {p} non trovato")
            continue
        recs, bad = read_jsonl(p)
        if not recs:
            print(f"[!] {p} vuoto")
            continue
        flat = [flatten(r) for r in recs]
        keys = sorted(set().union(*[set(f) for f in flat]))
        cols = {}
        for k in keys:
            vals = [f.get(k) for f in flat]
            if all(isinstance(v, (int, float)) for v in vals if v is not None):
                arr = np.array([np.nan if v is None else float(v)
                                for v in vals], dtype=float)
                if np.isfinite(arr).sum() >= 10:
                    cols[k] = arr
        cols_by_reg[reg] = cols
        meta_by_reg[reg] = {"file": str(p), "n_record": len(recs),
                            "righe_illeggibili": bad}
        print(f"[ok] {reg}: {len(recs)} record, {bad} righe scartate, "
              f"{len(cols)} colonne numeriche")

    if not cols_by_reg:
        print("\nNessun JSONL leggibile. Verifica --project_root.")
        sys.exit(1)

    # ---------------------------------------------------- schema (diagnostica)
    print("\n" + "=" * 76)
    print("SCHEMA DEL JSONL  (serve a validare la scelta automatica delle chiavi)")
    print("=" * 76)
    reg0 = next(iter(cols_by_reg))
    for k, v in sorted(cols_by_reg[reg0].items()):
        fin = v[np.isfinite(v)]
        if fin.size:
            print(f"  {k:<34s} mediana={np.median(fin):>14.4g}  "
                  f"min={fin.min():>12.4g}  max={fin.max():>12.4g}")
    rep["schema"] = sorted(cols_by_reg[reg0].keys())

    # ---------------------------------------------------- V3: rank empirici
    print("\n" + "=" * 76)
    print("V3 - RANK EMPIRICI  (statistica primaria della revisione)")
    print("=" * 76)

    ours = {}
    for reg, cols in cols_by_reg.items():
        if args.nh1_key and args.nh1_key in cols:
            key, why = args.nh1_key, "forzata da --nh1_key"
        else:
            key, why = pick_key(cols, N_H1_HINTS, BASELINE_HINTS)
        if key is None:
            print(f"  {reg}: nessuna colonna N_H1 riconosciuta. "
                  f"Rilancia con --nh1_key <nome>.")
            continue
        v = cols[key]
        v = v[np.isfinite(v)]
        ours[reg] = (key, v)

        below = int((v < DESI[reg]).sum())
        ties = int((v == DESI[reg]).sum())
        n = v.size
        d = describe(v)
        z = (DESI[reg] - d["mean"]) / d["std"]

        print(f"\n  {reg}   colonna scelta: '{key}'  ({why})   N mock = {n}")
        print(f"    DESI            : {DESI[reg]:.0f}")
        print(f"    mock            : {d['mean']:.1f} +/- {d['std']:.1f}")
        print(f"    mock sotto DESI : {below}   (pari: {ties})")
        print(f"    RANK EMPIRICO   : {below + 1}/{n + 1}"
              f"   ->  p <= {(below + 1) / (n + 1):.3e}")
        print(f"    z (parentetico) : {z:+.2f}")
        print(f"    margine al minimo dell'ensemble: "
              f"{d['min'] - DESI[reg]:+.0f} loop "
              f"({(d['min'] - DESI[reg]) / d['std']:+.2f} sigma)")

        rep["regioni"][reg] = {
            "meta": meta_by_reg[reg], "colonna_nh1": key,
            "n_mock": n, "n_sotto_desi": below, "n_pari": ties,
            "rank": f"{below + 1}/{n + 1}",
            "p_empirica": (below + 1) / (n + 1),
            "z_gaussiano_equivalente": z, "stats": d,
        }

    # ---------------------------------------------------- V2: la nostra sigma
    print("\n" + "=" * 76)
    print("V2 - CARATTERIZZAZIONE DELLA NOSTRA DISPERSIONE")
    print("=" * 76)

    for reg, (key, v) in ours.items():
        d = rep["regioni"][reg]["stats"]
        n = d["n"]
        print(f"\n  {reg}:  sigma = {d['std']:.1f} +/- {d['std_err']:.1f}"
              f"   (errore campionario su sigma, N={n})")
        print(f"    sigma da IQR    : {d['sigma_from_iqr']:.1f}")
        print(f"    sigma da MAD    : {d['sigma_from_mad']:.1f}")
        print(f"    skew {d['skew']:+.3f}   curtosi in eccesso "
              f"{d['kurt_excess']:+.3f}")
        print(f"    range [{d['min']:.0f}, {d['max']:.0f}]   "
              f"p01 {d['p01']:.0f}   p99 {d['p99']:.0f}")

        print("    sigma cumulativa: ", end="")
        for m in (100, 200, 500, 1000, v.size):
            if m <= v.size:
                print(f"N={m}:{v[:m].std(ddof=1):.0f}  ", end="")
        print()

        if reg == "NGC":
            tgt = M26_NGC["std"]
            gap = (tgt - d["std"]) / d["std_err"]
            extra = np.sqrt(max(tgt ** 2 - d["std"] ** 2, 0.0))
            frac = 100.0 * (tgt ** 2 - d["std"] ** 2) / tgt ** 2
            print(f"\n    --- confronto diretto con M26 (NGC) ---")
            print(f"    M26      : {M26_NGC['mean']:.0f} +/- {tgt:.0f}")
            print(f"    noi      : {d['mean']:.1f} +/- {d['std']:.1f}")
            print(f"    scarto sulle medie : "
                  f"{100 * abs(d['mean'] - M26_NGC['mean']) / M26_NGC['mean']:.3f}%")
            print(f"    scarto sulle sigma : {tgt / d['std']:.3f}x  "
                  f"= {gap:.0f} volte l'errore campionario su sigma")
            print(f"    -> la discrepanza NON e' fluttuazione campionaria; "
                  f"e' meccanica.")
            print(f"    componente di varianza mancante nella nostra catena: "
                  f"sigma_extra = {extra:.0f}  ({frac:.0f}% della varianza M26)")
            rep["confronto_m26_ngc"] = {
                "m26": M26_NGC, "nostro_mean": d["mean"], "nostro_std": d["std"],
                "nostro_std_err": d["std_err"],
                "rapporto_sigma": tgt / d["std"],
                "gap_in_errori_campionari": gap,
                "sigma_extra_richiesta": float(extra),
                "frazione_varianza_mancante_pct": float(frac),
            }

    # ---------------------------------------------------- V2/H2: densita'
    print("\n" + "=" * 76)
    print("V2 / H2 - N_H1 CORRELA COL CONTEGGIO DI GALASSIE DEL MOCK?")
    print("=" * 76)
    print("  (se la nostra catena appaia la densita', questa correlazione e'")
    print("   assente o debole da noi ma sarebbe presente in una catena non")
    print("   appaiata: e' il discriminante fra H1 e H2)")

    rep["test_densita"] = {}
    for reg, (key, v) in ours.items():
        cols = cols_by_reg[reg]
        gkey, _ = pick_key(cols, NGAL_HINTS, vmin=1e3, vmax=1e9)
        if gkey is None:
            print(f"\n  {reg}: nessuna colonna di conteggio galassie nel JSONL "
                  f"-> test rimandato (serve il catalogo dei mock)")
            rep["test_densita"][reg] = {"disponibile": False}
            continue
        g = cols[gkey]
        m = np.isfinite(g) & np.isfinite(cols[key])
        x, y = g[m], cols[key][m]
        r = float(np.corrcoef(x, y)[0, 1])
        rs = spearman(x, y)
        slope = float(np.polyfit(x, y, 1)[0])
        var_from_n = (slope * x.std(ddof=1)) ** 2
        print(f"\n  {reg}: colonna '{gkey}'   N={x.size}")
        print(f"    n_gal = {x.mean():.0f} +/- {x.std(ddof=1):.0f} "
              f"({100 * x.std(ddof=1) / x.mean():.2f}%)")
        print(f"    Pearson r = {r:+.3f}   Spearman = {rs:+.3f}   "
              f"pendenza = {slope:.4f} loop/galassia")
        print(f"    varianza di N_H1 imputabile a n_gal: "
              f"sigma = {np.sqrt(var_from_n):.0f}  "
              f"({100 * var_from_n / y.var(ddof=1):.1f}% della nostra varianza)")
        rep["test_densita"][reg] = {
            "disponibile": True, "colonna": gkey, "pearson": r,
            "spearman": rs, "pendenza": slope,
            "sigma_da_ngal": float(np.sqrt(var_from_n)),
            "frazione_varianza_pct": float(100 * var_from_n / y.var(ddof=1)),
            "ngal_mean": float(x.mean()), "ngal_std": float(x.std(ddof=1)),
        }

    # ---------------------------------------------------- V2: caccia a M26
    print("\n" + "=" * 76)
    print("V2 - RICERCA DEI RISULTATI PER-MOCK DI M26")
    print("=" * 76)
    cands = hunt_m26(root, args.m26_file, our_dir)
    if not cands:
        print("  nessun file candidato trovato in results\\ "
              "(escluso results\\paper1\\).")
        print("  -> se il per-mock di M26 esiste solo nei log di phase8, "
              "passalo con --m26_file")
        rep["candidati_m26"] = []
    else:
        print(f"  {len(cands)} array candidati (ordinati per plausibilita'):\n")
        rep["candidati_m26"] = []
        for c in cands[:12]:
            print(f"    {c['n']:>5d} valori  mean={c['mean']:>10.1f}  "
                  f"sd={c['std']:>7.1f}   {c['key']}")
            print(f"           {c['file']}")
            rep["candidati_m26"].append(
                {k: c[k] for k in ("file", "key", "n", "mean", "std", "median")})

        best = cands[0]
        if "NGC" in ours:
            _, v = ours["NGC"]
            a = best["_arr"]
            k = min(a.size, v.size)
            if k >= 100:
                x, y = a[:k], v[:k]
                r = float(np.corrcoef(x, y)[0, 1])
                rs = spearman(x, y)
                ident = float(np.mean(np.isclose(x, y, rtol=0, atol=0.5)))
                print(f"\n  confronto indice-per-indice col migliore "
                      f"candidato (primi {k}):")
                print(f"    Pearson r   = {r:+.4f}")
                print(f"    Spearman    = {rs:+.4f}")
                print(f"    frazione di valori identici (|d|<0.5) = "
                      f"{100 * ident:.1f}%")
                print(f"    sigma candidato {x.std(ddof=1):.1f} "
                      f"vs nostra {y.std(ddof=1):.1f}")
                print("\n    LETTURA:")
                if ident > 0.95:
                    print("      valori identici -> H3: stessa catena, "
                            "stima della varianza diversa (ddof/clipping/"
                            "sottoinsieme).")
                elif r > 0.5:
                    print("      forte correlazione senza identita' -> stessa "
                            "cosmologia per indice, realizzazione diversa: "
                            "la differenza e' nel sampling (H1/H2).")
                else:
                    print("      nessuna correlazione per indice -> ordinamento "
                            "o sottoinsieme dei mock diverso (H3), oppure "
                            "seeding indipendente (H1).")
                rep["confronto_per_indice"] = {
                    "file": best["file"], "key": best["key"], "n_confrontati": k,
                    "pearson": r, "spearman": rs, "frazione_identici": ident,
                    "std_candidato": float(x.std(ddof=1)),
                    "std_nostro": float(y.std(ddof=1)),
                }

    # ---------------------------------------------------- report
    outp = our_dir / "rev_v2v3_report.json"
    atomic_write_json(outp, rep)
    print("\n" + "=" * 76)
    print(f"report scritto in: {outp}")
    print("=" * 76)


if __name__ == "__main__":
    main()
