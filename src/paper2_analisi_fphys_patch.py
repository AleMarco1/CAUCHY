#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_analisi_fphys_patch.py — due incoerenze emerse dal run a --levels 1 0 2 3.

INCOERENZA 1 — il denominatore asimmetrico sopravvive nel ramo "adeguato"
  Il record 19 ha stabilito che 0.027 NON e' il range fisico: e' il lato piccolo
  di un intervallo asimmetrico. L'inviluppo misurato su dodici angoli
  (results/paper2/item12a_cosmo.jsonl) vale [0.973869, 1.040504] in convenzione
  pipeline e [0.961073, 1.026832] in convenzione standard, reciproci esatti,
  quindi la deviazione MASSIMA e' 0.0405 e 0.0389 rispettivamente.

  La patch precedente ha tolto il blocco che usava 0.027 nel ramo "modello
  INADEGUATO". Il ramo "modello ADEGUATO" e' rimasto com'era, e a k=2 si e'
  attivato per la prima volta: `within_physical_range` confronta |dF| = 2.2346
  con 0.027 invece che con 0.0389. Il verso della conclusione non cambia, il
  numero si'.

INCOERENZA 2 — a k=2,3 si sopprime l'esito E1-E4 ma si emette la §5.4
  A k=2 il codice stampa "|dF| <= 0.027 ? NO -> falsificazione pulita", cioe'
  emette una regola depositata, allo stesso livello dove abbiamo appena deciso
  di NON emettere l'esito perche' le soglie non sono registrate per k=2,3. O si
  sopprimono entrambe o la soppressione dell'esito non regge. Si sopprimono
  entrambe: i numeri si stampano, il verdetto no.

QUATTRO MODIFICHE
  A  F_PHYS resta 0.027 ma affiancato da F_PHYS_MAX_DEV = 0.0389 e
     dall'inviluppo misurato, con la provenienza in chiaro.
  B  required_F() decide su F_PHYS_MAX_DEV e riporta ENTRAMBI i rapporti.
  C  il ramo "adeguato" stampa il rapporto contro la deviazione massima, e
     dichiara quanto cambierebbe con l'altro estremo.
  D  a k non in (0,1) la §5.4 non si emette, come l'esito; e il controllo 9
     del selftest dell'analisi, che leggeva la chiave `physical_range` ora
     rinominata, andrebbe in KeyError: viene aggiornato qui, non lasciato rotto.

Uso:
    python src\\paper2_analisi_fphys_patch.py selftest
    python src\\paper2_analisi_fphys_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_analisi.py")

A_OLD = '''F_PHYS = 0.027                   # range fisico di F_AP'''

A_NEW = '''F_PHYS = 0.027                   # ATTENZIONE: NON e' il range fisico.
# Emendamento 19, 1 set 2026. 0.027 e' il LATO PICCOLO di un intervallo
# asimmetrico: e' +0.0268 arrotondato, l'estremo superiore in convenzione
# standard. L'inviluppo misurato su dodici angoli in (Om, w0),
# results/paper2/item12a_cosmo.jsonl, vale [0.973869, 1.040504] in convenzione
# pipeline e [0.961073, 1.026832] in convenzione standard — reciproci esatti,
# 1/1.040504 = 0.961073. La deviazione MASSIMA e' quindi 0.0405 e 0.0389.
# Ogni quantita' divisa per 0.027 sovrastima del 40-50%. F_PHYS resta definito
# perche' e' il numero DEPOSITATO al §5.2 e va citato come tale, ma le
# decisioni si prendono su F_PHYS_MAX_DEV.
F_PHYS_MAX_DEV = 0.0389          # max |F-1|, convenzione standard, misurato
F_PHYS_MAX_DEV_PIPELINE = 0.0405  # lo stesso in convenzione pipeline
F_PHYS_ENVELOPE = {"standard": (0.961073, 1.026832),
                   "pipeline": (0.973869, 1.040504),
                   "source": "results/paper2/item12a_cosmo.jsonl, 12 angoli",
                   "is_a_posterior": False}'''

B_OLD = '''    dF = -D_fid / a
    return {"F_required": 1.0 + dF, "delta_F": dF,
            "within_physical_range": bool(abs(dF) <= F_PHYS),
            "physical_range": F_PHYS}'''

B_NEW = '''    dF = -D_fid / a
    # La decisione si prende sulla deviazione MASSIMA, non sul lato piccolo
    # (emendamento 19). Si riportano entrambi i rapporti, perche' la loro
    # distanza e' essa stessa il punto: un numero che cambia del 44% a seconda
    # dell'estremo scelto non e' un risultato robusto.
    return {"F_required": 1.0 + dF, "delta_F": dF,
            "within_physical_range": bool(abs(dF) <= F_PHYS_MAX_DEV),
            "physical_range_used": F_PHYS_MAX_DEV,
            "physical_range_deposited": F_PHYS,
            "ratio_vs_max_dev": float(abs(dF) / F_PHYS_MAX_DEV),
            "ratio_vs_deposited": float(abs(dF) / F_PHYS),
            "envelope": F_PHYS_ENVELOPE}'''

C_OLD = '''        else:
            print(f"\\n  D(fid) = {D_fid:.1f}   F richiesto = {req['F_required']:.4f} "
                  f"(dF = {req['delta_F']:+.4f})")
            print(f"  |dF| <= {F_PHYS} ? {'SI' if req['within_physical_range'] else 'NO'}"
                  + ("" if req["within_physical_range"] else
                     "  -> l'AP NON puo' spiegare il deficit: falsificazione pulita"))
            if req["within_physical_range"] and esito == "E3":
                print("  -> condizione E4: il punto a F richiesto va MISURATO, "
                      "non estrapolato.")'''

C_NEW = '''        elif ki not in (0, 1):
            # Coerenza con la soppressione dell'esito: a k=2,3 non si emette
            # nemmeno la regola §5.4. Le soglie e il disegno sono registrati per
            # k=0,1; emettere una falsificazione qui sarebbe estendere la regola
            # esattamente come lo sarebbe emettere E1-E4.
            print(f"\\n  D(fid) = {D_fid:.1f}   dF = {req['delta_F']:+.4f}  "
                  f"({req['ratio_vs_max_dev']:.0f}x la deviazione massima "
                  f"{F_PHYS_MAX_DEV})")
            print("  §5.4: NON EMESSA — livello diagnostico, come l'esito. La "
                  "regola e' registrata per k=0,1; emetterla qui la "
                  "estenderebbe senza registrarla. Il numero si riporta, il "
                  "verdetto no.")
        else:
            print(f"\\n  D(fid) = {D_fid:.1f}   F richiesto = {req['F_required']:.4f} "
                  f"(dF = {req['delta_F']:+.4f})")
            print(f"  |dF| <= {F_PHYS_MAX_DEV} (deviazione MASSIMA misurata) ? "
                  f"{'SI' if req['within_physical_range'] else 'NO'}"
                  + ("" if req["within_physical_range"] else
                     "  -> l'AP NON puo' spiegare il deficit"))
            print(f"  rapporto: {req['ratio_vs_max_dev']:.0f}x la deviazione "
                  f"massima 0.0389, {req['ratio_vs_deposited']:.0f}x il valore "
                  f"depositato 0.027. La distanza fra i due e' il punto: il "
                  f"range e' ASIMMETRICO e 0.027 ne e' il lato piccolo "
                  f"(emendamento 19).")
            if req["within_physical_range"] and esito == "E3":
                print("  -> condizione E4: il punto a F richiesto va MISURATO, "
                      "non estrapolato.")'''

D_OLD = '''    expect("9. il range fisico e' quello depositato",
           r is not None and r["physical_range"] == 0.027
           and r["within_physical_range"] is False)'''

D_NEW = '''    expect("9. il range depositato e' citato, ma la decisione usa la "
           "deviazione MASSIMA (emendamento 19)",
           r is not None and r["physical_range_deposited"] == 0.027
           and r["physical_range_used"] == F_PHYS_MAX_DEV
           and r["within_physical_range"] is False)
    expect("9b. e i due rapporti differiscono del 44%, che e' il punto",
           r is not None
           and abs(r["ratio_vs_deposited"] / r["ratio_vs_max_dev"]
                   - F_PHYS_MAX_DEV / F_PHYS) < 1e-9,
           f"({r['ratio_vs_max_dev']:.0f}x contro {r['ratio_vs_deposited']:.0f}x)"
           if r else "")'''

EDITS = [
    ("A  F_PHYS affiancato dalla deviazione massima misurata", A_OLD, A_NEW),
    ("B  required_F decide sulla deviazione massima", B_OLD, B_NEW),
    ("C  il ramo adeguato riporta entrambi i rapporti, e tace a k=2,3", C_OLD, C_NEW),
    ("D  il selftest 9 non va piu' in KeyError", D_OLD, D_NEW),
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
    chk("1  analisi presente", ok, path)
    if not ok:
        return _report(checks)
    s = read(path)
    chk("2  la patch dei livelli e' gia' applicata (va prima)",
        ("--levels" in s) and ("emendamento 19" in s))
    chk("3  idempotenza: F_PHYS_MAX_DEV non c'e' ancora", "F_PHYS_MAX_DEV" not in s)
    for i, (name, old, new) in enumerate(EDITS, start=4):
        c = s.count(old)
        chk("%-2d ancora %s" % (i, name), c == 1, "occorrenze=%d" % c)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("8  il risultato e' Python valido", _parses(out))
        chk("8a il selftest dell'analisi non usa piu' la chiave rimossa",
            'r["physical_range"]' not in out)
        chk("8  F_PHYS depositato resta, e resta citabile come tale",
            "F_PHYS = 0.027" in out and "physical_range_deposited" in out)
        chk("9  la decisione si prende sulla deviazione MASSIMA",
            'abs(dF) <= F_PHYS_MAX_DEV' in out
            and 'abs(dF) <= F_PHYS)' not in out)
        chk("10 entrambi i rapporti sono riportati",
            ("ratio_vs_max_dev" in out) and ("ratio_vs_deposited" in out))
        chk("11 l'inviluppo misurato e' nel codice, con la sua provenienza",
            ("0.961073" in out) and ("1.040504" in out)
            and ("item12a_cosmo.jsonl" in out))
        chk("12 ed e' dichiarato che NON e' un posterior",
            '"is_a_posterior": False' in out)
        chk("13 a k=2,3 la §5.4 non e' emessa, come l'esito",
            ("§5.4: NON EMESSA" in out) and ("elif ki not in (0, 1):" in out))
        chk("14 a k=0,1 la §5.4 e' emessa come prima",
            ("condizione E4" in out) and ("F richiesto = " in out))

        # verifica numerica: i due rapporti a k=2 NGC, dF = +2.2346
        dF = 2.2346
        r_max, r_dep = dF / 0.0389, dF / 0.027
        chk("15 aritmetica: dF=2.2346 da' 57x contro 83x (44%% di differenza)",
            abs(r_max - 57.4) < 0.5 and abs(r_dep - 82.8) < 0.5
            and abs(r_dep / r_max - 1.441) < 0.01,
            "%.1f contro %.1f" % (r_max, r_dep))
        chk("16 e i due estremi dell'inviluppo sono reciproci esatti",
            abs(1.0 / 1.040504 - 0.961073) < 1e-6
            and abs(1.0 / 0.973869 - 1.026832) < 1e-6)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_analisi_fphys_patch ===")
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
    bak = a.path + ".pre_fphys"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print("\nPoi:")
    print("  python src\\paper2_fase3_analisi.py selftest")
    print("  python src\\paper2_fase3_analisi.py run --region NGC --levels 1 0 2 3")
    print("A k=1 e k=0 nulla deve cambiare. A k=2 la §5.4 non si emette piu'.")
    print("Il selftest dell'analisi deve dare PASS: il suo controllo 9 e' stato")
    print("aggiornato dalla modifica D, e ne e' stato aggiunto un 9b sui rapporti.")
    return 0


def main():
    p = argparse.ArgumentParser(description="denominatore asimmetrico e coerenza dei livelli")
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
