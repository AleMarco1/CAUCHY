#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_d5c_chiusura_patch.py — D5c torna a bloccare, con la soglia 28. Record 36.

COSA CHIUDE
  La deroga aperta dal record 23 e rilegata a una CONDIZIONE dal record 34:
  «D5c misura per TUTTI i run finche' la soglia non e' dichiarata sulla
  distribuzione osservata». Il record 36 l'ha dichiarata. La condizione e'
  soddisfatta e la deroga finisce qui.

LA SOGLIA, E DA DOVE VIENE
  n_clipped >= 28 per punto. NON e' un quantile della distribuzione osservata:
  quella dice che il clipping attuale e' trascurabile, non dove mettere il
  cancello. 28 e' il numero di voxel il cui effetto raggiunge META' della SEM
  piu' piccola: 0.5 x 8.7 / 0.1574 = 27.6, con 0.1574 generatori per voxel dal
  cancello 2.2a.

  Il massimo osservato su 4800 misure e' 9, quindi il margine e' 3.1x: sui dati
  attuali non spara mai, che e' corretto perche' sui dati attuali non c'e'
  niente da fermare.

TRE MODIFICHE
  A  D5C_SOGLIA = 28, con la derivazione nel commento
  B  D5C_MODE torna a "block", e il cancello confronta con la soglia invece che
     con zero
  C  l'avviso e' riscritto: diceva "NON per un run che produce risultati", che
     era la formulazione del record 23 quando la deroga copriva due run
     nominati. Il record 34 l'ha resa una condizione e il 36 l'ha chiusa: quel
     messaggio allarmava su una cosa regolare, e un avviso che grida al lupo
     smette di essere letto.

DA APPLICARE A RUN FERMI.

Uso:
    python src\\paper2_d5c_chiusura_patch.py selftest
    python src\\paper2_d5c_chiusura_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_runner_fase3_mock.py")

A_OLD = '''D5C_MODE = "measure"'''

A_NEW = '''D5C_MODE = "block"

# SOGLIA DI D5c, record 36. Derivata dall'EFFETTO, non dai quantili.
#
# Il cancello 2.2a misura 216 voxel di maschera = 34 generatori, cioe' 0.1574
# generatori per voxel. La SEM piu' piccola di DDmax vale 8.7 (SGC k=1). Il
# numero di voxel il cui effetto raggiunge META' di quella SEM e'
#     0.5 * 8.7 / 0.1574 = 27.6  ->  28
#
# Perche' META' e non un quarto o la SEM intera. In quadratura un termine
# accanto a uno dominante aggiunge +3.1% a un quarto, +5.4% a un terzo, +11.8%
# a meta', +41.4% alla parita': meta' e' dove "trascurabile" smette di essere
# difendibile. E dall'altro lato: il massimo osservato su 4800 misure e' 9, e
# la distribuzione e' fortemente sovra-dispersa (sotto Poisson(0.703) un 9 ha
# probabilita' 6e-08), quindi una soglia a un quarto - 13.8, solo 1.5x il
# massimo - sparerebbe sulla crescita ordinaria della coda. Meta' da' 3.1x.
# L'unita' e' scartata dal lato opposto: a 55 voxel il clipping contribuirebbe
# quanto l'errore campionario e dovrebbe entrare nel budget come termine.
#
# NON e' un quantile: la distribuzione dice che il clipping attuale e'
# trascurabile, non dove mettere il cancello.
D5C_SOGLIA = 28'''

B_OLD = '''            if _cl["n_clipped"] and D5C_MODE == "block":
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo. "
                         f"Dettaglio: {_cl}. Il punto non si misura "
                         f"(emendamento 17).")
            if _cl["n_clipped"] and D5C_MODE == "measure":
                print(f"    [D5c misura] {name}/mock {kk}: "
                      f"n_clipped = {_cl['n_clipped']}")'''

B_NEW = '''            if _cl["n_clipped"] >= D5C_SOGLIA and D5C_MODE == "block":
                sys.exit(f"[FATAL] D5c: {region}/{name}/mock {kk}: "
                         f"{_cl['n_clipped']} posizioni fuori dal cubo, soglia "
                         f"{D5C_SOGLIA} (record 36). A questo conteggio "
                         f"l'impilamento vale ~{_cl['n_clipped'] * 0.1574:.1f} "
                         f"generatori, cioe' meta' della SEM piu' piccola: "
                         f"non e' piu' distinguibile dal rumore campionario. "
                         f"Dettaglio: {_cl}.")
            if _cl["n_clipped"] and D5C_MODE == "measure":
                print(f"    [D5c misura] {name}/mock {kk}: "
                      f"n_clipped = {_cl['n_clipped']}")'''

C_OLD = '''def _avviso_d5c():
    if D5C_MODE != "block":
        print("=" * 74)
        print(f"  ATTENZIONE: D5c e' in modalita' '{D5C_MODE}', NON in 'block'.")
        print("  Il cancello MISURA e non ferma. Va bene per un giro")
        print("  diagnostico; NON per un run che produce risultati.")
        print("  Rimettere D5C_MODE = 'block' in cima a questo file.")
        print("=" * 74)'''

C_NEW = '''def _avviso_d5c():
    """Lo stato di D5c si stampa SEMPRE, non solo quando e' anomalo.

    Il messaggio precedente diceva "NON per un run che produce risultati": era
    la formulazione del record 23, quando la deroga copriva due run NOMINATI. Il
    record 34 l'ha rilegata a una condizione che copriva tutti i run, e il 36
    l'ha chiusa dichiarando la soglia. Quel testo ha continuato ad allarmare su
    una cosa regolare per due record, e un avviso che grida al lupo smette di
    essere letto."""
    if D5C_MODE == "block":
        print(f"  [D5c] modalita' 'block', soglia {D5C_SOGLIA} "
              f"(record 36: meta' della SEM piu' piccola, "
              f"{D5C_SOGLIA * 0.1574:.1f} generatori).")
        return
    print("=" * 74)
    print(f"  ATTENZIONE: D5c e' in modalita' '{D5C_MODE}', NON in 'block'.")
    print("  Il cancello MISURA e non ferma. La deroga dei record 23 e 34 e'")
    print("  CHIUSA dal record 36, che ha dichiarato la soglia: questa")
    print("  modalita' non e' piu' coperta da nessun record.")
    print(f"  Rimettere D5C_MODE = 'block' in cima a questo file.")
    print("=" * 74)'''

EDITS = [
    ("A  D5C_SOGLIA = 28 e D5C_MODE = block", A_OLD, A_NEW),
    ("B  il cancello confronta con la soglia, non con zero", B_OLD, B_NEW),
    ("C  l'avviso e' riscritto e stampa sempre lo stato", C_OLD, C_NEW),
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

    import math
    gv, smin = 34.0 / 216.0, 8.7
    chk("1  la soglia e' meta' della SEM piu' piccola in voxel",
        abs(0.5 * smin / gv - 27.6) < 0.1, "%.1f -> 28" % (0.5 * smin / gv))
    chk("2  e il massimo osservato le sta 3.1x sotto",
        abs(28 / 9.0 - 3.11) < 0.02, "28/9 = %.2f" % (28 / 9.0))
    chk("3  in quadratura, meta' aggiunge l'11.8%: non piu' trascurabile",
        abs(100 * (math.sqrt(1.25) - 1) - 11.8) < 0.1)

    ok = os.path.isfile(path)
    chk("4  runner presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("5  idempotenza: la soglia non c'e' ancora", "D5C_SOGLIA" not in s)
    chk("6  e la deroga e' ancora aperta, cioe' c'e' qualcosa da chiudere",
        'D5C_MODE = "measure"' in s)
    for i, (name, old, new) in enumerate(EDITS, start=7):
        n = s.count(old)
        chk("%-2d ancora %s" % (i, name), n == 1, "occorrenze=%d" % n)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("10 il risultato e' Python valido", _parses(out))
        chk("11 D5C_MODE e' tornato a 'block'",
            'D5C_MODE = "block"' in out and 'D5C_MODE = "measure"' not in out)
        chk("12 il cancello confronta con la SOGLIA, non con zero",
            '_cl["n_clipped"] >= D5C_SOGLIA' in out
            and 'if _cl["n_clipped"] and D5C_MODE == "block"' not in out)
        chk("13 il messaggio d'arresto DICE quanto vale l'effetto",
            "generatori" in out.split("[FATAL] D5c")[1][:600]
            and "0.1574" in out.split("[FATAL] D5c")[1][:600])
        chk("14 la modalita' 'measure' resta possibile, non si cancella",
            'D5C_MODE == "measure"' in out and "[D5c misura]" in out)
        chk("15 lo stato si stampa SEMPRE, anche in block",
            "[D5c] modalita' 'block', soglia" in out)
        # La frase superata resta nella DOCSTRING che spiega perche' e' stata
        # tolta: e' storia, non un messaggio. Quel che conta e' che non venga
        # piu' STAMPATA. Il controllo cercava la stringa nel file e non nella
        # print, e sarebbe stato soddisfatto solo cancellando la spiegazione.
        _stampate = "\n".join(l for l in out.splitlines() if "print(" in l)
        chk("16 la frase superata non e' piu' STAMPATA (resta in docstring)",
            ("NON per un run che produce risultati" not in _stampate)
            and ("NON per un run che produce risultati" in out),
            "tolta dalle print, conservata come storia")
        chk("17 la derivazione della soglia e' nel codice, non a memoria",
            ("0.5 * 8.7 / 0.1574" in out) and ("record 36" in out)
            and ("NON e' un quantile" in out))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_d5c_chiusura_patch ===")
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
    bak = a.path + ".pre_d5cblock"
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
DA APPLICARE A RUN FERMI: il modulo e' in memoria mentre un run gira, quindi il
processo in corso non cambierebbe, ma una ripartenza rileggerebbe un file
diverso da quello con cui e' cominciato.

  python src\paper2_runner_fase3_mock.py selftest
  python src\paper2_runner_fase3_mock.py smoke --region NGC

Lo smoke deve stampare, in cima:
    [D5c] modalita' 'block', soglia 28 (record 36: meta' della SEM piu'
    piccola, 4.4 generatori).
e NON deve fermarsi: il massimo osservato su 4800 misure e' 9, contro 28.
Se si ferma, il conteggio e' cambiato regime e va guardato prima di proseguire.

Le righe '[D5c misura]' spariscono: in modalita' block non si stampano piu' i
conteggi sotto soglia. Il valore resta comunque in OGNI record, come i record
23 e 36 richiedono.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="D5c torna a bloccare, soglia 28, record 36")
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
