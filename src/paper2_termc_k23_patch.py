#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_termc_k23_patch.py — TERM_C ai livelli 2 e 3. Record 26.

COSA CHIUDE
  `TERM_C` aveva solo le chiavi 0 e 1, perche' il reseed del carving era stato
  girato prima che k=2 e k=3 esistessero. Il budget a quei livelli era percio'
  non costruibile: e' la voce 3.9 della checklist, aperta dal 1 settembre.

  Il reseed FID-only a `--erosions 2 3` del record 26 e' girato il 4 settembre,
  1.49 h + 1.48 h. Le due chiavi si aggiungono qui.

I VALORI, E DA DOVE VENGONO
  TERM_C = sd(dN)/sqrt(2)/sqrt(200), con dN la differenza appaiata fra il run
  principale e il reseed al fiduciale. Il sqrt(2) perche' la differenza e' fra
  DUE estrazioni indipendenti dalla stessa distribuzione condizionata.

      k    NGC      SGC
      0    7.687    6.785      <- depositati 7.69 e 6.78
      1    7.725    6.288      <- depositati 7.73 e 6.29
      2    7.001    5.537      NUOVI
      3    5.799    4.409      NUOVI

IL CANCELLO, ED E' IL PUNTO
  I livelli 0 e 1 vengono RICALCOLATI dallo stesso registro e dallo stesso
  codice dei nuovi. Se non riproducono i depositati entro 0.01, i valori nuovi
  non sono confrontabili con quelli vecchi e non si scrivono. Il cancello
  verifica che una quantita' gia' congelata esca invariata dalla strada che
  produce quelle nuove: senza, si aggiungerebbero due numeri di provenienza
  ignota accanto a due noti.

UNA STRUTTURA CHE VALE LA PENA REGISTRARE, e non e' un verdetto
  TERM_C DECRESCE monotonamente con l'erosione in ENTRAMBI gli emisferi: 7.69 ->
  5.80 in NGC, 6.79 -> 4.41 in SGC. Ha senso - erodendo si tolgono i voxel di
  bordo, dove il carving fa la differenza - ma non era stato previsto, e i due
  emisferi vanno nello STESSO verso, il che e' notevole dato che nelle altre
  misure di questi giorni sono andati in versi opposti tre volte. Nessuna
  soglia era dichiarata su questo: si riporta e basta.

Uso:
    python src\\paper2_termc_k23_patch.py selftest
    python src\\paper2_termc_k23_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import math
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

# Misurati sul reseed del 4 set 2026, fiduciale, n = 200.
SD = {("NGC", 0): 153.739, ("NGC", 1): 154.502,
      ("NGC", 2): 140.018, ("NGC", 3): 115.980,
      ("SGC", 0): 135.694, ("SGC", 1): 125.758,
      ("SGC", 2): 110.731, ("SGC", 3): 88.176}
DEPOSITATI = {("NGC", 1): 7.73, ("NGC", 0): 7.69,
              ("SGC", 1): 6.29, ("SGC", 0): 6.78}


def termc(sd, n=200):
    return sd / math.sqrt(2.0) / math.sqrt(n)


A_OLD = '''TERM_C = {"NGC": {1: 7.73, 0: 7.69}, "SGC": {1: 6.29, 0: 6.78}}'''

A_NEW = '''# TERM_C = sd(dN)/sqrt(2)/sqrt(200) al fiduciale, con dN la differenza appaiata
# fra il run principale e il reseed del carving. Il sqrt(2) perche' la
# differenza e' fra DUE estrazioni indipendenti dalla stessa distribuzione
# condizionata, non fra una misura e una verita'.
#
# k=0 e k=1: reseed del 31 ago 2026, valori depositati.
# k=2 e k=3: reseed FID-only del 4 set 2026 (record 26), 1.49 h + 1.48 h.
#   Il cancello di riproduzione ha verificato che 0 e 1, ricalcolati dallo
#   stesso registro e dallo stesso codice dei nuovi, ridiano 7.687, 7.725,
#   6.785 e 6.288 contro i depositati 7.69, 7.73, 6.78 e 6.29.
#
# TERM_C DECRESCE con l'erosione in entrambi gli emisferi - 7.69 -> 5.80 in NGC,
# 6.79 -> 4.41 in SGC - e i due vanno nello STESSO verso. Non era previsto e non
# porta verdetto: nessuna soglia era dichiarata su questo.
TERM_C = {"NGC": {0: 7.69, 1: 7.73, 2: 7.00, 3: 5.80},
          "SGC": {0: 6.78, 1: 6.29, 2: 5.54, 3: 4.41}}'''


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    n = s.count(A_OLD)
    if n != 1:
        fail("ancora non unica per TERM_C (occorrenze=%d)" % n)
    return s.replace(A_OLD, A_NEW, 1)


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

    # 1 — IL CANCELLO: i livelli gia' depositati devono uscire invariati dalla
    # stessa formula che produce i nuovi. Se non lo fanno, i nuovi non sono
    # confrontabili e non si scrivono.
    bad = []
    for k, dep in DEPOSITATI.items():
        got = termc(SD[k])
        if abs(got - dep) > 0.01:
            bad.append("%s k=%d: %.3f contro %.2f" % (k[0], k[1], got, dep))
    chk("1  CANCELLO: k=0 e k=1 ricalcolati riproducono i depositati",
        not bad, "; ".join(bad) if bad else
        "7.687/7.725/6.785/6.288 contro 7.69/7.73/6.78/6.29")

    # 2-4 — la struttura che il commento afferma
    for reg in ("NGC", "SGC"):
        v = [termc(SD[(reg, k)]) for k in (0, 1, 2, 3)]
        chk("2%s %s: TERM_C decresce da k=1 in poi" % (reg[0].lower(), reg),
            v[1] > v[2] > v[3],
            "  ".join("%.2f" % x for x in v))
    chk("3  e i due emisferi vanno nello STESSO verso",
        (termc(SD[("NGC", 3)]) < termc(SD[("NGC", 0)]))
        and (termc(SD[("SGC", 3)]) < termc(SD[("SGC", 0)])),
        "rapporti k3/k0: %.3f e %.3f" % (termc(SD[("NGC", 3)]) / termc(SD[("NGC", 0)]),
                                         termc(SD[("SGC", 3)]) / termc(SD[("SGC", 0)])))

    ok = os.path.isfile(path)
    chk("4  budget presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("5  idempotenza: i livelli 2 e 3 non ci sono ancora",
        "2: 7.00" not in s and "3: 5.80" not in s)
    n = s.count(A_OLD)
    chk("6  ancora TERM_C unica", n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("7  il risultato e' Python valido", _parses(out))
        # TERM_C si VALUTA, non si legge come stringa
        import ast
        ns = {}
        nodo = next(x for x in ast.parse(out).body
                    if isinstance(x, ast.Assign)
                    and any(getattr(t, "id", "") == "TERM_C" for t in x.targets))
        exec(compile(ast.Module(body=[nodo], type_ignores=[]), "<t>", "exec"), ns)
        T = ns["TERM_C"]
        chk("8  TERM_C valutato: due emisferi, quattro livelli ciascuno",
            set(T) == {"NGC", "SGC"} and all(set(T[r]) == {0, 1, 2, 3} for r in T),
            repr(T))
        chk("9  i valori depositati NON sono stati toccati",
            all(abs(T[k[0]][k[1]] - dep) < 1e-9 for k, dep in DEPOSITATI.items()))
        chk("10 e i nuovi coincidono col misurato entro l'arrotondamento",
            all(abs(T[reg][k] - round(termc(SD[(reg, k)]), 2)) < 1e-9
                for reg in ("NGC", "SGC") for k in (2, 3)),
            "NGC 7.00/5.80  SGC 5.54/4.41")
        chk("11 la provenienza dei nuovi e' nel codice, con la data e il record",
            ("record 26" in out) and ("4 set 2026" in out)
            and ("cancello di riproduzione" in out))
        # I frammenti non devono attraversare un fine riga: nel commento la
        # frase e' spezzata fra "non" e "porta verdetto" con un "# " in mezzo.
        chk("12 la struttura decrescente e' riportata SENZA verdetto",
            ("DECRESCE" in out) and ("porta verdetto" in out)
            and ("nessuna soglia era dichiarata" in out))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_termc_k23_patch ===")
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
    bak = a.path + ".pre_termck23"
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
  python src\paper2_fase3_budget.py selftest
  python src\paper2_fase3_budget.py run --region NGC
  python src\paper2_fase3_budget.py run --region SGC

A k=0 e k=1 NULLA deve cambiare: gli stessi valori di TERM_C, lo stesso
pavimento a sei punti (32.96 / 51.13 / 27.51 / 34.61), lo stesso sistematico
(41.9 / 60.3 / 53.7 / 42.1). Se cambiano, la patch ha toccato piu' di quel che
doveva.

E se il budget accetta --level 2 e --level 3, girali: e' la voce 3.9 della
checklist, aperta dal 1 settembre. Serve che paper2_fase3_analisi.py sia stato
girato a quei livelli, perche' il budget legge il suo per_point.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="TERM_C ai livelli 2 e 3, record 26")
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
