#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
sonda_null_sgc.py — estrae il null SGC da strutture JSON annidate.

PERCHE' SERVE
-------------
trova_null_sgc.py legge solo colonne numeriche piatte. In
per_mock_SGC_R5.jsonl le chiavi 'base', 'null' e 'remap' sono
sotto-dizionari, quindi il valore cercato c'era ma non e' stato visto.
Il file NGC equivalente (per_mock_NGC_R5_nullmm.jsonl) ha invece
delta_N_H1 gia' appiattito: media -0.88, sd 30.29, SEM 2.14, cioe'
esattamente il "-0.9 +/- 2.1" con sigma_null = 30 del manoscritto. La
struttura SGC e' quasi certamente la stessa, un livello piu' in basso.

USO
---
  # 1) appiattisci e guarda cosa c'e' dentro
  python src/sonda_null_sgc.py results/paper1/per_mock_SGC_R5.jsonl

  # 2) se esiste gia' una differenza per mock
  python src/sonda_null_sgc.py results/paper1/per_mock_SGC_R5.jsonl \
      --campo null.delta_N_H1

  # 3) se ci sono due conteggi da sottrarre
  python src/sonda_null_sgc.py results/paper1/per_mock_SGC_R5.jsonl \
      --base base.N_H1 --null null.N_H1

  # controprova sul NGC, che deve restituire -0.9 +/- 2.1
  python src/sonda_null_sgc.py results/paper1/per_mock_NGC_R5_nullmm.jsonl \
      --campo delta_N_H1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np

REF_NGC = dict(mean=-0.9, sem=2.1, sd=30.0)


def flatten(obj, prefix=""):
    """dizionari annidati -> {'a.b.c': valore}"""
    out = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            out.update(flatten(v, f"{prefix}{k}."))
    elif isinstance(obj, (list, tuple)):
        if obj and all(isinstance(x, (int, float)) for x in obj):
            out[prefix[:-1]] = obj            # lista numerica: la teniamo
    else:
        out[prefix[:-1]] = obj
    return out


def load(path: Path):
    rows = []
    for line in path.open(encoding="utf-8", errors="replace"):
        line = line.strip()
        if line:
            try:
                o = json.loads(line)
                if isinstance(o, dict):
                    rows.append(flatten(o))
            except json.JSONDecodeError:
                pass
    return rows


def column(rows, name):
    vals = []
    for r in rows:
        v = r.get(name)
        if isinstance(v, (int, float)) and np.isfinite(v):
            vals.append(float(v))
    return np.asarray(vals)


def report(v, etichetta, atteso=None, correl=None):
    n = v.size
    sd = v.std(ddof=1)
    sem = sd / np.sqrt(n)
    print(f"\n{etichetta}")
    print(f"  n            : {n}")
    print(f"  media        : {v.mean():+.2f}")
    print(f"  sd per mock  : {sd:.2f}")
    if correl is not None:
        print(f"  corr(base,null): {correl:.4f}   <- e' cio' che rende "
              f"piccola la sd appaiata")
    print(f"  SEM          : {sem:.2f}")
    print(f"\n  da scrivere in Sez. 2.4 e Tabella 2: "
          f"${v.mean():+.1f}\\pm{sem:.1f}$")
    # il confronto avviene contro il valore atteso passato da chi chiama,
    # non contro una costante cablata: il controllo NGC attende -0.9, non +8.8
    if atteso is not None and abs(v.mean() - atteso) > max(1.0, 0.2*abs(atteso)):
        print(f"\n  ATTENZIONE: media {v.mean():+.2f} contro {atteso:+.2f} "
              f"atteso.\n  Campo sbagliato, o sottoinsieme diverso da quello "
              f"del manoscritto.")
    elif atteso is not None:
        print(f"\n  controllo superato: {v.mean():+.2f} contro {atteso:+.2f} "
              f"atteso dal manoscritto.")
    if n > 1000:
        print(f"\n  NOTA: n = {n}. Il null NGC gira su 200 mock, quindi le due\n"
              f"  righe di Tabella 2 avranno precisioni molto diverse: dirlo\n"
              f"  in didascalia, altrimenti sembra un errore di battitura.")
    return sem


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--campo", help="campo appiattito con la differenza")
    ap.add_argument("--base", help="campo del conteggio di partenza")
    ap.add_argument("--null", dest="nullk", help="campo del conteggio col null")
    ap.add_argument("--atteso", type=float, default=None,
                    help="valore dichiarato nel manoscritto, per il controllo "
                         "(+8.8 per il SGC, -0.9 per il NGC)")
    a = ap.parse_args()

    p = Path(a.file)
    rows = load(p)
    if not rows:
        raise SystemExit(f"nessuna riga leggibile in {p}")
    print(f"file : {p}\nrighe: {len(rows)}")

    if a.campo:
        report(column(rows, a.campo), f"campo {a.campo}", a.atteso)
        return
    if a.base and a.nullk:
        b, nl = column(rows, a.base), column(rows, a.nullk)
        if b.size != nl.size:
            raise SystemExit(f"lunghezze diverse: {b.size} contro {nl.size}")
        rho = float(np.corrcoef(b, nl)[0, 1])
        report(nl - b, f"differenza {a.nullk} - {a.base}", a.atteso, rho)
        return

    # ---------- esplorazione ----------
    keys = sorted(set().union(*(r.keys() for r in rows)))
    print(f"campi appiattiti: {len(keys)}\n")
    print("=" * 66)
    print("CAMPI NUMERICI")
    print("=" * 66)
    cand_delta, cand_count = [], []
    for k in keys:
        v = column(rows, k)
        if v.size < 10:
            continue
        m, sd = v.mean(), v.std(ddof=1)
        nota = ""
        if 5.0 < m < 13.0 and 5 < sd < 80:
            nota = "  <<< media compatibile con +8.8"
            cand_delta.append(k)
        elif -5 < m < 5 and 10 < sd < 80:
            nota = "  <- media ~0, sd ~30: forma del null"
            cand_delta.append(k)
        elif 10000 < m < 30000:
            nota = "  <- conteggio SGC (~18700)"
            cand_count.append(k)
        print(f"  {k:38s} n={v.size:5d} media {m:12.2f} sd {sd:9.2f}{nota}")

    print()
    print("=" * 66)
    print("COSA FARE ORA")
    print("=" * 66)
    if cand_delta:
        print("Differenza per mock gia' presente. Rilancia con:")
        for k in cand_delta[:3]:
            print(f"    --campo {k}")
    else:
        # accoppia campi con la STESSA foglia sotto prefissi diversi
        # (base.N_H1 con null.N_H1), non due campi qualsiasi
        coppie = []
        for k in keys:
            if "." not in k:
                continue
            pre, foglia = k.rsplit(".", 1)
            if pre in ("base", "orig", "originale"):
                for alt in ("null", "nullmm", "partner"):
                    if f"{alt}.{foglia}" in keys:
                        coppie.append((k, f"{alt}.{foglia}", foglia))
        # priorita' al conteggio totale
        coppie.sort(key=lambda c: 0 if c[2].lower() in
                    ("n_h1", "nh1", "b2_max_count") else 1)
        if coppie:
            b, nl, _ = coppie[0]
            print("Nessuna differenza pronta, ma i due stadi ci sono."
                  " Rilancia con:")
            print(f"    --base {b} --null {nl}")
            print("\n(l'ordine conta: null meno base, non il contrario)")
            if len(coppie) > 1:
                print("\nAltre coppie disponibili, per controlli secondari:")
                for b2, n2, _ in coppie[1:5]:
                    print(f"    --base {b2} --null {n2}")
        else:
            print("""Nessun campo utile. Restano le due strade gia' note:
rilanciare il null SGC con scrittura per mock, oppure non quotare la SEM
dichiarando che non e' stata registrata. Non ricavarla riscalando il NGC.""")

    print("\nControprova consigliata prima di fidarsi del numero SGC:")
    print("    python src/sonda_null_sgc.py "
          "results/paper1/per_mock_NGC_R5_nullmm.jsonl --campo delta_N_H1")
    print(f"    deve restituire media {REF_NGC['mean']:+.1f}, "
          f"sd ~{REF_NGC['sd']:.0f}, SEM ~{REF_NGC['sem']:.1f}")


if __name__ == "__main__":
    main()
