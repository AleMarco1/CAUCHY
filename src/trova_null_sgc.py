#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
trova_null_sgc.py — caccia ai risultati per-mock del test null SGC.

COSA CERCHIAMO
--------------
Il null di Sez. 2.4: ogni mock i viene rimappato sulla scala di quantili
grezza di un mock partner j = (i + N/2) mod N, e si misura lo spostamento
di N_H1. Nel NGC il risultato e' -0.9 +/- 2.1 loop con rumore procedurale
per mock sigma_null = 30. Nel SGC abbiamo +8.8 e manca l'incertezza.

INDIZIO UTILE SULLA DIMENSIONE DELL'ENSEMBLE
    2.1 = 30 / sqrt(N)  ->  N = (30/2.1)^2 = 204
quindi il null NGC girava su ~200 mock, non su 2000. Il file SGC avra'
verosimilmente la stessa taglia: cercare qualcosa con ~200 righe.

COSA SERVE
----------
La SEM e' sd(risposte per mock) / sqrt(n). Servono quindi le risposte
per mock, non la sola media. Se sul disco c'e' soltanto il valore
aggregato +8.8, il numero non e' recuperabile e il null SGC va rilanciato.

USO
---
    python trova_null_sgc.py --root D:\\projects\\cauchy
    python trova_null_sgc.py --root D:\\projects\\cauchy --calcola FILE:CHIAVE
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np

# parole che suggeriscono il test null, e quelle che suggeriscono il SGC
HINT_NULL = ["null", "partner", "shuffle", "control", "placebo", "mirror"]
HINT_SGC = ["sgc", "south"]
# nomi plausibili per la risposta per mock
KEYS_DELTA = ["delta", "response", "shift", "dn", "d_nh1", "diff", "resp"]
KEYS_N = ["n_h1", "nh1", "b2_max_count", "beta1_max", "n_tot"]


def read_rows(p: Path):
    """Restituisce una lista di dizionari, per jsonl/json/csv."""
    try:
        if p.suffix.lower() == ".jsonl":
            out = []
            for line in p.open(encoding="utf-8", errors="replace"):
                line = line.strip()
                if line:
                    try:
                        o = json.loads(line)
                        if isinstance(o, dict):
                            out.append(o)
                    except json.JSONDecodeError:
                        pass
            return out
        if p.suffix.lower() == ".json":
            o = json.load(p.open(encoding="utf-8", errors="replace"))
            if isinstance(o, list) and o and isinstance(o[0], dict):
                return o
            if isinstance(o, dict):
                return [o]
        if p.suffix.lower() == ".csv":
            import csv
            return list(csv.DictReader(p.open(newline="", encoding="utf-8",
                                              errors="replace")))
    except Exception:
        pass
    return []


def score(p: Path) -> int:
    """Quanto un file somiglia a cio' che cerchiamo."""
    low = p.name.lower() + " " + str(p.parent).lower()
    s = 0
    if any(h in low for h in HINT_NULL):
        s += 3
    if any(h in low for h in HINT_SGC):
        s += 3
    if "remap" in low or "rank" in low or "quantile" in low:
        s += 1
    return s


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=".")
    ap.add_argument("--calcola", help="FILE:CHIAVE da cui calcolare la SEM")
    a = ap.parse_args()
    root = Path(a.root).resolve()

    # ---------- modalita' calcolo ----------
    if a.calcola:
        fn, key = a.calcola.rsplit(":", 1)
        p = Path(fn)
        if not p.is_absolute():
            p = root / p
        rows = read_rows(p)
        vals = []
        for r in rows:
            try:
                v = float(r[key])
                if np.isfinite(v):
                    vals.append(v)
            except (KeyError, TypeError, ValueError):
                pass
        v = np.asarray(vals)
        if v.size < 10:
            raise SystemExit(f"solo {v.size} valori validi per la chiave "
                             f"{key!r}: controllare il nome.")
        sd = v.std(ddof=1)
        sem = sd / np.sqrt(v.size)
        print(f"file        : {p}")
        print(f"n           : {v.size}")
        print(f"media       : {v.mean():+.2f}   <- deve dare circa +8.8")
        print(f"sd per mock : {sd:.1f}          <- l'analogo di sigma_null=30")
        print(f"SEM         : {sem:.2f}         <- il numero da inserire")
        print(f"\nda scrivere nel manoscritto: $+8.8\\pm{sem:.1f}$")
        return

    # ---------- modalita' ricerca ----------
    cands = []
    for pat in ("*.jsonl", "*.json", "*.csv"):
        for p in root.rglob(pat):
            try:
                if p.stat().st_size < 200 or ".git" in str(p):
                    continue
            except OSError:
                continue
            cands.append(p)
    cands.sort(key=lambda p: (-score(p), str(p)))

    print(f"radice: {root}\nfile esaminati: {len(cands)}\n")
    print("=" * 70)
    print("A. FILE CON NOME COMPATIBILE COL NULL / SGC")
    print("=" * 70)
    shown = 0
    for p in cands:
        if score(p) < 3 or shown >= 25:
            continue
        rows = read_rows(p)
        if not rows:
            continue
        shown += 1
        keys = sorted(set().union(*(r.keys() for r in rows)))
        print(f"\n* {p}   ({len(rows)} righe, punteggio {score(p)})")
        print(f"    chiavi: {', '.join(map(str, keys[:14]))}"
              f"{' ...' if len(keys) > 14 else ''}")
        # se una colonna ha media vicina a +8.8, e' quasi certamente lei
        for k in keys:
            try:
                v = np.array([float(r[k]) for r in rows
                              if r.get(k) is not None], float)
            except (TypeError, ValueError):
                continue
            v = v[np.isfinite(v)]
            if v.size < 10:
                continue
            m, sd = v.mean(), v.std(ddof=1)
            flag = ""
            if 6.0 < m < 12.0 and sd > 1:
                flag = "   <<< media compatibile con +8.8: PROVARE QUESTA"
            elif -3 < m < 3 and 10 < sd < 60:
                flag = "   <- media ~0, sd ~30: somiglia al null NGC"
            if flag or any(h in str(k).lower() for h in KEYS_DELTA):
                print(f"      {str(k):22s} n={v.size:4d} media {m:+9.2f} "
                      f"sd {sd:7.2f} SEM {sd/np.sqrt(v.size):6.2f}{flag}")

    if not shown:
        print("\nNessun file con 'null'/'sgc' nel nome.\n")

    print()
    print("=" * 70)
    print("B. QUALSIASI FILE CHE CONTENGA IL VALORE 8.8")
    print("=" * 70)
    pat = re.compile(r"8\.8[0-9]?")
    hits = 0
    for p in cands:
        if hits >= 20:
            break
        try:
            txt = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        if pat.search(txt) and any(h in txt.lower() for h in ("null", "sgc")):
            hits += 1
            for line in txt.splitlines():
                if pat.search(line) and len(line) < 400:
                    print(f"  {p}\n      {line.strip()[:200]}")
                    break
    if not hits:
        print("  nessuna occorrenza.")

    print()
    print("=" * 70)
    print("SE NON SALTA FUORI NULLA")
    print("=" * 70)
    print("""Il null SGC e' stato probabilmente eseguito senza scrivere le
risposte per mock, oppure il file e' stato sovrascritto. In quel caso ci
sono due strade oneste:

  1. Rilanciare il null SGC con scrittura per mock. E' il test piu'
     economico dell'intero paper: N ~ 200 rimappature su campi gia' in
     cache, e restituisce anche il sigma_null del SGC, che oggi manca.

  2. Non quotare la SEM. Scrivere in Sez. 2.4 e in Tabella 2 il solo
     valore, dichiarando che il null SGC e' stato misurato sulla media
     d'ensemble e che la sua incertezza per mock non e' stata registrata.
     E' meno bello ma e' vero, e il null non porta peso argomentativo:
     serve solo a mostrare che la procedura non e' distorta, cosa gia'
     stabilita dal NGC con -0.9 +/- 2.1.

Sconsigliata la terza strada, cioe' dedurre la SEM del SGC riscalando
quella del NGC: sarebbe un numero non misurato in una tabella di numeri
misurati, ed e' esattamente il tipo di cosa che questo ciclo di revisione
ha passato due tornate a togliere dal paper.""")


if __name__ == "__main__":
    main()
