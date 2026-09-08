#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
paper2_minori_patch.py - i cinque rilievi minori del secondo report, D.2-D.6.

Quattro si accettano. Uno si accetta e si CORREGGE nell'ampiezza.

D.2 e' il solo sostanziale. Il rilievo e' fondato -- il canale RSD e' misurato,
e' un'asimmetria fra i due lati, e il budget non ce l'ha -- ma i 17-25
generatori sono la risposta a togliere l'RSD al 100%. Il termine di budget e'
l'effetto del DISALLINEAMENTO fra l'ampiezza RSD del campo osservato e quella
dei mock HOD, che questo lavoro non misura. Riportare 17-25 come sistematico
equivarrebbe a dichiarare che i mock sbagliano l'RSD del 100%.

E il rilievo B.2 dello STESSO report riguarda lo stesso run: quelle differenze
valgono 1.0, 0.63, 1.27 e 1.19 sigma. Un canale misurato a ~1 sigma entra come
LIMITE SUPERIORE, non come valore.

D.4 si chiude con un numero che avevamo gia': la soglia D5c vale 28 e viene da
META' DELLA SEM PIU' PICCOLA (emendamento 36), cioe' da una proprieta'
dell'ensemble di mock e non dalla distribuzione osservata. La quarantena regge.

Una modifica sola: la sezione, prima di «Sezioni ancora aperte».
"""

from __future__ import annotations

import argparse
import hashlib
import os
import sys

DEFAULT_TARGET = "risposta_referee.md"
ANCORA = "---\n\n## Sezioni ancora aperte\n"
SEZIONE = "---\n\n## Secondo report, rilievi minori D.2–D.6 — **[SCRITTA]**\n\n### D.2 — Il canale RSD: accettato come termine, corretto nell'ampiezza\n\nIl rilievo è fondato: togliere l'RSD sposta Δ_mock del ±13%, è un'asimmetria **misurata** fra i due\nlati, e il budget a sei termini non ce l'ha. Il fatto che non spieghi il fattore 2 non la rende\ninesistente.\n\n**Ma i 17–25 generatori non sono il termine di budget.** Sono la risposta a togliere l'RSD **al\n100%**. Il termine è l'effetto del **disallineamento** fra l'ampiezza RSD del campo osservato e\nquella dei mock HOD, che è una frazione di quel 100% e che **questo lavoro non misura**. Riportare\n17–25 come sistematico equivarrebbe a dichiarare che i mock sbagliano l'RSD del 100%.\n\nLa forma corretta è un **coefficiente**:\n\n> ∂*N*_H1 / ∂(ampiezza RSD) ≈ **17–25 generatori per una variazione del 100%**, con **segno opposto\n> fra i due emisferi** — NGC risponde meno senza RSD, SGC di più.\n\nE il termine entra nel budget come **limite superiore**, non come valore, per la ragione del rilievo\nB.2 dello stesso report: le quattro differenze valgono 1.0σ, 0.63σ, 1.27σ e 1.19σ. Un canale\nmisurato a ~1σ non si somma in quadratura come se fosse noto.\n\n**Il moltiplicatore va da altrove.** Vincolare il disallineamento RSD fra DESI e i mock HOD è fuori\ndal perimetro del Paper 2 — è una calibrazione delle velocità dell'HOD — e lo dichiariamo come tale\ninvece di sceglierne un valore. Con un disallineamento del 10%, che è generoso per una calibrazione\nHOD, il termine varrebbe ~2 generatori: **più piccolo del carving**, che vale 6–8, e trascurabile\ncontro il non attribuito.\n\nIl canale esce quindi dal «cestino dei meccanismi falsificati» — dove non doveva stare — ed entra fra\ni termini **dichiarati e non quantificati**, con il suo coefficiente e la ragione per cui il\nmoltiplicatore manca.\n\n### D.3 — B6 per il limite e non per il verdetto: accettato\n\nL'uso è coerente e dichiarato nello stesso record che aggiunge il punto, quindi non è cherry-picking\n— e il report lo riconosce. Ma nel paper i due usi finiranno a due righe di distanza, e chi legge lo\nleggerà come tale se non lo si segnala.\n\n**Si segnala esplicitamente**, con la ragione: B6 dà **leva** alla domanda sulla forma e al limite\nsuperiore, e **non** entra nella classificazione perché le soglie E-erano tarate sui cinque punti\ndella linea B dichiarati in pre-registrazione. Aggiungere un punto e usarlo per il verdetto\ncambierebbe la soglia dopo aver visto il dato.\n\n### D.4 — La deroga D5c: la soglia non viene dalla distribuzione osservata\n\nIl rilievo è giusto in linea di principio: se la soglia fosse **derivata dalla** distribuzione\nosservata, la quarantena non la renderebbe pre-dichiarata, la renderebbe post-hoc con un ritardo.\n\n**Non è il caso.** La soglia D5c vale **28 posizioni clippate**, e viene da **metà della SEM più\npiccola** — 4.4 generatori — cioè da una proprietà dell'**ensemble di mock**, non dalla distribuzione\ndei clippati osservati. È l'emendamento 36 a dichiararlo. La quarantena serviva a non citare numeri\nprima che la soglia esistesse, e la soglia esiste ancorata a una quantità indipendente.\n\nLo scriviamo in chiaro perché la formulazione precedente lasciava aperte entrambe le letture, ed è\nesattamente il tipo di ambiguità che il report chiede di chiudere.\n\n### D.5 — `config_hash` non è un ancoraggio degli ingressi: accettato\n\nLa scelta di non ridefinirlo resta corretta — ridefinirlo invaliderebbe le chiavi di ripresa di tutti\ni registri esistenti. Ma il nome suggerisce ciò che non fa, e nel paper **non sarà citato come\nancoraggio degli ingressi**: solo i digest depositati lo sono.\n\nVa detto perché è la stessa classe del §3.9: un nome che promette una garanzia che il campo non dà.\n\n### D.6 — L'omogeneità va citata dove si fa l'assunzione: accettato\n\nL'argomento a 3.7σ che esclude il canale nuovo regge, e la conclusione «σ_HOD da solo = 68.1» poggia\nsull'assunzione — dichiarata — che il rumore di downsampling non dipenda dalla cosmologia, mentre i\n128.3 vengono da quattro nodi dell'ipercubo e i 108.7 dal solo fiduciale.\n\n**L'evidenza che serve l'abbiamo già**: le quattro dispersioni stanno fra 124.9 e 137.3 con\nχ² = 1.56 su 3 gradi di libertà. Quell'omogeneità **è** il test dell'assunzione, e va citata dove\nl'assunzione si fa — non dove si descrivono i nodi. Correzione di collocazione, non di sostanza, e la\nsegnaliamo come tale.\n\n"

EDITS = [
    ("1. i minori D.2-D.6", ANCORA, SEZIONE + ANCORA,
     "## Secondo report, rilievi minori D.2\u2013D.6"),
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
    for prereq, chi in (("## Secondo report, punto A", "paper2_sottrazioni_patch.py"),):
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
    bak = args.target + ".premin"
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
        ("la sezione esiste", "## Secondo report, rilievi minori D.2\u2013D.6" in n),
        ("e precede «Sezioni ancora aperte»",
         n.index("rilievi minori D.2") < n.index("## Sezioni ancora aperte")),
        ("D.2 accetta il rilievo", "il rilievo \u00e8 fondato" in f),
        # niente `A and B or C`: la precedenza rende il controllo vero per il
        # solo terzo termine. E l'enfasi sta su «**al 100%**», non su «al **100%**».
        ("ma corregge l'ampiezza: 17-25 e' il 100%, non il termine",
         ("non sono il termine di budget" in f)
         and ("togliere l'rsd **al 100%**" in f)),
        ("D.2 riporta il COEFFICIENTE, non un valore",
         "generatori per una variazione del 100%" in f),
        ("D.2 entra come LIMITE SUPERIORE, con il sigma di B.2",
         "limite superiore" in f and "1.0\u03c3, 0.63\u03c3, 1.27\u03c3 e 1.19\u03c3" in n),
        ("D.2 dichiara che il moltiplicatore manca e perche'",
         "fuori\ndal perimetro" in n or "fuori dal perimetro" in f),
        ("D.2 dice dove il canale NON deve stare",
         "cestino dei meccanismi falsificati" in f),
        ("D.3 accettato, con la ragione della non-classificazione",
         "d.3" in f and "cambierebbe la soglia dopo aver visto il dato" in f),
        ("D.4 chiuso con il numero: 28 da meta' della SEM",
         "28 posizioni clippate" in f and "met\u00e0 della sem" in f
         and "emendamento 36" in f),
        ("D.4 dice che NON viene dalla distribuzione osservata",
         "non dalla distribuzione" in f),
        ("D.5 accettato: config_hash non sara' citato come ancoraggio",
         "non sar\u00e0 citato come\nancoraggio" in n or "non sar\u00e0 citato come ancoraggio" in f),
        ("D.6 accettato: l'omogeneita' va dove si fa l'assunzione",
         "124.9 e 137.3" in n and "1.56 su 3 gradi" in f),
        ("le sezioni precedenti sono intatte",
         "## Risposta 5 \u2014 Il terzo canale" in n
         and "## Secondo report, punto A" in n),
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

    corpo = ("# Risposta\n\n## Risposta 5 \u2014 Il terzo canale, misurato\n\nt\n\n"
             "## Secondo report, punto A \u2014 **[SCRITTA]**\n\nt\n\n" + ANCORA)

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

        p2 = os.path.join(td, "senzaA.md")
        with open(p2, "wb") as fh:
            fh.write(corpo.replace("## Secondo report, punto A \u2014 **[SCRITTA]**",
                                   "## Altro").encode("utf-8"))

        class B:
            target = p2
            apply = False
            backup = False
            allow_eol_normalise = False
        chk("6  senza la sezione del punto A la patch rifiuta",
            _exits(lambda: cmd_patch(B())))

    fs = piatto(SEZIONE)
    chk("7  D.2: accetta E corregge, non fa solo una delle due",
        "il rilievo \u00e8 fondato" in fs and "non sono il termine di budget" in fs)
    chk("7b D.2: il numero corretto e' un coefficiente, con il suo segno opposto",
        "segno opposto" in fs and "per una variazione del 100%" in fs)
    chk("7c D.2: e il moltiplicatore e' dichiarato mancante",
        "questo lavoro non misura" in fs)
    chk("8  D.4 e' chiuso da un numero, non da un'opinione",
        "28 posizioni clippate" in fs and "4.4 generatori" in fs)
    chk("9  tutti e cinque i rilievi sono nominati",
        all(("### d.%d" % i) in fs for i in (2, 3, 4, 5, 6)))

    print("=== SELFTEST paper2_minori_patch ===")
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
    p = argparse.ArgumentParser(description="I rilievi minori D.2-D.6 del secondo report")
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
