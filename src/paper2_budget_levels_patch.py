#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_budget_levels_patch.py — --levels sul budget. Chiude la voce 3.9.

COSA CHIUDE
  Il ciclo dei livelli nel budget e' CABLATO a (1, 0). `TERM_C` ha ora le quattro
  chiavi (patch precedente) e l'analisi e' stata girata a k=2,3, ma nessuno le
  legge: e' il difetto del flag scollegato in forma diversa - la quantita' c'e',
  la strada per usarla no.

TRE MODIFICHE
  A  il ciclo diventa parametrico su a.levels
  B  --levels in main(), default "1 0", cioe' il comportamento di oggi
  C  un CANCELLO prima di usare TERM_C: se il livello richiesto non ha la sua
     chiave, si ferma dicendo quale manca e da dove verrebbe. Senza, un
     KeyError a meta' run.

UNA DECISIONE CHE VA DICHIARATA, NON DEDOTTA
  A k=2 e k=3 l'analisi NON emette l'esito E1-E4 ne' la §5.4: le soglie
  depositate sono tarate sul deficit a k=0,1. Il budget a quei livelli produce
  quindi un pavimento e un sistematico senza un verdetto a cui applicarli.

  Va bene - sono grandezze diagnostiche - ma il codice lo DICE, a ogni livello
  fuori da (0,1), invece di lasciare che qualcuno fra un mese legga quei numeri
  come se fossero al pari degli altri. Il budget li' DESCRIVE e non CLASSIFICA.

Uso:
    python src\\paper2_budget_levels_patch.py selftest
    python src\\paper2_budget_levels_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_budget.py")

A_OLD = '''    for ki, lab in ((1, "k=1  PRIMARIO"), (0, "k=0")):
        B = build(a, reg, ki)
        c_term = TERM_C[reg][ki]'''

A_NEW = '''    levels = getattr(a, "levels", None) or [1, 0]
    _LAB = {1: "k=1  PRIMARIO", 0: "k=0",
            2: "k=2  DIAGNOSTICO", 3: "k=3  DIAGNOSTICO"}
    # CANCELLO: TERM_C deve avere la chiave PRIMA che il livello si costruisca.
    # Senza, il run muore a meta' con un KeyError e senza dire da dove verrebbe
    # il numero mancante.
    _senza = [ki for ki in levels if ki not in TERM_C.get(reg, {})]
    if _senza:
        sys.exit(f"[FATAL] TERM_C[{reg}] non ha i livelli {_senza}. Si "
                 f"misurano con un reseed del carving al fiduciale a quelle "
                 f"erosioni: paper2_runner_fase3_mock.py run --points FID "
                 f"--carve-reseed 777 --erosions {' '.join(map(str, _senza))} "
                 f"(record 26).")
    for ki, lab in ((ki, _LAB.get(ki, f"k={ki}")) for ki in levels):
        B = build(a, reg, ki)
        c_term = TERM_C[reg][ki]
        if ki not in (0, 1):
            # L'analisi a questi livelli NON emette l'esito E1-E4 ne' la §5.4:
            # le soglie depositate sono tarate sul deficit a k=0,1. Il budget
            # qui produce un pavimento e un sistematico senza un verdetto a cui
            # applicarli. Si dice, invece di lasciarlo dedurre.
            print(f"\\n  [k={ki}] Il budget a questo livello DESCRIVE e non "
                  f"CLASSIFICA: l'analisi non emette esito ne' §5.4 qui, "
                  f"quindi pavimento e sistematico non hanno una soglia a cui "
                  f"essere confrontati. Sono grandezze diagnostiche.")'''

B_OLD = '''    q.add_argument("--out", default="results/paper2/fase3_budget.jsonl")'''

B_NEW = '''    q.add_argument("--out", default="results/paper2/fase3_budget.jsonl")
    q.add_argument("--levels", type=int, nargs="+", default=[1, 0],
                   choices=[0, 1, 2, 3],
                   help="livelli di erosione. Default 1 0, il comportamento "
                        "depositato. A k=2,3 il budget DESCRIVE e non "
                        "CLASSIFICA: l'analisi non emette esito a quei livelli, "
                        "quindi pavimento e sistematico sono diagnostici")'''


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


EDITS = [
    ("A  ciclo parametrico e cancello su TERM_C", A_OLD, A_NEW),
    ("B  --levels in main()", B_OLD, B_NEW),
]


def apply_all(s):
    for name, old, new in EDITS:
        n = s.count(old)
        if n != 1:
            fail("ancora non unica per %s (occorrenze=%d)" % (name, n))
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

    ok = os.path.isfile(path)
    chk("1  budget presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("2  prerequisito: TERM_C ha gia' i quattro livelli",
        ("2: 7.00" in s or "2: 7.0" in s) and ("3: 5.80" in s or "3: 5.8" in s))
    chk("3  il difetto e' ancora presente: il ciclo e' CABLATO a (1, 0)",
        '((1, "k=1  PRIMARIO"), (0, "k=0"))' in s,
        "se questo FALLISCE, il file e' gia' patchato o e' un altro")
    chk("4  idempotenza: --levels non c'e' ancora", "--levels" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=5):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("7  il risultato e' Python valido", _parses(out))
        chk("8  SCOPE: cmd_run, ogni nome legato",
            not _nomi_liberi(out, "cmd_run"),
            ", ".join(sorted(_nomi_liberi(out, "cmd_run"))))
        chk("9  il default resta 1 0: il comportamento depositato non cambia",
            "default=[1, 0]" in out)
        chk("10 CANCELLO: TERM_C si verifica PRIMA di build, non durante",
            out.index("_senza = [ki for ki in levels") < out.index("B = build(a, reg, ki)"))
        chk("11 e il messaggio DICE come si ottiene il valore mancante",
            ("--carve-reseed 777" in out) and ("record 26" in out))
        chk("12 a k=2,3 il budget dichiara che DESCRIVE e non CLASSIFICA",
            ("DESCRIVE e non " in out) and ("CLASSIFICA" in out)
            and ("if ki not in (0, 1):" in out))
        # Compare DUE volte, ed e' giusto: una nella print a ogni livello
        # diagnostico, una nell'help di --levels. Il controllo originale ne
        # pretendeva una sola e avrebbe costretto a toglierla dall'help.
        chk("13 e lo stampa a ogni livello diagnostico, oltre che nell'help",
            out.count("DESCRIVE e non ") == 2
            and ("[k={ki}] Il budget" in out)
            and ("DESCRIVE e non " in out.split("--levels")[-1][:1200]))
        chk("14 i livelli ammessi sono i quattro che TERM_C ora ha",
            "choices=[0, 1, 2, 3]" in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_budget_levels_patch ===")
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
    bak = a.path + ".pre_budgetlevels"
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

Senza --levels nulla deve cambiare: stessi pavimenti 32.96 / 51.13 / 27.51 /
34.61, stesso sistematico 41.9 / 60.3 / 53.7 / 42.1.

E POI i quattro livelli, che chiudono la voce 3.9:
  python src\paper2_fase3_budget.py run --region NGC --levels 1 0 2 3
  python src\paper2_fase3_budget.py run --region SGC --levels 1 0 2 3

A k=2 e k=3 deve comparire la riga '[k=2] Il budget a questo livello DESCRIVE e
non CLASSIFICA'. Se non compare, il ramo non e' attivo e quei numeri
finirebbero nel registro senza la loro qualificazione.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="--levels sul budget, voce 3.9")
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
