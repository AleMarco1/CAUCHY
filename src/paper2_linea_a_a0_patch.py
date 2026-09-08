#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_linea_a_a0_patch.py — aggiunge A0 e A0m a LINE_A. Record 30.

UNA MODIFICA SOLA
  LINE_A = [("A1", 0.9725), ("A1m", 1.0275), ("A3", 1.0406), ("A3m", 0.9594)]
  diventa
  ... piu' ("A0", 0.981373) e ("A0m", 1.018627)

  Nient'altro. `c`, `L`, il box e il resto li DERIVA deform() da alpha_iso, come
  per ogni altro punto: il record 28 vieta di scriverli altrove.

PERCHE' UNA TERZA AMPIEZZA
  Il record 29 misura il residuo del blocco A a 0.0275 e 0.0406 e trova che in
  NGC si CONTRAE al crescere della deformazione, in entrambe le parti. Ma il
  residuo ad alpha = 1 e' ZERO ESATTO - alpha = 1 E' il fiduciale - quindi
  vanish a 0, sale, e a 0.0275-0.0406 sta gia' scendendo: c'e' un MASSIMO in
  (0, 0.0406). Due ampiezze danno un rapporto, tre danno una forma, e la terza
  dice DOVE sta il massimo, che e' la scala del meccanismo.

  a0 = 0.0275^2 / 0.0406 = 0.018627: la continuazione GEOMETRICA verso il basso,
  cosi' le tre ampiezze sono equispaziate in log a rapporto 1.476364, che e' la
  spaziatura ottima per stimare una potenza.

  Verso il basso NON per la leva: ln(a_max/a_min) vale 0.7792 scendendo a
  0.018627 e 0.7802 salendo a 0.0600, e non discrimina. Per due altre ragioni:
  0.0600 metterebbe entrambi gli alpha FUORI dal range fisico, e il vincolo
  residuo(0) = 0 morde a piccola ampiezza, dove il massimo deve stare.

  Entrambi gli alpha, 0.981373 e 1.018627, sono DENTRO [0.9725, 1.0406]: questa
  coppia non ha bisogno della dichiarazione di fuori-range che A3m ha richiesto.

LA PREDIZIONE QUANTITATIVA, dal record 30
  La potenza stimata sulle due ampiezze note ha esponenti -1.51, -2.16, -2.60 e
  continuata a a0 predice |pari| = 32.4, 75.4, 15.1 contro 18.0, 32.5, 5.5
  misurati a 0.0275. Ma una potenza negativa diverge per a -> 0 e il residuo
  deve tornare a zero: quella predizione DEVE fallire da qualche parte, e la
  domanda e' se ha gia' fallito a 0.018627.

I NOMI
  A0 (compressione) e A0m (espansione), stessa convenzione di A1/A1m. Non A2:
  sulla linea B il 3 e' saltato perche' B3 e' il fiduciale, quindi A2 e'
  riservato per la stessa convenzione.

COSA QUESTA PATCH NON FA
  Nessun cancello sul gauge `derived`: li' una dilatazione pura e' l'IDENTITA'
  per costruzione, e un controllo che l'algebra garantisce non e' un cancello
  (record 28). Il selftest verifica il CABLAGGIO, che puo' fallire. E i residui
  da decomporre vivono in `regauged`.

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
A0C, A0E = 0.981373, 1.018627          # compressione, espansione
A0 = 0.018627                          # |alpha - 1| della terza ampiezza

OLD = '''LINE_A = [("A1", 0.9725), ("A1m", 1.0275), ("A3", 1.0406), ("A3m", 0.9594)]'''

NEW = '''# A0 e A0m: emendamento 30. TERZA ampiezza, |alpha - 1| = 0.018627, che e' la
# continuazione GEOMETRICA verso il basso: 0.0275^2/0.0406, cosi' le tre
# ampiezze sono equispaziate in log a rapporto 1.476364.
# Serve perche' il residuo ad alpha = 1 e' ZERO ESATTO (alpha = 1 E' il
# fiduciale) e il record 29 lo misura in DISCESA fra 0.0275 e 0.0406: c'e'
# quindi un MASSIMO in (0, 0.0406), e due ampiezze non dicono dove. La terza
# si'. La potenza stimata sulle due note predice |pari| = 32.4/75.4/15.1 a
# questa ampiezza contro 18.0/32.5/5.5 a 0.0275; ma non puo' divergere per
# a -> 0, quindi quella predizione deve fallire e la domanda e' se lo fa gia' qui.
# Verso il basso NON per la leva (0.7792 contro 0.7802: non discrimina) ma
# perche' 0.0600 metterebbe entrambi gli alpha fuori range, e perche' il
# vincolo residuo(0)=0 morde a piccola ampiezza.
# Entrambi DENTRO [0.9725, 1.0406]: nessuna dichiarazione di fuori-range.
LINE_A = [("A0", 0.981373), ("A1", 0.9725), ("A1m", 1.0275),
          ("A3", 1.0406), ("A3m", 0.9594), ("A0m", 1.018627)]'''


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
    chk("1  la coppia nuova e' simmetrica esattamente",
        abs(abs(A0E - 1) - abs(A0C - 1)) < 1e-9,
        "scarto %.2e" % abs(abs(A0E - 1) - abs(A0C - 1)))
    r = abs(A3 - 1) / abs(A1 - 1)
    # a0 e' dichiarato a SEI cifre nel record 30, gia' appeso: i passi in log
    # sono quindi uguali a meno di quell'arrotondamento, ~1.2e-05 in rapporto,
    # non esattamente. Si verifica quel che e' vero, non quel che suona meglio.
    chk("2  a0 e' la continuazione geometrica, entro l'arrotondamento dichiarato",
        abs(A0 - abs(A1 - 1) / r) < 1e-6
        and abs(abs(A1 - 1) / A0 - r) < 1e-4,
        "passi %.6f e %.6f, scarto %.1e" % (abs(A1 - 1) / A0, r,
                                            abs(abs(A1 - 1) / A0 - r)))
    import math
    chk("3  la leva NON discrimina, come il record 30 dichiara",
        abs(math.log(abs(A3 - 1) / A0) - 0.7792) < 5e-4
        and abs(math.log(0.0600 / abs(A1 - 1)) - 0.7802) < 5e-4)
    chk("4  entrambi i nuovi alpha DENTRO il range fisico",
        (A1 <= A0C <= A3) and (A1 <= A0E <= A3))

    ok = os.path.isfile(path)
    chk("5  paper2_item13a_15a presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("6  prerequisito: A1m e A3m ci sono gia' (record 27-28)",
        ("A1m" in s) and ("A3m" in s))
    chk("6b idempotenza: A0 non c'e' ancora", '"A0"' not in s)
    chk("7  ancora LINE_A unica", s.count(OLD) == 1, "occorrenze=%d" % s.count(OLD))

    if all(c[1] for c in checks):
        out = s.replace(OLD, NEW, 1)
        import ast
        try:
            ast.parse(out)
            chk("8  il risultato e' Python valido", True)
        except SyntaxError as exc:
            chk("8  il risultato e' Python valido", False, str(exc))
        # LINE_A si valuta davvero, non si legge come stringa. Ora sta su PIU'
        # righe, quindi si estrae con ast e non prendendo la riga dopo "=":
        # quell'estrattore prendeva mezza lista e falliva con "'[' was never
        # closed", che e' un difetto dell'estrattore e non del contenuto.
        ns = {}
        _assegn = next(n for n in ast.parse(out).body
                       if isinstance(n, ast.Assign)
                       and any(getattr(t, "id", "") == "LINE_A" for t in n.targets))
        exec(compile(ast.Module(body=[_assegn], type_ignores=[]),
                     "<line_a>", "exec"), ns)
        la = ns["LINE_A"]
        chk("9  LINE_A valutata: sei punti, nomi e alpha giusti",
            la == [("A0", 0.981373), ("A1", 0.9725), ("A1m", 1.0275),
                   ("A3", 1.0406), ("A3m", 0.9594), ("A0m", 1.018627)], repr(la))
        chk("10 i QUATTRO esistenti non sono toccati",
            [t for t in la if t[0] in ("A1", "A1m", "A3", "A3m")]
            == [("A1", 0.9725), ("A1m", 1.0275),
                ("A3", 1.0406), ("A3m", 0.9594)])
        chk("11 nessun nome collide, e A2 resta libero",
            len({n for n, _ in la}) == 6 and "A2" not in {n for n, _ in la})
        chk("12 TRE coppie simmetriche, ognuna a due a due",
            sorted(round(abs(a - 1), 6) for _, a in la) ==
            [0.018627, 0.018627, 0.0275, 0.0275, 0.0406, 0.0406])
        chk("13 e le tre ampiezze sono equispaziate in log (entro 1.2e-05)",
            abs((0.0275 / 0.018627) - (0.0406 / 0.0275)) < 1e-4)
        chk("14 solo alpha_iso: nessuna tupla porta c o L",
            all(len(t) == 2 for t in la))
        chk("15 il commento dichiara il vincolo residuo(1)=0 e la predizione",
            ("ZERO ESATTO" in out) and ("32.4/75.4/15.1" in out))
        chk("16 e dichiara che la leva NON discrimina, senza vantarla",
            ("non discrimina" in out) and ("0.7792" in out))
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_linea_a_a0_patch ===")
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
    bak = a.path + ".pre_a0"
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

  python src\paper2_runner_fase3.py run --region NGC --points A0 A0m ^
      --out results\paper2\fase3.jsonl
  python src\paper2_runner_fase3.py run --region SGC --points A0 A0m ^
      --out results\paper2\fase3.jsonl

REGISTRO: questi vanno in fase3.jsonl, con gli altri punti di griglia. Non e'
un diagnostico come la maschera-intersezione: sono punti della griglia, aggiunti
per emendamento come lo fu B6, e appartengono al registro principale.

DA GUARDARE:
  - in gauge `derived` i due nuovi punti devono dare il FIDUCIALE esatto,
    23790 / 28256 in NGC e 12011 / 15122 in SGC. Non e' un cancello: e'
    algebra (record 28). Ma se NON lo danno, il punto e' malformato.
  - in gauge `regauged` danno i residui. La domanda e' UNA: |pari(a0)| e'
    MINORE o MAGGIORE di |pari(0.0275)|, cioe' 18.0 / 32.5 / 5.5 / 8.0?
    Minore -> il massimo sta fra 0.0186 e 0.0406. Maggiore -> sta sotto
    0.0186 e la struttura e' su una scala piu' fine del 2% in alpha.""")
    return 0


def main():
    p = argparse.ArgumentParser(description="A0 e A0m in LINE_A, record 30")
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
