#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_selchan_fix_patch.py — il metadato esce dal contenitore dei dati.

IL DIFETTO, ED E' MIO
    TypeError: list indices must be integers or slices, not str

  La patch precedente metteva la lista dei punti saltati DENTRO il dizionario
  restituito da selection_channel, sotto la chiave "_punti_saltati". Ma quel
  dizionario e' una mappa punto -> misura, e chi lo consuma cicla su .values()
  aspettandosi dizionari. Un valore lista in mezzo rompe il consumatore.

  E' la stessa classe di difetto della fusione last-wins: un contenitore che
  porta due cose diverse. Li' erano livelli di erosione mescolati; qui e' un
  metadato mescolato ai dati.

LA CORREZIONE
  selection_channel restituisce una COPPIA: la mappa dei punti, e la lista dei
  saltati. Il chiamante le mette in due chiavi distinte del record. Nessun
  consumatore deve imparare a filtrare, perche' non c'e' niente da filtrare.

  L'alternativa - insegnare a ogni consumatore a saltare le chiavi che iniziano
  per "_" - e' peggiore: sposta il costo su ogni lettore presente e futuro, e
  basta dimenticarsene una volta.

Uso:
    python src\\paper2_selchan_fix_patch.py selftest
    python src\\paper2_selchan_fix_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_analisi.py")

A_OLD = '''    out = {"_punti_saltati": sorted(saltati)} if saltati else {}
    for p in disponibili:'''

A_NEW = '''    # Il metadato NON entra nel dizionario dei dati: quello e' una mappa
    # punto -> misura, e chi lo consuma cicla su .values() aspettandosi
    # dizionari. Si restituisce una coppia.
    out = {}
    for p in disponibili:'''

B_OLD = '''        out[p] = {"d_N_H1": float(dn), "d_n_sel": float(ds),
                  "gen_per_gal": float(dn / ds) if abs(ds) > 1.0 else None}
    return out'''

B_NEW = '''        out[p] = {"d_N_H1": float(dn), "d_n_sel": float(ds),
                  "gen_per_gal": float(dn / ds) if abs(ds) > 1.0 else None}
    return out, sorted(saltati)'''

C_OLD = '''        L["selection_channel"] = selection_channel(mock, key, desi)'''

C_NEW = '''        L["selection_channel"], _saltati = selection_channel(mock, key, desi)
        if _saltati:
            L["selection_channel_saltati"] = _saltati'''

EDITS = [
    ("A  il metadato esce dal dizionario dei dati", A_OLD, A_NEW),
    ("B  selection_channel restituisce una coppia", B_OLD, B_NEW),
    ("C  il chiamante mette i saltati in una chiave a parte", C_OLD, C_NEW),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
        s = s.replace(old, new, 1)
    return s


def _parses(src):
    import ast
    try:
        ast.parse(src)
        return True
    except SyntaxError as exc:
        print("      [sintassi] %s" % exc)
        return False


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1 — il difetto riprodotto: un valore lista rompe il consumatore
    misto = {"B1": {"gen_per_gal": 1.0}, "_punti_saltati": ["A0"]}
    try:
        [v["gen_per_gal"] for v in misto.values() if v["gen_per_gal"] is not None]
        rotto = False
    except TypeError:
        rotto = True
    chk("1  il difetto e' riprodotto: la lista in mezzo rompe .values()", rotto)
    pulito = {"B1": {"gen_per_gal": 1.0}}
    try:
        [v["gen_per_gal"] for v in pulito.values() if v["gen_per_gal"] is not None]
        ok2 = True
    except TypeError:
        ok2 = False
    chk("2  e senza il metadato il consumatore funziona", ok2)

    ok = os.path.isfile(path)
    chk("3  analisi presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("4  prerequisito: il filtro dei saltati c'e' gia'", "saltati" in s)
    chk("5  idempotenza: la coppia non c'e' ancora",
        "return out, sorted(saltati)" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=6):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("9  il risultato e' Python valido", _parses(out))
        chk("10 il dizionario dei dati non porta piu' metadati",
            '"_punti_saltati"' not in out)
        chk("11 ma i saltati NON sono persi: vanno in una chiave a parte",
            'L["selection_channel_saltati"] = _saltati' in out)
        chk("12 e si stampano comunque",
            "punti saltati" in out and "tabella che segue e' parziale" in out)
        chk("13 un solo punto di chiamata, e riceve la coppia",
            out.count("selection_channel(mock, key, desi)") == 1
            and 'L["selection_channel"], _saltati =' in out)
        chk("14 il consumatore a valle non e' stato toccato",
            'v["gen_per_gal"] for v in L["selection_channel"].values()' in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_selchan_fix_patch ===")
    nfail = 0
    for name, ok, detail in checks:
        if not ok:
            nfail += 1
        print("  [%s] %s%s" % ("PASS" if ok else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nfail))
    return nfail


def cmd_apply(a):
    if selftest(a.path):
        print("")
        fail("selftest fallito: nessuna scrittura.")
    s = read(a.path)
    out = apply_all(s)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_selchanfix"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print(r"""
POI:
  python src\paper2_fase3_analisi.py selftest
  python src\paper2_fase3_analisi.py run --region NGC --levels 1 0 2 3 --out results\paper2\fase3_analisi.jsonl
  python src\paper2_fase3_analisi.py run --region SGC --levels 1 0 2 3 --out results\paper2\fase3_analisi.jsonl

A k=1 e k=0 devono ricomparire -98.3 e -114.0, e NESSUNA riga di punti saltati.
A k=2 e k=3 deve comparire '[canale selezione] 4 punti saltati ... A0, A0m,
A1m, A3m' e il run deve ARRIVARE IN FONDO.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="metadato fuori dai dati in selection_channel")
    p.add_argument("--path", default=DEFAULT_PATH)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selftest").set_defaults(func=lambda a: 1 if selftest(a.path) else 0)
    ap = sub.add_parser("apply")
    ap.add_argument("--write", action="store_true")
    ap.set_defaults(func=cmd_apply)
    a = p.parse_args()
    sys.exit(a.func(a))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
