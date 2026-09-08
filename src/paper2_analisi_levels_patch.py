#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_analisi_levels_patch.py — aggiunge --levels a paper2_fase3_analisi.py e
ritira dal codice l'estrapolazione che l'emendamento 19 ha ritirato dal registro.

PERCHE' LE DUE COSE INSIEME
  Il ciclo dei livelli emette, per ogni livello, il blocco "Ordine di grandezza,
  indipendente dalla forma: ... 247 volte il range fisico 0.027". Quel blocco e'
  stato RITIRATO dal record 19 stamattina. Aggiungere k=2 e k=3 senza toccarlo
  significherebbe emettere l'affermazione ritirata a DUE LIVELLI IN PIU', e
  scriverla in `fase3_analisi.jsonl` se si usa --out. Un record di registro che
  il codice contraddice e' peggio di nessun record.

QUATTRO MODIFICHE
  A  desi_side(): legge la scala di erosione `ladder` invece dei due campi
     piatti, con un CANCELLO che verifica che ladder['0']['N_H1'] == N_H1_k0 e
     ladder['1']['N_H1'] == N_H1. Se non concordano, il record e' incoerente e
     si ferma. `desi[p][ki]` continua a funzionare: restituisco un dizionario a
     chiavi intere, non una tupla.
  B  cmd_run(): il ciclo sui livelli diventa parametrico.
  C  main(): --levels, default "1 0", cioe' il comportamento di oggi.
  D  il blocco dell'estrapolazione e' sostituito dall'affermazione in-range.

UNA DECISIONE, DICHIARATA QUI E REVERSIBILE
  Ai livelli k=2 e k=3 NON si emette l'esito E1-E4. Il protocollo depositato
  dichiara k=1 primario e k=0 in parallelo; le soglie di rilevanza (390 e 206)
  sono l'1.1% di un deficit misurato a QUEI livelli, e a k=2,3 il deficit vale
  altro. Emettere un esito con soglie tarate altrove estenderebbe in silenzio la
  regola depositata. I numeri si stampano tutti; il verdetto no, e il codice
  dice perche'. Se si vuole un esito anche li', va registrata una regola con le
  sue soglie, prima del run.

Uso:
    python src\\paper2_analisi_levels_patch.py selftest
    python src\\paper2_analisi_levels_patch.py apply
    python src\\paper2_analisi_levels_patch.py apply --write
"""

from __future__ import annotations

import argparse
import difflib
import os
import sys

DEFAULT_PATH = os.path.join("src", "paper2_fase3_analisi.py")

A_OLD = '''    out = {}
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region:
            continue
        p = r.get("point")
        if r.get("gate") == "d3" or r.get("gauge") == "fid":
            out["FID"] = (r["N_H1_k0"], r["N_H1"])
        elif r.get("gauge") == gauge and p:
            out[p] = (r["N_H1_k0"], r["N_H1"])
    return out'''

A_NEW = '''    out = {}
    for l in Path(path).read_text(encoding="utf-8").splitlines():
        if not l.strip():
            continue
        r = json.loads(l)
        if r.get("region") != region:
            continue
        p = r.get("point")
        # La scala di erosione completa sta in `ladder`: {'0','1','2','3'} con
        # N_H1, b1_peak, n_voxels, retained, wbar. I due campi piatti N_H1_k0 e
        # N_H1 sono k=0 e k=1 e restano la fonte se il ladder manca.
        lad = r.get("ladder") or {}
        vals = {int(kk): int(vv["N_H1"]) for kk, vv in lad.items()
                if isinstance(vv, dict) and "N_H1" in vv}
        if vals:
            # CANCELLO: la scala e i campi piatti devono concordare. Se non lo
            # fanno il record e' incoerente e non si indovina quale sia giusto.
            for kk, flat in ((0, r.get("N_H1_k0")), (1, r.get("N_H1"))):
                if flat is not None and kk in vals and int(flat) != vals[kk]:
                    sys.exit(f"[FATAL] {region}/{p or 'FID'}: ladder['{kk}'] = "
                             f"{vals[kk]} contro il campo piatto {int(flat)}. "
                             f"Record incoerente, non si sceglie.")
        else:
            vals = {0: r["N_H1_k0"], 1: r["N_H1"]}
        if r.get("gate") == "d3" or r.get("gauge") == "fid":
            out["FID"] = vals
        elif r.get("gauge") == gauge and p:
            out[p] = vals
    return out'''

B_OLD = '''    for ki, lab in ((1, "k=1  PRIMARIO"), (0, "k=0  parallelo per v1")):'''

B_NEW = '''    levels = getattr(a, "levels", None) or [1, 0]
    _LAB = {1: "k=1  PRIMARIO", 0: "k=0  parallelo per v1",
            2: "k=2  DIAGNOSTICO (nessun esito: vedi sotto)",
            3: "k=3  DIAGNOSTICO (nessun esito: vedi sotto)"}
    missing_lv = [ki for ki in levels
                  if any(ki not in desi[p] for p in desi)]
    if missing_lv:
        sys.exit(f"[FATAL] il lato dati non ha i livelli {missing_lv}: "
                 f"la scala di erosione dei record del 3.1 non li contiene.")
    for ki, lab in ((ki, _LAB.get(ki, f"k={ki}")) for ki in levels):'''

C_OLD = '''    q.add_argument("--out", default=None)
    a = p.parse_args()
    return (cmd_selftest if a.cmd == "selftest" else cmd_run)(a)'''

C_NEW = '''    q.add_argument("--out", default=None)
    q.add_argument("--levels", type=int, nargs="+", default=[1, 0],
                   choices=[0, 1, 2, 3],
                   help="livelli di erosione da analizzare. Default 1 0, cioe' "
                        "il comportamento depositato. A k=2 e 3 i numeri si "
                        "stampano ma NON si emette l'esito E1-E4: le soglie "
                        "depositate sono tarate sul deficit a k=0,1.")
    a = p.parse_args()
    return (cmd_selftest if a.cmd == "selftest" else cmd_run)(a)'''

D_OLD = '''        esito, testo = classify(dd_abs, reg)
        L["DD_max_B5_B1"] = m
        L["outcome"] = {"code": esito, "meaning": testo}
        print(f"  DD_max (B5 - B1) = {m['estimate']:+8.1f}  "
              f"sem {m['sem']:5.1f}  IC95 [{m['ci95'][0]:+.1f}, {m['ci95'][1]:+.1f}]")
        print(f"  ESITO: {esito} — {testo}")'''

D_NEW = '''        print(f"  DD_max (B5 - B1) = {m['estimate']:+8.1f}  "
              f"sem {m['sem']:5.1f}  IC95 [{m['ci95'][0]:+.1f}, {m['ci95'][1]:+.1f}]")
        L["DD_max_B5_B1"] = m
        if ki in (0, 1):
            esito, testo = classify(dd_abs, reg)
            L["outcome"] = {"code": esito, "meaning": testo}
            print(f"  ESITO: {esito} — {testo}")
        else:
            # Le soglie 53 / 390 / 206 sono tarate sul deficit a k=0 e k=1. A
            # k=2 e k=3 il deficit vale altro, quindi un esito calcolato con
            # quelle soglie estenderebbe in silenzio la regola depositata.
            esito = None
            L["outcome"] = {"code": None, "meaning":
                            "nessun esito: livello diagnostico, soglie non "
                            "registrate per k=%d" % ki}
            print("  ESITO: NON EMESSO — livello diagnostico. Le soglie "
                  "depositate (53, %d) sono tarate sul deficit a k=0,1; "
                  "emetterle qui estenderebbe la regola senza registrarla."
                  % RELEVANCE[reg])'''

E_OLD = '''                # L'ordine di grandezza NON dipende dal modello: si riporta a
                # parte, perche' e' il risultato piu' forte della Fase 3.
                slope = fit["a"]          # NON `a`: e' il namespace di argparse
                if slope:
                    dF = -D_fid / slope
                    print(f"  Ordine di grandezza, indipendente dalla forma: con "
                          f"una pendenza di {slope:+.0f} gen per unita' di F servirebbe "
                          f"dF = {dF:+.2f}, cioe' {abs(dF)/F_PHYS:.0f} volte il "
                          f"range fisico {F_PHYS}. L'AP non puo' spiegare il "
                          f"deficit, e questa conclusione non dipende dal fit.")'''

E_NEW = '''                # RITIRATO dall'emendamento 19, 1 set 2026. L'estrapolazione
                # invertiva un coefficiente della famiglia quadratica che il
                # fit dichiara inadeguata tre righe sopra; il denominatore
                # F_PHYS = 0.027 e' il lato PICCOLO di un intervallo
                # asimmetrico la cui deviazione massima vale 0.0389 in
                # convenzione standard e 0.0405 in convenzione pipeline; e a
                # dF ~ 6.7 il termine quadratico domina il lineare di ~5e4,
                # quindi "non dipende da un fattore due" e' falso.
                print("  L'ordine di grandezza per estrapolazione e' RITIRATO "
                      "(emendamento 19): inverte un coefficiente di una "
                      "famiglia dichiarata inadeguata, e 0.027 non e' il range "
                      "fisico ma il suo lato piccolo (max 0.0389).")
                print("  Al suo posto, l'affermazione IN-RANGE: su tutto "
                      "l'insieme campionato, B6 incluso, D si muove al piu' di "
                      "172.5 generatori, cioe' il 2.0-4.8% del deficit, e il "
                      "rango empirico resta 1/201 in ogni punto della griglia. "
                      "Non si estrapola nulla e non serve un modello.")'''

EDITS = [
    ("A  desi_side legge il ladder, con cancello di coerenza", A_OLD, A_NEW),
    ("B  ciclo sui livelli parametrico", B_OLD, B_NEW),
    ("C  --levels in main()", C_OLD, C_NEW),
    ("D  nessun esito E1-E4 a k=2,3", D_OLD, D_NEW),
    ("E  estrapolazione ritirata (emendamento 19)", E_OLD, E_NEW),
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
    chk("2  la patch di fusione e' gia' applicata (va prima)",
        'd["points"].setdefault(_p, {}).update(_v)' in s)
    chk("3  idempotenza: --levels non c'e' ancora",
        ("--levels" not in s) and ("emendamento 19" not in s))
    for i, (name, old, new) in enumerate(EDITS, start=4):
        c = s.count(old)
        chk("%-2d ancora %s" % (i, name), c == 1, "occorrenze=%d" % c)

    if all(c[1] for c in checks):
        out = apply_all(s)
        chk("9  il risultato e' Python valido", _parses(out))
        chk("10 desi[p][ki] resta indicizzabile: dizionario a chiavi INTERE",
            "int(kk): int(vv[\"N_H1\"])" in out and "out[p] = vals" in out)
        chk("11 il cancello di coerenza ladder/campi piatti c'e' ed e' fatale",
            "Record incoerente, non si sceglie" in out
            and "sys.exit" in out.split("lad = r.get")[1][:900])
        chk("12 a k=2,3 l'esito NON e' emesso, e il codice dice perche'",
            "ESITO: NON EMESSO" in out and "estenderebbe la regola" in out)
        chk("13 a k=0,1 l'esito e' emesso come prima",
            'if ki in (0, 1):' in out and 'classify(dd_abs, reg)' in out)
        chk("14 l'estrapolazione ritirata non e' piu' stampata",
            ("Ordine di grandezza, indipendente dalla forma" not in out)
            and ("volte il range fisico" not in out))
        chk("15 e al suo posto c'e' l'affermazione in-range del record 19",
            ("172.5 generatori" in out) and ("1/201" in out)
            and ("emendamento 19" in out))
        chk("16 il default resta 1 0: il comportamento di oggi non cambia",
            "default=[1, 0]" in out)
        chk("17 il livello mancante nel lato dati ferma invece di indovinare",
            "il lato dati non ha i livelli" in out)
        chk("18 F_PHYS resta definito (serve altrove) ma non piu' come range",
            "F_PHYS = 0.027" in out)
    return _report(checks)


def _report(checks):
    print("=== SELFTEST paper2_analisi_levels_patch ===")
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
    bak = a.path + ".pre_levels"
    if not os.path.exists(bak):
        with open(bak, "w", encoding="utf-8", newline="") as f:
            f.write(s)
        print("[backup] %s" % bak)
    tmp = a.path + ".tmp"
    with open(tmp, "w", encoding="utf-8", newline="") as f:
        f.write(out)
    os.replace(tmp, a.path)
    print("[OK] %s aggiornato" % a.path)
    print("\nPoi, nell'ordine:")
    print("  python src\\paper2_fase3_analisi.py selftest")
    print("  python src\\paper2_fase3_analisi.py run --region NGC")
    print("  python src\\paper2_fase3_analisi.py run --region NGC --levels 1 0 2 3")
    print("Il secondo deve ancora dare -98.3 e -114.0: il default non cambia.")
    return 0


def main():
    p = argparse.ArgumentParser(description="--levels e ritiro dell'estrapolazione")
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
