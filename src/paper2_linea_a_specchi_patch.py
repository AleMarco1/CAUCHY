#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_linea_a_specchi_patch.py — aggiunge A1m e A3m a LINE_A. Record 27 e 28.

UNA MODIFICA SOLA
  LINE_A = [("A1", 0.9725), ("A3", 1.0406)]
  diventa
  LINE_A = [("A1", 0.9725), ("A1m", 1.0275), ("A3", 1.0406), ("A3m", 0.9594)]

  Nient'altro. `c`, `L`, il box e il resto li DERIVA deform() da alpha_iso, come
  per ogni altro punto: il record 28 vieta di scriverli altrove.

PERCHE' DUE PUNTI, E PERCHE' QUESTI
  A1 e A3 stanno a |alpha - 1| = 0.0275 e 0.0406, cioe' a distanze DIVERSE da 1.
  Con due punti asimmetrici pari e dispari non si separano: una risposta
  puramente pari e quadratica darebbe A3/A1 = (0.0406/0.0275)^2 = 2.18, che si
  legge come un 37% di dispari che non c'e'. I due specchi costruiscono due
  coppie SIMMETRICHE, e le due ampiezze in rapporto 1.4764 distinguono un
  dispari lineare (rapporto atteso 1.476) da un gradino costante (1.000).

  A3m = 0.9594 cade sotto il range fisico isotropo [0.9725, 1.0406]. Sul blocco A
  il segnale e' zero PER TEOREMA a qualunque alpha, quindi un test nullo fuori
  range e' lecito. Dichiarato nel record 27, ripetuto qui.

I NOMI
  A1m e A3m, non A2 e A4: sulla linea B il 3 e' saltato perche' B3 e' il
  fiduciale, quindi per la stessa convenzione A2 e' riservato e riusarlo
  creerebbe una collisione silenziosa.

COSA QUESTA PATCH NON FA, E IL RECORD 28 SPIEGA PERCHE'
  Non aggiunge un cancello sul gauge `derived`. Li' una dilatazione pura e'
  l'IDENTITA' per costruzione - A*E + 2p = E + 2p da' A = 1 esatto - quindi un
  controllo che l'algebra garantisce non e' un cancello. Il selftest verifica il
  CABLAGGIO: che i punti arrivino nel piano, con l'alpha giusto, nel blocco
  giusto. Quello puo' fallire.

  E i residui da decomporre vivono nel gauge `regauged`, non in `derived` dove
  sono zero per costruzione (record 28).

Uso:
    python src\\paper2_linea_a_specchi_patch.py selftest
    python src\\paper2_linea_a_specchi_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_item13a_15a.py")

A1, A3 = 0.9725, 1.0406
A1M, A3M = 1.0275, 0.9594

OLD = '''LINE_A = [("A1", 0.9725), ("A3", 1.0406)]'''

NEW = '''# A1m e A3m: emendamenti 27 e 28. Specchi ESATTI di A1 e A3 attorno a 1, cioe'
# 1 + 0.0275 e 1 - 0.0406. Servono perche' A1 e A3 stanno a distanze DIVERSE da
# 1 (0.0275 contro 0.0406, rapporto 1.4764) e con due punti asimmetrici pari e
# dispari NON si separano: una risposta puramente pari e quadratica darebbe
# A3/A1 = 1.4764^2 = 2.18, che si legge come un 37% di dispari inesistente.
# Con due coppie simmetriche la decomposizione e' pulita, e le due ampiezze
# distinguono un dispari LINEARE (rapporto atteso 1.476) da un GRADINO (1.000).
# A3m = 0.9594 e' sotto il range fisico isotropo [0.9725, 1.0406]: sul blocco A
# il segnale e' zero PER TEOREMA a qualunque alpha, quindi il test nullo resta
# valido. Dichiarato, non nascosto.
# I nomi non sono A2 e A4: sulla linea B il 3 e' saltato perche' B3 e' il
# fiduciale, quindi A2 e' riservato per la stessa convenzione.
# Qui c'e' SOLO alpha_iso: c, L e il box li deriva deform(), e il record 28
# vieta di scriverli in un secondo posto.
LINE_A = [("A1", 0.9725), ("A1m", 1.0275), ("A3", 1.0406), ("A3m", 0.9594)]'''


def fail(msg):
    print("[FATAL] " + msg)
    sys.exit(2)


def read(path):
    with open(path, "r", encoding="utf-8", newline="") as f:
        return f.read()


def selftest(path):
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    # 1-4: l'aritmetica del disegno, verificata e non asserita
    chk("1  A1m specchia A1 esattamente",
        abs(abs(A1M - 1) - abs(A1 - 1)) < 1e-12,
        "scarto %.2e" % abs(abs(A1M - 1) - abs(A1 - 1)))
    chk("2  A3m specchia A3 esattamente",
        abs(abs(A3M - 1) - abs(A3 - 1)) < 1e-12,
        "scarto %.2e" % abs(abs(A3M - 1) - abs(A3 - 1)))
    r = abs(A3 - 1) / abs(A1 - 1)
    chk("3  rapporto delle ampiezze e confondente pari",
        abs(r - 1.4764) < 5e-4 and abs(r * r - 2.18) < 0.01,
        "r=%.4f  r^2=%.4f" % (r, r * r))
    chk("4  A1m dentro il range fisico, A3m fuori: come dichiarato",
        (A1 <= A1M <= A3) and not (A1 <= A3M <= A3))

    ok = os.path.isfile(path)
    chk("5  paper2_item13a_15a presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("6  idempotenza: A1m non c'e' ancora", "A1m" not in s)
    chk("7  ancora LINE_A unica", s.count(OLD) == 1, "occorrenze=%d" % s.count(OLD))

    if all(c[1] for c in checks):
        out = s.replace(OLD, NEW, 1)
        import ast
        try:
            ast.parse(out)
            chk("8  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("8  il risultato e' Python valido", False, str(exc))
        # LINE_A si valuta davvero, non si legge come stringa
        ns = {}
        exec(compile(ast.parse(out).body[0] if False else
                     "LINE_A = " + out.split("LINE_A = ")[1].split("\n")[0],
                     "<line_a>", "exec"), ns)
        la = ns["LINE_A"]
        chk("9  LINE_A valutata: quattro punti, nomi e alpha giusti",
            la == [("A1", 0.9725), ("A1m", 1.0275),
                   ("A3", 1.0406), ("A3m", 0.9594)], repr(la))
        chk("10 i due esistenti NON sono toccati",
            la[0] == ("A1", 0.9725) and la[2] == ("A3", 1.0406))
        chk("11 nessun nome collide, e A2 resta libero",
            len({n for n, _ in la}) == 4 and "A2" not in {n for n, _ in la})
        chk("12 e le coppie simmetriche esistono davvero nella lista",
            sorted(round(abs(a - 1), 6) for _, a in la) ==
            [0.0275, 0.0275, 0.0406, 0.0406])
        chk("13 solo alpha_iso: nessuna tupla porta c o L",
            all(len(t) == 2 for t in la))
        chk("14 il commento dichiara A3m fuori range, non lo tace",
            "sotto il range fisico" in out and "PER TEOREMA" in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_linea_a_specchi_patch ===")
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
    out = s.replace(OLD, NEW, 1)
    diff = list(difflib.unified_diff(s.splitlines(True), out.splitlines(True),
                                     fromfile="prima", tofile="dopo", n=2))
    print("\n=== DIFF (%d righe) ===" % len(diff))
    sys.stdout.write("".join(diff))
    print("righe: %d -> %d" % (s.count("\n"), out.count("\n")))
    if not a.write:
        print("[DRY-RUN] nulla scritto. Rilancia con --write.")
        return 0
    bak = a.path + ".pre_specchi"
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
  python src\paper2_runner_fase3.py selftest
  python -c "import sys; sys.path.insert(0,'src'); import paper2_item13a_15a as I; print(I.LINE_A)"

Il secondo deve stampare quattro coppie. Se ne stampa due, la patch non e'
sul modulo che il runner importa.

POI, otto run deterministici, circa sei minuti in tutto. I punti gia' fatti
si saltano da soli: la chiave di ripartenza e' (punto, gauge, config_hash).

  python src\paper2_runner_fase3.py run --region NGC --points A1m A3m ^
      --out results\paper2\fase3.jsonl
  python src\paper2_runner_fase3.py run --region SGC --points A1m A3m ^
      --out results\paper2\fase3.jsonl

REGISTRO: questi vanno in fase3.jsonl, con gli altri punti di griglia. Non e'
un diagnostico come la maschera-intersezione: sono punti della griglia, aggiunti
per emendamento come lo fu B6, e appartengono al registro principale.

DA GUARDARE:
  - in gauge `derived` i due nuovi punti devono dare il FIDUCIALE esatto,
    23790 / 28256 in NGC e 12011 / 15122 in SGC. Non e' un cancello: e'
    algebra (record 28). Ma se NON lo danno, il punto e' malformato.
  - in gauge `regauged` danno i residui da decomporre. E' li' che vivono.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="A1m e A3m in LINE_A, record 27 e 28")
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
