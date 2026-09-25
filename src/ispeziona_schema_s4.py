#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ispeziona_schema_s4.py -- SOLA LETTURA. Descrive la struttura dei registri da cui escono i numeri
del par. 4 del manoscritto, per scrivere lo strumento che li ricontrolla. Non scrive nulla fuori
da logs/schema_s4.txt. Lanciare dalla radice del repository.

Per ogni file: esistenza, byte, sha256, righe; per i JSONL l'unione delle chiavi di primo livello
(con conteggio e tipi), le sottochiavi dei campi-dizionario e i valori distinti dei campi a bassa
cardinalita'; per i JSON la struttura fino a tre livelli. Le righe illeggibili si contano e si
riportano, non si saltano in silenzio.
"""
import collections
import glob
import hashlib
import json
import os
import sys

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

FILES = [
    "results/paper2/fase3_analisi.jsonl",
    "results/paper2/fase3_budget.jsonl",
    "results/paper2/fase3.jsonl",
    "results/paper2/fase3_mock.jsonl",
    "results/paper2/preflight_NGC.jsonl",
    "results/paper2/preflight_SGC.jsonl",
    "results/paper2/item15a_g13_NGC.jsonl",
    "results/paper2/item15a_g13_SGC.jsonl",
    "results/paper2/item12a_cosmo.jsonl",
    "results/paper2/fase3_intersezione_verdetto.jsonl",
    "logs/b1_decomposizione_v2.json",
    "logs/forma_lato_mock_v3.json",
]
FILES += sorted(glob.glob("results/paper2/item12a_geom_*.jsonl"))
FILES += sorted(glob.glob("results/**/rev1_r11_tiling.json", recursive=True))
OUT = os.path.join("logs", "schema_s4.txt")
MAXDIST = 16


def tipo(v):
    return type(v).__name__


def descrivi_json(x, pref, righe, livello=0):
    if livello > 3:
        return
    if isinstance(x, dict):
        for k in list(x)[:60]:
            v = x[k]
            extra = ""
            if isinstance(v, (list, tuple)):
                extra = " len=%d" % len(v)
            elif not isinstance(v, dict):
                extra = " = %s" % repr(v)[:60]
            righe.append("%s%s: %s%s" % ("  " * (livello + 1), pref + str(k), tipo(v), extra))
            if isinstance(v, dict):
                descrivi_json(v, pref + str(k) + ".", righe, livello + 1)
            elif isinstance(v, list) and v and isinstance(v[0], dict):
                descrivi_json(v[0], pref + str(k) + "[0].", righe, livello + 1)
        if len(x) > 60:
            righe.append("%s... altre %d chiavi" % ("  " * (livello + 1), len(x) - 60))


def descrivi_jsonl(p, righe):
    chiavi = collections.Counter()
    tipi = collections.defaultdict(set)
    sotto = collections.defaultdict(collections.Counter)
    valori = collections.defaultdict(collections.Counter)
    n = cattive = 0
    with open(p, encoding="utf-8") as fh:
        for riga in fh:
            if not riga.strip():
                continue
            n += 1
            try:
                r = json.loads(riga)
            except Exception:
                cattive += 1
                continue
            if not isinstance(r, dict):
                tipi["<radice>"].add(tipo(r))
                continue
            for k, v in r.items():
                chiavi[k] += 1
                tipi[k].add(tipo(v))
                if isinstance(v, dict):
                    for s, w in v.items():
                        sotto[k][s + ":" + tipo(w)] += 1
                        if isinstance(w, dict):
                            for u, z in w.items():
                                sotto[k][s + "." + u + ":" + tipo(z)] += 1
                elif isinstance(v, (str, int, bool)) or v is None:
                    if len(valori[k]) <= MAXDIST:
                        valori[k][repr(v)[:40]] += 1
    righe.append("  record: %d, righe illeggibili: %d" % (n, cattive))
    for k, c in sorted(chiavi.items()):
        righe.append("  %s: %d record, tipi %s" % (k, c, sorted(tipi[k])))
        if k in sotto:
            righe.append("    sottochiavi: " + ", ".join("%s(%d)" % kv for kv in sorted(sotto[k].items())[:80]))
        if k in valori and len(valori[k]) <= MAXDIST:
            righe.append("    valori: " + ", ".join("%s x%d" % kv for kv in sorted(valori[k].items())))
    return n


def main():
    if not (os.path.isdir("results") and os.path.isdir("logs")):
        print("ERRORE: lanciare dalla radice del repository")
        return 2
    righe, schermo = [], []
    for p in FILES:
        righe.append("=" * 100)
        righe.append(p)
        if not os.path.exists(p):
            righe.append("  ASSENTE")
            schermo.append("%-55s ASSENTE" % p)
            continue
        b = open(p, "rb").read()
        righe.append("  byte %d, sha256 %s" % (len(b), hashlib.sha256(b).hexdigest()))
        try:
            if p.endswith(".jsonl"):
                n = descrivi_jsonl(p, righe)
                schermo.append("%-55s %6d record" % (p, n))
            else:
                x = json.loads(b.decode("utf-8"))
                righe.append("  radice: %s" % tipo(x))
                descrivi_json(x, "", righe)
                schermo.append("%-55s JSON %s" % (p, tipo(x)))
        except Exception as e:
            righe.append("  ERRORE di lettura: %s: %s" % (type(e).__name__, e))
            schermo.append("%-55s ERRORE %s" % (p, type(e).__name__))
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("\n".join(righe) + "\n")
    for s in schermo:
        print(s)
    print("scritto %s (%d righe)" % (OUT, len(righe)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
