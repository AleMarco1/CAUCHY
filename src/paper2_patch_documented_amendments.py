#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_documented_amendments.py — incrementa DOCUMENTED_AMENDMENTS.

Sostituisce UNA riga di costante, a livello di byte, con asserzione sull'ancora:
se l'ancora non e' unica, o se il valore vecchio non e' quello dichiarato, il
patcher RIFIUTA e non tocca il file. Le terminazioni di riga sono preservate
perche' il file e' letto e riscritto in binario.

Uso:
    python paper2_patch_documented_amendments.py selftest
    python paper2_patch_documented_amendments.py apply --file src\\paper2_freeze_verify.py --da 48 --a 49 --dry-run
    python paper2_patch_documented_amendments.py apply --file src\\paper2_freeze_verify.py --da 48 --a 49
"""

import argparse
import json
import os
import re
import shutil
import sys
import tempfile
import time

NOME = "DOCUMENTED_AMENDMENTS"
# Il \r? finale serve: senza, su file CRLF l'ancora non viene trovata.
ANCORA = re.compile(rb"(?m)^(" + NOME.encode() + rb"[ \t]*=[ \t]*)(\d+)([ \t]*\r?)$")


class Rifiuto(Exception):
    pass


def leggi(path):
    with open(path, "rb") as fh:
        return fh.read()


def trova_ancora(raw):
    """Restituisce (match, valore_corrente). Rifiuta se le ancore non sono esattamente una."""
    matches = list(ANCORA.finditer(raw))
    if len(matches) == 0:
        raise Rifiuto(f"ancora assente: nessuna riga '{NOME} = <numero>'")
    if len(matches) > 1:
        righe = [raw[:m.start()].count(b"\n") + 1 for m in matches]
        raise Rifiuto(f"ancora non unica: {len(matches)} occorrenze alle righe {righe}")
    m = matches[0]
    return m, int(m.group(2))


def patch(raw, da, a):
    m, corrente = trova_ancora(raw)
    if corrente == a:
        raise Rifiuto(f"gia' applicato: {NOME} vale gia' {a}")
    if corrente != da:
        raise Rifiuto(f"valore vecchio inatteso: atteso {da}, trovato {corrente}")
    nuovo = raw[:m.start()] + m.group(1) + str(a).encode() + m.group(3) + raw[m.end():]
    return nuovo, corrente


def conta_ledger(path):
    """Numero di record del ledger: righe non vuote e JSON valido."""
    with open(path, "rb") as fh:
        raw = fh.read()
    n, malformate = 0, []
    for i, riga in enumerate(raw.decode("utf-8").split("\n"), 1):
        if not riga.strip():
            continue
        try:
            json.loads(riga)
        except Exception:
            malformate.append(i)
        n += 1
    return n, malformate


def cmd_apply(args):
    path = args.file
    if not os.path.isfile(path):
        print(f"RIFIUTO: file inesistente: {path}")
        return 2

    # Il cancello che mancava: la costante dichiara quanti record ci sono, quindi non si
    # porta a N se sul disco non ce ne sono N. Senza questo, un append fallito e un patcher
    # riuscito lasciano la costante avanti al file - accaduto il 7 set 2026.
    if args.ledger:
        if not os.path.isfile(args.ledger):
            print(f"RIFIUTO: ledger inesistente: {args.ledger}")
            return 2
        n_led, malformate = conta_ledger(args.ledger)
        if malformate:
            print(f"RIFIUTO: ledger con righe malformate: {malformate}")
            return 2
        if n_led != args.a:
            print(f"RIFIUTO: il ledger ha {n_led} record, la costante andrebbe a {args.a}. "
                  f"{'Manca un append.' if n_led < args.a else 'Manca un incremento.'}")
            return 2
        print(f"ledger  : {os.path.abspath(args.ledger)}  record {n_led}  concorda con --a")
    else:
        print("ledger  : NON verificato (--ledger non passato)")

    raw = leggi(path)
    try:
        nuovo, corrente = patch(raw, args.da, args.a)
    except Rifiuto as e:
        print(f"RIFIUTO: {e}")
        return 2

    riga = raw[:ANCORA.search(raw).start()].count(b"\n") + 1
    print(f"file    : {os.path.abspath(path)}")
    print(f"riga    : {riga}")
    print(f"ancora  : unica")
    print(f"valore  : {corrente} -> {args.a}")

    if args.dry_run:
        print("dry-run: nessuna scrittura")
        return 0

    if args.backup:
        os.makedirs(os.path.dirname(os.path.abspath(args.backup)) or ".", exist_ok=True)
        with open(args.backup, "wb") as fh:
            fh.write(raw)
        print(f"backup  : {os.path.abspath(args.backup)}")

    with open(path, "wb") as fh:
        fh.write(nuovo)

    # rilettura: il valore su disco DEVE essere quello nuovo
    _, riletto = trova_ancora(leggi(path))
    if riletto != args.a:
        print(f"ERRORE: dopo la scrittura il file dichiara {riletto}, non {args.a}")
        return 3
    print(f"riletto : {riletto}  OK")
    print("APPLICATO")
    return 0


def cmd_selftest(args):
    controlli = []

    def ok(nome, cond):
        controlli.append((nome, bool(cond)))

    base = tempfile.mkdtemp(prefix="patch_amend_")

    def scrivi(nome, testo, eol=b"\n"):
        p = os.path.join(base, nome)
        raw = testo.replace(b"\n", eol)
        with open(p, "wb") as fh:
            fh.write(raw)
        return p

    # Fixture con le esche: le altre occorrenze del nome NON sono ancore.
    corpo = (b"PREREG_AMENDMENTS_AT_DEPOSIT = 12\n"
             b"DOCUMENTED_AMENDMENTS = 48\n"
             b"REFERENCE_SELF_SHA = \"865a\"\n"
             b"x = b'{\"a\":1}\\n' * (DOCUMENTED_AMENDMENTS - 1)\n"
             b"y = b'{\"a\":1}\\n' * DOCUMENTED_AMENDMENTS\n"
             b"z = b'{\"a\":1}\\n' * (DOCUMENTED_AMENDMENTS + 1)\n")

    p_lf = scrivi("lf.py", corpo, b"\n")
    orig_lf = leggi(p_lf)
    _, prima = trova_ancora(orig_lf)
    ok("1 ancora unica malgrado tre esche", prima == 48)

    nuovo, corrente = patch(orig_lf, 48, 49)
    _, dopo = trova_ancora(nuovo)
    ok("2 il valore cambia davvero: 48 -> 49", prima == 48 and dopo == 49 and prima != dopo)
    ok("3 un solo byte di differenza", len(nuovo) == len(orig_lf) and
       sum(1 for a, b in zip(nuovo, orig_lf) if a != b) == 1)
    ok("4 le esche restano intatte",
       b"(DOCUMENTED_AMENDMENTS - 1)" in nuovo and b"(DOCUMENTED_AMENDMENTS + 1)" in nuovo)

    # CRLF preservato
    p_crlf = scrivi("crlf.py", corpo, b"\r\n")
    orig_crlf = leggi(p_crlf)
    nuovo_crlf, _ = patch(orig_crlf, 48, 49)
    ok("5 CRLF preservato", nuovo_crlf.count(b"\r\n") == orig_crlf.count(b"\r\n") and
       b"\r\nDOCUMENTED_AMENDMENTS = 49\r\n" in nuovo_crlf)
    ok("6 nessun LF isolato introdotto", nuovo_crlf.count(b"\n") == nuovo_crlf.count(b"\r\n"))

    # Rifiuti
    def rifiuta(raw, da, a):
        try:
            patch(raw, da, a)
            return None
        except Rifiuto as e:
            return str(e)

    ok("7 rifiuta se gia' applicato", (rifiuta(nuovo, 48, 49) or "").startswith("gia' applicato"))
    ok("8 rifiuta se il valore vecchio non torna", "valore vecchio inatteso" in (rifiuta(orig_lf, 47, 49) or ""))
    doppio = orig_lf + b"DOCUMENTED_AMENDMENTS = 48\n"
    ok("9 rifiuta se l'ancora non e' unica", "non unica" in (rifiuta(doppio, 48, 49) or ""))
    ok("10 rifiuta se l'ancora e' assente", "assente" in (rifiuta(b"a = 1\n", 48, 49) or ""))

    # Percorso completo su disco, con dry-run e backup
    class A:
        pass

    a = A(); a.file = p_lf; a.da = 48; a.a = 49; a.dry_run = True; a.backup = None; a.ledger = None
    rc_dry = cmd_apply(a)
    ok("11 dry-run: esito 0 e file immutato", rc_dry == 0 and leggi(p_lf) == orig_lf)

    bak = os.path.join(base, "logs", "backup.py")
    a2 = A(); a2.file = p_lf; a2.da = 48; a2.a = 49; a2.dry_run = False; a2.backup = bak
    a2.ledger = None
    rc = cmd_apply(a2)
    ok("12 apply: esito 0", rc == 0)
    ok("13 il file su disco dichiara 49", trova_ancora(leggi(p_lf))[1] == 49)
    ok("14 il backup e' identico all'originale", leggi(bak) == orig_lf)

    a3 = A(); a3.file = p_lf; a3.da = 48; a3.a = 49; a3.dry_run = False; a3.backup = None
    a3.ledger = None
    rc2 = cmd_apply(a3)
    ok("15 seconda applicazione rifiutata, esito 2", rc2 == 2 and trova_ancora(leggi(p_lf))[1] == 49)

    # Il cancello sul ledger: la costante non si porta a N senza N record sul disco.
    def led(n):
        q = os.path.join(base, f"led{n}.jsonl")
        with open(q, "wb") as fh:
            for i in range(n):
                fh.write(json.dumps({"item": f"r{i}"}).encode() + b"\r\n")
        return q

    scrivi("target2.py", corpo, b"\n")
    p2 = os.path.join(base, "target2.py")
    b4 = A(); b4.file = p2; b4.da = 48; b4.a = 49; b4.dry_run = False; b4.backup = None

    b4.ledger = led(48)
    ok("16 ledger a 48 record, costante verso 49: rifiuto",
       cmd_apply(b4) == 2 and trova_ancora(leggi(p2))[1] == 48)
    b4.ledger = led(50)
    ok("17 ledger a 50 record, costante verso 49: rifiuto",
       cmd_apply(b4) == 2 and trova_ancora(leggi(p2))[1] == 48)
    b4.ledger = led(49)
    ok("18 ledger a 49 record: la costante passa a 49",
       cmd_apply(b4) == 0 and trova_ancora(leggi(p2))[1] == 49)
    b4.ledger = os.path.join(base, "non-esiste.jsonl")
    ok("19 ledger inesistente: rifiuto", cmd_apply(b4) == 2)

    shutil.rmtree(base, ignore_errors=True)

    passati = sum(1 for _, c in controlli if c)
    print()
    for nome, c in controlli:
        print(("  OK  " if c else "  KO  ") + nome)
    print(f"selftest: {passati}/{len(controlli)}")
    return 0 if passati == len(controlli) else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)

    p_ap = sub.add_parser("apply", help="incrementa la costante")
    p_ap.add_argument("--file", required=True)
    p_ap.add_argument("--da", type=int, required=True, help="valore vecchio atteso")
    p_ap.add_argument("--a", type=int, required=True, help="valore nuovo")
    p_ap.add_argument("--dry-run", action="store_true")
    p_ap.add_argument("--backup", default=None)
    p_ap.add_argument("--ledger", default=None,
                      help="ledger degli emendamenti: il suo numero di record deve valere --a")
    p_ap.set_defaults(func=cmd_apply)

    p_st = sub.add_parser("selftest", help="esegue i 15 controlli")
    p_st.set_defaults(func=cmd_selftest)

    args = ap.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
