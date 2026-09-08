#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_sezione_c_patch.py - il §C del secondo report, con il test costruito
apposta e il suo esito NEGATIVO.

E' l'unico punto dei due report dove ci viene contestato il difetto opposto --
scartare un segnale vero -- e l'unico dove possiamo rispondere con un test
disegnato per quel rilievo.

UNA CORREZIONE AL DISEGNO PRIMA DI ESEGUIRLO
---------------------------------------------
La traslazione dell'origine proposta dal rilievo NON varia lo spostamento
relativo: lo lascia invariato per costruzione, ed e' la proprieta' su cui poggia
lo scan del record 45. Varia la FASE, e con essa la frazione di voxel il cui
cella sorgente cambia. Il che rende l'esperimento migliore: a spostamento
relativo FISSO si varia la frazione e si guarda se Delta_ripattern la segue.

L'ESITO
-------
Frazione da 0.00% a 100.00%, e Delta_ripattern non si muove: la differenza vale
-15.70 +- 18.75 e -17.19 +- 17.31 contro una soglia di 55 dichiarata prima. E i
quattro Delta ai due offset sono TUTTI compatibili con zero, quindi il 2.2-2.5
sigma su cui il rilievo poggia non si riproduce a fasi diverse.

Una modifica sola: la sezione, prima di «Sezioni ancora aperte».
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"
ANCORA = "---\n\n## Sezioni ancora aperte\n"
SEZIONE = "---\n\n## Secondo report, §C — **[SCRITTA]** — *test costruito apposta, ed esce negativo*\n\n> *«Vale la pena chiudere questo canale perché, se regge, spiega una classe di effetti SGC-specifici\n> che ora inseguite separatamente. Il test è diretto: misurate Δ_ripattern in funzione dello\n> spostamento relativo, variandolo deliberatamente.»*\n\nÈ l'unico punto dei due report dove ci viene contestato il difetto **opposto** — di scartare un\nsegnale vero — e l'abbiamo preso sul serio. Il test è stato costruito, ed **esce negativo**.\n\n### Una correzione al disegno, prima di eseguirlo\n\nLa traslazione proposta — «un'origine dell'embedding diversa che lasci invariata la geometria di\nsurvey» — **non varia lo spostamento relativo**. Lo lascia invariato *per costruzione*: traslare in\nblocco entrambe le griglie sposta B1 e B5 della stessa quantità, e la loro differenza non cambia. È\nla proprietà su cui poggia lo scan dell'emendamento 45, ed è fissata da un controllo dello strumento.\n\nQuello che la traslazione varia è la **fase** della griglia rispetto al reticolo del box, e con essa\nla **frazione** di voxel la cui cella sorgente cambia — da 0% a 100% in SGC.\n\n**Il che rende l'esperimento migliore di come è formulato**: a spostamento relativo **fisso** si varia\nla frazione, e si guarda se Δ_ripattern la segue. Se la segue, il meccanismo è il ripattern. Se non\nla segue, la frazione non è la leva.\n\nE costa meno, perché le configurazioni si scelgono a costo zero con lo scan geometrico prima di\nspendere ore: due offset al centro di due plateau, **+4.0** (frazione 0.00%) e **−2.1** (frazione\n100.00%).\n\n### Il risultato\n\nQuattro bracci in SGC — due offset, ciascuno con il suo braccio standard e il suo randomizzato, 200\nrealizzazioni per braccio. Confrontare un braccio randomizzato a un offset con uno standard a un\naltro misurerebbe l'offset, non il ripattern.\n\n| offset | frazione | Δ_ripattern *k*=0 | Δ_ripattern *k*=1 |\n|---|---:|---:|---:|\n| **+4.0** | 0.00% | +6.61 ± 12.28 | +16.49 ± 11.90 |\n| **−2.1** | 100.00% | −9.09 ± 14.18 | −0.70 ± 12.58 |\n| **differenza** | | **−15.70 ± 18.75** | **−17.19 ± 17.31** |\n\n**Soglia dichiarata prima dei run: 55 generatori**, cioè 3× la SEM della differenza. Entrambi i\nlivelli sono **sotto**, e a meno di 1σ da zero.\n\nPortare il ripattern da praticamente **nullo** a praticamente **totale**, a spostamento relativo\ninvariato, **non muove Δ_ripattern**. La frazione non è la leva.\n\n### E il 2.4σ non sopravvive\n\nI quattro Δ_ripattern ai due offset sono **tutti compatibili con zero**: +0.54σ, +1.39σ, −0.64σ e\n−0.06σ. Compreso l'offset a frazione 100%, dove **ogni** voxel cambia cella sorgente.\n\nIl 2.2–2.5σ su cui il rilievo poggia era misurato all'origine originale, e a due fasi diverse **non\nsi riproduce**. Questo è coerente con l'audit dell'emendamento 48, che già riportava il nostro «sotto\nsoglia» in SGC a **1.4σ e 1.9σ** dalla soglia — cioè non un verdetto — e ora se ne vede la ragione.\n\n*(L'appaiamento fra bracci è di nuovo nullo — correlazioni +0.036, +0.022, −0.065, −0.025 — come\nnell'emendamento 44: randomizzare le repliche produce di fatto una realizzazione indipendente della\nstessa cosmologia.)*\n\n### Cosa sopravvive, e cosa no\n\n**Sopravvive** lo spostamento relativo di `box_min`, 0.0076 voxel in NGC contro 0.3822 in SGC — un\nfattore cinquanta, indipendente dalla fase. Resta un fatto misurato.\n\n**Non sopravvive** la catena che lo collegava agli effetti SGC-specifici. Se quel fattore cinquanta\nagisce, **non agisce attraverso la frazione di ripattern**, perché la frazione può andare da 0 a 100\nsenza che Δ_ripattern se ne accorga.\n\n### Un limite del test, dichiarato\n\nIl termine (e) esiste **dentro** ciascun offset — traslando la griglia la maschera cambia — ma si\ncancella nella differenza fra i due bracci dello **stesso** offset, che è ciò che misuriamo. Fra i\ndue offset i conteggi differiscono di 27 e 103 voxel, cioè **~10 generatori** alla pendenza del lato\ndati: piccolo contro una soglia di 55, e lo diciamo invece di lasciarlo assumere.\n\nIl test è su **SGC soltanto** e su **due** configurazioni di fase. Che valga a tutte le fasi\nintermedie è un'estrapolazione, e i due estremi sono il caso più favorevole al rilievo: se l'effetto\nesistesse, fra 0% e 100% dovrebbe vedersi.\n\n"

EDITS = [
    ("1. il \u00a7C con il test e il suo esito", ANCORA, SEZIONE + ANCORA,
     "## Secondo report, \u00a7C \u2014 **[SCRITTA]**"),
]

def fail(msg):
    print("ERRORE: %s" % msg, file=sys.stderr)
    sys.exit(2)


def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def read_target(path):
    with open(path, "rb") as fh:
        raw = fh.read()
    txt = raw.decode("utf-8")
    n_crlf = txt.count("\r\n")
    n_lf = txt.count("\n") - n_crlf
    return txt, ("\r\n" if n_crlf >= n_lf else "\n"), n_crlf, n_lf


def norm(t):
    return t.replace("\r\n", "\n")


def piatto(t):
    righe = [l.lstrip().lstrip(">").strip() for l in norm(t).split("\n")]
    return " ".join(" ".join(righe).split()).lower()


def plan(txt):
    n = norm(txt)
    ok, done, bad = [], [], []
    for name, old, new, marker in EDITS:
        if marker in n:
            done.append(name)
        elif n.count(old) == 1:
            ok.append(name)
        else:
            bad.append("%s: %d occorrenze dell'ancora" % (name, n.count(old)))
    return ok, done, bad


def apply_all(txt):
    ok, done, bad = plan(txt)
    if bad:
        fail("nessuna modifica applicata. " + "; ".join(bad))
    if not ok:
        return None, done
    n = norm(txt)
    for name, old, new, marker in EDITS:
        prima = len(n)
        n = n.replace(old, new, 1)
        if len(n) == prima:
            fail("la sostituzione %r non ha cambiato nulla." % name)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  righe     : %d   sezioni: %d" % (len(n.splitlines()), n.count("\n## ")))
    print("  fine riga : CRLF=%d LF=%d%s" % (n_crlf, n_lf,
                                             "   MISTI" if (n_crlf and n_lf) else ""))
    ok, done, bad = plan(txt)
    for lst, lab in ((ok, "da applicare"), (done, "gia' applicate"), (bad, "problemi")):
        print("  %-15s: %s" % (lab, ", ".join(lst) if lst else "nessuna"))
    return 0 if not bad else 3


def cmd_patch(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    for prereq, chi in (("## Secondo report, B.3", "paper2_b3_patch.py"),):
        if prereq not in n:
            fail("manca %r: lancia prima %s. Questa sezione ci si appoggia."
                 % (prereq, chi))
    if n_crlf and n_lf and not args.allow_eol_normalise:
        fail("fine riga MISTI (CRLF=%d, LF=%d): --allow-eol-normalise."
             % (n_crlf, n_lf))
    new_n, done = apply_all(txt)
    print("=== PATCH %s ===" % args.target)
    print("  sha256 prima : %s" % sha256_file(args.target))
    if new_n is None:
        print("  [OK] niente da fare (%s)." % ", ".join(done))
        return 0
    out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
    print("  %d -> %d righe" % (len(n.splitlines()), len(new_n.splitlines())))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prec"
    if args.backup and not os.path.exists(bak):
        with open(bak, "wb") as fh:
            fh.write(txt.encode("utf-8"))
        print("  copia    : %s" % bak)
    tmp = args.target + ".tmp"
    with open(tmp, "wb") as fh:
        fh.write(out.encode("utf-8"))
    os.replace(tmp, args.target)
    print("  sha256 dopo  : %s" % sha256_file(args.target))
    print("  [OK] scritto")
    return cmd_verify(args)


def cmd_verify(args):
    n = norm(read_target(args.target)[0])
    f = piatto(n)
    ok = True
    print("")
    print("=== VERIFY ===")
    checks = [
        ("la sezione esiste", "## Secondo report, \u00a7C" in n),
        ("e precede «Sezioni ancora aperte»",
         n.index("## Secondo report, \u00a7C") < n.index("## Sezioni ancora aperte")),
        ("riconosce che il rilievo contesta il difetto OPPOSTO",
         "il difetto **opposto**" in n),
        # L'ordinamento si verifica DENTRO la sezione: «### Il risultato» non e'
        # unico nel documento, e index() confronterebbe occorrenze di sezioni
        # diverse. Un controllo di ordine su una stringa non unica non ordina.
        ("la correzione al disegno e' dichiarata PRIMA dell'esito",
         (lambda sez: "non varia lo spostamento relativo" in sez
          and "### Il risultato" in sez
          and sez.index("non varia lo spostamento relativo")
          < sez.index("### Il risultato"))(
              n[n.index("## Secondo report, \u00a7C"):]
              .split("\n## ")[0])),
        # sul piatto: e' un inizio di frase, quindi maiuscola.
        ("e dice perche': la traslazione lo lascia invariato",
         "lo lascia invariato *per costruzione*" in f),
        ("i due offset e le due frazioni ci sono",
         "**+4.0**" in n and "**\u22122.1**" in n
         and "0.00%" in n and "100.00%" in n),
        ("i quattro Delta_ripattern ci sono",
         "+6.61" in n and "+16.49" in n and "\u22129.09" in n and "\u22120.70" in n),
        ("la differenza e' riportata con la sua SEM",
         "\u221215.70 \u00b1 18.75" in n and "\u221217.19 \u00b1 17.31" in n),
        ("la soglia era dichiarata PRIMA", "dichiarata prima dei run: 55" in f),
        ("l'esito e' sotto soglia", "entrambi i\nlivelli sono **sotto**" in n
         or "entrambi i livelli sono **sotto**" in f),
        ("dice che la frazione NON e' la leva", "la frazione non \u00e8 la leva" in f),
        ("il 2.4 sigma non sopravvive, con i quattro sigma",
         "+0.54\u03c3, +1.39\u03c3, \u22120.64\u03c3 e \u22120.06\u03c3" in n
         and "non\nsi riproduce" in n or "non si riproduce" in f),
        ("e il collegamento con l'audit del 48 c'e'",
         "1.4\u03c3 e 1.9\u03c3" in n and "emendamento 48" in f),
        ("cio' che SOPRAVVIVE e' distinto da cio' che no",
         "**sopravvive** lo spostamento relativo" in f
         and "**non sopravvive** la catena" in f),
        ("il termine (e) fra offset e' dichiarato",
         "27 e 103 voxel" in n and "~10 generatori" in n),
        ("i limiti del test sono scritti",
         "**sgc soltanto**" in f and "estrapolazione" in f),
        ("le sezioni precedenti sono intatte",
         "## Secondo report, punto A" in n
         and "## Secondo report, B.3" in n
         and "## Secondo report, rilievi minori" in n),
    ]
    for name, cond in checks:
        print("  [%s] %s" % ("ok" if cond else "NO", name))
        ok &= bool(cond)
    print("  esito: %s" % ("CLEAN" if ok else "SPORCO"))
    return 0 if ok else 3


def cmd_selftest(args):
    import tempfile
    checks = []

    def chk(name, cond, detail=""):
        checks.append((name, bool(cond), detail))

    corpo = ("# Risposta\n\n## Secondo report, punto A \u2014 **[SCRITTA]**\n\nt\n\n"
             "## Secondo report, rilievi minori D.2\u2013D.6 \u2014 **[SCRITTA]**\n\nt\n\n"
             "## Secondo report, B.3 \u2014 **[SCRITTA]**\n\nt\n\n" + ANCORA)

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s ancora unica" % lab, len(ok) == 1 and not bad,
                "ok=%d bad=%s" % (len(ok), bad))
            new_n, _ = apply_all(txt)
            out = new_n.replace("\n", eol) if eol == "\r\n" else new_n
            with open(p, "wb") as fh:
                fh.write(out.encode("utf-8"))

            class A:
                target = p
            chk("3%s verify passa dopo la patch" % lab, cmd_verify(A()) == 0)
            chk("4%s fine riga preservati" % lab,
                (read_target(p)[0].count("\r\n") == 0) if eol == "\n"
                else (read_target(p)[0].count("\n")
                      == read_target(p)[0].count("\r\n")))
            ok2, _, bad2 = plan(read_target(p)[0])
            chk("5%s idempotenza" % lab, not ok2 and not bad2,
                "ok=%s bad=%s" % (ok2, bad2))

        p2 = os.path.join(td, "senzaB3.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace("## Secondo report, B.3 \u2014 **[SCRITTA]**",
                                   "## Altro").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza la sezione B.3 la patch rifiuta", _exits(lambda: cmd_patch(B())))

    fs = piatto(SEZIONE)
    chk("7  la correzione al disegno precede l'esito",
        SEZIONE.index("non varia lo spostamento relativo")
        < SEZIONE.index("### Il risultato"))
    chk("7b la soglia e' dichiarata come DICHIARATA PRIMA",
        "dichiarata prima dei run: 55" in fs)
    chk("7c l'esito e' negativo e detto tale",
        "la frazione non \u00e8 la leva" in fs)
    chk("7d e non si rivendica piu' di quanto il test dia",
        "**sgc soltanto**" in fs and "due** configurazioni" in fs)
    chk("7e cio' che sopravvive resta distinto",
        "fattore cinquanta, indipendente dalla fase" in fs)

    print("=== SELFTEST paper2_sezione_c_patch ===")
    nf = 0
    for name, okk, detail in checks:
        if not okk:
            nf += 1
        print("  [%s] %s%s" % ("PASS" if okk else "FAIL", name,
                               ("   <- " + detail) if detail else ""))
    print("--- %d controlli, %d falliti ---" % (len(checks), nf))
    return 0 if not nf else 1


def _exits(fn):
    import contextlib
    import io
    try:
        with contextlib.redirect_stderr(io.StringIO()):
            fn()
        return False
    except SystemExit:
        return True
    except Exception:
        return False


def main():
    p = argparse.ArgumentParser(description="Il \u00a7C del secondo report, e il suo esito")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--target", default=DEFAULT_TARGET)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("inspect", parents=[common]).set_defaults(func=cmd_inspect)
    sub.add_parser("verify", parents=[common]).set_defaults(func=cmd_verify)
    sub.add_parser("selftest", parents=[common]).set_defaults(func=cmd_selftest)
    pa = sub.add_parser("patch", parents=[common])
    pa.add_argument("--apply", action="store_true")
    pa.add_argument("--backup", action="store_true", default=True)
    pa.add_argument("--allow-eol-normalise", action="store_true")
    pa.set_defaults(func=cmd_patch)
    args = p.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        except Exception:
            pass
    main()
