#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_risposta_r2_patch.py - i tre rilievi del secondo report che si chiudono
con una correzione di scrittura: B.1, D.1, B.2.

  B.1  Il cancello 2.3 e' il cancello di SIGMA_PX, non della regola di maschera.
       La checklist lo dice: «2.3 e 2.2a hanno geometria e MASCHERA IDENTICHE,
       cambia solo R_SMOOTH, quindi la differenza E' il canale». La risposta
       aveva riformulato, e la riformulazione e' sbagliata. Il §3.4 del referee
       non va ritirato: la sua lettura era quella giusta.
       Due posti: la sezione trasferibile e l'ancoraggio della soglia E3.
  D.1  Riga 419: «Il trattamento (B) e' dichiarato e non ancora eseguito»,
       mentre trenta righe sopra lo si esegue con tabella e cancelli. In un
       documento la cui tesi e' la disciplina di registro, una contraddizione su
       SE UN RUN SIA STATO ESEGUITO non e' un refuso.
  B.2  La «firma asimmetrica fra emisferi» vale 1.6 sigma ed e' UNA
       osservazione, non quattro: k=0 e k=1 condividono l'84.6% dei voxel, cosa
       che il §3.3 accetta e che non era stata applicata a valle. Due posti,
       dove e' chiamata «il vincolo piu' forte che abbiamo».

Le cinque modifiche si muovono INSIEME. Correggere il 2.3 in un posto e non
nell'altro lascerebbe la soglia E3 ancorata a una quantita' ritirata.
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"

B1A_V = (
    "Il cancello 2.3 misura di quanto cambia *N*_H1 quando si cambia **regola di maschera** fra due\n"
    "scelte entrambe difendibili. Vale **+391 generatori in NGC** e **+254 in SGC**, cio\u00e8 il **1.10%** e\n"
    "il **1.36%** del conteggio mock medio.")

B1A_N = (
    "Il cancello 2.3 misura di quanto cambia *N*_H1 quando **σ_px \u00e8 libero di seguire la cella** a\n"
    "dilatazione e maschera invariate: stessa geometria, stessa maschera, cambia solo `R_SMOOTH`.\n"
    "Vale **+391 generatori in NGC** e **+254 in SGC**, cio\u00e8 il **1.10%** e il **1.36%** del conteggio\n"
    "mock medio.\n"
    "\n"
    "**Correzione (rilievo B.2 del secondo report).** Una versione precedente di questa sezione lo\n"
    "descriveva come «di quanto cambia *N*_H1 quando si cambia regola di maschera». \u00c8 **sbagliato**, e\n"
    "la checklist alla voce 2.3 lo dice in chiaro: «2.3 e 2.2a hanno geometria e **maschera identiche**,\n"
    "cambia solo `R_SMOOTH`, quindi la differenza **\u00e8** il canale». Il cancello misura una\n"
    "**convenzione di lisciamento**, cio\u00e8 il canale isotropo isolato per costruzione. La lettura del\n"
    "referee in prima tornata era quella corretta, e il suo §3.4 **non va ritirato**: ritiriamo la\n"
    "nostra riformulazione. L'elasticit\u00e0 di σ_px vale −0.267 in NGC contro −0.346 in SGC.")

B1B_V = (
    "**205.8** \u2014 e l'ancoraggio \u00e8 l'ambiguit\u00e0 della regola di maschera, cio\u00e8 i **+391 generatori** del\n"
    "§3.4. \u00c8 una lacuna della richiesta di review, non del deposito, e la colmiamo col puntatore.")

B1B_N = (
    "**205.8** \u2014 e l'ancoraggio \u00e8 il pi\u00f9 grande sistematico gi\u00e0 caratterizzato, cio\u00e8 i **+391\n"
    "generatori** del cancello 2.3. \u00c8 una lacuna della richiesta di review, non del deposito, e la\n"
    "colmiamo col puntatore.\n"
    "\n"
    "**E la natura di quell'ancoraggio va detta (B.1).** Il cancello 2.3 misura una **convenzione di\n"
    "lisciamento**, non la regola di maschera: la riformulazione che comparve in una versione\n"
    "precedente di questa risposta \u00e8 ritirata. Ne segue che «E2 = sensibilit\u00e0 sotto-dominante»\n"
    "significa **pi\u00f9 piccola dell'ambiguit\u00e0 di quella convenzione**, non «piccola» in assoluto. E con\n"
    "SGC *k*=0 a 222.0 contro 206 nella lettura max\u2212min, la formulazione onesta \u00e8 **comparabile a**,\n"
    "non sotto-dominante.")

D1_V = (
    "**Il trattamento (B) \u00e8 dichiarato e non ancora eseguito.** Il protocollo per misurarlo \u2014 perimetro,\n"
    "cancelli, predizione, regola di quotazione \u2014 \u00e8 registrato prima del run, con l'etichetta obbligatoria\n"
    "\u00abpost-review, dichiarato prima dell'esecuzione\u00bb. L'esito depositato resta valutato su (A), che d\u00e0\n"
    "l'escursione pi\u00f9 grande: il paper conclude sul pi\u00f9 conservativo dei due.")

D1_N = (
    "**Il trattamento (B) \u00e8 stato ESEGUITO**, 3\u20134 settembre, emendamento 38, ed \u00e8 riportato pi\u00f9 sopra in\n"
    "questa stessa sezione. Il protocollo per misurarlo \u2014 perimetro, cancelli, predizione, regola di\n"
    "quotazione \u2014 era registrato **prima** del run, con l'etichetta obbligatoria \u00abpost-review,\n"
    "dichiarato prima dell'esecuzione\u00bb, ed \u00e8 quella priorit\u00e0 a rendere il risultato citabile. L'esito\n"
    "depositato resta valutato su (A), che d\u00e0 l'escursione pi\u00f9 grande: il paper conclude sul pi\u00f9\n"
    "conservativo dei due.\n"
    "\n"
    "*(Correzione, rilievo D.1: una versione precedente di questa riga diceva «dichiarato e non ancora\n"
    "eseguito», contraddicendo la tabella trenta righe sopra. In un documento la cui tesi \u00e8 la\n"
    "disciplina di registro, una contraddizione su se un run sia stato eseguito non \u00e8 un refuso, e la\n"
    "segnaliamo invece di correggerla in silenzio.)*")

B2A_V = (
    "**E la deviazione ha segno opposto fra i due emisferi** \u2014 NGC risponde *meno* senza RSD, SGC *di\n"
    "pi\u00f9*. Un meccanismo che si limitasse a scalare la risposta non potrebbe produrlo, e questo \u00e8 il\n"
    "vincolo pi\u00f9 forte che abbiamo su qualunque spiegazione futura.")

B2A_N = (
    "**E la deviazione ha segno opposto fra i due emisferi** \u2014 NGC risponde *meno* senza RSD, SGC *di\n"
    "pi\u00f9*. Un meccanismo che si limitasse a scalare la risposta non potrebbe produrlo.\n"
    "\n"
    "**Con quanta forza (rilievo B.2).** Le quattro differenze sono +17.4 \u00b1 16.9, +10.0 \u00b1 15.9,\n"
    "\u221216.4 \u00b1 12.9 e \u221214.5 \u00b1 12.2, cio\u00e8 1.0σ, 0.63σ, 1.27σ e 1.19σ; la differenza fra emisferi vale\n"
    "33.8 \u00b1 21.3 = **1.6σ**. E poich\u00e9 *k*=0 e *k*=1 condividono l'84.6% dei voxel \u2014 il §3.3 lo\n"
    "stabilisce e non l'avevamo applicato a valle \u2014 \u00e8 **una** osservazione a 1.6σ, non quattro.\n"
    "**Un'osservazione a 1.6σ non vincola niente**, e la riportiamo con il suo σ invece che come un\n"
    "vincolo: la formula che compariva qui in una versione precedente \u00e8 ritirata.")

B2B_V = (
    "**E c'\u00e8 una firma che si ripete e che \u00e8 il vincolo pi\u00f9 forte che abbiamo.** Sotto (B) il rapporto\n"
    "scende in NGC e **sale** in SGC; in spazio reale identico, 0.920 e 0.942 contro 1.120 e 1.131. Due\n"
    "manipolazioni diverse, la stessa asimmetria fra emisferi. Un meccanismo che si limitasse a scalare\n"
    "la risposta non potrebbe produrla. Chi vorr\u00e0 spiegare il fattore dovr\u00e0 spiegare anche questo.")

B2B_N = (
    "**E c'\u00e8 una firma che si ripete, riportata con il suo σ (B.2).** Sotto (B) il rapporto scende in\n"
    "NGC e **sale** in SGC; in spazio reale identico, 0.920 e 0.942 contro 1.120 e 1.131. Sono **due**\n"
    "numeri per manipolazione, non quattro: i due livelli di erosione condividono l'84.6% dei voxel.\n"
    "L'asimmetria fra emisferi vale **1.6σ**, e a quel livello \u00e8 un'**osservazione**, non un vincolo.\n"
    "La riportiamo perch\u00e9 si ripete sotto due manipolazioni diverse e perch\u00e9 chi vorr\u00e0 spiegare il\n"
    "fattore far\u00e0 bene a guardarla \u2014 non perch\u00e9 escluda qualcosa.")

EDITS = [
    ("1. B.1: il cancello 2.3 \u00e8 σ_px, non la regola di maschera", B1A_V, B1A_N,
     "\u00e8 libero di seguire la cella** a"),
    ("2. B.1: l'ancoraggio della soglia E3", B1B_V, B1B_N,
     "il pi\u00f9 grande sistematico gi\u00e0 caratterizzato"),
    ("3. D.1: il trattamento (B) \u00e8 stato eseguito", D1_V, D1_N,
     "Il trattamento (B) \u00e8 stato ESEGUITO"),
    ("4. B.2: la deviazione con il suo σ", B2A_V, B2A_N,
     "Con quanta forza (rilievo B.2)"),
    ("5. B.2: la firma ripetuta con il suo σ", B2B_V, B2B_N,
     "una firma che si ripete, riportata con il suo σ"),
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
    if len(ok) != len(EDITS):
        fail("applicazione PARZIALE gia' presente (%s). Le cinque modifiche si "
             "muovono insieme: correggere il 2.3 in un posto e non nell'altro "
             "lascerebbe la soglia E3 ancorata a una quantita' ritirata."
             % ", ".join(done))
    n = norm(txt)
    for name, old, new, marker in EDITS:
        n = n.replace(old, new, 1)
    return n, done


def cmd_inspect(args):
    if not os.path.isfile(args.target):
        fail("bersaglio assente: %s (usa --target)" % args.target)
    txt, eol, n_crlf, n_lf = read_target(args.target)
    n = norm(txt)
    print("=== %s ===" % args.target)
    print("  sha256    : %s" % sha256_file(args.target))
    print("  righe     : %d" % len(n.splitlines()))
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
    if "## Risposta 5 \u2014 Il terzo canale" not in n:
        fail("questo patcher va DOPO paper2_risposta_finale_patch.py: la "
             "risposta 5 non c'e' ancora.")
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
    print("  %d -> %d righe, 5 modifiche"
          % (len(n.splitlines()), len(new_n.splitlines())))
    if not args.apply:
        print("  [DRY-RUN] nulla scritto. Rilancia con --apply.")
        return 0
    bak = args.target + ".prer2"
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
        ("B.1 il 2.3 e' descritto come cancello di sigma_px",
         "\u03c3_px \u00e8 libero di seguire la cella" in f),
        ("B.1 la riformulazione «regola di maschera» e' ritirata",
         "ritiriamo la nostra riformulazione" in f),
        ("B.1 il \u00a73.4 del referee NON va ritirato",
         "non va ritirato" in f),
        ("B.1 la citazione della checklist e' riportata",
         "geometria e **maschera identiche**" in n),
        ("B.1 l'ancoraggio della soglia non cita piu' la regola di maschera",
         "l'ancoraggio \u00e8 l'ambiguit\u00e0 della regola di maschera" not in f),
        # sul testo PIATTO: la frase attraversa un fine riga. Terza occorrenza
        # della stessa svista in questa sessione, e l'ultima.
        ("B.1 «sotto-dominante» e' corretto in «comparabile a»",
         "comparabile a**, non sotto-dominante" in f),
        ("D.1 il trattamento (B) risulta ESEGUITO",
         "il trattamento (b) \u00e8 stato eseguito" in f),
        ("D.1 la contraddizione precedente non c'e' piu'",
         "dichiarato e non ancora eseguito.**" not in n),
        ("D.1 ed e' segnalata invece che corretta in silenzio",
         "non \u00e8 un refuso, e la" in f),
        ("B.2 la firma e' riportata a 1.6 sigma",
         "1.6\u03c3" in n),
        ("B.2 e come UNA osservazione, non quattro",
         "una** osservazione a 1.6\u03c3, non quattro" in n),
        ("B.2 «il vincolo piu' forte» non compare piu'",
         "vincolo pi\u00f9 forte che abbiamo" not in f),
        ("B.2 l'84.6% del \u00a73.3 e' citato come ragione",
         f.count("84.6%") >= 2),
        ("il resto del documento e' intatto",
         "## Risposta 5 \u2014 Il terzo canale" in n
         and "## \u00a74.6 \u2014 Il ripattern del tiling" in n
         and "## Attesa a priori" in n),
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

    corpo = ("# Risposta\n\n## Il trasferibile\n\n" + B1A_V + "\n\n"
             "## Risposta 5 \u2014 Il terzo canale, misurato\n\ntesto\n\n"
             "## \u00a74.6 \u2014 Il ripattern del tiling\n\ntesto\n\n"
             "## Attesa a priori\n\ntesto\n\n"
             "## §3.8\n\n" + B2A_V + "\n\n"
             "## §1\n\n" + B2B_V + "\n\n"
             "## §4.1\n\n" + D1_V + "\n\n"
             "## §4.2\n\n" + B1B_V + "\n")

    with tempfile.TemporaryDirectory() as td:
        for lab, eol in (("LF", "\n"), ("CRLF", "\r\n")):
            p = os.path.join(td, "r_%s.md" % lab)
            with open(p, "wb") as fh:
                fh.write(corpo.replace("\n", eol).encode("utf-8"))
            txt, det, _, _ = read_target(p)
            chk("1%s fine riga rilevato" % lab, det == eol, repr(det))
            ok, done, bad = plan(txt)
            chk("2%s le cinque ancore sono uniche" % lab,
                len(ok) == 5 and not bad, "ok=%d bad=%s" % (len(ok), bad))
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

        p2 = os.path.join(td, "parziale.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace(B1A_V, B1A_N).encode("utf-8"))
        chk("6  applicazione parziale: si ferma",
            _exits(lambda: apply_all(read_target(p2)[0])))

        p3 = os.path.join(td, "senza5.md")
        with open(p3, "wb") as fh:
            fh.write(corpo.replace("## Risposta 5 \u2014 Il terzo canale, misurato",
                                   "## Altro").encode("utf-8"))

        class B:
            target = p3
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("7  senza la risposta 5 la patch rifiuta", _exits(lambda: cmd_patch(B())))

    chk("8  B.1: la correzione dice che la lettura del referee era giusta",
        "era quella corretta" in piatto(B1A_N))
    chk("8b B.1: e che ritiriamo NOI, non lui",
        "ritiriamo la nostra riformulazione" in piatto(B1A_N)
        and "non va ritirato" in piatto(B1A_N))
    chk("9  D.1: la correzione e' dichiarata, non silenziosa",
        "correzione, rilievo d.1" in piatto(D1_N))
    chk("10 B.2: entrambi i passaggi portano il sigma e l'84.6%",
        "1.6\u03c3" in B2A_N and "1.6\u03c3" in B2B_N
        and "84.6%" in B2A_N and "84.6%" in B2B_N)
    chk("10b B.2: nessuno dei due rivendica piu' un vincolo",
        "vincolo pi\u00f9 forte" not in piatto(B2A_N)
        and "vincolo pi\u00f9 forte" not in piatto(B2B_N))

    print("=== SELFTEST paper2_risposta_r2_patch ===")
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
    p = argparse.ArgumentParser(description="B.1, D.1 e B.2 del secondo report")
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
