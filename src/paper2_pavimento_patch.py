#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_pavimento_patch.py — il pavimento (f) diventa il MASSIMO dei moduli.
Record 32 (obiettivo) e 33 (regola corretta e cancello).

LA REGOLA
  (f) = max |b_residual| sui SEI punti del blocco A, per emisfero e livello, sui
  residui DOPO la sottrazione del canale voxel, in gauge `regauged`.

PERCHE' IL MASSIMO E NON UNA rms
  La proprieta' che serve e' che la regola non possa ABBASSARE il pavimento: una
  regola adottata dopo aver visto i dati grezzi non deve poter fabbricare un
  sistematico piu' piccolo. Per un insieme finito

      rms = sqrt(media(x^2)) <= sqrt(max(x^2)) = max|x|

  quindi il massimo sui sei e' >= la rms di QUALUNQUE sottoinsieme, inclusa la
  coppia depositata {A1, A3}, per ogni valore che i residui prenderanno. E' una
  disuguaglianza, non una congettura.

  Il record 32 aveva proposto "massimo fra le rms per ampiezza" sostenendo la
  stessa proprieta'. Era FALSO: BLOCK_A = ("A1", "A3") e quei due punti stanno a
  |alpha-1| = 0.0275 e 0.0406, cioe' ad ampiezze DIVERSE, quindi il depositato
  non e' la rms a un'ampiezza. Contro-esempio nel record 33: con residui -10.0,
  -10.3, 0, 0 le rms per ampiezza sarebbero 7.07 e 7.28 contro un depositato di
  10.15 - avrebbe abbassato.

IL CANCELLO, PRIMA DI OGNI VALORE NUOVO
  La rms sulla COPPIA depositata {A1, A3} deve riprodurre 10.1, 17.7, 20.2 e
  32.5 entro un decimo. Se non lo fa, l'estensione ha cambiato il calcolo
  esistente e nulla di quel che segue si usa.

TRE MODIFICHE
  A  BLOCK_A passa da due a sei punti
  B  floor: massimo dei moduli, e il cancello sulla coppia depositata
  C  la stampa riporta il punto che DETERMINA il pavimento, non solo il valore

Uso:
    python src\\paper2_pavimento_patch.py selftest
    python src\\paper2_pavimento_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import math
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

A_OLD = '''BLOCK_A = ("A1", "A3")'''

A_NEW = '''# Sei punti dopo i record 27, 28 e 30: tre coppie simmetriche a |alpha-1| =
# 0.018627, 0.0275 e 0.0406. La coppia DEPOSITATA e' {A1, A3}, che sta a due
# ampiezze diverse e mescola una compressione con un'espansione: e' la ragione
# per cui la regola del record 32 non reggeva (record 33).
BLOCK_A = ("A0", "A1", "A1m", "A3", "A3m", "A0m")
BLOCK_A_DEPOSITATO = ("A1", "A3")      # la coppia del pavimento depositato
FLOOR_DEPOSITATO = {"NGC": {1: 10.1, 0: 17.7}, "SGC": {1: 20.2, 0: 32.5}}'''

B_OLD = '''    floor = (float(np.sqrt(np.mean([x["b_residual"] ** 2 for x in a_rows])))
             if a_rows else float("nan"))'''

B_NEW = '''    # CANCELLO, record 33: prima di riportare qualunque valore nuovo, la rms
    # sulla COPPIA DEPOSITATA {A1, A3} deve riprodurre il pavimento depositato.
    # Se non lo fa, l'estensione a sei punti ha cambiato il calcolo esistente e
    # nulla di quel che segue si usa. Il cancello e' sulla COPPIA e non su
    # un'ampiezza: quei due punti stanno ad ampiezze diverse.
    dep = [x for x in a_rows if x["pt"] in BLOCK_A_DEPOSITATO]
    atteso = FLOOR_DEPOSITATO.get(region, {}).get(ki)
    if len(dep) == len(BLOCK_A_DEPOSITATO) and atteso is not None:
        rms_dep = float(np.sqrt(np.mean([x["b_residual"] ** 2 for x in dep])))
        if abs(rms_dep - atteso) > 0.1:
            sys.exit(f"[FATAL] pavimento, cancello del record 33: la rms sulla "
                     f"coppia depositata {BLOCK_A_DEPOSITATO} vale {rms_dep:.2f} "
                     f"contro {atteso} depositato, {region} k={ki}. "
                     f"L'estensione a sei punti ha cambiato il calcolo "
                     f"esistente: nulla di quel che segue si usa.")
    else:
        rms_dep = float("nan")

    # (f) = MAX |b_residual| sui punti disponibili (record 33). Il massimo e'
    # >= la rms di qualunque sottoinsieme, quindi la regola non puo' ABBASSARE
    # il pavimento rispetto al depositato, qualunque siano i numeri. E' la
    # proprieta' che la rende adottabile dopo aver visto i grezzi.
    floor = (float(max(abs(x["b_residual"]) for x in a_rows))
             if a_rows else float("nan"))
    floor_driver = (max(a_rows, key=lambda x: abs(x["b_residual"]))["pt"]
                    if a_rows else None)
    floor_rms_dep = rms_dep
    floor_n = len(a_rows)'''

C_OLD = '''    out = []
    for r in meas:'''

C_NEW = '''    # Il pavimento si riporta con il punto che lo DETERMINA e con quanti punti
    # lo compongono: un massimo senza il suo argomento non e' verificabile.
    print(f"  (f) pavimento = {floor:7.2f}  su {floor_n} punti, determinato da "
          f"{floor_driver}   [rms coppia depositata {floor_rms_dep:.2f} contro "
          f"{FLOOR_DEPOSITATO.get(region, {}).get(ki)}]")

    out = []
    for r in meas:'''

EDITS = [
    ("A  BLOCK_A a sei punti, piu' la coppia depositata", A_OLD, A_NEW),
    ("B  floor = massimo dei moduli, con il cancello sulla coppia", B_OLD, B_NEW),
    ("C  la stampa riporta il punto che determina il pavimento", C_OLD, C_NEW),
]


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def apply_all(s):
    for name, old, new in EDITS:
        if s.count(old) != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, s.count(old)))
        s = s.replace(old, new, 1)
    return s


def _nomi_liberi(src, funcname):
    import ast
    import builtins
    tree = ast.parse(src)
    glob = {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    glob |= {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for n in tree.body:
        if isinstance(n, (ast.Import, ast.ImportFrom)):
            glob |= {(al.asname or al.name.split(".")[0]) for al in n.names}
        elif isinstance(n, ast.Assign):
            glob |= {t.id for t in ast.walk(n) if isinstance(t, ast.Name)}
    fn = next((f for f in ast.walk(tree)
               if isinstance(f, ast.FunctionDef) and f.name == funcname), None)
    if fn is None:
        return {"<funzione %s non trovata>" % funcname}
    bound = set(glob) | set(dir(builtins))
    a = fn.args
    for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
        bound.add(arg.arg)
    for extra in (a.vararg, a.kwarg):
        if extra is not None:
            bound.add(extra.arg)
    for node in ast.walk(fn):
        if isinstance(node, ast.Name) and isinstance(node.ctx, (ast.Store, ast.Del)):
            bound.add(node.id)
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            bound |= {(al.asname or al.name.split(".")[0]) for al in node.names}
        elif isinstance(node, ast.ExceptHandler) and node.name:
            bound.add(node.name)
        elif isinstance(node, (ast.FunctionDef, ast.Lambda)):
            for arg in list(node.args.args) + list(node.args.kwonlyargs):
                bound.add(arg.arg)
        elif isinstance(node, ast.comprehension):
            bound |= {t.id for t in ast.walk(node.target) if isinstance(t, ast.Name)}
    usati = {node.id for node in ast.walk(fn)
             if isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load)}
    return usati - bound


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

    # 1-3: la matematica della regola, verificata e non asserita
    import random
    rms = lambda v: math.sqrt(sum(x * x for x in v) / len(v))
    random.seed(2)
    ok = True
    for _ in range(5000):
        v = [random.uniform(-100, 100) for _ in range(6)]
        sub = random.sample(v, random.randint(1, 6))
        if max(abs(x) for x in v) < rms(sub) - 1e-12:
            ok = False
            break
    chk("1  max|x| >= rms di ogni sottoinsieme, su 5000 casi", ok)
    chk("2  e il pavimento depositato E' la rms della coppia {A1, A3}",
        all(abs(rms(v) - d) < 0.1 for v, d in
            (((-10.0, -10.3), 10.1), ((-18.1, -17.4), 17.7),
             ((26.3, -10.9), 20.2), ((33.5, -31.4), 32.5))))
    chk("3  la regola SCARTATA del record 32 poteva abbassare",
        max(rms((-10.0, 0.0)), rms((0.0, -10.3))) < rms((-10.0, -10.3)),
        "7.28 contro 10.15")

    okf = os.path.isfile(path)
    chk("4  budget presente", okf, path)
    if not okf:
        return _report(checks)
    s = read(path)
    chk("5  idempotenza: la regola nuova non c'e' ancora",
        ("BLOCK_A_DEPOSITATO" not in s) and ("floor_driver" not in s))
    for i, (name, old, new) in enumerate(EDITS, start=6):
        c = s.count(old)
        chk("%-2d ancora %s" % (i, name), c == 1, "occorrenze=%d" % c)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("9  il risultato e' Python valido", _parses(out))
        chk("10 SCOPE: build, ogni nome legato",
            not _nomi_liberi(out, "build"),
            ", ".join(sorted(_nomi_liberi(out, "build"))))
        chk("11 BLOCK_A ha sei punti e la coppia depositata e' a parte",
            'BLOCK_A = ("A0", "A1", "A1m", "A3", "A3m", "A0m")' in out
            and 'BLOCK_A_DEPOSITATO = ("A1", "A3")' in out)
        chk("12 il pavimento e' il MASSIMO dei moduli, non una rms",
            'max(abs(x["b_residual"]) for x in a_rows)' in out
            and 'np.sqrt(np.mean([x["b_residual"] ** 2 for x in a_rows]))' not in out)
        # Il marcatore giusto e' il COMMENTO, non la stringa del messaggio: il
        # testo "cancello del record 33" compare dentro sys.exit, quindi
        # cercarlo li' metteva il marcatore DOPO la riga che voleva localizzare.
        chk("13 il cancello e' PRIMA del calcolo del pavimento e ferma",
            out.index("# CANCELLO, record 33") < out.index("(f) = MAX")
            and "sys.exit" in out[out.index("# CANCELLO, record 33"):
                                  out.index("(f) = MAX")])
        chk("14 e confronta la COPPIA depositata, non un'ampiezza",
            "BLOCK_A_DEPOSITATO" in out.split("dep = [x for x")[1][:120])
        # IL DIFETTO CHE QUESTO CONTROLLO ESISTE PER PRENDERE. La chiave del nome
        # del punto e' "pt", non "point": gather() la crea come {"pt": p,
        # "block": ...}. Averla indovinata dava KeyError A RUN AVVIATO, dopo che
        # selftest e apply erano passati entrambi. ast vede i nomi, non le
        # chiavi di un dizionario costruito in un'altra funzione: quelle vanno
        # confrontate con la sorgente che le crea.
        chk("14b le chiavi usate esistono in gather: 'pt', non 'point'",
            ('x["pt"]' in out) and ('x["point"]' not in out)
            and ('"pt": p' in out),
            "gather crea 'pt'; 'point' e' il campo del JSONL, non della riga")

        chk("15 il pavimento si riporta col punto che lo determina",
            "floor_driver" in out and "determinato da" in out)
        chk("16 i quattro valori depositati sono nel codice, non a memoria",
            'FLOOR_DEPOSITATO = {"NGC": {1: 10.1, 0: 17.7}, '
            '"SGC": {1: 20.2, 0: 32.5}}' in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_pavimento_patch ===")
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
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_pavimento"
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
PRIMA:
  python src\paper2_fase3_budget.py selftest

POI:
  python src\paper2_fase3_budget.py run --region NGC
  python src\paper2_fase3_budget.py run --region SGC

IL CANCELLO PARLA PER PRIMO. Se la rms sulla coppia {A1, A3} non riproduce
10.1 / 17.7 / 20.2 / 32.5 entro un decimo, il budget SI FERMA e non riporta
niente: vuol dire che estendere BLOCK_A a sei punti ha cambiato il calcolo
esistente, non che il pavimento e' diverso.

DA GUARDARE:
  - la riga "(f) pavimento = ... determinato da XXX". Il punto che determina
    il massimo e' l'informazione, non solo il valore.
  - il pavimento puo' solo SALIRE o restare uguale rispetto a 10.1/17.7/
    20.2/32.5. Se scende, e' un difetto e non un risultato: max >= rms.
  - se sale, sale anche sigma_sys, e SGC k=0 si allontana ANCORA di meno dal
    confine E1 dei suoi 0.51 sigma (record 20 e 32).""")
    return 0


def main():
    p = argparse.ArgumentParser(description="pavimento = max dei moduli, record 32-33")
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
