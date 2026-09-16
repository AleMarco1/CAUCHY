#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
paper2_patch_n6_m26.py

Toglie da paper1_rev_n6_fkp.py il confronto con un valore di M26 che il
manoscritto non porta piu'.

IL DIFETTO
----------
`M26_TAB1_SHIFT = 600.0` cita la Tabella 1 di M26 PRIMA della revisione. Su
quel valore lo script costruisce due verdetti, e per i numeri veri entrambi
sparano a vuoto:

    d = -78.0 +/- 8.0
    ramo di lettura : «ATTENZIONE: e' la direzione OPPOSTA a quella che M26
                       Tabella 1 riporta. La discrepanza va risolta prima di
                       citare l'uno o l'altro.»
    cancello 'agree': |78 - 600| = 522 contro 3*8 + 0.3*600 = 204
                    -> «compatibile in modulo con M26 Tabella 1: NO - da chiarire»

LA RISOLUZIONE, GIA' SCRITTA IN DUE MANOSCRITTI
-----------------------------------------------
Paper 1 §7.2, nota (i): il test di M26 riporta **+622** «away from the data»,
ma NON e' la stessa misura — parte da una linea di base di **35 838**, che non
e' l'ensemble congelato (35 436.686), e applica un «peso posizionale in stile
FKP» invece del w_FKP(z) radiale che dati e random portano davvero. La nota si
chiude con «its Table-1 row is corrected in the M26 revision».
M26 R1, Tabella 1, riga sulla pesatura: **-78.0 +/- 8.0 — towards data (~1%)**.

COSA FA QUESTO PATCHER
----------------------
Sostituisce il confronto con una RIPRODUZIONE: il valore di riferimento diventa
la riga pubblicata in R1, e il cancello chiede se il run la riproduce. Il ramo
d'allarme resta, ma scatta per la condizione giusta — un segno POSITIVO, che
contraddirebbe sia R1 sia il run precedente.

Il valore pre-revisione resta nel file come **+622**, con il suo ruolo scritto
accanto: e' storia, non un termine di paragone. Una costante che cita un
manoscritto in revisione scade se serve da confronto, non se serve da
riproduzione.

Il file NON e' fra gli undici protetti da 2.1-P (che sono registri, maschere e
il reference: nessuno script). Verificato prima di scrivere.

USO
    python src\\paper2_patch_n6_m26.py selftest
    python src\\paper2_patch_n6_m26.py applica --file src\\paper1_rev_n6_fkp.py --dry-run
    python src\\paper2_patch_n6_m26.py applica --file src\\paper1_rev_n6_fkp.py ^
        --backup logs\\n6_pre_m26.py

Uscita: 0 se applicato, 2 se rifiutato, 3 se la rilettura o la compilazione non torna.
"""

from __future__ import annotations

import argparse
import os
import sys
import tempfile

# (etichetta, testo vecchio, testo nuovo). Ogni vecchio deve comparire UNA volta.
SOSTITUZIONI = [
    ("costante", """M26_TAB1_SHIFT = 600.0     # spostamento citato da M26, Tabella 1""",
     '''# M26 PRE-REVISIONE, Tabella 1: +622 generatori, "away from the data".
# NON e' la stessa misura (Paper 1 §7.2, nota (i)): parte da una linea di base di
# 35 838, che non e' l'ensemble congelato (35 436.686), e applica un "peso
# posizionale in stile FKP" invece del w_FKP(z) radiale che dati e random
# portano. La riga E' CORRETTA in M26 R1, che oggi porta -78.0 +/- 8.0
# "towards data (~1%)". Il valore sotto e' STORIA, non un termine di paragone:
# confrontarci una misura nuova produce un verdetto falso.
M26_TAB1_PREREV = 622.0    # ruolo: provenienza. NON usare come confronto.
# M26 R1, Tabella 1, riga "w_FKP(z) on mocks (60 pairs)". Ruolo: RIPRODUZIONE.
M26_R1_ROW = -78.0
M26_R1_SEM = 8.0'''),

    ("stampa del confronto", """    print(f"  M26 Tabella 1 cita ~{M26_TAB1_SHIFT:.0f} generatori "
          f"({100*M26_TAB1_SHIFT/DEFICIT:.1f}%), in allontanamento dai dati")""",
     """    print(f"  M26 R1, Tabella 1: {M26_R1_ROW:+.1f} +/- {M26_R1_SEM:.1f}, "
          f"verso i dati -- e' questa la riga da riprodurre")
    print(f"  (il +{M26_TAB1_PREREV:.0f} pre-revisione e' un'ALTRA misura: "
          f"base 35838, peso posizionale. Paper 1 §7.2 nota (i))")"""),

    ("ramo d'allarme", """        print(f"    ATTENZIONE: e' la direzione OPPOSTA a quella che M26")
        print(f"    Tabella 1 riporta. La discrepanza va risolta prima di")
        print(f"    citare l'uno o l'altro.")""",
     """        print(f"    E' la direzione che M26 R1 e Paper 1 §7.2 riportano.")"""),

    ("cancello", """    agree = abs(abs(d.mean()) - M26_TAB1_SHIFT) < 3 * sem + 0.3 * M26_TAB1_SHIFT
    print(f"\\n    compatibile in modulo con M26 Tabella 1: "
          f"{'SI' if agree else 'NO - da chiarire'}")""",
     """    tolleranza = 3 * max(sem, M26_R1_SEM)
    agree = abs(d.mean() - M26_R1_ROW) <= tolleranza
    print(f"\\n    riproduce la riga di M26 R1 ({M26_R1_ROW:+.1f}): "
          f"{'SI' if agree else 'NO'}  "
          f"(scarto {abs(d.mean() - M26_R1_ROW):.1f} contro {tolleranza:.1f})")
    if d.mean() > 0:
        print("    *** ALLARME: segno POSITIVO. Contraddice sia M26 R1 sia il")
        print("    run precedente, e va risolto prima di citare qualunque valore. ***")"""),

    ("report", """        "m26_tab1_shift": M26_TAB1_SHIFT,""",
     """        "m26_r1_row": M26_R1_ROW, "m26_r1_sem": M26_R1_SEM,
        "m26_tab1_prerev": M26_TAB1_PREREV,
        "riproduce_m26_r1": bool(agree),"""),
]

# Dopo la patch questi frammenti NON devono esistere piu'.
SPARITI = ["M26_TAB1_SHIFT", "direzione OPPOSTA", "NO - da chiarire"]
# E questi devono esserci.
PRESENTI = ["M26_R1_ROW", "M26_TAB1_PREREV", "riproduce la riga di M26 R1",
            "ALLARME: segno POSITIVO"]


def applica(path, dry_run=False, backup=None):
    if not os.path.isfile(path):
        raise SystemExit(f"RIFIUTO: file inesistente: {path}")
    with open(path, "rb") as fh:
        grezzo = fh.read()
    testo = grezzo.decode("utf-8")

    nuovo = testo
    print(f"file    : {os.path.abspath(path)}")
    for etichetta, vecchio, sost in SOSTITUZIONI:
        n = nuovo.count(vecchio)
        if n != 1:
            raise SystemExit(f"RIFIUTO: ancora '{etichetta}' trovata {n} volte, attesa 1")
        nuovo = nuovo.replace(vecchio, sost)
        print(f"  ok    {etichetta}: {len(vecchio)} -> {len(sost)} byte")

    for f in SPARITI:
        if f in nuovo:
            raise SystemExit(f"RIFIUTO: '{f}' e' ancora presente dopo la sostituzione")
    for f in PRESENTI:
        if f not in nuovo:
            raise SystemExit(f"RIFIUTO: '{f}' manca dopo la sostituzione")

    try:
        compile(nuovo, path, "exec")
    except SyntaxError as e:
        raise SystemExit(f"RIFIUTO: il file patchato non compila: {e}")
    print(f"  ok    il file patchato compila")
    print(f"byte    : {len(grezzo)} -> {len(nuovo.encode('utf-8'))}")

    if dry_run:
        print("dry-run: nessuna scrittura")
        return 0

    if backup:
        os.makedirs(os.path.dirname(os.path.abspath(backup)) or ".", exist_ok=True)
        with open(backup, "wb") as fh:
            fh.write(grezzo)
        print(f"backup  : {os.path.abspath(backup)}")

    with open(path, "w", encoding="utf-8", newline="") as fh:
        fh.write(nuovo)
    with open(path, "r", encoding="utf-8") as fh:
        riletto = fh.read()
    if riletto != nuovo:
        print("ERRORE: la rilettura non coincide con lo scritto")
        return 3
    try:
        compile(riletto, path, "exec")
    except SyntaxError as e:
        print(f"ERRORE: il file su disco non compila: {e}")
        return 3
    print("riletto : compila, i frammenti vecchi non ci sono, i nuovi ci sono")
    print("APPLICATO")
    return 0


# ---------------------------------------------------------------------------
# selftest: riproduce il difetto PRIMA di correggerlo
# ---------------------------------------------------------------------------

FINTO = '''DEFICIT = 7181.5
M26_TAB1_SHIFT = 600.0     # spostamento citato da M26, Tabella 1


def analisi(d_mean, sem):
    class D:
        def mean(self):
            return d_mean
    d = D()
    print(f"  M26 Tabella 1 cita ~{M26_TAB1_SHIFT:.0f} generatori "
          f"({100*M26_TAB1_SHIFT/DEFICIT:.1f}%), in allontanamento dai dati")
    if d.mean() > 0:
        pass
    else:
        print(f"    ATTENZIONE: e' la direzione OPPOSTA a quella che M26")
        print(f"    Tabella 1 riporta. La discrepanza va risolta prima di")
        print(f"    citare l'uno o l'altro.")
    agree = abs(abs(d.mean()) - M26_TAB1_SHIFT) < 3 * sem + 0.3 * M26_TAB1_SHIFT
    print(f"\\n    compatibile in modulo con M26 Tabella 1: "
          f"{'SI' if agree else 'NO - da chiarire'}")
    rep = {
        "m26_tab1_shift": M26_TAB1_SHIFT,
    }
    return agree, rep
'''


def _esegui(sorgente, d_mean, sem):
    """Esegue il modulo finto e ritorna (agree, report, stampato)."""
    import io
    import contextlib
    ns = {}
    exec(compile(sorgente, "<finto>", "exec"), ns)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        agree, rep = ns["analisi"](d_mean, sem)
    return agree, rep, buf.getvalue()


def selftest():
    ok = tot = 0

    def chk(n, cond, det=""):
        nonlocal ok, tot
        tot += 1
        if cond:
            ok += 1
            print(f"  [ok ] {tot:2d} {n}")
        else:
            print(f"  [FAIL] {tot:2d} {n}  {det}")

    print("selftest paper2_patch_n6_m26")

    # --- 1. il difetto, riprodotto sui numeri veri, PRIMA della patch -------
    agree, rep, out = _esegui(FINTO, -78.0, 8.0)
    chk("difetto: il cancello vecchio dichiara NO - da chiarire",
        agree is False and "NO - da chiarire" in out)
    chk("difetto: il ramo d'allarme vecchio scatta su -78",
        "direzione OPPOSTA" in out)
    chk("difetto: |78-600| supera 3*8+0.3*600",
        abs(abs(-78.0) - 600.0) > 3 * 8.0 + 0.3 * 600.0,
        f"{abs(78-600)} contro {3*8+0.3*600}")

    base = tempfile.mkdtemp(prefix="n6_")
    f = os.path.join(base, "n6.py")

    def scrivi(t=FINTO):
        with open(f, "w", encoding="utf-8", newline="") as fh:
            fh.write(t)

    scrivi()
    prima = open(f, "rb").read()
    chk("dry-run non scrive",
        applica(f, dry_run=True) == 0 and open(f, "rb").read() == prima)

    bk = os.path.join(base, "bk.py")
    chk("applica riesce", applica(f, backup=bk) == 0)
    chk("il backup e' il file di prima", open(bk, "rb").read() == prima)

    dopo = open(f, encoding="utf-8").read()
    for fr in SPARITI:
        chk(f"sparito: {fr!r}", fr not in dopo)
    for fr in PRESENTI[:2]:
        chk(f"presente: {fr!r}", fr in dopo)

    # --- 2. il comportamento nuovo, sugli stessi numeri ---------------------
    agree2, rep2, out2 = _esegui(dopo, -78.0, 8.0)
    chk("nuovo: -78 riproduce la riga di M26 R1", agree2 is True, out2)
    chk("nuovo: nessun allarme su -78", "ALLARME" not in out2)
    chk("nuovo: il report porta la riga di R1 e la sua riproduzione",
        rep2.get("m26_r1_row") == -78.0 and rep2.get("riproduce_m26_r1") is True, rep2)
    chk("nuovo: il +622 resta nel report come provenienza",
        rep2.get("m26_tab1_prerev") == 622.0, rep2)

    # il segno positivo, che e' la condizione per cui l'allarme deve esistere
    agree3, rep3, out3 = _esegui(dopo, +600.0, 8.0)
    chk("nuovo: un segno POSITIVO fa scattare l'allarme", "ALLARME" in out3)
    chk("nuovo: un segno positivo non riproduce R1", agree3 is False)

    # uno scarto grande ma dello stesso segno: niente allarme, ma non riproduce
    agree4, rep4, out4 = _esegui(dopo, -300.0, 8.0)
    chk("nuovo: -300 non riproduce R1 ma non e' un allarme",
        agree4 is False and "ALLARME" not in out4)

    # tolleranza: 3*max(sem, 8)
    agree5, _, _ = _esegui(dopo, -78.0 + 23.9, 8.0)
    agree6, _, _ = _esegui(dopo, -78.0 + 24.1, 8.0)
    chk("nuovo: dentro 3*8 riproduce, fuori no", agree5 is True and agree6 is False)

    # --- 3. rifiuti ---------------------------------------------------------
    scrivi(FINTO.replace("M26_TAB1_SHIFT = 600.0     # spostamento citato da M26, Tabella 1", ""))
    try:
        applica(f, dry_run=True)
        chk("ancora assente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("ancora assente: rifiuto", "costante" in str(e), str(e))

    scrivi(FINTO + '\n"""' + '        "m26_tab1_shift": M26_TAB1_SHIFT,' + '"""\n')
    try:
        applica(f, dry_run=True)
        chk("ancora doppia: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("ancora doppia: rifiuto", "2 volte" in str(e), str(e))

    scrivi()
    applica(f)
    try:
        applica(f, dry_run=True)
        chk("seconda passata: rifiuto, non doppia patch", False, "non ha rifiutato")
    except SystemExit as e:
        chk("seconda passata: rifiuto, non doppia patch", "0 volte" in str(e), str(e))

    try:
        applica(os.path.join(base, "nope.py"))
        chk("file inesistente: rifiuto", False, "non ha rifiutato")
    except SystemExit as e:
        chk("file inesistente: rifiuto", "inesistente" in str(e))

    print(f"\n{ok}/{tot} controlli superati")
    return 0 if ok == tot else 1


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("applica")
    a.add_argument("--file", required=True)
    a.add_argument("--dry-run", action="store_true")
    a.add_argument("--backup", default=None)
    sub.add_parser("selftest")
    x = ap.parse_args(argv)
    if x.cmd == "applica":
        return applica(x.file, x.dry_run, x.backup)
    return selftest()


if __name__ == "__main__":
    sys.exit(main())
